#!/usr/bin/python3
""" generate.py: Generate an eBook and print-ready book format
        from a manuscript in Markdown

    Eric M. Jackson
    start of work 2020-07-02

    Generate at least part of the formatting necessary for ebook and PDF formats
"""

# import statements
import sys
import os
import unicodedata
import datetime

# Global variables for settings:
OUTPUT_FILE = 'output.txt'


# helper functions
def addparagraphs(lines):
    """Put HTML paragraph tags around each paragraph"""
    print("Writing to file...", end='')
    with open(OUTPUT_FILE, mode='w', encoding='utf-8-sig') as output:
        for line in lines:
            line = line.rstrip('\n')
            output.write("<p>{}</p>\n".format(line))
    print("done.")
    return(0)


# Main
def main():
    """Run editing checks on a text document"""

    # Check for proper command line usage
    if len(sys.argv) is not 2:
        print("Usage: generate.py text_file")
        exit(1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print("File path {} does not exist. Exiting...".format(filename))
        exit(1)

    print("Started at {}, checking file {}:".format(datetime.datetime.now(), filename))
    print("Reading file... ", end='')
    try:
        with open(filename, mode='r', encoding='utf-8-sig') as file:
            # CAUTION: reading the whole file into memory
            lines = file.readlines()
            print("done.\n")
    except IOError:
        print("Could not read {}".format(filename))
        exit(1)

    exitcode = addparagraphs(lines)
    if exitcode == 0:
        print("Finished with no errors.")
    exit(exitcode)


if __name__ == "__main__":
    main()

