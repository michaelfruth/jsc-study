#!/usr/bin/env python3
"""
Outputs statistics about the valid/invalid drafts of the data produced by schema_drafts.py.
@author: Michael Fruth
"""
import _util as util
from _model import GitFile, SchemaDrafts
from schema_drafts import ORIGINAL_SCHEMA_NAME, DEREFERENCED_SCHEMA_NAME


class CountValue:
    def __init__(self, schema_draft: SchemaDrafts):
        self.schema_draft = schema_draft
        self.schema_tag = schema_draft.git_history_file.schema_tag()
        self.file = schema_draft.git_history_file.full_path


class Counter:
    """
    Contains statistics about the occurring schemas, the total files, total valid/invalid schemas, statistics about the
    "name" ... The "name" is the name set in the analysis (module schema_drafts). It is set e.g. to "NORMAL" for the
    validation of the original json content or "NORMAL_REFS" for validation of the dereferenced json content.
    """

    def __init__(self):
        self.files = 0
        self.names = {}
        self.valid_drafts = {}
        self.invalid_drafts = {}

    def incr_files(self):
        self.files += 1

    def incr_name(self, name):
        if name not in self.names:
            self.names[name] = 0
        self.names[name] += 1

    def incr_valid_draft(self, name, draft, count_value: CountValue):
        self._incr_draft(name, draft, self.valid_drafts, count_value)

    def incr_invalid_draft(self, name, draft, count_value: CountValue):
        self._incr_draft(name, draft, self.invalid_drafts, count_value)

    def _incr_draft(self, name, draft, d, count_value: CountValue):
        if name not in d:
            d[name] = {}
        if draft not in d[name]:
            d[name][draft] = []
        d[name][draft].append(count_value)


counter = Counter()


def count_schema_draft(schema_draft: SchemaDrafts):
    """
    Count the vlaues of a single SchemaDrafts-object to the statistics.
    :param schema_draft: The SchemaDrafts-object
    :return: None
    """
    counter.incr_files()

    for name, drafts in schema_draft.drafts.items():
        if not all(none_or_ex is not None for none_or_ex in drafts.values()):
            # Schema must be valid to at least one validator to be counted as valid
            counter.incr_name(name)

        for draft, none_or_ex in drafts.items():
            if none_or_ex is None:
                counter.incr_valid_draft(name, draft, CountValue(schema_draft))
            else:
                counter.incr_invalid_draft(name, draft, CountValue(schema_draft))


def count(git_file: GitFile, schema_drafts: [SchemaDrafts]):
    """
    Counts the result of the SchemaDrafts-objects.
    :param git_file: The git file
    :param schema_drafts: The SchemaDrafts-objects to count
    :return: None
    """
    schema_draft: SchemaDrafts
    for schema_draft in schema_drafts:
        count_schema_draft(schema_draft)


def output_total_valid_invalid_schemas():
    """
    Outputs the valid(/invalid schemas based on the different steps of the manual "draft detection".
    :return: None
    """
    print("Valid/Invalid schemas in different steps:")
    print("Total Files: {}".format(counter.files))
    count_before = counter.files
    for name, count in counter.names.items():
        print("{}: {}".format(name, count))
        print("{}: {} Fails".format(name, count_before - count))
        count_before = count


def output_invalid_drafts(show_files):
    print("Invalid schemas by drafts:")
    _output_valid_or_invalid_drafts(counter.invalid_drafts, show_files)


def output_valid_drafts():
    print("Valid schemas by drafts:")
    _output_valid_or_invalid_drafts(counter.valid_drafts)


def _output_valid_or_invalid_drafts(valid_or_invalid_drafts, show_files=False):
    for name, drafts in valid_or_invalid_drafts.items():
        print("{}: {} (Total)".format(name, counter.names[name]))
        for draft, schema_tags in drafts.items():
            count = len(schema_tags)
            files_by_schema_tags = _group_files_by_schema_tag(schema_tags)
            print("{} - {}: {}".format(name, draft, count))
            for schema_tag, files in files_by_schema_tags.items():
                print("\t{}: {}".format(schema_tag, len(files)))
                if show_files:
                    [print("\t\t{}".format(file)) for file in files]


def _group_files_by_schema_tag(count_values: [CountValue]):
    counted_schema_tags = {}

    count_value: CountValue
    for count_value in count_values:
        schema_tag = count_value.schema_tag
        if schema_tag not in counted_schema_tags:
            counted_schema_tags[schema_tag] = []
        counted_schema_tags[schema_tag].append(count_value.file)
    return counted_schema_tags


def _count_all_valid_invalid_drafts_for_name(git_files_data, lookup_name, lookup_drafts: []):
    """
    Counts the invalid/valid drafts for a given name (lookup_name) and for only specific drafts (validate_drafts).
    :param git_files_data: The data containing the SchemaDrafts-objects.
    :param lookup_name: The name for which the valid/invalid drafts should be counted.
    :param lookup_drafts: The drafts to consider
    :return: The number of valid/invalid drafts, validated by a given name (lookup_name) and only considering specific draft version (validate_drafts).
    """
    valid_draft_schemas = 0
    invalid_draft_schemas = 0

    for git_file, invalid_schema_drafts in git_files_data:
        invalid_schema_draft: SchemaDrafts
        for invalid_schema_draft in invalid_schema_drafts:
            valid, invalid = _all_drafts_valid_or_valid_for_name(invalid_schema_draft.drafts,
                                                                 lookup_drafts,
                                                                 lookup_name)
            valid_draft_schemas += valid
            invalid_draft_schemas += invalid

    return valid_draft_schemas, invalid_draft_schemas


def _all_drafts_valid_or_valid_for_name(drafts_by_name, lookup_drafts: [], lookup_name):
    """
    Checks if drafts_by_name contains for the specific lookup_drafts only valid drafts (for the specific name (lookup_name))
    :param drafts_by_name: The dictionary which groups the drafts results by name.
    :param lookup_drafts: The drafts to lookup for
    :param lookup_name: The name to lookup for
    :return: (1,0) if everything is valid, (0,1) otherwise
    """
    if lookup_name in drafts_by_name:
        drafts = drafts_by_name[lookup_name]

        all_none = True
        for draft_name in lookup_drafts:
            if drafts[draft_name] is not None:
                # Exception occurred, so the schema was not valid to this specific draft.
                all_none = False
                break

        if all_none:
            return 1, 0

    return 0, 1


def output_specified_schema_drafts(git_files_data):
    """
    Prints a statistic about the schema tags set in the files.
    :param git_files_data: The files to check.
    :return: None
    """
    schema_tags = {}
    for git_file, invalid_schema_drafts in git_files_data:
        invalid_schema_draft: SchemaDrafts
        for invalid_schema_draft in invalid_schema_drafts:
            schema_tag = invalid_schema_draft.git_history_file.schema_tag()
            if schema_tag not in schema_tags:
                schema_tags[schema_tag] = 0
            schema_tags[schema_tag] += 1

    print("Specified Schema Tags (Total files: {}):".format(counter.files))
    total_value = 0
    for schema_tag, value in schema_tags.items():
        print("{}: {}".format(schema_tag, value))
        total_value += value
    print("Total: {}".format(total_value))


def main():
    import _arguments as args
    show_files, git_files_data = args.parse_load_schema_drafts(
        {
            args.CLAShowFiles: args.CLAShowFiles()
        }
    )

    for git_file, schema_drafts in git_files_data:
        count(git_file, schema_drafts)

    output_total_valid_invalid_schemas()
    print("#" * 50)
    output_valid_drafts()
    print("#" * 50)
    output_invalid_drafts(show_files)

    print("#" * 50)
    validate_drafts = [util.DRAFT4_NAME, util.DRAFT6_NAME, util.DRAFT7_NAME]
    print("Schemas valid/invalid to all drafts:")
    print(validate_drafts)

    normal_valid, normal_invalid = _count_all_valid_invalid_drafts_for_name(git_files_data,
                                                                            ORIGINAL_SCHEMA_NAME,
                                                                            validate_drafts)
    print("NORMAL valid: {} | invalid: {}".format(normal_valid, normal_invalid))

    normal_refs_valid, normal_refs_invalid = _count_all_valid_invalid_drafts_for_name(git_files_data,
                                                                                      DEREFERENCED_SCHEMA_NAME,
                                                                                      validate_drafts)
    print("NORMAL REFS valid: {} | invalid: {}".format(normal_refs_valid, normal_refs_invalid))

    print("#" * 50)
    output_specified_schema_drafts(git_files_data)


if __name__ == '__main__':
    main()
