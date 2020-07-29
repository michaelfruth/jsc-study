"""
Helper functions.
@author: Michael Fruth
"""
import json
import logging
import multiprocessing
import pickle
from os import path

import chardet
from jsonschema import Draft3Validator, Draft4Validator, Draft6Validator, Draft7Validator

logger = logging.getLogger(__name__)

# Separator used to separate the commit-count and the SHA of the repository in the directory-name.
_COMMIT_HISTORY_DIRECTORY_SPEARATOR = "#"

DRAFT3_NAME = 'Draft3'
DRAFT4_NAME = 'Draft4'
DRAFT6_NAME = 'Draft6'
DRAFT7_NAME = 'Draft7'

SCHEMA_VALIDATORS = {
    DRAFT3_NAME: Draft3Validator,
    DRAFT4_NAME: Draft4Validator,
    DRAFT6_NAME: Draft6Validator,
    DRAFT7_NAME: Draft7Validator
}


def commit_directory_name(commit_count, sha):
    return str(commit_count) + _COMMIT_HISTORY_DIRECTORY_SPEARATOR + str(sha)


def info_from_commit_directory_name(directory_name_or_path: str):
    directory_name = path.basename(directory_name_or_path)
    commit_count, sha = directory_name.split(_COMMIT_HISTORY_DIRECTORY_SPEARATOR)
    return int(commit_count), sha


def load_json(json_file):
    """
    Loads the given json file while considering different encodings. First, UTF-8 will be tried. If this doesn't work,
    the encoding will be determined ba the module chardet and it is tried again to load the json file.
    :param json_file: The json file to load
    :return: Plain content of the file (str), the loaded json content (dict), the encoding and a flag which indicates
    if a error occured.
    """
    content, json_content = None, None
    encoding = 'UTF-8'
    error = False
    try:
        content, json_content = _load_json_with_enconding(json_file, encoding)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # File has probably other charset - determine charset and try again
        with open(json_file, 'rb') as f:
            content = f.read()
            encoding = chardet.detect(content)['encoding']
        try:
            content, json_content = _load_json_with_enconding(json_file, encoding)
        except (json.JSONDecodeError, UnicodeDecodeError):
            error = True
    return content, json_content, encoding, error


def _load_json_with_enconding(file, encoding):
    with open(file, 'r', encoding=encoding) as f:
        content = f.read()
        json_content = json.loads(content)
        return content, json_content


def schema_validate_all_drafts(json_content):
    """
    Validate the json based on all drafts (Draft 3, 4, 6, 7).
    :param json_content: The json to validate.
    :return: a dictionary with the draft as key and the result of the validation as value.
    If the value is None, the json is valid to the given draft (key).
    If value is not None, the value is a tuple; first element is the string-representation of the type of the exception,
     the second value is the string-representation of the excepetion (error message).
    """
    result = {}
    for draft, validator in SCHEMA_VALIDATORS.items():
        try:
            # Validator throws an excepetion if its invalid; Otherwise nothing happens.
            validator.check_schema(json_content)
            result[draft] = None
        except Exception as e:
            result[draft] = (str(type(e)), str(e))
    return result


def schema_tag(json_content):
    """
    Gets the schema tag ($schema) out of the json.
    :param json_content:
    :return:
    """
    if u"$schema" in json_content:
        return json_content[u"$schema"]
    return None


def append_pickle(file, data):
    """
    Pickle data on the same file multiple times and the data is appended each time instead of overwriting the old data.
    The file will be first unpickled, data will be appendend and the file will be pickled again.
    :param file: The file which stores the data.
    :param data: The data to store.
    :return: None.
    """
    logger.info("Read old data %s" % file)
    if path.isfile(file):
        # Read old data
        with open(file, 'rb') as f:
            pickle_data = pickle.load(f)
    else:
        # File doesn't exists
        pickle_data = []

    logger.info("Write new data %s" % file)
    with open(file, 'wb') as f:
        # Append data and pickle
        pickle_data.append(data)
        pickle.dump(pickle_data, f)


def find_in_json_recursive(dictionary, lookup_key, yield_parent=False, _parent=None):
    """
    Generator-implementation to find a specific entry (lookup_key) in a json dictionary. The lookup_key must be a
    dictionary-entry. This method can throw an RecursionError.
    :param dictionary: The dictionary to search for the lookup_key.
    :param lookup_key: The key which should be contained in the dictionary.
    :param yield_parent: If the parent or the element which contains the key should be yielded.
    :param _parent: The current parent element (do not set this from outside! Internal use only.
    :return: A list with all elements containing the lookup_key. (Empty list if no key matching the lookup_key was found)
    """
    if not isinstance(dictionary, dict):
        return

    for key, value in dictionary.items():
        if key == lookup_key:
            if yield_parent:
                # Yield parent if parent is set - otherwise yield the dictionary
                yield _parent
            else:
                yield dictionary
        elif isinstance(value, dict):
            for result in find_in_json_recursive(value, lookup_key, yield_parent=yield_parent, _parent=key):
                yield result
        elif isinstance(value, list):
            for item in value:
                for result in find_in_json_recursive(item, lookup_key, yield_parent=yield_parent, _parent=key):
                    yield result


def multiprocess_and_set_files_later(cores, func, iterable, reset_func, use_map=False):
    """
    This method is used to compute something in parallel. A processing pool is opened with the specified number of cores
    and executes "func" on each item of "iterable. The "reset_func" is used when the computation is done.

    Reminder: This is multi-processing and not multi-threading! For each function call, a new process will be opened and
    the passed data is pickled and passed to the function. When execution is done, the data will be pickled again to
    return it back to the main process. This can lead to unwanted behavior!
    E.g.
    Outside                         Multiprocessing-Process
    1. Create object a
    2. Pass object a to process -->
                                    3. Make computations with object a
                                    4. Create own object b and save a reference to object a
                                <-- Return object b

    The object "a" of "Outside" is NOT the same object as in "Multiprocessing-Process" duo to the pickling.
    To handle this unwanted behavior, the reset_func is called after computation to set the reference from object to
    object a to the real (outside) object a.

    The reset_func method gets the original passed values as well as the result of its computation.

    :param cores: The number of process which should be used in maximum.
    :param func: The function to execute.
    :param iterable: The items on which the "func" should be executed
    :param reset_func: The function to reset the references.
    :param use_map: If true, "map" will be used, otherwise "star_map"
    :return: The results (as lsit) of the "func".
    """
    logger.info("Starting multiproccessing... Using {} cores for {} items:".format(cores, len(iterable)))
    with multiprocessing.Pool(processes=cores) as pool:
        if use_map:
            result = pool.map(func, iterable)
        else:
            result = pool.starmap(func, iterable)

    if len(iterable) != len(result):
        raise ValueError(
            "Length of iterables () doesn't match the length of the result ({})".format(len(iterable), len(result)))

    for i in range(len(iterable)):
        if isinstance(iterable[i], tuple) or isinstance(iterable[i], list):
            reset_func(*iterable[i], result[i])
        else:
            reset_func(iterable[i], result[i])

    return result
