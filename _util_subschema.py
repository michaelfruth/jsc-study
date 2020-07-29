"""
Helper functions for the schema containment check.
@author: Michael Fruth
"""
import logging
import subprocess
import time
from os import path

import jsonsubschema

import _util as util

logger = logging.getLogger(__name__)

SYM_EQUAL = '≡'
SYM_SUBSET = '⊂'
SYM_SUPERSET = '⊃'
SYM_FAIL = '⟂'
SYM_NOTHING = '∥'


def create_symbol_map(func):
    """
    Creates a map with the symbol as key and applies func() as value.
    :param func: The function which returns the initial value of the keys of the dictionary.
    :return: A dictionary.
    """
    return {
        SYM_EQUAL: func(),
        SYM_SUBSET: func(),
        SYM_SUPERSET: func(),
        SYM_FAIL: func(),
        SYM_NOTHING: func()
    }


def get_name_for_symbol(symbol):
    if symbol == SYM_EQUAL:
        return "Equal " + symbol
    elif symbol == SYM_SUBSET:
        return "Subschema " + symbol
    elif symbol == SYM_SUPERSET:
        return "Superschema " + symbol
    elif symbol == SYM_FAIL:
        return "Fail " + symbol
    elif symbol == SYM_NOTHING:
        return "Nothing " + symbol
    else:
        raise ValueError("Unrecognized symbol {}".format(symbol))


def get_symbol(subschema):
    if subschema.s1_compare_s2.is_subset is True and subschema.s2_compare_s1.is_subset is True:
        # S1 \sub S2 and S2 \sub S1 -> EQUAL
        return SYM_EQUAL
    if subschema.s1_compare_s2.is_subset is None or subschema.s2_compare_s1.is_subset is None:
        # S1 \fail S2 or S2 \fail S1 -> FAILURE
        return SYM_FAIL
    if subschema.s1_compare_s2.is_subset is True and subschema.s2_compare_s1.is_subset is False:
        # S1 \sub S2 and S2 \nothing S1 -> SUBSET
        return SYM_SUBSET
    if subschema.s1_compare_s2.is_subset is False and subschema.s2_compare_s1.is_subset is True:
        # S1 \nothing S2 and S2 \sub S1 -> SUPERSET
        return SYM_SUPERSET
    if subschema.s1_compare_s2.is_subset is False and subschema.s2_compare_s1.is_subset is False:
        # S1 \nothing S2 and S2 \nothing S1 -> NOTHING
        return SYM_NOTHING

    raise ValueError("This should not happen...\n{}".format(subschema))


def npm_json_schema_diff_validator(path1, path2):
    """
    The execution of the containment check using json-schema-diff-validator. The containment is only checked in one!
    direction (path1 \sub path2).
    :param path1: Path to the first file.
    :param path2: Path to the second file.
    :return: SubschemaComparison containing the information of the containment check.
    """
    logger.info("Compare S1 %s sub S2 %s by NPM-json-schema-diff-validator" % (path1, path2))
    process_output = _execute_npm_json_schema_diff_validator(path1, path2)  # Call/Execute the tool.
    logger.info("End compare S1 %s sub S2 %s by NPM-json-schema-diff-validator" % (path1, path2))

    # Process the tool specific output
    return _process_output_from_npm_json_schema_diff_validator(process_output)


def _process_output_from_npm_json_schema_diff_validator(process_result):
    """
    Parses the output of the tool json-schema-diff-validator.
    :param process_result: The output of the tool
    :return: A object of SubschemaComparison containing all information about the containment check.
    """
    from _model import SubschemaComparison
    # Read the output printed to console of the tool
    process_output = process_result.stdout.decode('utf-8')
    lines = process_output.splitlines()

    """
    Example-Output:
    
    Success:
    >>>>>>>>>>>>>
    OK
    1595925143.59
    1595925143.592
    <<<<<<<<<<<<<<

    Failure:
    >>>>>>>>>>>>>
    Exception
    AssertionError [ERR_ASSERTION]: The schema is not backward compatible. Difference include breaking change = [{"op":"add","path":"/type","value":"string"}]
    1595925145.826
    1595925145.828
    <<<<<<<<<<<<<<
    """

    start_time = float(lines[-2]) / 1000
    end_time = float(lines[-1]) / 1000
    lines = lines[:-2]  # Remove start/end line

    sub_exception = None
    if lines[0] == 'OK':
        is_sub = True
    elif lines[0] == 'Exception':
        is_sub = None

        error_type = None
        if len(lines) >= 2:
            # Use first word of error message as exception type
            # E.G. AssertionError [ERR_ASSERTION]: The schema is not ...
            # "AssertionError" is used as exception type
            splitted = lines[1].split()
            if len(splitted) > 0:
                error_type = splitted[0]
        sub_exception = (error_type, "\n".join(lines[1:]))
    else:
        raise ValueError("Invalid output from npm " + process_output)

    return SubschemaComparison(is_sub, sub_exception, start_time, end_time)


def _execute_npm_json_schema_diff_validator(path1, path2):
    npm_path = path.abspath(path.join(path.dirname(path.realpath(__file__)), 'tools/npm-json-schema-diff-validator'))
    result = subprocess.run(['node', '-r', 'esm', 'cli.js', path1, path2], stdout=subprocess.PIPE,
                            cwd=npm_path)
    return result


def npm_is_json_schema_subset(path1, path2):
    """
    The execution of the containment check using is-json-schema-subset. The containment is only checked in one!
    direction (path1 \sub path2).
    :param path1: Path to the first file.
    :param path2: Path to the second file.
    :return: SubschemaComparison containing the information of the containment check.
    """
    logger.info("Compare S1 %s sub S2 %s by NPM-is-json-schema-subset" % (path1, path2))
    process_output = _execute_npm_is_json_schema_subset(path1, path2)  # Call/Execute the tool.
    logger.info("End compare S1 %s sub S2 %s by NPM-is-json-schema-subset" % (path1, path2))

    return _process_output_from_npm_is_json_schema_subset(process_output)


def _execute_npm_is_json_schema_subset(path1, path2):
    npm_path = path.abspath(path.join(path.dirname(path.realpath(__file__)), 'tools/npm-is-json-schema-subset'))
    result = subprocess.run(['node', '-r', 'esm', 'cli.js', path1, path2], stdout=subprocess.PIPE,
                            cwd=npm_path)
    return result


def _process_output_from_npm_is_json_schema_subset(process_result):
    """
    Parses the output of the tool is-json-schema-subset.
    :param process_result: The output of the tool
    :return: A object of SubschemaComparison containing all information about the containment check.
    """
    from _model import SubschemaComparison
    process_output = process_result.stdout.decode('utf-8')
    lines = process_output.splitlines()

    """
    Example output:
    
    Success:
    >>>>>>>>>>>>>
    OK
    1595925736.52
    1595925736.544
    <<<<<<<<<<<<<
    
    No-Success:
    >>>>>>>>>>>>>
    Fail
    1595925657.538
    1595925657.575
    <<<<<<<<<<<<<
    
    Failure:
    >>>>>>>>>>>>>
    Exception
    RangeError: Maximum call stack size exceeded
    1595925798.553
    1595925798.956
    <<<<<<<<<<<<<
    """

    start_time = float(lines[-2]) / 1000
    end_time = float(lines[-1]) / 1000
    lines = lines[:-2]  # Remove the start/end line

    sub_exception = None
    if lines[0] == 'OK':
        is_sub = True
    elif lines[0] == 'Fail':
        is_sub = False
    elif lines[0] == 'Exception':
        is_sub = None

        error_type = None
        if len(lines) >= 2:
            # Use first word of error message as exception type
            # E.G. ResolverError: Error opening file ...
            # ResolveError: is used as exception type
            splitted = lines[1].split()
            if len(splitted) > 0:
                error_type = splitted[0]
        sub_exception = (error_type, "\n".join(lines[1:]))
    else:
        raise ValueError("Invalid output from npm " + process_output)

    return SubschemaComparison(is_sub, sub_exception, start_time, end_time)


def python_jsonsubschema(path1, path2):
    """
    The execution of the containment check using jsonsubschema. The containment is only checked in one!
    direction (path1 \sub path2).
    :param path1: Path to the first file.
    :param path2: Path to the second file.
    :return:
    """
    from _model import SubschemaComparison
    logger.info("Compare S1 %s sub S2 %s python jsonsubschema" % (path1, path2))

    s1_json_content = util.load_json(path1)[1]
    s2_json_content = util.load_json(path2)[1]

    is_sub = None
    sub_exception = None

    start = time.time()
    try:
        is_sub = jsonsubschema.isSubschema(s1_json_content, s2_json_content)
    except BaseException as e:
        sub_exception = (str(type(e)), str(e))
    finally:
        end = time.time()

    logger.info("End compare S1 %s sub S1 %s" % (path1, path2))
    return SubschemaComparison(is_sub, sub_exception, start, end)
