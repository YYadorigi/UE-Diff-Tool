import os
import re
import json
import shutil, tempfile
from typing import Any
from enum import Enum
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from DiffTool import *

class Choice(Enum):
    PLUGINS = "Plugins"
    SOURCE = "Source"


UE_ROOT_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.6")
UE_VERSION = "5.6"
DEPRECATION_CHOICE = Choice.PLUGINS
OUTPUT_DIR = "outputs/deprecations"


def filter_deprecation_files(UEpath: Path, UEversion: str, choice: Choice) -> None:
    UE_SOURCE_DIR = Path("Engine\\Source")
    UE_DEVELOPER_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Developer")
    UE_EDITOR_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Editor")
    UE_RUNTIME_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Runtime")
    UE_PLUGINS_DIR = Path("Engine\\Plugins")
    UE_PLUGINS_DIR = os.path.join(UEpath, UE_PLUGINS_DIR)

    all_files = []
    target_dirs = [
        *([UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR] if choice == Choice.SOURCE else []),
        *([UE_PLUGINS_DIR] if choice == Choice.PLUGINS else [])
    ] if choice else [UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR, UE_PLUGINS_DIR]
    for target_dir in target_dirs:
        for root, _, files in os.walk(target_dir):
            all_files.extend(
                os.path.join(root, file) 
                for file in files 
                if file.endswith(".h")
            )
    
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR, onexc=lambda f,p,_: (os.chmod(p, 0o777), f(p)))
    os.makedirs(OUTPUT_DIR)   

    for file_path in tqdm(all_files, desc="Processing files", unit="file"):
        try:
            with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                content = f.read()

                # Preprocessing
                content = re.sub(r'TEXT\s*\(\"(.*?)\"\)', 'TEXT("")', content)      # Replace TEXT("...") with empty string
                content = re.sub(r'^\s*#.*', '', content, flags=re.MULTILINE)       # Remove preprocessor directives
                content = re.sub(r'^\s*(UCLASS|USTRUCT|UFUNCTION|UPROPERTY).*', '', content, flags=re.MULTILINE)  # Remove UE macros
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)        # Remove multi-line comments
                content = re.sub(r'\s*//.*', '', content, flags=re.MULTILINE)       # Remove C++ comments

                deprecated_matches = re.finditer(
                    r"UE_DEPRECATED\s*\(\s*(\d+\.\d+)\s*,\s*\"(.*?)\"\s*\)",
                    content,
                    re.DOTALL
                )

                for deprecated_match in deprecated_matches:
                    deprecated_version = deprecated_match.group(1)
                    if deprecated_version == UEversion:
                        relative_path = Path(file_path).relative_to(UEpath)
                        output_path = Path(OUTPUT_DIR) / relative_path
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        break
        except Exception as e:
            print(f"Error processing file {file_path}. Please check the file manually.")

    return


# TODO: Support parsing more types of deprecations
def parse_deprecated_functions(UEpath: Path, UEversion: str, choice: Choice) -> list[dict[str, Any]]:
    # Filter files with deprecated functions
    filter_deprecation_files(UEpath, UEversion, choice)

    deprecated_functions: list[dict[str, Any]] = []

    UE_SOURCE_DIR = Path("Engine\\Source")
    UE_DEVELOPER_DIR = os.path.join(OUTPUT_DIR, UE_SOURCE_DIR, "Developer")
    UE_EDITOR_DIR = os.path.join(OUTPUT_DIR, UE_SOURCE_DIR, "Editor")
    UE_RUNTIME_DIR = os.path.join(OUTPUT_DIR, UE_SOURCE_DIR, "Runtime")
    UE_PLUGINS_DIR = Path("Engine\\Plugins")
    UE_PLUGINS_DIR = os.path.join(OUTPUT_DIR, UE_PLUGINS_DIR)

    all_files = []
    target_dirs = [
        *([UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR] if choice == Choice.SOURCE else []),
        *([UE_PLUGINS_DIR] if choice == Choice.PLUGINS else [])
    ] if choice else [UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR, UE_PLUGINS_DIR]
    for target_dir in target_dirs:
        for root, _, files in os.walk(target_dir):
            all_files.extend(
                os.path.join(root, file) 
                for file in files 
                if file.endswith(".h")
            )

    for file_path in tqdm(all_files, desc="Processing files", unit="file"):
        try:
            with open(file_path, "r", encoding='utf-8') as f:
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
                    # function_line = content[:function_match.start()].count('\n') + 1

                    if deprecated_version == UEversion:
                        function_declaration = function_declaration.strip()
                        func_name = function_declaration[:function_declaration.find('(')].strip().split()[-1]
                        relpath = str(Path(file_path).relative_to(OUTPUT_DIR))
                        
                        # Find the innermost scope containing the function
                        local_scope = None
                        
                        deprecated_functions.append({
                            "relpath": relpath,
                            "module": relpath.split("\\")[2] + "::" + relpath.split("\\")[3],
                            "name": func_name,
                            "scope": local_scope,
                            "reason": deprecated_reason,
                            "declaration": function_declaration,
                        })
        except Exception as e:
            print(f"Error processing file {file_path}. Please check the file manually.")

    return deprecated_functions


# TODO: Implement more organized report
def report_deprecated_functions(deprecated_funcs: list[dict[str, Any]], output: str) -> None:
    # Create a DataFrame from the deprecated functions list
    df = pd.DataFrame(deprecated_funcs)
    # Save the DataFrame to a CSV file
    df.to_csv(output, index=False)


if __name__ == "__main__":
    deprecated_funcs = parse_deprecated_functions(UE_ROOT_DIR, UE_VERSION, DEPRECATION_CHOICE)
    
    report_deprecated_functions(deprecated_funcs, f"outputs/UE_DEPRECATED_{UE_VERSION}.csv")