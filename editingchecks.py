#!/usr/bin/python3
""" editingchecks: run several automated editing checks on a text file.

    Eric M. Jackson
    start of work 2020-05-27

    Check for problems with blank space, certain punctuation (turned
    quotation marks, em- and en-dashes)
"""

# import statements
import sys
import os
import unicodedata
import datetime
from itertools import groupby
from operator import itemgetter
from inventory import getinventory, prettyprint


# Global variables for settings:

# a list containing characters whose context we want to check
CHARS_WORTH_CHECKING = set([chr(8211),  # &ndash;
                            chr(8212),  # &mdash;
                            chr(34),    # "
                            chr(39),    # '
                            chr(8216),  # &lsquo; ‘
                            chr(8217),  # &rsquo; ’
                            chr(8220),  # &ldquo; “
                            chr(8221)]) # &rdquo; ”

# TODO: add checks for 8230 … versus ..., 9674 ◊ in threes

# Punctuation in use
PUNCTUATION = set(['.', ',', '?', '!'])

# the number of characters to display to the left and right of a character of interest
SNIPPET_RADIUS = 10

# helper functions
def findall(string, character):
    """Find all positions of a character in a string"""

    # Credit to Lev Levitsky. https://stackoverflow.com/questions/11122291/how-to-find-char-in-string-and-get-all-the-indexes
    return [i for i, item in enumerate(string) if item == character]


def findall_blank(string):
    """Find all positions of blank space in a string"""

    # Based on the helper function /findall/; could be abstracted, probably
    return [i for i, item in enumerate(string) if item.isspace()]


def verify(character, left_context, right_context):
    """
    Verify that the character is properly used in this context. Currently defined only for:
        em dash
        en dash
        left single and double quote
        right single and double quote
    """
    #   different file checking for (space chr(32)), just look for doubles?
    #   likewise different checking for ... versus ellipsis?

    defined = [chr(8211), chr(8212), chr(8216), chr(8217), chr(8220), chr(8221)] # en dash, em dash, lsquo, rsquo, ldquo, rdquo

    # Verify that the character is one we can check for
    if character not in defined:
        print("Error in /verify/: Checks for {} have not been defined".format(character), file=sys.stderr)
        return False

    # Verification for em dash: must have letters to left and right (no num, no punct, no space?)
    if character == chr(8212):
        return left_context[-1].isalpha() and right_context[0].isalpha()

    # Verification for en dash: must be symmetric, either both alpha or both alpha-space?
    if character == chr(8211):
        return (left_context[-1].isalpha() and right_context[0].isalpha()) or \
               (left_context[-2].isalpha() and left_context[-1].isspace() and right_context[0].isspace() and right_context[1].isalpha())

    # Interrupted quotes should be em dash, or en dash?

    # Verification for left single quote OR left double quote: to left is space, to right is alpha (not alphanumeric?)
    if character == chr(8216) or character == chr(8220):
        if len(left_context) > 0 and len(right_context) > 0:
            return left_context[-1].isspace() and right_context[0].isalpha()
        elif len(left_context) == 0:
            return right_context[0].isalpha()
        else:
            return False

    # Verification for right single quote: to left is alpha or punct, to right is space OR (as apostrophe in contractions) left & right only alpha
    if character == chr(8217):
        if len(left_context) > 0 and len(right_context) > 0:
            return ((left_context[-1].isalpha() or left_context[-1] in PUNCTUATION) and right_context[0].isspace()) or \
                   (left_context[-1].isalpha() and right_context[0].isalpha())
        elif len(right_context) == 0:
            return left_context[-1].isalpha() or left_context[-1] in PUNCTUATION
        else:
            return False

    # Verification for right double quote: to left is alpha or punct, to right is space
    if character == chr(8221):
        if len(left_context) > 0 and len(right_context) > 0:
            return (left_context[-1].isalpha() or left_context[-1] in PUNCTUATION) and right_context[0].isspace()
        elif len(right_context) == 0:
            return left_context[-1].isalpha() or left_context[-1] in PUNCTUATION
        else:
            return False


def runchecks(lines, charlist):
    """Given a list of charcters to check, run editing checks on a file"""

    # Run check for bad blank space: two or more adjacent blanks, blanks at end of line
    print("Checking for blank space problems:")
    for index, line in enumerate(lines):
        print_for_this_line = False
        line = line.rstrip('\n')
        blanks, sequences = findall_blank(line), []
        if len(blanks) == 0:
            continue
        for k, group in groupby(enumerate(blanks), lambda x: x[0] - x[1]):
            blanks_group = list(map(itemgetter(1), group))
            if len(blanks_group) > 1:
                sequences.append(blanks_group)
        if len(sequences) > 0:
            print_for_this_line = True
            print("Line {}:".format(index+1))
            for sequence in sequences:
                print("   Position {}, blank sequence of length {}".format(sequence[0], len(sequence)))
        if blanks[-1] == len(line)-1:
            print_for_this_line = True
            print("NB: blank at end of line {}".format(index+1))
        if print_for_this_line:
            print("")
    print("Done with blanks check.\n")

    # Run additional checks for elements in charlist
    for item in charlist:
        found_none = True
        try:
            print("Searching for {}, {}:".format(item, unicodedata.name(item)))
        except ValueError:
            print("Searching for {}, (no Unicode name):".format(item))

        for index, line in enumerate(lines):
            line = line.rstrip('\n')

    # If the char is found in this line, then evaluate whether the context is correct
    # If the context isn't correct, then print the char and its context
    # For any non-ASCII chars that haven't been checked yet, just show the context
            if item in line:
                found_none = False
                print("Line {}:".format(index+1))
                item_indices = findall(line, item)
                # determine context
                for index in item_indices:
                    if index < SNIPPET_RADIUS:
                        left_extent = 0
                    else:
                        left_extent = index - SNIPPET_RADIUS

                    left_context = line[left_extent:index]
                    right_context = line[index + 1:index + 1 + SNIPPET_RADIUS]

                    if verify(item, left_context, right_context):
                        continue
                        # Removing these prints will save lots of output space
                        # print("  pos {}: okay".format(index))
                    else:
                        print("  pos {}: ...{}{}{}...".format(index, left_context, item, right_context))
                print()
        if found_none:
            # This should no longer happen if the character inventory limits the characters to check
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

    print("Started at {}, checking file {}:".format(datetime.datetime.now(), filename))
    print("Reading file for inventory... ", end='')
    try:
        with open(filename, mode='r', encoding='utf-8-sig') as file:
            # CAUTION: reading the whole file into memory
            lines = file.readlines()
            print("done.\n")
    except IOError:
        print("Could not read {}".format(filename))
        exit(1)

    char_inventory = getinventory(lines)
    prettyprint(sorted(char_inventory))
    # Limit the characters to be checked to only those that are found in the document
    chars_to_check = sorted(list(char_inventory.intersection(CHARS_WORTH_CHECKING) | char_inventory.difference([chr(i) for i in range(128)])))
    exitcode = runchecks(lines, chars_to_check)
    if exitcode == 0:
        print("Finished with no errors.")
        exit(0)
    else:
        print("Finished with errors.")
        exit(exitcode)


if __name__ == "__main__":
    main()

