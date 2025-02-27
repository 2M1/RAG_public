import os

from pathlib import Path
import pathlib

from docling.document_converter import DocumentConverter

__all__ = [
    "convert_dir_files",
]


def _parse_collection_file_struct_from_dir(base_dir: Path) -> dict[str : list[str]]:
    """
    parses the folder structure for two levels deep from the disk starting at `base_dir` into a python directory

    Expected/Example file_structure:
    ```
    base_dir(default: db_files_pdf)/
    ├── Ansible (collection name 1)
    │   └── Ansible.pdf (file in collection named Ansible)
    ├── OpenShift (collection named OpenShift)
    │   ├── SingleNode/ (ignored)
    │   │    └── Test.pdf
    │   └── Openshift.pdf (file in collection named Openshift)
    └── POWER10 (collection named POWER10)
        ├── S1012.anything_else (also ignored)
        └── E1050.pdf (file in collection named Power10)

    ```

    Will result in the following dict:

    ```
    {
        "Ansible": ["Ansible.pdf"],
        "OpenShift": ["Openshift.pdf"],
        "POWER10": ["E1050.pdf"],
    }
    ```


    :returns: The directory structure of folder to md files under folder
    """
    result = {}
    sub_dirs = map(
        lambda entry: entry.name,
        filter(lambda entry: entry.is_dir(), os.scandir(base_dir)),
    )

    for directory in sub_dirs:
        files = list(
            map(
                lambda entry: entry.name,
                filter(
                    # filter for only markdown files:
                    lambda entry: entry.is_file()
                    and os.path.splitext(entry)[-1] == ".pdf",
                    os.scandir(base_dir / directory),
                ),
            )
        )
        result[directory] = files

    return result


def convert_dir_files(source_directory: Path, output_directory: Path) -> None:
    """Converts all pdf files living under a subdir of the source directory into
    markdown using docling and saves them under the output directory/ the same subdir.

    Converted files can be processed by chromaDB_md.py

    :param source_directory: Path to the source directory
    :param output_directory: Path to the output directory. Will be created if it does not
                             exist yet.
    """

    # parse directory structure
    input_files: dict[str : list[str]] = _parse_collection_file_struct_from_dir(
        source_directory
    )

    # Ensure the output directories exists
    for directory in input_files.keys():
        os.makedirs(output_directory / directory, exist_ok=True)

    # Initialize the DocumentConverter
    converter = DocumentConverter()

    # Loop through all files in the source directory
    for dir_name, file_names in input_files.items():
        for file in file_names:
            if os.path.splitext(file)[1] == ".pdf":  # Process only PDF files
                source_path = os.path.join(source_directory / dir_name, file)
                print(f"Processing file: {source_path}")

                # Define the output file path with .md extension
                output_file_name = os.path.splitext(file)[0] + ".md"
                output_file_path = os.path.join(
                    output_directory / dir_name, output_file_name
                )

                if Path(output_file_path).exists():
                    print(f"File {output_file_path} does already exist. Skipping.")
                    continue

                try:
                    # Convert the PDF to a document
                    result = converter.convert(source_path)

                    # Export the document to Markdown
                    markdown_content = result.document.export_to_markdown()

                    # Save the Markdown content to the output file
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(markdown_content)

                    print(f"Saved Markdown file: {output_file_path}")
                except Exception as e:
                    print(f"Failed to process {source_path}: {e}")

    print("All files processed!")


def main() -> None:
    # Specify the source directory containing the PDF files
    source_directory = Path(os.getenv("RAG_PDF_FILE_DIR", "./db_files_pdf/"))
    output_directory = Path(os.getenv("RAG_MD_FILE_DIR", "./db_files_md/"))

    convert_dir_files(source_directory, output_directory)


if __name__ == "__main__":
    main()
