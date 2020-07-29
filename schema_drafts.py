#!/usr/bin/env python3
"""
Computes for each JSON Schema document the valid drafts.
@author: Michael Fruth
"""
import logging

import jsonref

import _util as util
from _model import ExecutionSettings, GitFile, GitHistoryFile, SchemaDrafts

logger = logging.getLogger(__name__)

execution_settings = ExecutionSettings()

ORIGINAL_SCHEMA_NAME = "NORMAL"
DEREFERENCED_SCHEMA_NAME = "NORMAL_REFS"


def _check_drafts_and_add(invalid_schema_drafts: SchemaDrafts, json_content, name):
    """
    Validates the json content against each available draft. The result is stored in invalid_schema_drafts under the
    passed "name"
    :param invalid_schema_drafts: The SchemaDrafts-object which stores the information about the check
    :param json_content: The content to check
    :param name: The name under which the result of the check is stored
    :return: True if the json content is valid to at least one validator.
    """
    drafts = util.schema_validate_all_drafts(json_content)
    invalid_schema_drafts.add(name, drafts)

    if all(v is not None for v in drafts.values()):
        logger.info("End check file - abort {}: {}".format(name, invalid_schema_drafts.git_history_file.full_path))
        return False

    return True


def _multiprocessing_reset(git_history_file: GitHistoryFile, schema_drafts_result: SchemaDrafts):
    # Reset the git_history_file, because by pickling the data, the reference is removed to the "original" GitHistoryFile
    schema_drafts_result.git_history_file = git_history_file


def check_file(git_history_file: GitHistoryFile):
    """
    Checks the file for different schema drafts. The file is loaded and validated against each available draft-
    validator (Draft 3, 4 ,6 and 7). If the schema is valid to at least on draft, the schema will be derferenced and
    this schema will be checked again with each validator. If the schema is invalid to all validators in the first step,
    this check will not be performed.
    :param git_history_file: The file to check
    :param check_jsonsubschema: Whether jsonsubschema should be checked (if maybe canonicalization results an invalid schema)
    :return: A SchemaDrafts-object containing all information.
    """
    logger.info("Check file: " + git_history_file.full_path)
    schema_drafts_result = SchemaDrafts(git_history_file)

    content, json_content, encoding, error = util.load_json(git_history_file.full_path)
    if error:
        return schema_drafts_result

    # NORMAL
    if not _check_drafts_and_add(schema_drafts_result, json_content, ORIGINAL_SCHEMA_NAME):
        return schema_drafts_result

    try:
        # Dereference
        json_content_refs = jsonref.JsonRef.replace_refs(json_content)
    except Exception:
        logger.info("End check file - abort refs: {}".format(git_history_file.full_path))
        return schema_drafts_result

    # NORMAL REFS
    if not _check_drafts_and_add(schema_drafts_result, json_content_refs, DEREFERENCED_SCHEMA_NAME):
        return schema_drafts_result

    logger.info("End check file: {}".format(git_history_file.full_path))
    return schema_drafts_result


def check_schema_draft(git_file: GitFile):
    """
    Checks the schema draft of the version files of a specific root file.
    :param git_file: The root file from which the version files should be checked.
    :return: The root file and the result of the check (a list containing SchemaDraft-objects)
    """
    logger.info("Check git_file: " + git_file.path)
    result = util.multiprocess_and_set_files_later(cores=execution_settings.multiprocessing_cores,
                                                   func=check_file,
                                                   iterable=git_file.history,
                                                   use_map=True,
                                                   reset_func=_multiprocessing_reset)
    logger.info("End git_file: " + git_file.path)
    return git_file, result


def schema_drafts(output_file, git_files: [GitFile]):
    """
    Classifies each schema based on the draft and saves the result to the output file.
    :param output_file: The output file in which the result is stored.
    :param git_files: The files to check the schema drafts from
    :return: None
    """
    for git_file in git_files:
        r = check_schema_draft(git_file)
        util.append_pickle(output_file, r)


def main():
    import _arguments as args
    output_file, multiprocessing_cores, git_files, git_deleted_files = args.parse_load_file_changes(
        {
            args.CLAOutputFile: args.CLAOutputFile().required(),
            args.CLAMultiprocessingCores: args.CLAMultiprocessingCores()
        }
    )

    execution_settings.set_multiprocessing_cores(multiprocessing_cores)

    schema_drafts(output_file, git_files)


if __name__ == '__main__':
    main()
