#!/usr/bin/env python3
"""
Outputs and plots statistics about the exception types when a failure occured of a particular JSC-tool (data from subschemas.py).
@author: Michael Fruth
"""
import logging

import pandas as pd
import plotly.express as px

import _util_subschema as subschema_util
from _model import GitFile, Subschema

logger = logging.getLogger(__name__)


def _create_df(git_file: GitFile, subschemas: [Subschema]):
    pandas_data = []
    subschema: Subschema
    for subschema in subschemas:
        symbol = subschema_util.get_symbol(subschema)

        if symbol != subschema_util.SYM_FAIL:
            # Get only the exception types
            continue

        # Sort exception types to not have duplicates with different order
        # E.g.: This avoids "a | b" and "b | a" (only "a | b" is counted twice}
        exception_types = []
        if subschema.s1_compare_s2.is_subset_exception is not None:
            exception_types.append(subschema.s1_compare_s2.is_subset_exception[0])
        if subschema.s2_compare_s1.is_subset_exception is not None:
            exception_types.append(subschema.s2_compare_s1.is_subset_exception[0])
        if len(exception_types) == 0:
            raise ValueError("This should not happen... No exception is given but the subschema has no decision..")

        exception_types.sort()
        if len(exception_types) == 2 and exception_types[0] != exception_types[1]:
            exception_type = " | ".join(exception_types)
        else:
            exception_type = exception_types[0]
        pandas_data.append(exception_type)

    df = pd.DataFrame(pandas_data, columns=['Exception_Type'])
    return df


def plot(git_files_data):
    dfs = []
    total_pairs = 0
    for git_file, subschemas in git_files_data:
        dfs.append(_create_df(git_file, subschemas))
        total_pairs += len(subschemas)

    df = pd.concat(dfs, ignore_index=True)
    # Count the excepetion type
    df_values = df['Exception_Type'].value_counts().rename_axis('Exception_Type').reset_index(name='Counts')
    # Compute the percentage of the excepetion type occurrences
    df_values['Percentage'] = df_values['Counts'] / float(len(df)) * 100

    print(df_values)
    print(df_values.round(1))
    print("Total pairs: {}".format(total_pairs))
    print("Total errors: {}".format(len(df)))

    fig = px.pie(df, values=[1] * len(df), names='Exception_Type')
    fig.update_layout(title='All | Total Subschemas: {} | Total Symbols: {}'.format(total_pairs, len(df)))
    fig.show()


def main():
    import _arguments as args
    git_files_data = args.parse_load_subschemas()
    plot(git_files_data)


if __name__ == '__main__':
    main()
