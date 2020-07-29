#!/usr/bin/env python3
"""
Outputs statistics about the history of the files computed by git_file_changes.py
@author: Michael Fruth
"""
import filter_filters
from _model import GitFile, GitHistoryFile


def output_occurrences(git_files):
    """
    Counts the length of the history of the root files and outputs a small statistic about the occurrences.
    :param git_files: The root files containing the version files.
    :return: None
    """
    occurrence = {}
    for git_file in git_files:
        if len(git_file.history) not in occurrence:
            occurrence[len(git_file.history)] = 0
        occurrence[len(git_file.history)] += 1

    for length, count in occurrence.items():
        print("History: {} ({} schema(s))".format(length, count))


def output_history_number(git_files: [GitFile]):
    """
    Outputs for each file the number of versions as well as the minimum und maximum commit count where the file was
    added and modified last
    :param git_files: The root files containing the version files.
    :return: None.
    """
    git_file: GitFile
    for git_file in git_files:
        min_count = None
        max_count = None
        if len(git_file.history) > 0:
            min_count = git_file.history[0].commit_count
            max_count = git_file.history[-1].commit_count
        print("{}: {} version(s) | Min-Count: {} Max-Count: {}".format(git_file.path, len(git_file.history), min_count,
                                                                       max_count))


def count_successive_schemas(git_files: [GitFile]):
    """
    Counts the number of successive schema versions.
    :param git_files: The root files containing the versioned files.
    :return: The number of successive schema versions
    """
    counter = 0
    for git_file in git_files:
        for i in range(len(git_file.history)):
            if i + 1 < len(git_file.history):
                counter += 1
    return counter


def count_unique_commit_counts(git_files):
    """
    Counts the number of unique commit counts.
    :param git_files: The root files containing the versioned files.
    :return: The number of unique commit counts.
    """
    commit_counts = set()
    for git_file in git_files:
        h: GitHistoryFile
        for h in git_file.history:
            commit_counts.add(h.commit_count)

    return commit_counts


def output_filter(git_files: [GitFile], filter: filter_filters.DraftFilter):
    """
    Outputs statistics about the filter. E.g. the total number of filtered files by this filter as well as the path of
    the filtered files.
    :param git_files: The root files.
    :param filter: The filter for which the statistic is printed
    :return: None
    """
    filtered_files = []

    total_files = 0
    for git_file in git_files:

        total_files += len(git_file.history)
        filtered_history = git_file.history[:]  # Copy list to not remove elements from the original list

        h: GitHistoryFile
        for h in filtered_history[:]:  # Copy list to iterate and remove elements
            if not filter.is_valid(h):
                filtered_history.remove(h)
                filtered_files.append((git_file, filtered_history, h.full_path))

    print("Total filtered files: {} (of {})".format(len(filtered_files), total_files))
    print("Filtered files:")
    for git_file, filtered_history, full_file_path in filtered_files:
        print("\tFile: {} | History: Before: {} - After: {}  | Path: {}".format(git_file.path,
                                                                                len(git_file.history),
                                                                                len(filtered_history),
                                                                                full_file_path))


def output_files_change_type(git_files):
    """
    Outputs a small statistic about the occurrences of the change types (e.g. how often a file was added/removed/renamed...)
    :param git_files: The root files containing the version files
    :return: None
    """
    change_types = {}
    for git_file in git_files:
        h: GitHistoryFile
        for h in git_file.history:
            if h.change_type not in change_types:
                change_types[h.change_type] = 0
            change_types[h.change_type] += 1
    print(change_types)


def output_all(git_files, git_deleted_files):
    """
    Outputs several statistics/numbers.
    :param git_files: The files which are present in the latest state of the repository
    :param git_deleted_files: The file which were deleted.
    :return: None
    """
    print("Total files: {}".format(len(git_files)))
    print("Total deleted files: {}".format(len(git_deleted_files)))
    print("Total file versions: {}".format(sum(map(lambda git_file: len(git_file.history), git_files))))
    print("Total deleted versions: {}".format(sum(map(lambda git_file: len(git_file.history), git_deleted_files))))
    print("Total successive versions: {}".format(count_successive_schemas(git_files)))
    print("Total successive deleted versions: {}".format(count_successive_schemas(git_deleted_files)))

    print("+" * 50)
    all_files = []
    all_files.extend(git_files)
    all_files.extend(git_deleted_files)
    schema_affects = count_unique_commit_counts(all_files)
    print("Unique commit count (number of total (current + deleted) repositories affected by 'paths':): {}".format(
        len(schema_affects)))

    print("+" * 50)
    print("Occurrences:")
    output_occurrences(git_files)
    print("+" * 50)
    print("Available History:")
    output_history_number(git_files)
    print("+" * 50)
    print("Deleted History:")
    output_history_number(git_deleted_files)

    print("+" * 50)
    print("Change types from GIT diff:")
    output_files_change_type(git_files)


def main():
    import _arguments as args

    default_args_file_changes = args.default_args_file_changes()
    del default_args_file_changes[args.CLADraftFilterGroup]

    cla_draft_filter_group = args.CLADraftFilterGroup().do_nothing()  # Filter should not be applied on startup
    _, git_files, git_deleted_files = args.parse_load_file_changes(
        {
            args.CLADraftFilterGroup: cla_draft_filter_group
        }, default_args=default_args_file_changes
    )

    draft_filters = [cla.draft_filter for cla in cla_draft_filter_group.clas if cla.draft_filter is not None]
    draft_filter = None
    if len(draft_filters) == 1:
        # cla_draft_filter_group is a mutually exclusive group - if a filter is set, only one should be set
        draft_filter = draft_filters[0]

    print("#" * 50 + " UNFILTERED " + "#" * 50)
    output_all(git_files, git_deleted_files)

    if draft_filter:
        import _arguments_filter

        print("#" * 50 + " FILTERED " + "#" * 50)
        print("Filtered by draft filter {}:".format(draft_filter))
        output_filter(git_files, draft_filter)
        print("+" * 50)

        _arguments_filter.filter_git_files(draft_filter, git_files)
        _arguments_filter.filter_git_files(draft_filter, git_deleted_files)
        output_all(git_files, git_deleted_files)


if __name__ == '__main__':
    main()
