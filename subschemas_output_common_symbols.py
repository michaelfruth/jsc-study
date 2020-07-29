#!/usr/bin/env python3
"""
Outputs statistics about the common symbols of two datas produced by subschemas.py.
@author: Michael Fruth
"""
import logging
import pickle

import _util_subschema as subschema_util
from _model import Subschema

logger = logging.getLogger(__name__)


def _group_symbols(git_files_data):
    """
    Creates a group for the symbols (decisions of the schema containment). The key is a tuple which contains the files of the containment.
    :param git_files_data: The data which contains the Subschema-objects.
    :return: A group with a tuple (file_path1, file_path2) as key and the symbol as value.
    """
    group = {}
    for git_file, subschemas in git_files_data:
        subschema: Subschema
        for subschema in subschemas:
            key = (subschema.s1.full_path, subschema.s2.full_path)
            if key in group:
                raise KeyError("Key {} already exists!".format(key))
            group[key] = subschema_util.get_symbol(subschema)
    return group


def compare(git_files_data1, git_files_data2, show_files=False):
    """
    Compare the subschema-objects of two files and print statistics about common symbols for the same file (for the same
    containment check). For the differently symbols, the left symbol is the decision of file 1, the right symbol the
    decision of file 2.

    E.g.
    ≡ - ⟂: 22
    Means, in 22 times file 1 has decided for equality, while file 2 decided for failure.

    :param git_files_data1: Data 1 to compare
    :param git_files_data2: Date 2 to compare
    :param show_files: Flag if detailed statistics should be printed or only a summary.
    :return:None
    """
    grouped_symbols1 = _group_symbols(git_files_data1)
    grouped_symbols2 = _group_symbols(git_files_data2)

    # Keys (the compared files) must be equal.
    # Do not allow a comparison of two sets, where subschema was computed on different files.
    if set(grouped_symbols1.keys()) != set(grouped_symbols2.keys()):
        raise ValueError(
            "The given files computed subschemas for different files. Compare only equal file sets! (E.g. do NOT compare -self with a file without -self)")

    equal_by_symbol = subschema_util.create_symbol_map(lambda: [])
    not_equal_by_symbol = subschema_util.create_symbol_map(lambda: subschema_util.create_symbol_map(lambda: []))

    total_files = 0
    for key in grouped_symbols1.keys():
        symbol1 = grouped_symbols1[key]
        symbol2 = grouped_symbols2[key]

        if symbol1 == symbol2:
            equal_by_symbol[symbol1].append(key)
        else:
            not_equal_by_symbol[symbol1][symbol2].append(key)
        total_files += 1

    # Remove empty symbols
    equal_by_symbol = {k: v for k, v in equal_by_symbol.items() if len(v) > 0}
    not_equal_by_symbol = {outer_k: {inner_k: inner_v for inner_k, inner_v in outer_v.items() if len(inner_v) > 0} for
                           outer_k, outer_v in not_equal_by_symbol.items()}
    not_equal_by_symbol = {k: v for k, v in not_equal_by_symbol.items() if len(v) > 0}

    if show_files:
        _output_summary(equal_by_symbol, not_equal_by_symbol, total_files, True)
    print("Total: {}".format(total_files))
    _output_summary(equal_by_symbol, not_equal_by_symbol, total_files)


def _output_summary(equal_by_symbol, not_equal_by_symbol, total_files, print_files=False):
    """
    Outputs the statistics about equal and not equal symbols.
    :param equal_by_symbol: The equal symbols.
    :param not_equal_by_symbol: The symbols, which are differently.
    :param total_files: The total files
    :param print_files: If a detailed statistic should be printed or not
    :return: None
    """
    total_files = float(total_files)

    if print_files:
        print("+" * 10 + " Details " + "+" * 10)
    else:
        print("+" * 10 + " Summary " + "+" * 10)

    print("Equal Symbols:")
    if len(equal_by_symbol) == 0:
        print("-")
    else:
        for symbol in equal_by_symbol:
            files = equal_by_symbol[symbol]
            print("{}: {} ({:.1f}%)".format(symbol, len(files), len(files) / total_files * 100.))
            if print_files:
                [print("\t{}\n\t{}\n".format(file[0], file[1])) for file in files]

    print("Differently Symbols:")
    if len(not_equal_by_symbol) == 0:
        print("-")
    else:
        for symbol1 in not_equal_by_symbol:
            for symbol2 in not_equal_by_symbol[symbol1]:
                files = not_equal_by_symbol[symbol1][symbol2]
                print("{} - {}: {} ({:.1f}%)".format(symbol1, symbol2, len(files), len(files) / total_files * 100.))
                if print_files:
                    [print("\t{} {}".format(file[0], file[1])) for file in files]

    if print_files:
        print("+" * 10 + " End Details " + "+" * 10)
    else:
        print("+" * 10 + " End Summary " + "+" * 10)


def _load_file(file_path, commit_directory):
    with open(file_path, 'rb') as f:
        git_files_data = pickle.load(f)
        [h.set_full_path(commit_directory) for f in git_files_data for h in f[0].history]
    return git_files_data


def main():
    import _arguments as args
    import _arguments_filter as args_filter
    default_args = args.default_args_detailed_data()

    input_file_2, show_files, git_files_data1 = args.parse_load_subschemas(
        {
            args.CLAInputFile2: args.CLAInputFile2().required(),
            args.CLAShowFiles: args.CLAShowFiles()
        }, default_args=default_args
    )
    # Process input file with the same arguments/filter applied before
    # The default_args has already all information from the console loaded, so both files will be loaded with the same
    # arguments.
    git_files_data2 = args.process_input_file(input_file_2, default_args, {}, args_filter.filter_subschemas)

    compare(git_files_data1, git_files_data2, show_files)


if __name__ == '__main__':
    main()
