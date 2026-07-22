from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_prompt_file(
    relative_path: str
) -> str:

    file_path = BASE_DIR / relative_path

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()
