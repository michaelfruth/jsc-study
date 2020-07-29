# Json Schema Containment Study (JSC-Study)

The whole pipeline is written for Python 3.7.

## Pipeline
All scripts follow the same naming structure: There is a root-script which computes/analyzes data and stores the result on disk as pickled data. To further analyze/view the pickled data, the scripts having the postfix <root-script>*_output* or <root-script>*_plot* can be used. The "_output" scripts print to console, _plot scripts print also to console and additionally show a chart. E.g. there is a script *git_file_changes.py*, which stores pickled data on disk and this data can be analyzed/viewed by *git_file_changes_output.py*.

### Scripts
Each script is controlled over the command line. Use `python <script> --help` to see all details and a description for the possible arguments.

- **git_history_cloner.py**: Clones every version (only commits made to the *master* branch) of a repository into a separate directory.
- **git_file_changes.py**: Creates a history for each file by comparing two successive repositories, created by **git_history_cloner.py**. The history of a file consists of the versions, where the file was changed/added/removed in a commit (`git diff is used)

These two scripts are the starting point of the pipeline. We need the cloned repositories from *git_history_cloner.py* and the data from *git_file_changes.py* for further analysis.

*git_history_cloner.py* creates in the specified output directory the following structure:
- output-directory
    - bare-master
    - commits

If a script requires as command line argument the path to the commit-directory, this is refereed to the "commits" directory of the output-directory as shown above.

- **schema_drafts.py**: Validates each JSON Schema document against each available validator (Draft 3, Draft 4, Draft 6, Draft 7). This is done for the original document, and if the JSON document is valid for at least one draft, the document is dereferenced (all $ref's are resolved) and checked again against each draft.
- **subschemas.py**: Checks the files for containment by using different tools. There are three different tools that can be used: jsonsubschema, is-json-schema-subset and json-schema-diff-validator.
- **filter.py**: Creates a filter which can be applied to the other scripts to filter specific data beforehand. E.g. there is a filter which allows only JSON Schema documents valid to Draft 4, Draft 6 and Draft 7 (Schema is validated against each Draft-Validator and is seen as valid, if every validation is successful) and the schema should not contain any keywords changed or introduced in Draft 5 or higher (name of the filter: Draft4).

### Which script takes which data?
The data produced by *git_file_changes.py* is the starting point for the other root-scripts. Each root-script takes the data from *git_file_changes.py* as input and produces new data that is stored (pickled) on disk. The analysis-scripts (*_output*, *_plot*) takes the data of their respective root-script.

### Filter
It is recommended,to **not** apply the filter to the root-scripts due to following reason: Do a complete analysis of the *whole* dataset (using the root-scripts). Afterwards, the filter can be applied to the analysis-scripts, so there can be controlled which data should be filtered. This is much more efficient than computing the data produced by the root-scripts again and again with different filters.

There are two kinds of filters: a "on-the-fly" filter and "file-filter". These kind of filters can be applied to almost every root-script (not recommended) and analysis-script. It is recommended to not use the "on-the-fly-filter". Each filter does the same: it filters the data beforehand and only the filtered data is processed. Each data produced by the root-scripts can be filtered, so there is no limitation. The "on-the-fly" filter computes the filtered data on runtime, so if the same on-the-fly-filter, e.g. "Draft4", is applied to two different scripts, the files to filter are computed twice, which is very inefficient. Better create a filter stored on disk beforehand (by using *filter.py*) and specify the "file-filter" when filtering data.
 
 
## Setup
Module **setup_tools.sh** is used to install the required tools which can be used for the JSC checks.

Make sure that the following tools are available in your terminal:
- npm
- git
- pipenv

## Troubleshooting

Make sure you use the right Python-Version (Python 3.7). E.g., running subschemas.py with Python 3.8 causes some errors.

### MacOS
Some modules can be executed with multiple processes, so some computations can be done in parallel. Due to the security features of MacOS for multithreading/multiprocessing, some scripts might crash by runtime. Export or start the script with the following variable: `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`.