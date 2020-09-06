import logging

import pandas as pd
import plotly.express as px

import _util as util
from _model import GitFile, SchemaDrafts

logger = logging.getLogger(__name__)
_DRAFT_TO_CHECK = util.DRAFT4_NAME


def _create_df(git_file: GitFile, schema_drafts: [SchemaDrafts]):
    pandas_data = []
    schema_draft: SchemaDrafts
    for schema_draft in schema_drafts:
        for name, drafts in schema_draft.drafts.items():
            none_or_ex = schema_draft.drafts[name][_DRAFT_TO_CHECK]
            if none_or_ex is not None:
                none_or_ex = _DRAFT_TO_CHECK + " " + none_or_ex[0]  # 0 = type, 1 = message
                name = _DRAFT_TO_CHECK + " " + name
                pandas_data.append((schema_draft.git_history_file.full_path,
                                    name, none_or_ex,
                                    name + " | " + none_or_ex))
                break  # Break loop to get the next file
    df = pd.DataFrame(pandas_data, columns=['File', 'Invalid_Type_Name', 'Exception', 'Invalid_Type_Name_Exception'])
    return df


def plot(git_files_data: [GitFile, [SchemaDrafts]]):
    dfs = []
    total_elements = 0
    for git_file, schema_drafts in git_files_data:
        total_elements += len(schema_drafts)
        dfs.append(_create_df(git_file, schema_drafts))

    df = pd.concat(dfs, ignore_index=True)

    fig = px.pie(df, values=[1] * len(df), names='Invalid_Type_Name_Exception')
    fig.update_layout(title='Combined | Total Elements: {} | Elements: {}'.format(total_elements, len(df)))
    fig.show()

    fig = px.pie(df, values=[1] * len(df), names='Invalid_Type_Name')
    fig.update_layout(title='Invalid by name | Total Elements: {} | Elements: {}'.format(total_elements, len(df)))
    fig.show()

    fig = px.pie(df, values=[1] * len(df), names='Exception')
    fig.update_layout(title='Exception | Total Elements: {} | Elements: {}'.format(total_elements, len(df)))
    fig.show()


def main():
    import _arguments as args

    git_files_data = args.parse_load_schema_drafts()
    plot(git_files_data)


if __name__ == "__main__":
    main()
