import base64
import os
from pathlib import Path



def read_markdown_file(file_path: Path, file_label: str) -> str:
    """
    Reads and validates a Markdown file.

    Args:
        file_path (Path): Path to the Markdown file.
        file_label (str): Label used in error messages.

    Returns:
        str: Contents of the Markdown file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path is invalid, the file is not a `.md` file, or the file is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_label} file not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"{file_label} path is not a file: {file_path}")

    if file_path.suffix.lower() != ".md":
        raise ValueError(f"{file_label} must be a .md file: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{file_label} file is empty: {file_path}")

    return content
    