import os
import re
import json
import shutil, tempfile
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from DiffTool import *

# Configure the path to the Unreal Engine source code directory
UE_ROOT_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.5")

def filter_deprecated_files(UEpath: Path, UEversion: str) -> int:
    UE_PLUGINS_DIR = Path("Engine\\Plugins")
    UE_SOURCE_DIR = Path("Engine\\Source")

    UE_DEVELOPER_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Developer")
    UE_EDITOR_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Editor")
    UE_RUNTIME_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Runtime")
    UE_PLUGINS_DIR = os.path.join(UEpath, UE_PLUGINS_DIR)

    if os.path.exists("outputs/deprecated"):
        shutil.rmtree("outputs/deprecated", onexc=lambda f,p,_: (os.chmod(p, 0o777), f(p)))
    os.makedirs("outputs/deprecated")   

    # Traverse the UE source code directory
    # Collect all .h files first for accurate progress tracking
    all_files = []
    for target_dir in [UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR, UE_PLUGINS_DIR]:
        for root, _, files in os.walk(target_dir):
            all_files.extend([(root, file) for file in files if file.endswith(".h")])

    # Process files with tqdm progress bar
    file_count = 0
    match_count = 0
    for root, file in tqdm(all_files, desc="Processing files", unit="file"):
        file_path = os.path.join(root, file)
        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
            content = f.read()

            deprecated_matches = re.finditer(
                r"UE_DEPRECATED\s*\(\s*(\d+\.\d+)\s*,\s*\"(.*?)\"\s*\)",
                content,
                re.DOTALL
            )

            for deprecated_match in deprecated_matches:
                match_count += 1
                deprecated_version = deprecated_match.group(1)
                if deprecated_version == UEversion:
                    relative_path = Path(file_path).relative_to(UEpath)
                    output_path = Path("outputs/deprecated") / relative_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(file_path, str(output_path))
                    file_count += 1
                    break
    return file_count, match_count


def parse_deprecated_functions() -> list[any]:
    deprecated_functions = []

    output_path = Path("outputs\\deprecated")
    UE_PLUGINS_DIR = Path("Engine\\Plugins")
    UE_SOURCE_DIR = Path("Engine\\Source")
    UE_DEVELOPER_DIR = os.path.join(output_path, UE_SOURCE_DIR, "Developer")
    UE_EDITOR_DIR = os.path.join(output_path, UE_SOURCE_DIR, "Editor")
    UE_RUNTIME_DIR = os.path.join(output_path, UE_SOURCE_DIR, "Runtime")
    UE_PLUGINS_DIR = os.path.join(output_path, UE_PLUGINS_DIR)

    # Traverse the UE source code directory
    for target_dir in [UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR, """UE_PLUGINS_DIR"""]:
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".h"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                        # Read the file content
                        content = f.read()
    
                        # Find all UFUNCTION declarations in class body
                        function_matches = re.finditer(
                            r'^\s*UE_DEPRECATED\s*\(\s*(\d+\.\d+)\s*,\s*"(.*?)"\s*\)\s*?\n\s*(.*?)\s*?(?=\n|$)',
                            content,
                            re.MULTILINE | re.DOTALL
                        )
    
                        for function_match in function_matches:
                            deprecated_version = function_match.group(1)
                            deprecated_reason = function_match.group(2)
                            function_declaration = function_match.group(3)
    
                            if float(deprecated_version) == 5.5:
                                function_declaration = function_declaration.strip()
                                func_name = function_declaration[:function_declaration.find('(')].strip().split()[-1]
                                relpath = str(Path(file_path).relative_to(output_path))
                                deprecated_functions.append({
                                    "relpath": relpath,
                                    "module": relpath.split("\\")[2] + "::" + relpath.split("\\")[3],
                                    "name": func_name,
                                    "reason": deprecated_reason,
                                    "declaration": function_declaration,
                                })

    return deprecated_functions


def report_deprecated_functions(deprecated_funcs: list[any]) -> None:
    # Create a DataFrame from the deprecated functions list
    df = pd.DataFrame(deprecated_funcs)
    # Save the DataFrame to a CSV file
    df.to_csv("outputs/deprecated_functions.csv", index=False)


if __name__ == "__main__":
    file_num, match_num = filter_deprecated_files(UE_ROOT_DIR, "5.5")

    print(f"Found {match_num} deprecated functions in {file_num} files.")

    deprecated_funcs = parse_deprecated_functions()
    
    print(f"Found {len(deprecated_funcs)} deprecated functions.")

    report_deprecated_functions(deprecated_funcs)