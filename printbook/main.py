# Don't forget the import statements

def main() -> int:
    args = parse_arguments()

    try:
        pdf_path = build_print_book(
            book_directory=args.book_directory,
            output_directory=args.output_directory,
        )
    except PrintBookError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Created: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())