from pathlib import Path
from app.utils.helpers import read_markdown_file

PROMPT_DIR = Path(__file__).resolve().parent

CONSTITUTION = read_markdown_file(
    PROMPT_DIR / "Constitution.md",
    "wintheam Constitution",
)

SPECIFICATION = read_markdown_file(
    PROMPT_DIR / "specification.md",
    "wintheam Specification",
)

SYS_PROMPT = read_markdown_file(
    PROMPT_DIR / "system_prompt.md",
    "wintheam User Prompt",
)