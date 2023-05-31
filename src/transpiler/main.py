import os
import sys
from typing import Any, List, Union, Optional

import astor
import typer
import pydantic

from transpiler.c_parser import parse_c_file
from transpiler.ast_converter import CtoPythonVisitor


def transpile(source_file: str, target_file: str) -> None:
    c_ast = parse_c_file(source_file)
    visitor = CtoPythonVisitor(c_ast)
    python_ast = visitor.run()
    source_code = astor.to_source(python_ast)
    print(source_code)
    with open(target_file, "w") as f:
        f.write(source_code)


def main(source_file: str, target_file: str) -> None:
    if not os.path.isfile(source_file):
        print(f"Error: {source_file} either does not exist or is not a file")
        return

    if os.path.exists(target_file):
        match input(
            f"Warning: {target_file} already exists. Overwrite? [y/N] "
        ).lower().strip():
            case "y":
                os.remove(target_file)
            case "n":
                return
            case _:
                print("Invalid input")
                return

    transpile(source_file, target_file)


if __name__ == "__main__":
    typer.run(main)
