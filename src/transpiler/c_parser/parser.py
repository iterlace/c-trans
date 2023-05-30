from typing import Any

import pydantic
from pycparser import c_ast, parse_file

__all__ = ["parse_c_file"]


def parse_c_file(file_path: str | pydantic.FilePath) -> Any:
    ast = parse_file(
        file_path,
        use_cpp=True,
        cpp_path="cpp",
        cpp_args=[
            "-E",
            "-I/home/a/PycharmProjects/c-trans/src/transpiler/c_parser/fake_libc_include",
        ],
    )
    return ast
