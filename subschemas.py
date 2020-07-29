import logging

import _util as util
from _model import ExecutionSettings, GitFile, GitHistoryFile, Subschema

logger = logging.getLogger(__name__)

execution_settings = ExecutionSettings()


def _compute_subschema(s1: GitHistoryFile, s2: GitHistoryFile):
    """
    Computes the schema containment of the given files. The implementation, which is set at the subschema_factory, is
    used.
    :param s1: The first file to check for the containment
    :param s2: The second file to check for the containment
    :return: A subschema-object containing the result of the containment check.
    """
    return execution_settings.subschema_factory(s1, s2)


def _multiprocessing_reset(s1: GitHistoryFile, s2: GitHistoryFile, result_subschema: Subschema):
    # Reset the references to the original GitHistoryFiles (multiprocessing destroyed the references)
    result_subschema.s1 = s1
    result_subschema.s2 = s2


def _subschema_file(git_file: GitFile):
    """
    Checks the containment of the version-files of a given root file.
    :param git_file: The root file containing the version files.
    :return: The Subschema-objects
    """
    git_history = git_file.history

    subschema_pairs = []
    for i in range(len(git_history)):
        if execution_settings.self_check:
            # Self check
            subschema_pairs.append((git_history[i], git_history[i]))
        else:
            # Successive check
            if i + 1 < len(git_history):
                subschema_pairs.append((git_history[i], git_history[i + 1]))

    subschemas = util.multiprocess_and_set_files_later(cores=execution_settings.multiprocessing_cores,
                                                       func=_compute_subschema,
                                                       iterable=subschema_pairs,
                                                       reset_func=_multiprocessing_reset)

    return subschemas


def subschemas(output_file, git_files: [GitFile]):
    """
    Computes the containment of the given files.
    :param output_file: The output file in which the result is stored.
    :param git_files: The files to check.
    :return: None
    """
    git_file: GitFile
    for git_file in git_files:
        logger.info("Check overall git file: %s" % git_file.path)

        schemas = _subschema_file(git_file)
        util.append_pickle(output_file, (git_file, schemas))

        logger.info("Finished overall git file: %s" % git_file.path)


def main():
    import _arguments as args
    cla_subschema_implementation = args.CLASubschemaImplementations().required()
    output_file, multiprocessing_cores, self_check, _, git_files, git_deleted_files = args.parse_load_file_changes(
        {
            args.CLAOutputFile: args.CLAOutputFile().required(),
            args.CLAMultiprocessingCores: args.CLAMultiprocessingCores(),
            args.CLASelfCheck: args.CLASelfCheck(),
            args.CLASubschemaImplementations: cla_subschema_implementation
        }
    )

    execution_settings.set_multiprocessing_cores(multiprocessing_cores)
    execution_settings.set_self_check(self_check)
    execution_settings.set_subschema_factory(cla_subschema_implementation.subschema_implementation)

    subschemas(output_file, git_files)


if __name__ == '__main__':
    main()
