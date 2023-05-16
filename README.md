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

# Study

Here are the commands and used data presented to reproduce the results of our study.

## Preparation

### Schemastore

1. Check out the SchemaStore from GitHub (https://github.com/SchemaStore/schemastore)
   `git clone https://github.com/SchemaStore/schemastore`
2. Revert the repository to the commit used for our study: 
   `git checkout c48c727`
3. Clone each commit made to the repository in a separate directory:
   `python git_history_cloner.py -g <path-to-cloned-schemastore-repository> -od <some-output-directory>`
   This command may take a while and needs about 24GB of disk space.

These steps are mandatory and have to be done on your machine. For automatic preparation, the script *preparation.sh* can be used. The steps to generate further data are optional. The precomputed data in the *data* directory can be used. For the following instructions, the name of the precomputed data is given first and the steps to create this data are stated afterwards.

For the commands below, ee use the environment variable `$COMMIT_DIR` to specify the directory containing all commits. In our case, the variable has the value `schemastore_history/commits` (e.g. `export COMMIT_DIR=schemastore_history/commits`).

### Base data

*data/data-06-19-2020.pick*

Get all changed files out of the history. This is the data which is used for further analysis:

`python git_file_changes.py -c $COMMIT_DIR -o <output-file>`

### Filter

- *data/filter_draft4.pick* - only valid Draft4 documents
- *data/filter_draft4_no-jsonref.pick* - a subset where all references are non-recursive, document-internal or URLs, and can be resolved (referred to as *RF* in figure 4 of the study)
- *data/filter_draft4_no-not.pick* - without *not* keyword (referred to as *NF* in figure 4 of the study)
- *data/filter_draft4_no-jsonref_no-not.pick* - the combination of *RF* and *NF*  (referred to as *RF+NF* in figure 4 of the study)

Create the filter out of the data based on specific conditions (only valid Draft4 documents, no *not* keyword, only valid *$ref*)

`python filter.py -f data/data-06-19-2020.pick -c $COMMIT_DIR -p src/schemas/json/ -o <output-name> -filter-on-the-fly <filter-condition>`

See the help text of *filter.py* (`python filter.py --help`) for the available filter conditions.

## Docker
For reproducibility, a Docker container can be created in which all commands below can be executed.

```
# 1. Build docker container
docker build -t jsc-study .

# 2. Run a container
docker run -it -d --name jsc-study jsc-study 

# 3. Access container
docker exec -it jsc-study /bin/bash

# 4. Activate pipenv shell
pipenv shell

# 5. Prepare all data (this step only has to be done once)
./preparation.sh

# 6. Now, the commands below can be executed within the container.
```

## Study data

The filter *filter_draft4.pick* is applied to **every** script to get only the documents valid to Draft4. Details are described in section *3.2 Analysis Process* of the paper. 

The data is available in the *output* directory. In the beginning of each file is the command given to produce this data.

### General numbers

- *output/general_numbers.txt*

`python git_file_changes_output.py -f data/data-06-19-2020.pick -c $COMMIT_DIR -p src/schemas/json/ -filter-file data/filter_draft4.pick`

View the overall numbers of different documents, historic versions, ...

#### Filtered data based on keyword

- *output/filter_keyword.txt*

` python draft4_new_keywords_finder.py -f data/data-06-19-2020.pick -p src/schemas/json/ -c $COMMIT_DIR`

The exakt number of files filtered based on introduced keywords after Draft4 (mentioned in section *3.2* of the paper).

### Number of valid/invalid schemas

- *data/schema_drafts.pick*

 `python schema_drafts.py -c $COMMIT_DIR -p src/schemas/json/ -f data/data-06-19-2020.pick -o schema_drafts.pick`

- *output/schema_drafts.txt*

`python schema_drafts_output_statistics.py -f data/schema_drafts.pick -c $COMMIT_DIR -filter-file data/filter_draft4.pick`

Statistics about the distribution of the different schema drafts of the SchemaStore documents, how many schemas contain an invalid reference, ...

`python schema_drafts_plot.py -f data/schema_drafts.pick -c $COMMIT_DIR`

Statistics about the different error cases (Recursion Error, Reference Error, ...).

### 4.1 RQ1: What is the real-world applicability of JSC-tools?

- *data/subschemas_self_python-jsonsubschema.pick* - data from Tool A
- *data/subschemas_self_npm-is-json-schema-subset.pick* - data from Tool B

Data generation: ` python subschemas.py -f data/data-06-19-2020.pick -c $COMMIT_DIR -p src/schemas/json/ -o <output-file> -si <tool-to-check-containment> -self`

The flag `-self` is important to check each schema against itself. Otherwise successive schemas will be compared.

- *data/rq1_applicability.txt*

`python subschemas_output_common_symbols.py -f data/subschemas_self_python-jsonsubschema.pick -f2 data/subschemas_self_npm-is-json-schema-subset.pick -c $COMMIT_DIR -filter-file data/filter_draft4.pick`

The data for table 1a.

### 4.2 RQ2: Which language features are difficult to handle?

The data generated in *4.1 RQ1* is used.

#### Figure 3 - Top 3 Errors

- *output/rq2_top3-failures_tool-A.txt*
- *output/rq2_top3-failures_tool-B.txt*

Tool A: `python subschemas_plot_exception_types.py -f data/subschemas_self_python-jsonsubschema.pick -c $COMMIT_DIR -filter-file data/filter_draft4.pick`

Tool B: `python subschemas_plot_exception_types.py -f data/subschemas_self_npm-is-json-schema-subset.pick -c $COMMIT_DIR -filter-file data/filter_draft4.pick`

#### Figure 4 - problematic operators

- *data/subschemas_python-jsonsubschema.pick* - data from Tool A
- *data/subschemas_npm-is-json-schema-subset.pick* - data from Tool B

Data should be generated as in RQ1, but just *without* the `-self` flag.

- Tool A:
  - *output/rq2_problematic-operator_EC_tool-A.txt*
  - *output/rq2_problematic-operator_NF_tool-A.txt*
  - *output/rq2_problematic-operator_RF_tool-A.txt*
  - *output/rq2_problematic-operator_RF+NF_tool-A.txt*
- Tool B:
  - *output/rq2_problematic-operator_EC_tool-B.txt*
  - *output/rq2_problematic-operator_NF_tool-B.txt*
  - *output/rq2_problematic-operator_RF_tool-B.txt*
  - *output/rq2_problematic-operator_RF+NF_tool-B.txt*



Filter-Name-Mapping:

- **EC** = *data/filter_draft4.pick*
- **NF** = *data/filter_draft4_no-not.pick*
- **RF** = *data/filter_draft4_no-jsonref.pick*
- **RF+NF** = *data/filter_draft4_no-jsonref_no-not.pick*

Apply *each* filter to the following command to get the result of figure 4.

##### Tool A:

`python subschemas_plot_symbols_bar.py -f data/subschemas_python-jsonsubschema.pick -c $COMMIT_DIR -filter-file <filter>`

##### Tool B:

`python subschemas_plot_symbols_bar.py -f data/subschemas_npm-is-json-schema-subset.pick -c $COMMIT_DIR -filter-file <filter>`

### 4.3 RQ3: What is the degree of consensus among JSC-tools?

The data generated in *4.2 RA2 - Figure 4* is used.

- *output/rq3_consensus.txt*

`python subschemas_output_common_symbols.py -f data/subschemas_python-jsonsubschema.pick -f2 data/subschemas_npm-is-json-schema-subset.pick -c $COMMIT_DIR -filter-file data/filter_draft4.pick`

The data for table 1b.

### Section 5 - Discussion of Results and Research Opportunities - Categorization

- *output/categorization_NF.txt*
- *output/categorization_RF.txt*
- *output/categorization_RF+NF.txt*

As `<filter>`, use the RF, NF or RF+NF filter (as described in *4.2 RA2 - Figure 4*)

` python filter_output_categories.py -f <filter> -c $COMMIT_DIR`

The statistics about the categorisation of the filtered data.

