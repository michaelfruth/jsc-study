import logging

import filter_filters

logger = logging.getLogger(__name__)


def output(draft_filter: filter_filters.FileDraftFilter):
    # Print all information about the filter;
    # The filtered files, the used filter and the total amount of filtered files.
    [print("\t{}".format(file.full_path)) for file in draft_filter.invalid_files]
    print("File Filter containing draft filter {}".format(draft_filter))
    print("Total filtered files: {}".format(len(draft_filter.invalid_files)))


def main():
    import _arguments as args
    draft_filter = args.parse_load_filter()
    output(draft_filter)


if __name__ == "__main__":
    main()
