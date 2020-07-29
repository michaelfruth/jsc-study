"""
Contains all possible command line arguments. Handles also the parsing of arguments.
@author: Michael Fruth
"""
import logging
import multiprocessing
import pickle
from argparse import ArgumentParser, ArgumentTypeError, ArgumentError
from os import path

import _arguments_filter as args_filter
import filter_filters
from _model import GitFile, SchemaDrafts, Subschema, SUBSCHEMA_IMPLEMENTATIONS


#############################################################################
# Start of methods used by the arguments parser
#############################################################################

def check_directory_exists(value):
    if not path.isdir(value):
        raise ArgumentTypeError("%s doesn't exist!" % value)
    return path.realpath(value)


def check_directory_not_exists(value):
    if path.isdir(value):
        raise ArgumentTypeError("%s already exists!" % value)
    return path.realpath(value)


def check_file_not_exists(value):
    if path.isfile(value):
        raise ArgumentTypeError("%s already exists!" % value)
    return path.realpath(value)


def check_file_exists(value):
    if not path.isfile(value):
        raise ArgumentTypeError("%s doesn't exist!" % value)
    return path.realpath(value)


def check_int_greater_0(value):
    try:
        int_value = int(value)
        if int_value < 0:
            raise ArgumentError("%d is <= 0!" % int_value)
    except ValueError:
        raise ArgumentTypeError("%s is not a number!" % value)
    return int_value


def check_process_cores(value):
    try:
        value = int(value)
        if value < 0:
            raise ArgumentTypeError("%s is invalid!" % value)
        if value == 0:
            value = multiprocessing.cpu_count()
            if value <= 0:
                value = 1
        return value
    except ValueError:
        raise ArgumentTypeError("%s is not a number!" % value)


#############################################################################
# End of methods used by the arguments parser
#############################################################################

#############################################################################
# Start of CLA classes
#############################################################################

class CLA:
    """
    The base class for all command-line-arguments (CLA). Every possible argument inherits from this class.

    arguments:
    The property "arguments" contains the arguments for the command line parser (Type ArgumentParser).
    "dest" (parser.add_argument(dest=...) must not be added, because this will be overridden from the property destination.

    self.destination:
    The property "destination" is a tuple and contains the flags for the parser and as last argument the "dest".
    E.g. destination = ('-v', '--verbose', 'verbose') means:
    The flags '-v' and '--verbose' can be used in terminal. 'verbose' is used as "dest".

    self.value:
    After parsing the arguments from the user (terminal), the value of the user is safed in this variable.
    """

    arguments = {}

    def __init__(self):
        self.destination: () = None
        self.value = None
        self._do_nothing = False

    def get_destination(self):
        """
        :return: The "dest" property added to the parser.
        """
        return self.destination[-1]

    def add(self, parser):
        """
        Adds itself to the specified parser.
        :param parser: The parser to which arguments should be added.
        :return: None.
        """
        if self.destination is None:
            raise ValueError("destination is not set!")
        if self.arguments is None:
            raise ValueError("arguments is not set!")

        *flags, dest = self.destination  # First x arguments are flags, last argument is the destination for the parser
        # Add "dest" from destination
        self.arguments['dest'] = dest
        parser.add_argument(*flags, **self.arguments)

    def required(self):
        """
        Adds the required property to the arguments.
        :return: self to support a fluent API.
        """
        self.arguments['required'] = True
        return self

    def do_nothing(self):
        """
        Sets an internal flag to do nothing when do() is called.
        :return: self to support a fluent API.
        """
        self._do_nothing = True
        return self

    def load_value(self, args):
        """
        Loads the value from the args (args is the result from parser.parse_args()) into self.value.
        :param args: The parsed data from the parser (:ArgumentParser)
        :return: None
        """
        if self.value is None:
            # Load value only if it is not set
            self.value = getattr(args, self.get_destination())

    def do(self, data, **kwargs):
        """
        Executes some operations on the given data. The executed operation depends on the specific implementation. Nothing will be done if do_nothing() was called before.
        This method should not be overwritten. Overwrite _do() instead in the specific classes.
        :param data: The data on which operations are executed.
        :param kwargs: Arguments
        :return: None
        """
        if self._do_nothing:
            return
        if self.value is not None:
            self._do(data, **kwargs)

    def _do(self, data, **kwargs):
        """
        The internal method which really executes the operation on the given data.
        :param data: The data on which operations are executed.
        :param kwargs: Arguments
        :return:
        """
        pass


class CLAGroup(CLA):
    """
    Base class for mutually exclusive groups. The arguments for the group is stored in self.clas. This list contains only CLA-objects.

    The base-methods of CLA are overwritten to support the group. Most of the methods from the base-class CLA are forwarded to the arguments.
    """
    _required = False

    def __init__(self):
        super().__init__()
        self.arguments = None

        self.clas = []

    def required(self):
        # Save an internal flag and do not call required on the clas, because only the group should be required, not every single argument.
        self._required = True
        return self

    def load_value(self, args):
        for cla in self.clas:
            cla.load_value(args)
        self.value = [cla.value for cla in self.clas]

    def do_nothing(self):
        for cla in self.clas:
            cla.do_nothing()
        return self

    def add(self, parser):
        group = parser.add_mutually_exclusive_group(required=self._required)

        for cla in self.clas:
            cla.add(group)

    def do(self, data, **kwargs):
        for cla in self.clas:
            cla.do(data, **kwargs)


class _CLAVerbose(CLA):
    arguments = {
        'help': 'Prints logging information for logging.LEVEL=INFO',
        'action': 'store_true'
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-v', '--verbose', 'verbose')


class CLAShowFiles(CLA):
    arguments = {
        'help': 'Outputs the path of the invalid files.',
        'action': 'store_true'
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-show-files', 'show_files')


class CLAGitValidate(CLA):
    arguments = {
        'help': 'When computing the difference of the files of two directories, this is an extra check that no directory is missing. Specify the path to the root-directory (the bare_master).',
        'type': check_directory_exists
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-val', '--validate', 'validate')


class CLAGitRepo(CLA):
    arguments = {
        'help': 'The path or url to the git repository.',
        'type': str
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-g', '--git-repository', 'git_repository')


class CLAOutputDirectory(CLA):
    arguments = {
        'help': 'The output directory, in which the output is saved.',
        'type': check_directory_not_exists
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-od', '--output-directory', 'output_directory')


class CLAOutputFile(CLA):
    arguments = {
        'help': 'The file in which the output is stored.',
        'type': check_file_not_exists
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-o', '--output-file', 'output_file')


class CLAPathsFilter(CLA):
    arguments = {
        'help': "Filters all files that does not start with the paths specified. The filter is applied to the path-filenames instead of the full-path-filename. E.g. src/schemas/json/tsconfig.json instead of /Users/.../src/schemas/json/tsconfig.json.",
        'nargs': '+'
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-p', '--paths', 'paths')

    def _do(self, data, **kwargs):
        """
        GitFiles will be filtered based on their path. Only GitFiles matching the path will remain.
        :param data: [GitFile]
        :param kwargs: Nothing recognized.
        :return: None.
        """
        # Filter files based on their path.
        for d in data[:]:
            if not d.path.startswith(tuple(self.value)):
                data.remove(d)


class CLACommitDirectory(CLA):
    arguments = {
        'help': 'The path to the directory that contains all the version-directories.',
        'type': check_directory_exists
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-c', '--commit-directory', 'commit_directory')

    def _do(self, data, **kwargs):
        """
        Sets the full_path for all GitHistoryFiles. git_history_file_extraction_func will be used if set, otherwise it is assumend that data has following structure: [[GitFile], []]
        :param data: Any
        :param kwargs: If property "git_history_file_extraction_func" is set, it will be used. The data is passed to the function and it should return a list containing all GitHistoryFiles.
        :return: None.
        """
        git_history_file_extraction_func = kwargs['git_history_file_extraction_func']
        if git_history_file_extraction_func is None:
            [h.set_full_path(self.value) for f in data for h in f[0].history]
        else:
            history_files = git_history_file_extraction_func(data)
            [h.set_full_path(self.value) for h in history_files]


class CLANumberFilesFilter(CLA):
    arguments = {
        'help': "The number of data to be taken. E.g. a list with a total of 3 entries is loaded and '-n 2' is specified, only the first two entries will be taken.",
        'type': check_int_greater_0
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-n', '--number-files', 'number_files')

    def _do(self, data, **kwargs):
        del data[self.value:]


class CLASkipFilesFilter(CLA):
    arguments = {
        'help': "The number of data to be skipped. E.g. a list with a total of 3 entries is loaded and '-s 1' is specified, the first entrie will be skipped and only the last two entries will be taken.",
        'type': check_int_greater_0
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-s', '--skip-files', 'skip_files')

    def _do(self, data, **kwargs):
        del data[:self.value]


class CLADraftFilterOnTheFlyFilter(CLA):
    arguments = {
        'help': "Filters the data based on the specified filter. The data is filtered on startup, so its very time consuming. Use 'filter-file' if possible.",
        'choices': filter_filters.DRAFT_FILTERS.keys()
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-filter-on-the-fly', 'filter_on_the_fly')
        self.draft_filter = None

    def load_value(self, args):
        super().load_value(args)
        if self.value is not None:
            # Set the filter to avoid loading it multiple times.
            self.draft_filter = filter_filters.DRAFT_FILTERS[self.value]

    def _do(self, data, **kwargs):
        """
        Filters the data based on the passed filter from the arguments.
        :param data: The data to filter.
        :param kwargs: Property "filter_func" must be set. This is should be a function from the module _arguments_filter.
        :return: None.
        """
        filter_func = kwargs['filter_func']
        filter_func(self.draft_filter, data)


class CLADraftFilterFileFilter(CLA):
    arguments = {
        'help': "Filters the data based on the specified filter. The path to the filter must be specified.",
        'type': check_file_exists,
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-filter-file', 'filter_file')
        self.draft_filter = None

    def load_value(self, args):
        super().load_value(args)
        if self.value is not None:
            # Set the filter to avoid loading it multiple times.
            with open(self.value, 'rb') as f:
                self.draft_filter = pickle.load(f)

    def _do(self, data, **kwargs):
        """
        Filters the data based on the passed filter-file from the arguments.
        :param data: The data to filter.
        :param kwargs: Property "filter_func" must be set. This is should be a function from the module _arguments_filter.
        :return: None.
        """
        filter_func = kwargs['filter_func']
        filter_func(self.draft_filter, data)


class CLADraftFilterGroup(CLAGroup):

    def __init__(self):
        super().__init__()
        self.clas = [
            CLADraftFilterOnTheFlyFilter(),
            CLADraftFilterFileFilter()
        ]


class CLAMultiprocessingCores(CLA):
    arguments = {
        'help': "Specify the number of cores used for multiprocessing. 0 denotes the available cores on the machine.",
        'type': check_process_cores,
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-m', '--multiprocess-cores', 'multiprocess_cores')


class CLASelfCheck(CLA):
    arguments = {
        'help': "Do a sanity-/self-check (comparing each file against itself).",
        'action': 'store_true'
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-self', 'self_check')


class CLAInputFile(CLA):
    arguments = {
        'help': "The file which contains the data.",
        'type': check_file_exists
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-f', '--input-file', 'input_file')


class CLAInputFile2(CLAInputFile):
    def __init__(self):
        super().__init__()
        self.destination = ('-f2', '--input-file2', 'input_file2')


class CLASubschemaImplementations(CLA):
    arguments = {
        'help': "Specify the implementation which should be used for subschema containment.",
        'choices': SUBSCHEMA_IMPLEMENTATIONS.keys()
    }

    def __init__(self):
        super().__init__()
        self.destination = ('-si', '--subschema-implementation', 'subschema_implementation')
        self.subschema_implementation = None

    def load_value(self, args):
        super().load_value(args)
        if self.value is not None:
            self.subschema_implementation = SUBSCHEMA_IMPLEMENTATIONS[self.value]


#############################################################################
# End of CLA classes
#############################################################################

#############################################################################
# Start of the default arguments
#############################################################################
def default_args_filter():
    return {
        CLAInputFile: CLAInputFile().required(),
        CLACommitDirectory: CLACommitDirectory().required()
    }


def default_args_file_changes():
    return {
        CLAInputFile: CLAInputFile().required(),
        CLAPathsFilter: CLAPathsFilter().required(),
        CLACommitDirectory: CLACommitDirectory().required(),
        CLASkipFilesFilter: CLASkipFilesFilter(),
        CLANumberFilesFilter: CLANumberFilesFilter(),
        CLADraftFilterGroup: CLADraftFilterGroup()
    }


def default_args_detailed_data():
    return {
        CLAInputFile: CLAInputFile().required(),
        CLACommitDirectory: CLACommitDirectory().required(),
        CLASkipFilesFilter: CLASkipFilesFilter(),
        CLANumberFilesFilter: CLANumberFilesFilter(),
        CLADraftFilterGroup: CLADraftFilterGroup()
    }


#############################################################################
# End of the default arguments
#############################################################################

#############################################################################
# Start of the methods parsing, loading and processing the arguments
#############################################################################

def _parse_load_detailed_data(filter_func,
                              expected_default_args: {} = None,
                              default_args: {} = None,
                              input_args: {} = None,
                              verbose=True,
                              is_files_change=False,
                              git_history_file_extraction_func=None):
    """
    Parses the arguments from the command line and loads all values set by the user. It is assumed that the default_args contains CLAInputFile and that this file is set.
    The input file is loaded and will be processed by the passed arguments. E.g. the data is filtered if a filter is set.

    :param filter_func: The function to filter the data, when the user has a filter specified.
    :param expected_default_args: The expected default_args, used when the passed default_args from outside is None.
    :param default_args: The default_args passed from outside. If this is None, arguments from default_args_detailed_data() will be used.
    :param input_args: The arguments passed from outside which should be added to the default arguments.
    :param verbose: If verbose output should be printed.
    :param is_files_change: If produced data from the module git_extract_file_changes is loaded.
    :param git_history_file_extraction_func: The function to extract the GitHistoryFiles out of the loaded data.
    :return:
    """
    if expected_default_args is None:
        expected_default_args = default_args_detailed_data()
    if default_args is None:
        default_args = expected_default_args

    if input_args is None:
        input_args = {}

    # Parse and load all arguments
    parse_load(input_args, default_args, verbose=verbose)

    # Load input data
    cla_input_file = default_args[CLAInputFile]
    input_file_path = cla_input_file.value

    git_files_data = process_input_file(input_file_path,
                                        default_args,
                                        input_args,
                                        filter_func,
                                        git_history_file_extraction_func,
                                        is_files_change)

    # Get all values from the passed arguments from outside
    values = [cla.value for cla in input_args.values()]

    if is_files_change:
        # Data = ([], []); data[0] = git_files; data[1] = git_deleted_files
        return (*values, git_files_data[0], git_files_data[1])
    else:
        if len(values) == 0:
            return git_files_data
        return (*values, git_files_data)


def process_input_file(input_file_path, default_args, input_args, filter_func,
                       git_history_file_extraction_func=None, is_files_change=False):
    """
    Processes the input file based on the passed arguments.
    :param input_file_path: The path to the input file (pickled data).
    :param default_args: The default_args.
    :param input_args: The arguments from outside.
    :param filter_func: The function to filter the data.
    :param git_history_file_extraction_func: The function which extracts all GitHistoryFiles out of the loaded data.
    :param is_files_change: If produced data from the module git_extract_file_changes is loaded.
    :return: the loaded data from the input_file_path
    """
    with open(input_file_path, 'rb') as f:
        git_files_data = pickle.load(f)

    # Prepare kwargs for do() of the clas.
    do_args = {
        'filter_func': filter_func,
        'git_history_file_extraction_func': git_history_file_extraction_func
    }

    cla_values = list(default_args.values())
    cla_values.extend(input_args.values())

    # Process data based on the CLAs set and their specific do() implementation
    cla: CLA
    for cla in cla_values:
        if is_files_change:
            cla.do(git_files_data[0], **do_args)  # git_files
            cla.do(git_files_data[1], **do_args)  # git_deleted_files
        else:
            cla.do(git_files_data, **do_args)

    return git_files_data


def parse_load_filter(arguments: {} = None, default_args: {} = None,
                      verbose=True) -> filter_filters.FileDraftFilter:
    return _parse_load_detailed_data(args_filter.filter_subschemas,
                                     input_args=arguments,
                                     expected_default_args=default_args_filter(),
                                     default_args=default_args,
                                     verbose=verbose,
                                     git_history_file_extraction_func=lambda data: [h for h in data.invalid_files])


def parse_load_subschemas(arguments: {} = None, default_args: {} = None, verbose=True) -> [GitFile, [Subschema]]:
    return _parse_load_detailed_data(args_filter.filter_subschemas,
                                     input_args=arguments,
                                     default_args=default_args,
                                     verbose=verbose)


def parse_load_schema_drafts(arguments: {} = None, default_args: {} = None, verbose=True) -> [GitFile, [SchemaDrafts]]:
    return _parse_load_detailed_data(args_filter.filter_schema_drafts,
                                     input_args=arguments,
                                     default_args=default_args,
                                     verbose=verbose)


def parse_load_file_changes(arguments: {} = None, default_args: {} = None, verbose=True) -> [
    [GitFile], [GitFile]]:
    return _parse_load_detailed_data(args_filter.filter_git_files,
                                     input_args=arguments,
                                     default_args=default_args,
                                     expected_default_args=default_args_file_changes(),
                                     verbose=verbose, is_files_change=True,
                                     git_history_file_extraction_func=lambda data: [h for f in data for h in f.history])


def parse_load(arguments: {}, default_arguments: {} = None, verbose=True):
    """
    Creates an argsparse.ArgumentsParser and adds all arguments (CLA.add(parser)) from the passed arguments and default_arguments.
    Afterwards, the arguments are parsed and all values are loaded into the passed arguments from the result of the parser.

    :param arguments: The arguments to parse.
    :param default_arguments: The default arguments to parse.
    :param verbose: If the output should be verbose.
    :return: None
    """
    if arguments is None:
        arguments = {}
    if default_arguments is None:
        default_arguments = {}

    keys_a = set(arguments.keys())
    keys_b = set(default_arguments.keys())
    intersection = keys_a & keys_b
    # Intersection must be empty - otherwise there are overlapping keys and overlapping keys results in overlapping dest's for the parser.
    if len(intersection) != 0:
        raise ValueError(
            "Argument was specified multiple times! \narguments: {}\ndefault_arguments: {}".format(keys_a, keys_b))

    parser = ArgumentParser()

    cla: CLA
    cla_values = list(arguments.values())
    cla_values.extend(default_arguments.values())
    # Add each cla to the parser
    for cla in cla_values:
        cla.add(parser)

    if verbose:
        cla_verbose = _CLAVerbose()
        cla_verbose.add(parser)

    args = parser.parse_args()

    # Load all values
    for cla in cla_values:
        cla.load_value(args)

    if getattr(args, cla_verbose.get_destination()):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s,%(msecs)d | %(name)s | %(levelname)s | %(message)s',
                            datefmt='%d.%m.%Y %H:%M:%S')
        # Remove verbose from the args - the verbose value shouldn't be seen by anyone.
        delattr(args, cla_verbose.get_destination())

#############################################################################
# End of the methods parsing, loading and processing the arguments
#############################################################################
