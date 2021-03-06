#!/usr/bin/python3
""" inventory: generate an inventory of characters in a text file.

    Eric M. Jackson
    start of work 2020-05-06

    Read in a user-provided file, determine the set of all characters
    used in the file, and print them.
"""

# import statements
import sys
import os
import unicodedata
import datetime

# Global variables for settings:

# helper functions
def getinventory(lines):
    """Given a filename, generate the character inventory of that file"""

    inventory = set([])
    for line in lines:
        inventory.update(list(line))

    return inventory


def prettyprint(char_list):
    """Print a list of characters in an easy to read way. Assume the list is sorted."""

    print('ASCII LETTERS:')

    printed_something = False
    for index in range(65, 91):
        if chr(index) in char_list:
            if chr(index).lower() in char_list:
                print(chr(index), chr(index).lower())
            else:
                print(chr(index))
            printed_something = True
        elif chr(index).lower() in char_list:
            print(' ', chr(index).lower())
            printed_something = True
        elif index == 90 and not printed_something:
            print("(none)")

    print('\nPUNCTUATION, NUMBERS, SYMBOLS:')

    indices = list(range(33, 65)) + list(range(91, 97)) + list(range(123, 128))

    printed_something = False
    for index in indices:
        if chr(index) in char_list:
            print(chr(index))
            printed_something = True
        elif index == 127 and not printed_something:
            print("(none)")

    print('\nNON-PRINTING AND WHITESPACE:')

    printed_something = False
    for index in range(1, 33):
        if chr(index) in char_list:
            if index == 9:
                print("\\t, index {}, tab".format(index))
                printed_something = True
                continue
            elif index == 10:
                print("\\n, index {}, newline".format(index))
                printed_something = True
                continue
            else:
                try:
                    print("{}, index {}, {}".format(chr(index), index, unicodedata.name(chr(index))))
                    printed_something = True
                except ValueError:
                    print("{}, index {}, (no Unicode name)".format(chr(index), index))
                    printed_something = True
        elif index == 32 and not printed_something:
            print("(none)")

    print('\nABOVE ASCII:')

    above_ascii = (x for x in char_list if ord(x) > 127)

    if above_ascii:
        for char in above_ascii:
            try:
                print("{}, index {}, {}".format(char, ord(char), unicodedata.name(char)))
                printed_something = True
            except ValueError:
                print("{}, index {}, (no Unicode name)".format(char, ord(char)))
                printed_something = True
    else:
        print("(none)")

    print()


def main():
    """Generate a character inventory"""

    # Check for proper command line usage
    if len(sys.argv) is not 2:
        print("Usage: inventory.py text_file")
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

    prettyprint(sorted(getinventory(lines)))
    exit(0)


if __name__ == "__main__":
    main()

