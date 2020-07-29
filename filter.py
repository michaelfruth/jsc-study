#!/usr/bin/env python3
"""
Create a filter to filter the data on startup used by the different scripts.
@author: Michael Fruth
"""
import logging
import pickle

import filter_filters
from _model import GitFile

logger = logging.getLogger(__name__)


def create_filter(output_file, draft_filter: filter_filters.DraftFilter, git_files: [GitFile]):
    """
    Creates a new filter-file based on the passed filter.
    :param output_file: The file in which the filter is stored.
    :param draft_filter: The filter to be used.
    :param git_files: The files to be used for the filter.
    :return: None
    """
    file_filter = filter_filters.FileDraftFilter(draft_filter)
    for git_file in git_files:
        # Store all invalid files in the filter.
        # Later, the files can be filtered fast based on the stored, invalid files.
        [file_filter.check_append_invalid(h) for h in git_file.history]

    with open(output_file, 'wb') as f:
        pickle.dump(file_filter, f)


def main():
    import _arguments as args

    # Remove the FilterGroup from the default args; Data should not be filtered beforehand.
    default_args_file_changes = args.default_args_file_changes()
    del default_args_file_changes[args.CLADraftFilterGroup]

    cla_draft_filter_on_the_fly = args.CLADraftFilterOnTheFlyFilter().required().do_nothing()
    output_file, draft_filter, git_files, git_deleted_files = args.parse_load_file_changes(
        {
            args.CLAOutputFile: args.CLAOutputFile().required(),
            args.CLADraftFilterOnTheFlyFilter: cla_draft_filter_on_the_fly
        },
        default_args=default_args_file_changes
    )

    create_filter(output_file, cla_draft_filter_on_the_fly.draft_filter, git_files)


if __name__ == "__main__":
    main()
