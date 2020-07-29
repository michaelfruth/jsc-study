#!/usr/bin/env python3
"""
Clones the history of a repostiroy. Each version (commit) is checked out in a own directory.
@author: Michael Fruth
"""
import logging
from os import path

from git import Repo

import _util as util

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recursive_cloner")


def create_bare_master(output_directory, git_url):
    """
    Clone the git repository specified in git_url and create a bare-master repository in the output directory.
    :param output_directory: The directory in which a bare-master repository is created.
    :param git_url: The url to the git repository which should be cloned.
    :return: Name of the bare-master directory and the bare_master as GIT/Repository representation.
    """
    logger.info("Cloning %s into %s" % (git_url, output_directory))
    bare_master_directory = path.join(output_directory, 'bare-master')

    bare_master = Repo.clone_from(git_url, bare_master_directory, bare=True)
    logger.info("Finished cloning %s to %s" % (output_directory, git_url))

    return bare_master_directory, bare_master


def clone_all(output_directory, git_url):
    """
    Clones all "mainline" (--first-parent in git) versions of the specified git_url into the output_directory.
    The output_directory will have following structure:

    output_directory
        bare-master (bare-master of the specified GIT repository from git_url)
        commits
            1#ababa234252... (format: <count>#<sha>
            2#123aabbcc33...
            ....

        Where <count> is the number of commits made to the specific version of the repository and <sha> is the commit-hash
        of the repository.
    :param output_directory: The directory in which all directories are created.
    :param git_url: The git repository to clone all versions from.
    :return: None
    """
    bare_master_directory, bare_master = create_bare_master(output_directory, git_url)

    # Get all "mainline" commits
    commits = bare_master.iter_commits(first_parent=True)
    commits = list(commits)

    # Create commits directory path
    commits_directory = path.join(output_directory, "commits")

    # Clone version of the repository. One commit is one version of the repository.
    i = 0  # Just used for logging information
    for commit in commits:
        i += 1
        logger.info("Cloning commit %s (%s/%s)" % (commit.hexsha, i, len(commits)))

        # Commit-directoryname consists of the commit count and the commit -hash.
        # The commit count is the number of total commits made (until to the specific commit/version).
        # Low number = repository in its early stage; High number = repository in later stages/current state
        commit_directory_name = util.commit_directory_name(commit.count(first_parent=True), commit.hexsha)
        commit_directory = path.join(commits_directory, commit_directory_name)

        # Clone the bare-master repo into the commit directory
        commit_repo = Repo.clone_from(bare_master_directory, commit_directory, no_checkout=True)
        # Checkout the specific version of the new repository
        commit_repo.git.checkout(commit.hexsha)
        # commit_repo.git.reset(commit.hexsha, hard=True) # Use this if you want to lose the commit history to the master


def main():
    import _arguments as args
    cla_output_directory = args.CLAOutputDirectory().required()
    cla_git_repo = args.CLAGitRepo().required()
    args.parse_load({
        args.CLAOutputDirectory: cla_output_directory,
        args.CLAGitRepo: cla_git_repo
    })

    clone_all(cla_output_directory.value, cla_git_repo.value)


if __name__ == "__main__":
    main()
