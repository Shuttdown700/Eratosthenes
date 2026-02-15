import subprocess
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import API

from colorama import Fore, Style, init
init(autoreset=True)

def determine_author_from_filename(filename):
    book = ""
    auther = ""
    # Example filename: "Book Title by Author Name.epub"
    if " by " in filename:
        book = filename.split(" by ")[0].strip()
        auther = filename.split(" by ")[-1].strip()
    # Example filename: "Author Name - Book Title.epub"
    elif " - " in filename:
        book = filename.split(" - ")[-1].strip()
        auther = filename.split(" - ")[0].strip()
    return book, auther


def batch_convert_epubs(input_dir, output_dir, overwrite=False):
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    print("#"*10 + "\n")
    print(f"{Fore.GREEN}{Style.BRIGHT}Starting batch conversion{Style.RESET_ALL}: EPUB {Fore.YELLOW}{Style.BRIGHT}->{Style.RESET_ALL} PDF")
    print(f"{Fore.CYAN}{Style.BRIGHT}Input Directory{Style.RESET_ALL}: {input_dir}")
    print(f"{Fore.CYAN}{Style.BRIGHT}Output Directory{Style.RESET_ALL}: {output_dir}")
    print("\n" + "#"*10)
    os.makedirs(output_dir, exist_ok=True)

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(".epub"):
                epub_path = os.path.join(root, file)

                # Preserve relative path structure
                # rel_path = os.path.relpath(root, input_dir)
                # target_dir = os.path.join(output_dir, rel_path)
                os.makedirs(output_dir, exist_ok=True)

                pdf_filename = os.path.splitext(file)[0] + ".pdf"
                print(f"{Fore.CYAN}{Style.BRIGHT}\nProcessing{Style.RESET_ALL}: {epub_path}")
                output_pdf_path = os.path.join(output_dir, pdf_filename)

                convert_epub_to_pdf(epub_path, output_pdf_path, overwrite=overwrite)


def convert_epub_to_pdf(epub_path, output_pdf_path, overwrite=False):
    calibre_path = os.path.join(os.path.dirname(__file__), "..", "bin", "Calibre2", "ebook-convert.exe")

    if not os.path.exists(epub_path):
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")
    if not os.path.exists(calibre_path):
        raise FileNotFoundError(f"ebook-convert not found at: {calibre_path}")

    book_title, author = determine_author_from_filename(os.path.splitext(os.path.basename(epub_path))[0])

    if book_title:
        output_pdf_path = os.path.join(os.path.dirname(output_pdf_path), f"{book_title}.pdf")

    if os.path.exists(output_pdf_path):
        if overwrite:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Overwriting existing PDF{Style.RESET_ALL}: {output_pdf_path}")
        else:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Output PDF already exists{Style.RESET_ALL}: {output_pdf_path}")
            return

    command = [
        calibre_path,
        epub_path,
        output_pdf_path,
        "--pdf-page-numbers",
        "--embed-all-fonts",
        "--pretty-print",
        "--enable-heuristics"
    ]

    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"{Fore.GREEN}{Style.BRIGHT}Conversion complete{Style.RESET_ALL}: {output_pdf_path}")
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}{Style.BRIGHT}Conversion failed{Style.RESET_ALL}: {e}")


if __name__ == "__main__":
    # Example usage

    # Oxford World's Classics on Anna

    input_directory = r"W:\Temp\Books"
    output_directory = os.path.join(input_directory, "Converted PDFs")


    batch_convert_epubs(input_directory, output_directory, overwrite=True)
