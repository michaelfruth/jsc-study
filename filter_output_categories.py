"""
Outputs the categories of the filtered files. This categorization is used:
https://github.com/miniHive/schemastore-analysis/blob/master/categorisation.CSV
@author: Michael Fruth
"""
import csv
import difflib
import logging
from os import path

import filter_filters

logger = logging.getLogger(__name__)


def match(invalid_filenames, categories):
    """
    Tries to match the filenames with the categories. A heuristic (SequenceMatcher) is used.
    :param invalid_filenames: The filenames to find a category for.
    :param categories: A dicty with the filename as key and the category as value.
    :return: None.
    """
    min_ratio_limit = 0.8  # Minimum 80% must match

    resulting_categories = {}
    for filename in invalid_filenames:

        similar_filtered_filename = filename.lower()  # Lower to be case-insensitive
        # Remove fileending
        if similar_filtered_filename.endswith(".json"):
            similar_filtered_filename = similar_filtered_filename[:-len(".json")]

        highest_ratio = -1
        highest_ratio_file_categorie = None

        for file_category in categories:

            similar_filename_category = file_category.lower()  # Lower to be case-insensitive
            # Remove fileending
            if similar_filename_category.endswith(".json"):
                similar_filename_category = similar_filename_category[:-len(".json")]
            elif similar_filename_category.endswith(".yml"):
                similar_filename_category = similar_filename_category[:-len(".yml")]

            # Apply the heuristic
            ratio = difflib.SequenceMatcher(None, similar_filtered_filename, similar_filename_category).ratio()

            if ratio > highest_ratio:
                # New highest ratio found
                highest_ratio = ratio
                highest_ratio_file_categorie = file_category

            if highest_ratio < min_ratio_limit and similar_filename_category in similar_filtered_filename:
                # Make matching a bit "weaker". If no highest-ratio was found until now and the word of the category
                # is in the name of the filename - use this as new highest ratio.
                # Set the ratio to the min_ratio_limit, because if a "real" match is found, this will be used instead.
                highest_ratio = min_ratio_limit
                highest_ratio_file_categorie = file_category

            # Match sarif manually
            if similar_filtered_filename.startswith("sarif"):
                highest_ratio = min_ratio_limit
                highest_ratio_file_categorie = "sarif-1.0.0.json"
            # Match swagger manually
            if similar_filtered_filename.startswith("swagger"):
                highest_ratio = min_ratio_limit
                highest_ratio_file_categorie = "Swagger API 2.0"

        # Save category if a match was found that has a higher ratio than the limit.
        if highest_ratio >= min_ratio_limit:
            category = categories[highest_ratio_file_categorie]
            if category not in resulting_categories:
                resulting_categories[category] = []
            resulting_categories[category].append((filename, highest_ratio, highest_ratio_file_categorie))

    print("Unique files: {}".format(len(invalid_filenames)))
    print("Filtered categories:")

    for cat in resulting_categories:
        print("{}: {}".format(cat, len(resulting_categories[cat])))


"""
 for cat in resulting_categories:
        print("{}".format(cat))
        for filename, ratio, file_categorie in resulting_categories[cat]:
            print("\t{}, {}".format(filename, file_categorie))
"""


def get_categories():
    """
    Loads all categories of the file "categorisation.csv".
    https://github.com/miniHive/schemastore-analysis/blob/master/categorisation.CSV
    :return: A dictionary with the filename as key and the category as value.
    """
    with open('categorisation.csv') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        next(readCSV)  # Skip header

        files_per_categorie = {}
        for row in readCSV:
            files_per_categorie[row[0]] = row[1]
        return files_per_categorie


def get_filenames(draft_filter: filter_filters.FileDraftFilter):
    """
    Returns all filenames stored as invalid files of the passed filter.
    :param draft_filter: The filter which contains the all files.
    :return: A sorted list containg the filenames of the stored files of the filter.
    """
    invalid_files = list(map(lambda f: path.basename(f.full_path), draft_filter.invalid_files))
    invalid_files.sort()
    return invalid_files


def main():
    import _arguments as args
    draft_filter = args.parse_load_filter()
    filenames = get_filenames(draft_filter)
    categories = get_categories()

    print("Total files: {}".format(len(draft_filter.invalid_files)))
    match(filenames, categories)


if __name__ == "__main__":
    main()
