"""
Contains all possible command line arguments. Handles also the parsing of arguments.
@author: Michael Fruth
"""

import logging
from typing import Callable, Any, Union

from _model import GitFile, GitHistoryFile, Subschema, SchemaDrafts
from filter_filters import DraftFilter

logger = logging.getLogger(__name__)


def _filter(draft_filter: DraftFilter, items: [],
            git_history_file_extraction_func: Callable[[Any], Union[GitHistoryFile, list]]):
    """
    Applies the extraction_func on each itm in items and this result is applied to the filter. If the item is not valid, it is filtered.
    :param draft_filter: The filter to be applied.
    :param items: The items to filter.
    :param git_history_file_extraction_func: The function, which extracts the GitHistoryFile out of a item.
    :return: None. The items are manipulated directly.
    """
    if draft_filter is None:
        return

    for item in items[:]:  # Copy list to remove easily items
        do_remove = []  # Collect all items to remove

        # Extract the GitHistoryFile from the item
        extractions = git_history_file_extraction_func(item)

        if isinstance(extractions, list):
            extractions: [GitHistoryFile] = extractions
            for extraction in extractions:
                # change_type 'D' == Deleted
                if extraction.change_type == 'D' or not draft_filter.is_valid(extraction):
                    do_remove.append(extraction.full_path)
        else:
            extraction: GitHistoryFile = extractions
            # change_type 'D' == Deleted
            if extraction.change_type == 'D' or not draft_filter.is_valid(extraction):
                do_remove.append(extraction.full_path)

        if len(do_remove) > 0 and item in items:
            # We have GitHistoryFile-Paths to remove and item is still in original items
            items.remove(item)
            logger.info("Filtered {}".format("\n\t".join(do_remove)))


def filter_git_files(draft_filter: DraftFilter, git_files: [GitFile]):
    """
    Filters GitFiles based on the applied filter.
    :param draft_filter: The filter to be applied.
    :param git_files: The GitFiles to filter.
    :return: None. The filter manipulates directly the data.
    """
    if draft_filter is None:
        return

    git_file: GitFile
    for git_file in git_files[:]:  # Copy list to easily remove filtered elements
        _filter(draft_filter, git_file.history, lambda git_history_file: git_history_file)
        if len(git_file.history) == 0:
            git_files.remove(git_file)
            continue


def _default_filter(draft_filter: DraftFilter, git_files_data: [GitFile, [Any]],
                    git_history_file_extraction_func: Callable[[Any], Union[GitHistoryFile, list]]):
    """
    Filteres the given data based on the applied filter.
    :param draft_filter: The filter to be applied.
    :param git_files_data: The data to filter.
    :param git_history_file_extraction_func: A function to extract the GitHistoryFile out of the data.
    The data is iterated and for on each iteration, this method is called on the second value of the iterated data.
    This method should return a single GitHistoryFile or a list containing GitHistoryFiles.
    :return: None. The filter manipulates the data directly.
    """
    if draft_filter is None:
        return

    for git_file, any_data in git_files_data[:]:  # Copy list to easily remove filtered elements
        filter_git_files(draft_filter, [git_file])

        if len(git_file.history) == 0:
            logger.info("Remove file: {}".format(git_file.path))
            git_files_data.remove((git_file, any_data))
            continue

        _filter(draft_filter, any_data, git_history_file_extraction_func)


def filter_subschemas(draft_filter: DraftFilter, git_files_data: [GitFile, [Subschema]]):
    """
        Filters the pickled data from subschemas, based on the given filter.
        :param draft_filter: the filter to be applied
        :param git_files_data: the pickled data from schema_drafts
        :return: None. git_files_data is manipulated directly.
        """
    _default_filter(draft_filter, git_files_data, lambda subschema: [subschema.s1, subschema.s2])


def filter_schema_drafts(draft_filter: DraftFilter, git_files_data: [GitFile, [SchemaDrafts]]):
    """
    Filters the pickled data from schema_drafts, based on the given filter.
    :param draft_filter: the filter to be applied
    :param git_files_data: the pickled data from schema_drafts
    :return: None. git_files_data is manipulated directly.
    """
    _default_filter(draft_filter, git_files_data, lambda schema_draft: schema_draft.git_history_file)
