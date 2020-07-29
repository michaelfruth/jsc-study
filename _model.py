"""
Copyright (C) 2020  Michael Fruth
"""
import logging
from os import path

import _util as util
import _util_subschema as subschema_util

logger = logging.getLogger(__name__)


class ExecutionSettings:
    """
    Settings for the execution of a script. This class can be used by the scripts to set and save some settings.

    Use the set-methods to set a value because they check for invalid input.
    """

    def __init__(self):
        self.set_subschema_factory(None)
        self.set_multiprocessing_cores(None)
        self.set_self_check(None)

    def set_subschema_factory(self, factory):
        self.subschema_factory = factory

    def set_multiprocessing_cores(self, value):
        self.multiprocessing_cores = value
        if self.multiprocessing_cores is None or self.multiprocessing_cores < 0:
            self.multiprocessing_cores = 1

    def set_self_check(self, value):
        self.self_check = value
        if self.self_check is None or not isinstance(self.self_check, bool):
            self.self_check = False


#############################################################################
# Start of classes that represent a file and all its versions
#############################################################################

class GitHistoryFile(object):
    """
    A GitHistoryFile is the version of a file. This class contains the SHA of the commit/respository, the old and new
    path (based on difference of the commit), the changed type (see git diff documentation for the different types)
    as well as the commit count (indicates the number of commits made to the repository in which the file resides).
    """

    def __init__(self, sha, old_path, new_path, change_type, commit_count):
        self.sha = sha

        self.old_path = old_path
        self.new_path = new_path

        self.change_type = change_type

        self.commit_count = commit_count

    def schema_tag(self):
        """
        Loads the JSON Schema document and returns the specified schema tag ($schema).
        :return:
        """
        if not hasattr(self, '_schema_tag'):
            self._schema_tag = util.schema_tag(util.load_json(self.full_path)[1])
        return self._schema_tag

    def set_full_path(self, commit_directory):
        """
        Sets the full path to the file. E.g. commit_directory = /Users/.../JSStore/commits/
        :param commit_directory: The directory in which the file resides.
        :return:
        """
        self.full_path = self._full_path(commit_directory)

    def _full_path(self, commit_directory):
        file_directory = util.commit_directory_name(self.commit_count, self.sha)
        file_path = self.new_path
        if not file_path:
            file_path = self.old_path

        return path.join(commit_directory, file_directory, file_path)

    def __str__(self):
        return "Old: %s | New: %s | Type: %s | Count: %d | SHA: %s" % (
            self.old_path, self.new_path, self.change_type, self.commit_count, self.sha)

    def __eq__(self, other):
        return (
                self.__class__ == other.__class__
                and self.sha == other.sha
                and self.new_path == other.new_path
                and self.old_path == other.old_path)


class GitFile(object):
    """
    This class contains all versions of one specific file.
    The hierarchy is as follows:
    GitFile (tsconfig.json)
        GitHistoryFile (tsconfig.json Version 1)
        GitHistoryFile (tsconfig.json Version 2)
    GitFile (tslint.json)
        GitHistoryFile (tslint.json Version 1)
        ...
    """

    def __init__(self, file_path, added_sha):
        self.path = file_path
        self.added_sha = added_sha
        self.deleted_sha = None
        self.history: [GitHistoryFile] = []

    def add_history(self, history_file: GitHistoryFile):
        self.history.append(history_file)

    def __str__(self):
        out = "%s | Added: %s | Deleted: %s | History:" % (self.path, self.added_sha, self.deleted_sha)
        if len(self.history) == 0:
            out += " --"
        for h in self.history:
            out += "\n\t" + str(h)
        return out


#############################################################################
# End of classes that represent a file and all its versions
#############################################################################

#############################################################################
# Start of classes for specific analysis
#############################################################################
class SchemaDrafts:
    """
    Contains all information about the drafts of a JSON document.
    """

    def __init__(self, git_history_file: GitHistoryFile):
        self.git_history_file: GitHistoryFile = git_history_file

        # Structure: {<key>: {<draft>: None|Exception}}
        self.drafts = {}

    def add(self, key, drafts):
        if key in self.drafts:
            raise ValueError("Key {} already exists".format(key))
        self.drafts[key] = drafts


class SubschemaComparison(object):
    """
    Contains all information about the containment check of two files. This is only a check of one! direction.
    E.g. a \subset b OR b \subset a
    """

    def __init__(self, is_subset, is_subset_exception, start_time, end_time):
        self.is_subset = is_subset  # True = is subset; False = is not subset; None = failure
        self.is_subset_exception = is_subset_exception  # The exception if is_subset is None

        self.start_time = start_time  # Start (in seconds)
        self.end_time = end_time  # End (in seconds)
        self.duration = end_time - start_time


class Subschema(object):
    """
    Contains all information about the containment check of two files.
    """

    def __init__(self, s1: GitHistoryFile, s2: GitHistoryFile):
        self.s1: GitHistoryFile = s1
        self.s2: GitHistoryFile = s2

        # This should be set by the specific implementation
        self.s1_compare_s2: SubschemaComparison = None
        self.s2_compare_s1: SubschemaComparison = None

    def __str__(self):
        return "#" * 10 + " SUBSCHEMA " + "#" * 10 + "\n" + \
               "File 1: {}\nFile 2: {}\n" \
               "1 <: 2: {}\n 2 <: 1: {}\n" \
               "Duration (s) 1 <: 2: {}\nDuration (s) 2 <: 1: {}\n" \
               "Exc 1 <: 2: {}\nExc 2 <: 1: {}".format(
                   self.s1.full_path,
                   self.s2.full_path,
                   self.s1_compare_s2.is_subset, self.s2_compare_s1.is_subset,
                   self.s1_compare_s2.duration, self.s2_compare_s1.duration,
                   self.s1_compare_s2.is_subset_exception, self.s2_compare_s1.is_subset_exception
               )


class _NpmJsonSchemaDiffValidator(Subschema):
    """
    Contains all information about the containment check of two files using json-schema-diff-validator.
    https://www.npmjs.com/package/json-schema-diff-validator
    """

    def __init__(self, s1: GitHistoryFile, s2: GitHistoryFile):
        super().__init__(s1, s2)

        self.s1_compare_s2 = subschema_util.npm_json_schema_diff_validator(s1.full_path, s2.full_path)
        self.s2_compare_s1 = subschema_util.npm_json_schema_diff_validator(s2.full_path, s1.full_path)


class _NpmIsJsconSchemaSubsetSubschema(Subschema):
    """
    Contains all information about the containment check of two files using is-json-schema-subset
    https://www.npmjs.com/package/is-json-schema-subset
    """

    def __init__(self, s1: GitHistoryFile, s2: GitHistoryFile):
        super().__init__(s1, s2)

        self.s1_compare_s2 = subschema_util.npm_is_json_schema_subset(s1.full_path, s2.full_path)
        self.s2_compare_s1 = subschema_util.npm_is_json_schema_subset(s2.full_path, s1.full_path)


class _PythonJsonsubschemaSubschema(Subschema):
    """
    Contains all information about the containment check of two files using jsonsubschema.
    https://github.com/IBM/jsonsubschema
    """

    def __init__(self, s1: GitHistoryFile, s2: GitHistoryFile):
        super().__init__(s1, s2)

        self.s1_compare_s2 = subschema_util.python_jsonsubschema(s1.full_path, s2.full_path)
        self.s2_compare_s1 = subschema_util.python_jsonsubschema(s2.full_path, s1.full_path)


#############################################################################
# End of classes for specific analysis
#############################################################################

# This can be used in the arguments for choices and to set the subschema_factory in the execution_settings.
# Contains the specific implementations for the subschema containment check

FACTORY_NPM_IS_JSON_SCHEMA_SUBSET = 'NPMIsJsonSchemaSubset'
FACTORY_NPM_JSON_SCHEMA_DIFF_VALIDATOR = 'NPMJsonSchemaDiffValidator'
FACTORY_PYTHON_JSONSUBSCHEMA = 'PythonJsonsubschema'

SUBSCHEMA_IMPLEMENTATIONS = {
    FACTORY_NPM_IS_JSON_SCHEMA_SUBSET: _NpmIsJsconSchemaSubsetSubschema,
    FACTORY_PYTHON_JSONSUBSCHEMA: _PythonJsonsubschemaSubschema,
    FACTORY_NPM_JSON_SCHEMA_DIFF_VALIDATOR: _NpmJsonSchemaDiffValidator
}
