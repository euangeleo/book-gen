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
import datetime
import htmlentities
from inventory import getinventory

# Global variables for settings:
OUTPUT_FILE = 'books/output.txt'
CHARS2CONVERT = set(['"', "'", "&", " ", "–", "—", "‘", "’", "“", "”", "…", "◊"])


# helper functions
def convert2entities(lines):
    """Convert a limited set of reserved codepoints to HTML entities"""
    # TODO
    return lines
    

def addparagraphs(lines, outfile):
    """Put HTML paragraph tags around each paragraph"""
    print("Writing to file...", end='')
    with open(outfile, mode='w', encoding='utf-8-sig') as output:
        for line in lines:
            line = line.rstrip('\n')
            output.write("<p>{}</p>\n".format(line))
    print("done.")
    return(0)


# Main
def main():
    """Convert from input text to output for ebook"""

    # Check for proper command line usage
    if len(sys.argv) is not 2:
        print("Usage: generate.py text_file")
        exit(1)

    # Check the input file before starting the checks
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

    # ASSUMPTIONS:
    #     1. Input text may already have some HTML tags,
    #        which should not be altered.
    #     2. Input text may have characters which should
    #        be converted to HTML entities (eg, &ldquo;)
    # TRANSFORMATIONS IMPLEMENTED:
    #     1. Convert a set of characters of interest into
    #        HTML entities.
    #     2. Add paragraph tags to each paragraph.
    # TO DO:
    #     1. With templates, output the text to separate
    #        HTML files as appropriate for each chapter

    encoded_lines = convert2entities(lines)
    exitcode = addparagraphs(encoded_lines, OUTPUT_FILE)
    if exitcode == 0:
        print("Finished with no errors.")
    exit(exitcode)


if __name__ == "__main__":
    main()

