#!/usr/bin/env python3
"""
Computes the history of the files based on the history of a repository.
@author: Michael Fruth
"""
import logging
import os
import pickle
from os import path

from git import Repo

import _util as util
from _model import GitFile, GitHistoryFile

logger = logging.getLogger(__name__)

_files: {str, GitFile} = {}
_deleted: [GitFile] = []


def _add_new_file(git_file: GitFile, commit_count=None, git_history_file=None):
    """
    Adds/creates a new file (root file, which stores all versions of a file).
    :param git_file: The root file.
    :param commit_count: The commit count - must only be set if git_history_file is None
    :param git_history_file: The first version of the file
    :return:  None
    """
    if not git_history_file:
        # Create versioned file from the data
        git_history_file = GitHistoryFile(git_file.added_sha, None, git_file.path, 'A', commit_count)
    git_file.history.append(git_history_file)
    _files[git_file.path] = git_file


def _add_history_file(git_history_file: GitHistoryFile):
    """
    Adds a new versioned file.
    :param git_history_file: The versioned file
    :return: None
    """
    old_path = git_history_file.old_path
    new_path = git_history_file.new_path
    change_type = git_history_file.change_type

    if change_type == 'A':
        # Added
        _add_new_file(GitFile(new_path, git_history_file.sha), git_history_file=git_history_file)
    elif change_type == 'D':
        # Deleted
        # Append to the root file
        git_file = _files[old_path]
        git_file.history.append(git_history_file)

        # Set deleted sha of the root file, remove it from the current files and add it to the deleted files
        git_file.deleted_sha = git_history_file.sha
        del _files[old_path]
        _deleted.append(git_file)
    else:
        # Other (Change, Renaming etc..)
        # Append to the root file
        git_file = _files[old_path]
        git_file.history.append(git_history_file)

        if old_path != new_path:
            # Rename occurred - change keys stored in _files
            del _files[old_path]
            _files[new_path] = git_file
            # Also change the "path" to the current path of the git_file
            git_file.path = new_path


def _get_tracked_files(trees):
    """
    Returns all tracked files of a repository-tree.
    :param trees: The repository-tree.
    :return: The paths of the tracked files.
    """
    paths = []
    for tree in trees:
        for blob in tree.blobs:
            paths.append(blob.path)
        if tree.trees:
            paths.extend(_get_tracked_files(tree.trees))
    return paths


def _initialize_files(version_directory):
    """
    Adds all files of the repository to the tracked files. This method should be called with the initial or the lastest
    state of the repository.
    :param version_directory: The directory representing the first/latest state of the repository.
    :return: None
    """
    repo = Repo(version_directory)

    tracked_files = _get_tracked_files([repo.tree()])
    # Add all files existing in this version to the global tracked files
    for tracked_file in tracked_files:
        commit_count = util.info_from_commit_directory_name(version_directory)[0]
        _add_new_file(GitFile(tracked_file, repo.commit().hexsha), commit_count=commit_count)


def _diff_directories(version_before_directory, version_directory):
    """
    Gets the difference (from git) of the repositories.
    :param version_before_directory: The directory before
    :param version_directory: The "current"/subsequent directory
    :return: None
    """
    logger.info("Diff of %s and %s" % (version_before_directory, version_directory))

    repo_before = Repo(version_before_directory)
    repo = Repo(version_directory)

    if repo.git.rev_parse('HEAD~1') != repo_before.commit().hexsha:
        raise ValueError(
            "The SHA of HEAD~1 (previous commit of the current directory) doesn't match the SHA of the directory "
            "containing the previous commit. Comparing directories:\n"
            "\tCurrent directory: %s\n"
            "\tCurrent SHA: %s\n"
            "\tPrevious directory: %s\n"
            "\tPrevious SHA: %s"
            % (version_directory, repo.git.rev_parse('HEAD~1'), version_before_directory, repo_before.commit().hexsha))

    commit_before = repo_before.commit()
    commit = repo.commit()

    # https://gitpython.readthedocs.io/en/stable/reference.html#git.diff.Diff
    # Compute the difference of the two commits before and after
    diffs = commit_before.diff(commit)
    if len(diffs) == 0:
        logger.warning("Diff of %s and %s is empty!" % (version_before_directory, version_directory))
    for diff in diffs:
        old_path = diff.a_path
        new_path = diff.b_path

        commit_count = util.info_from_commit_directory_name(version_directory)[0]  # commit_count
        git_history_file = GitHistoryFile(commit.hexsha, old_path, new_path, diff.change_type, commit_count)

        _add_history_file(git_history_file)


def extract_file_changes(commits_directory, track_paths=None, output_file=None, validate_master=None):
    """
    Extract the file changes from the repositories cloned before (see module git_history_cloner). It extracts from each
    commit the changed/added/removed files and creates a version of the file for each change.
    :param commits_directory: The commit directory in which all the cloned repositories reside
    :param track_paths: If some files should be filtered by path (e.g. consider only files in the sub-directory src/schemas/json/)
    :param output_file: The file in which the the file differences are stored.
    :param validate_master: The bare-master repository for validation.
    :return: the created files and the deleted files are returnd as list.
    """
    # track_paths must be a list
    if not track_paths:
        track_paths = ''
    if not isinstance(track_paths, list):
        track_paths = [track_paths]

    # Get all commit directories (all directories containing the different versions of the repository)
    commit_directories = [path.join(commits_directory, d) for d in os.listdir(commits_directory)]
    commit_directories = [d for d in commit_directories if os.path.isdir(d)]
    # Sort directories based on count (number of available commits
    # High number = current sate; Low number = initial state
    commit_directories.sort(key=lambda x: util.info_from_commit_directory_name(x)[0],
                            reverse=False)

    # [0] = initial state. Add all files added in the first commit to the global tracked filed.
    # This files aren't recognized later by computing the difference
    _initialize_files(commit_directories[0])

    if validate_master:
        # Every version of the repository is locally available as own repository.
        # These versions can also be accessed from the root-repository. If validate_master is given, it will be checked
        # if the commit hash of the directory-repository does match the expected commit-hash from the history of the
        # master-repository.
        master = Repo(validate_master)
        commits = master.iter_commits(first_parent=True)
        commits = list(commits)
        commits.reverse()  # Reverse, because repositories are processed from intial to current state.

        if len(commits) != len(commit_directories):
            raise ValueError("Validate Error: Different length - master %d and commits %d" % (
                len(commits), len(commit_directories)))

    for i in range(0, len(commit_directories)):
        if validate_master:
            # Check if the hash of the directory matches the hash of the history of the master-repository.
            logger.info("Validate %d/%d" % (i + 1, len(commit_directories)))
            directory_sha = Repo(commit_directories[i]).commit().hexsha
            commit_sha = commits[i].hexsha
            if commit_sha != directory_sha:
                raise ValueError("Different SHA for master %s and %s" % (commit_sha, directory_sha))

        if i + 1 < len(commit_directories):
            # Compute difference of two successive repositories (get the difference - git diff - of them)
            _diff_directories(commit_directories[i], commit_directories[i + 1])

    # Filter files based on the path (e.g. all filenames have to start with src/schemas/json/...)
    files: [GitFile] = [f for f in _files.values() if f.path.startswith(tuple(track_paths))]
    deleted: [GitFile] = [f for f in _deleted if f.path.startswith(tuple(track_paths))]

    # Sort files by their history length
    files.sort(key=lambda x: len(x.history), reverse=True)
    deleted.sort(key=lambda x: len(x.history), reverse=True)

    [print(f) for f in files]
    if output_file:
        with open(output_file, 'wb') as f:
            # Save files to disk
            pickle.dump((files, deleted), f)
    return files, deleted


def main():
    import _arguments as args

    cla_commit_directory = args.CLACommitDirectory().required()
    cla_validate_directory = args.CLAGitValidate()
    cla_output_file = args.CLAOutputFile().required()
    cla_paths = args.CLAPathsFilter()
    args.parse_load(
        {
            args.CLACommitDirectory: cla_commit_directory,
            args.CLAGitValidate: cla_validate_directory,
            args.CLAOutputFile: cla_output_file,
            args.CLAPathsFilter: cla_paths
        }
    )

    extract_file_changes(cla_commit_directory.value, cla_paths.value, cla_output_file.value,
                         cla_validate_directory.value)


if __name__ == "__main__":
    main()
