from typing import Any

import pydantic
from pycparser import c_ast, parse_file

__all__ = ["parse_c_file"]


def parse_c_file(file_path: str | pydantic.FilePath) -> Any:
    try:
        ast = parse_file(
            file_path,
            use_cpp=True,
            cpp_path="cpp",
            cpp_args=["-E"],
        )
    except Exception as e:
        e.add_note(
            f"Error parsing {file_path}. "
            f"Please ensure the file is valid C code and does NOT contain any STD or 3rd-party #includes."
        )
        raise
    ast.show()
    return ast
