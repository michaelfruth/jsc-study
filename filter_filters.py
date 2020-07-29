"""
Contains the different filters which can be applied on the data.
@author: Michael Fruth
"""
import logging

import jsonref

import _util as util
from _model import GitHistoryFile

logger = logging.getLogger(__name__)


def _valid_draft4_keywords(json_content):
    import draft4_new_keywords_finder
    result = draft4_new_keywords_finder.check_history_json(json_content)
    if result:
        # Found incompatible/added keywords
        return False
    return True


def _valid_contains_not_keyword(json_content, keyword):
    """
    Checks if the json_content contains NOT the passed keyword. True is returned, if the keyword is NOT contained.
    :param json_content: The json content in which for the keyword is searched
    :param keyword: The keyword to search for
    :return: True if the keyword is NOT contained in the json content, false otherwise.
    """
    try:
        keyword_generator = util.find_in_json_recursive(json_content, keyword)
        next(keyword_generator)
        # keyword is present
        return False
    except RecursionError:
        # Recursion error occured while searching for the keyword - search manually
        # Manual search is "weaker" (because keyword can be in a comment or description), so possibly more results will
        # be filtered, but this is ok..
        json_str = str(json_content)
        if '"{}":'.format(keyword) in json_str:
            # keyword is present
            return False
        else:
            # keyword isn't present
            return True
    except StopIteration:
        # keyword isn't present
        return True


#############################################################################
# Start of the different filter classes
#############################################################################

class DraftFilter:
    """
    The base class for all filters.
    """
    _drafts_to_validate = None

    def is_valid(self, git_history_file: GitHistoryFile):
        """
        Loads the file and checks if it is valid to the specific filter.
        :param git_history_file: The file to check.
        :return: True if the file is valid to the specific filter, false otherwise.
        """
        raise NotImplementedError("Use the specific implementations!")

    def _is_valid(self, json_content):
        """
        Checks if the json_content is valid to the specific filter.
        :param json_content: The content to check.
        :return: True if the json content is valid to the specific filter, false otherwise.
        """
        raise NotImplementedError("Use the specific implementations!")

    @classmethod
    def _valid_all_drafts(cls, git_history_file: GitHistoryFile):
        """
        Loads the file and checks whether the content is valid to all drafts specified in _drafts_to_validate.
        :param git_history_file: The file to check.
        :return: True if the file is valid to all drafts, false otherwise.
        """
        json_content = util.load_json(git_history_file.full_path)[1]  # [1] is the json_content
        return cls._valid_all_drafts_json(json_content)

    @classmethod
    def _valid_all_drafts_json(cls, json_content):
        """
        Checks whether the content is valid to all drafts specified in _drafts_to_validate.
        :param json_content: The file to check.
        :return: True if the file is valid to all drafts, false otherwise.
        """
        drafts_validation = util.schema_validate_all_drafts(json_content)
        for draft in cls._drafts_to_validate:
            # Draft is valid -> result is None;
            # Exception occurred -> result is not None
            if drafts_validation[draft] is not None:
                return False
        return True


class FileDraftFilter(DraftFilter):
    """
    A file draft filter which stores the invalid files. Filtering is done by one of the specific filters.
    This filter can be used to save on disk on use later for a better performance, because the invalid files only have
    to be computed once. Make sure that you apply this filter on the same dataset where also this filter was created for.
    """

    def __init__(self, draft_filter: DraftFilter):
        self.draft_filter = draft_filter
        self.invalid_files = []

    def __str__(self):
        return str(type(self.draft_filter))

    def check_append_invalid(self, git_history_file):
        """
        Appends the file to the list of invalid_files if its invalid. The specified filter is used for validation.
        :param git_history_file: The file to check and possibly append to the list of invalid files
        :return: None.
        """
        if not self.draft_filter.is_valid(git_history_file):
            self.invalid_files.append(git_history_file)

    def is_valid(self, git_history_file: GitHistoryFile):
        """
        Check if the file is in the list of invalid files (__eq__ is overwritten in GitHistoryFile, so this works).
        :param git_history_file: The file to check
        :return: True if the file is not contained in the invalid files, false otherwise.
        """
        if git_history_file in self.invalid_files:
            return False
        return True


class Draft4Filter(DraftFilter):
    """
    Filtering based on following conditions:
    1. File must be valid to Draft 4 until Draft 7 (Draft 4, 6, 7)
    2. File should not contain any keywords added/introduced in Draft 6 or Draft 7
    """
    DraftFilter._drafts_to_validate = [
        util.DRAFT4_NAME,
        util.DRAFT6_NAME,
        util.DRAFT7_NAME
    ]

    def is_valid(self, git_history_file: GitHistoryFile):
        logger.info("File: {}".format(git_history_file.full_path))
        json_content = util.load_json(git_history_file.full_path)[1]
        return self._is_valid(json_content)

    def _is_valid(self, json_content):
        if not Draft4Filter._valid_all_drafts_json(json_content):
            return False

        if not _valid_draft4_keywords(json_content):
            return False

        return True


class Draft4ValidJsonRef(Draft4Filter):
    """
    Filtering based on following conditions:
    1. See conditions of Draft4Filter
    2. All references are evaluated and checked again with the conditions of 1.
    This means: All files containing e.g. invalid JsonReferences or RecursionErrors are filtered. Also, if a reference
    exists to an online resource and some invaild keywords are introduced through this source, this file will be filtered.
    """

    def is_valid(self, git_history_file: GitHistoryFile):
        logger.info("File: {}".format(git_history_file.full_path))
        json_content = util.load_json(git_history_file.full_path)[1]
        return self._is_valid(json_content)

    def _is_valid(self, json_content):
        # Draft4Filter-Check
        if not super()._is_valid(json_content):
            return False

        json_content_ref = jsonref.JsonRef.replace_refs(json_content)

        # Draft4Filter-Check but now the dereferenced JsonContent.
        if not super()._is_valid(json_content_ref):
            return False

        return True


class Draft4NoNot(Draft4Filter):
    """
    Filtering based on following conditions:
    1. See conditions of Draft4Filter
    2. Filters all files which contains the keyword "not"
    """

    def is_valid(self, git_history_file: GitHistoryFile):
        logger.info("File: {}".format(git_history_file.full_path))
        json_content = util.load_json(git_history_file.full_path)[1]
        return self._is_valid(json_content)

    def _is_valid(self, json_content):
        # Draft4Filter-Check
        if not super()._is_valid(json_content):
            return False

        # Keyword "not" check
        if not _valid_contains_not_keyword(json_content, "not"):
            return False

        return True


class Draft4ValidJsonRefNoNot(Draft4Filter):
    """
    Filtering based on following conditions:
    1. See conditions of Draft4Filter
    2. All references are evaluated and checked again with the conditions of 1. (see Draft4FilterJsonRef for more details)
    3. Filters all files which contains the keyword "not". They keyword will also be searched in the dereferenced json content. (see Draft4FilterNoNot for more details)
    """

    def is_valid(self, git_history_file: GitHistoryFile):
        logger.info("File: {}".format(git_history_file.full_path))
        json_content = util.load_json(git_history_file.full_path)[1]
        return self._is_valid(json_content)

    def _is_valid(self, json_content):
        # Draft4Filter-Check
        if not super()._is_valid(json_content):
            return False
        # keyword "not" check
        if not _valid_contains_not_keyword(json_content, "not"):
            return False

        json_content_ref = jsonref.JsonRef.replace_refs(json_content)

        # Draft4FilterJsonRef-Check
        if not super()._is_valid(json_content_ref):
            return False
        # keyword "not" check with dereferenced json content
        if not _valid_contains_not_keyword(json_content_ref, "not"):
            return False
        return True


#############################################################################
# End of the different filter classes
#############################################################################

# This can be used in the arguments for choices and to use the desired filter
DRAFT_FILTERS = {
    util.DRAFT4_NAME: Draft4Filter(),
    util.DRAFT4_NAME + "JsonRef": Draft4ValidJsonRef(),
    util.DRAFT4_NAME + "NoNot": Draft4NoNot(),
    util.DRAFT4_NAME + "JsonRefNoNot": Draft4ValidJsonRefNoNot(),
}
