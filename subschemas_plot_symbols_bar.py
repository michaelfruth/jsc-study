#!/usr/bin/env python3
"""
Outputs and plots statistics about the different decisions of a particular JSC-tool (data from subschemas.py).
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
        symbol_name = subschema_util.get_name_for_symbol(symbol)
        pandas_data.append(symbol_name)

    df = pd.DataFrame(pandas_data, columns=['Symbol'])
    return df


def plot(git_files_data):
    dfs = []
    total_pairs = 0
    for git_file, subschemas in git_files_data:
        dfs.append(_create_df(git_file, subschemas))
        total_pairs += len(subschemas)

    df = pd.concat(dfs, ignore_index=True)
    df_len = len(df)
    # Count the symbols
    df = df['Symbol'].value_counts().rename_axis('Symbol').reset_index(name='Counts')
    # Compute the percentage of the symbol occurrences
    df['Percentage'] = df['Counts'] / float(df_len) * 100

    # Be careful! 796 is hardcoded. Maybe specify some other value if you want the percentage to some other "base"
    # 796 was used to get the percentage based on the original file set, even if a filter is applied
    df['Percentage Base 796'] = df['Counts'] / 796.0 * 100.0

    print(df)
    print(df.round(1))
    print("Total Counts: {}".format(df_len))

    fig = px.bar(df, x='Symbol', y='Counts')
    fig.update_layout(title='All | Total Subschemas: {} | Total Symbols: {}'.format(total_pairs, len(df)))
    fig.show()


def main():
    import _arguments as args
    git_files_data = args.parse_load_subschemas()

    plot(git_files_data)


if __name__ == '__main__':
    main()
