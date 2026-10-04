"""UnicodeSummary: Print a summary of the Unicode characters in text

Usage: This command will accept text typed on the command line, text
that is piped from the command line, or a filename.

host:~/$ python unicodesummary.py "Héllo — café!"

host:~/$ echo "Héllo — café!" | python unicodesummary.py

host:~/$ python unicodesummary.py --file my_text.txt
"""

import unicodedata
import sys
import argparse
from collections import defaultdict
from typing import Dict, Tuple, Set, Iterable, List


class UnicodeSummary:
    """
    Analyze and print a readable summary of Unicode characters in text.
    """

    UNICODE_BLOCKS: Dict[str, Tuple[int, int]] = {
        "Latin-1 Supplement": (0x0080, 0x00FF),
        "Latin Extended-A+B": (0x0100, 0x024F),
        "IPA Extensions": (0x0250, 0x02AF),
        "Spacing Modifier Letters": (0x02B0, 0x02FF),
        "Combining Diacritical Marks": (0x0300, 0x036F),
        "Combining Diacritical Marks Extended": (0x1AB0, 0x1AFF),
        "Phonetic Extensions+Supplement": (0x1D00, 0x1DBF),
        "Combining Diacritical Marks Supplement": (0x1DC0, 0x1DFF),
        "Latin Extended Additional": (0x1E00, 0x1EFF),
        "General Punctuation": (0x2000, 0x206F),
        "Currency Symbols": (0x20A0, 0x20CF),
        "Arrows": (0x2190, 0x21FF),
        "Mathematical Operators": (0x2200, 0x22FF),
    }

    OTHER_BLOCK_NAME = "Other Unicode"

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, text: str) -> None:
        self.text = text
        self.unique_chars: List[str] = sorted(set(text), key=ord)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def print_summary(self) -> Set[str]:
        """
        Print a readable Unicode summary and return discovered characters.
        """
        ascii_letters = self._extract_ascii_letters(self.unique_chars)
        ascii_punct = self._extract_ascii_punctuation(self.unique_chars)
        nonprinting = self._extract_nonprinting(self.unique_chars)
        above_ascii = {c for c in self.unique_chars if ord(c) > 0x7F}

        self._print_ascii_letters_table(ascii_letters)
        self._print_simple_char_table(
            "ASCII PUNCTUATION / DIGITS / SYMBOLS",
            ascii_punct,
            show_names=False,
        )
        self._print_nonprinting_table(nonprinting)
        self._print_unicode_blocks(above_ascii)

        return set(self.unique_chars)

    # ------------------------------------------------------------------
    # Character classification helpers
    # ------------------------------------------------------------------

    def _extract_ascii_letters(self, chars: Iterable[str]) -> Set[str]:
        return {c for c in chars if ("A" <= c <= "Z") or ("a" <= c <= "z")}

    def _extract_ascii_punctuation(self, chars: Iterable[str]) -> Set[str]:
        return {c for c in chars if 33 <= ord(c) <= 127 and not c.isalpha()}

    def _extract_nonprinting(self, chars: Iterable[str]) -> Set[str]:
        return {
            c
            for c in chars
            if unicodedata.category(c).startswith("C") or c.isspace()
        }

    def _get_unicode_block(self, char: str) -> str:
        codepoint = ord(char)

        for block_name, (start, end) in self.UNICODE_BLOCKS.items():
            if start <= codepoint <= end:
                return block_name

        return self.OTHER_BLOCK_NAME

    def _group_by_unicode_block(
        self, chars: Iterable[str]
    ) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = defaultdict(list)

        for char in chars:
            block = self._get_unicode_block(char)
            groups[block].append(char)

        return dict(groups)

    # ------------------------------------------------------------------
    # Printing helpers
    # ------------------------------------------------------------------

    def _print_ascii_letters_table(self, letters: Set[str]) -> None:
        print("\nASCII LETTERS")
        print("-" * 20)

        rows: List[Tuple[str, str]] = []

        for i in range(ord("A"), ord("Z") + 1):
            upper = chr(i)
            lower = chr(i + 32)

            u = upper if upper in letters else ""
            l = lower if lower in letters else ""

            if u or l:
                rows.append((u, l))

        if not rows:
            print("(none)")
            return

        for u, l in rows:
            print(f"   {u:^2} {l:^2}")

    def _print_simple_char_table(
        self, title: str, chars: Iterable[str], *, show_names: bool
    ) -> None:
        print(f"\n{title}")
        print("-" * 40)

        chars = set(chars)
        if not chars:
            print("(none)")
            return

        header = f"{'Char':^6} | {'Code':^8}{' | Name' if show_names else ''}"
        print(header)
        print("-" * len(header))

        for c in sorted(chars, key=ord):
            code = f"U+{ord(c):04X}"
            line = f"{c:^6} | {code:^8}"
            if show_names:
                line += f" | {self._safe_unicode_name(c)}"
            print(line)

    def _print_nonprinting_table(self, chars: Set[str]) -> None:
        print("\nNON-PRINTING / WHITESPACE")
        print("-" * 40)

        if not chars:
            print("(none)")
            return

        header = f"{'Escape':^10} | {'Code':^8} | Name"
        print(header)
        print("-" * len(header))

        for c in sorted(chars, key=ord):
            code = f"U+{ord(c):04X}"
            print(
                f"{self._visible_escape(c):^10} | "
                f"{code:^8} | "
                f"{self._safe_unicode_name(c)}"
            )

    def _print_unicode_blocks(self, chars: Set[str]) -> None:
        print("\nHIGHER UNICODE BY BLOCK")
        print("-" * 40)

        if not chars:
            print("(none)")
            return

        groups = self._group_by_unicode_block(chars)

        for block_name in sorted(groups):
            self._print_simple_char_table(
                block_name,
                groups[block_name],
                show_names=True,
            )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _safe_unicode_name(self, char: str) -> str:
        try:
            return unicodedata.name(char)
        except ValueError:
            return "(no Unicode name)"

    def _visible_escape(self, char: str) -> str:
        escapes = {
            "\n": r"\n",
            "\t": r"\t",
            "\r": r"\r",
            " ": r"' '",
        }
        return escapes.get(char, repr(char))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a summary of the Unicode characters in text."
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="text to analyze",
    )

    parser.add_argument(
        "-f",
        "--file",
        help="read text from FILE",
    )

    args = parser.parse_args()

    # A file and command-line text cannot be specified together.
    if args.file and args.text:
        parser.error("cannot specify both TEXT and --file")

    # Read from a file.
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            parser.error(f"cannot read {args.file!r}: {e}")

    # Use command-line text.
    elif args.text is not None:
        text = args.text

    # Read piped/redirected stdin.
    elif not sys.stdin.isatty():
        text = sys.stdin.read()

    # Nothing was supplied.
    else:
        parser.error("provide TEXT, --file FILE, or pipe text to stdin")

    UnicodeSummary(text).print_summary()


if __name__ == "__main__":
    main()
