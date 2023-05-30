import os
import sys
from typing import Any, List, Union, Optional

import typer
import pydantic

from transpiler.c_parser.parser import parse_c_file


class CFile(pydantic.BaseModel):
    header: Optional[pydantic.FilePath] = None
    source: Optional[pydantic.FilePath] = None

    class Config:
        validate_all = True


class CProject(pydantic.BaseModel):
    files: List[CFile]

    class Config:
        validate_all = True


def traverse_c_directory(directory: str) -> CProject:
    items = os.listdir(directory)
    filenames = [
        ".".join(i.split(".")[:-1])
        for i in items
        if os.path.isfile(os.path.join(directory, i))
    ]
    project = CProject(files=[])
    for filename in filenames:
        header = None
        source = None
        if f"{filename}.h" in items:
            header = os.path.join(directory, f"{filename}.h")
        if f"{filename}.c" in items:
            source = os.path.join(directory, f"{filename}.c")
        project.files.append(CFile(header=header, source=source))
    return project


def transpile(source_directory: str, target_directory: str) -> None:
    c_project = traverse_c_directory(source_directory)
    # temporary approach
    main = None
    for cfile in c_project.files:
        if cfile.source is not None and cfile.source.name.split("/")[-1] == "main.c":
            main = cfile
            break
    assert main is not None

    c_ast = parse_c_file(main.source)
    print()


def main(source_dir: str, target_dir: str) -> None:
    if not os.path.isdir(source_dir):
        print(f"Error: {source_dir} does not exist")
        return

    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)

    transpile(source_dir, target_dir)


if __name__ == "__main__":
    typer.run(main)
