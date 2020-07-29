#!/usr/bin/env python3
"""
Find all keywords added or introduced in JSON Schema Draft 5 or higher.
@author: Michael Fruth
"""
import logging

from jsonschema import Draft4Validator, Draft6Validator, Draft7Validator

import _util as util
from _model import GitFile, GitHistoryFile

logger = logging.getLogger(__name__)

# https://json-schema.org/draft-06/json-schema-release-notes.html
draft4_to_draft6_incompatible = [
    "exclusiveMinimum",
    "exclusiveMaximum"
]

draft4_to_draft6_added = [
    'propertyNames',
    "contains",
    "const",
    # "examples", <- no semantics
]

# jsonsubschema ignores "format", so we do not strip new formats
draft4_todraft6_format = [
    ("format", "uri-reference"),
    ("format", "uri-template"),
    ("format", "json-pointer"),
]

# https://json-schema.org/draft-07/json-schema-release-notes.html#keywords
draft6_to_draft7_added = [
    # "$comment", <- no semantics
    "if",
    "then",
    "else",
    "readOnly",
    "writeOnly"
    # "contentMediaType",  <- no semantics; will be ignored by validation (see docu)
    # "contentEncoding"  <- no semantics; will be ignored by validation (see docu)
]

# jsonsubschema ignores "format", so we do not strip new formats
draft6_to_draft7_format = [
    ("format", "iri"),
    ("format", "iri-reference"),
    ("format", "uri-template"),
    ("format", "idn-email"),
    ("format", "idn-hostname"),
    ("format", "json-pointer"),
    ("format", "relative-json-pointer"),
    ("format", "regex"),
    ("format", "date"),
    ("format", "time"),
]


def _find_recursive_or_manually(json_content, lookup_keyword):
    """
    Searches for a keyword in the given json_content. If a recursion error while searching occurres, a manual search is done.
    :param json_content: The json content in which the keyword will be searched.
    :param lookup_keyword: The keyword to search for.
    :return: A list containg the findings or an empty list otherwise.
    """
    try:
        # Search for keyword in JSON. This can lead to a recursion error (because a recursive search is used).
        return list(util.find_in_json_recursive(json_content, lookup_keyword, yield_parent=True))
    except RecursionError:
        # Recursion Error occured - trying to find the keyword manually
        logger.warning("RecursionError - trying to find keyword '{}' manually.".format(keyword_not_in_draft4))

        json_str = str(json_content)
        # E.G. keyword = not; check if "not": is contained in the json_str.
        # This can potentially filter more results than expected, e.g. if "not": is contained in a
        # description/comment.. But this doesn't filter less results, so it's almost ok.
        if '"{}":'.format(lookup_keyword) in json_str:
            return [lookup_keyword]
    return []


def check_history_json(json_content):
    """
    Checkst if some keywords added or changed after Draft4 are contained in the json_content (dictionary).
    :param json_content: The json content to check.
    :return: The added keywords and incompatible keywords found and the schema tag.
    """
    # File must be valid to Draft 4, 6 and 7 in order to search for keywords, because only documents valid to these
    # darfts are used. This script should result only the numbers for the keywords; the filtering based on drafts
    # is done in schema_drafts.
    try:
        Draft4Validator.check_schema(json_content)
        Draft6Validator.check_schema(json_content)
        Draft7Validator.check_schema(json_content)
    except Exception as e:
        return

    schema_tag = util.schema_tag(json_content)
    if schema_tag is not None and "/draft-04/" in schema_tag:
        # Draft-04 documents doesn't include keywords for Draft 6/7, because they are Draft4...
        return

    draft4_to_draft7_added = []  # All keywords added from draft 4 until draft 7
    draft4_to_draft7_added.extend(draft4_to_draft6_added)
    draft4_to_draft7_added.extend(draft6_to_draft7_added)

    addeds = []
    for keyword_not_in_draft4 in draft4_to_draft7_added:
        findings = _find_recursive_or_manually(json_content, keyword_not_in_draft4)

        if len(findings) > 0:  # Found some new keyword
            for f in findings:
                addeds.append((keyword_not_in_draft4, f))

    # Filter "if" keywords when no "then" or "else" is present
    added_keywords = set(map(lambda data: data[0], addeds))
    if "if" in added_keywords and not ("then" in added_keywords or "else" in added_keywords):
        # "if" is present but no "then" or "else" - remove "if" from list because the new "if then else" construct
        # introduced in draft 7 is not used, because otherwise "then" or "else" would also be present
        addeds = list(filter(lambda data: data[0] != "if", addeds))

    draft4_to_draft7_incompatibles = []  # All keywords made incompatible from draft 4 until draft 7
    draft4_to_draft7_incompatibles.extend(draft4_to_draft6_incompatible)

    incompatibles = []
    for keyword_incompatible_to_draft4 in draft4_to_draft7_incompatibles:
        # Search for incompatible keywords
        findings = _find_recursive_or_manually(json_content, keyword_incompatible_to_draft4)

        if len(findings) > 0:  # Found incompatible keywords
            for f in findings:
                incompatibles.append((keyword_incompatible_to_draft4, f))

    # Return only a result if something was found.
    if len(addeds) > 0 or len(incompatibles) > 0:
        return addeds, incompatibles, schema_tag


def check_history_file(git_history_file: GitHistoryFile):
    """
    Loads the specific file and checks to content if some keywords added or changed after Draft4 are contained.
    :param git_history_file: The specific file to check.
    :return: The added keywords and incompatible keywords found and the schema tag.
    """
    logger.info("Checking file {}".format(git_history_file.full_path))
    content, json_content = util.load_json(git_history_file.full_path)[0:2]
    return check_history_json(json_content)


def output_addeds_incompatibles(git_history_file, schema_tag, addeds, incompatibles):
    # Found incompatible/added keyword in schema != draft-04
    print(git_history_file.full_path)
    print(schema_tag)
    if len(addeds) > 0:
        for a, b in addeds:
            print("ADDED " + str(a) + " " + str(b))
    if len(incompatibles) > 0:
        for a, b in incompatibles:
            print("INCOMPATIBLES " + str(a) + " " + str(b))
    print()


def check_git_file(git_file: GitFile):
    """
    Checks each version of this GitFile if it contains some keywords changed or added after Draft4.
    :param git_file: The GitFile of which all versions should be checked.
    :return: The number of added/incompatible keywords found.
    """
    added_total = 0
    incompatible_total = 0

    h: GitHistoryFile
    for h in git_file.history:
        result = check_history_file(h)

        if result:  # Result contains information
            addeds, incompatibles, schema_tag = result
            if len(addeds) > 0:
                added_total += 1
            if len(incompatibles) > 0:
                incompatible_total += 1

            # Print to console
            output_addeds_incompatibles(h, schema_tag, addeds, incompatibles)

    return added_total, incompatible_total


def main():
    import _arguments as args
    git_files, git_deleted_files = args.parse_load_file_changes()

    added_total = 0
    incompatible_total = 0

    for git_file in git_files:
        addeds, incompatibles = check_git_file(git_file)

        added_total += addeds
        incompatible_total += incompatibles

    print("ADDED TOTAL: " + str(added_total))
    print("INCOMPATIBLE TOTAL: " + str(incompatible_total))


if __name__ == "__main__":
    main()
