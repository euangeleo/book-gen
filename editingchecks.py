#!/usr/bin/python3
""" editingchecks: run several automated editing checks on a text file.

    Eric M. Jackson
    start of work 2020-05-27

    Check for problems with whitespace, certain punctuation (turned
    quotation marks, em- and en-dashes)
"""

# import statements
import sys
import os
import unicodedata
from inventory import getinventory, prettyprint

# Global variables for settings:
CHARS_WORTH_CHECKING = set([chr(8211), chr(8212), chr(34), chr(39)]) # &ndash; &mdash; " '

# helper functions
def runchecks(filename, charlist):
    """"Given a list of charcters to check, run editing checks on a file"""

    with open(filename, mode='r', encoding='utf-8-sig') as file:
        print("Reading file for search...", end = '')
        # CAUTION: reading the whole file into memory
        lines = file.readlines()
        print("done.\n")

    for item in charlist:
        found_none = True
        try:
            print("Searching for {}, {}:".format(item, unicodedata.name(item)))
        except ValueError:
            print("Searching for {}, (no Unicode name):".format(item))

        for index, line in enumerate(lines):
            # If the char is found in this line, then print the line
            if item in line:
                found_none = False
                print("Line {}: {}".format(index+1, line))
        if found_none:
           print("None found.")
        print()
    return 0


# Main
def main():
    """Run editing checks on a text document"""

    # Check for proper command line usage
    if len(sys.argv) is not 2:
        print("Usage: editingchecks.py text_file")
        exit(1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print("File path {} does not exist. Exiting...".format(filename))
        exit(1)

    char_inventory = getinventory(filename)
    prettyprint(sorted(char_inventory))
    # Limit the characters to be checked to only those that are found in the document
    chars_to_check = sorted(list(char_inventory.intersection(CHARS_WORTH_CHECKING)))
    exitcode = runchecks(filename, chars_to_check)
    if exitcode == 0:
        print("Finished with no errors.")
    exit(exitcode)


if __name__ == "__main__":
    main()
