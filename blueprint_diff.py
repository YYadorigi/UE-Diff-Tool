import os
import re
import json
import warnings
from typing import Any
from enum import Enum
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from DiffTool import *

class Choice(Enum):
    PLUGINS = "Plugins"
    SOURCE = "Source"


UE_PREV_ROOT_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.5")
UE_CUR_ROOT_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.6")
UE_PREV_VERSION = "5.5"
UE_CUR_VERSION = "5.6"
DIFF_CHOICE = Choice.PLUGINS


def parse_ue_classes(UEpath: Path, UEversion: str, choice: Choice) -> dict[str, dict[str, Any]]:
    u_classes: dict[str, dict[str, Any]] = {}

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

    for file_path in tqdm(all_files, desc="Processing UE headers", unit="files"):
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                content = f.read()
                
                # Preprocessing
                content = re.sub(r'TEXT\s*\(\"(.*?)\"\)', 'TEXT("")', content)      # Replace TEXT("...") with empty string
                content = re.sub(r'^\s*#.*', '', content, flags=re.MULTILINE)       # Remove preprocessor directives
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)        # Remove multi-line comments
                content = re.sub(r'\s*//.*', '', content, flags=re.MULTILINE)       # Remove C++ comments
            
                # Extract all UCLASS macro definitions
                class_matches = re.finditer(
                    r'^\s*UCLASS\s*\((.*?)\)\s*'
                    r'class\s+(.*?)\s*([{;])',
                    content,
                    re.DOTALL | re.MULTILINE
                )

                for class_match in class_matches:
                    uclass_params = split_arguments(extract_arguments(f"UCLASS({class_match.group(1)})", 'UCLASS'))

                    def process_class_decl(decl):
                        cleaned_decl = re.sub(r'\b[a-zA-Z0-9_]+_API\s*', '', decl.strip())
                        return f"class {cleaned_decl} {{}};"
                    class_decl = process_class_decl(class_match.group(2))

                    # Skip UE_DEPRECATED macro
                    deprecated_match = re.search(r"UE_DEPRECATED\s*\(\s*(\d+\.\d+)\s*,\s*\"(.*?)\"\s*\)", class_decl, re.DOTALL)
                    if deprecated_match:
                        deprecated_version = deprecated_match.group(1)
                        if float(deprecated_version) <= float(UEversion):
                            continue
                        class_decl = class_decl[:deprecated_match.start()] + class_decl[deprecated_match.end():]

                    class_decl_parsed = parse_class_declaration(class_decl)

                    class_name = class_decl_parsed["name"]
                    inheritance_list = class_decl_parsed["bases"]

                    u_classes[class_name] = {
                        "relpath": os.path.relpath(file_path, UEpath),
                        "uclass_params": uclass_params,
                        "inheritance_list": inheritance_list,
                        "ufunctions": [],
                    }

                    # Read class body
                    class_body = read_class_body(content[class_match.end() - 1:], 0)
                
                    # Parse UFUNCTION declarations inside class body
                    pos = 0
                    while pos < len(class_body):
                        deprecated_pos = class_body.find("UE_DEPRECATED", pos)
                        ufunction_pos = class_body.find("UFUNCTION", pos)
                    
                        if ufunction_pos == -1:
                            break
                    
                        # Check if there is a UE_DEPRECATION macro beforehand
                        has_deprecated = (
                            deprecated_pos != -1 and 
                            deprecated_pos < ufunction_pos and
                            class_body[deprecated_pos:ufunction_pos].strip().endswith(")")
                        )
                    
                        ufunction_args = read_arguments(class_body, ufunction_pos + len("UFUNCTION"))
                        args_end = ufunction_pos + len("UFUNCTION()") + len(ufunction_args)
                    
                        func_decl_start = args_end
                        re_backslash_s = {' ', '\t', '\n', '\r', '\f', '\v'}
                        while func_decl_start < len(class_body) and class_body[func_decl_start] in re_backslash_s:
                            func_decl_start += 1
                    
                        func_decl_end = func_decl_start
                        while func_decl_end < len(class_body):
                            c = class_body[func_decl_end]
                            if c == ';' or c == '{':
                                break
                            func_decl_end += 1
                        
                        func_decl = class_body[func_decl_start:func_decl_end].strip()
                        func_name = func_decl[:func_decl.find('(')].strip().split()[-1]
                        
                        # Skip deprecated functions
                        if has_deprecated:
                            dep_args = read_arguments(class_body, deprecated_pos + len("UE_DEPRECATED"))
                            version = split_arguments(dep_args)[0]
                            if version.strip('"\'') in {'all', ''} or float(version.strip('"\'')) <= float(UEversion):
                                pos = func_decl_end
                                continue
                        
                        u_classes[class_name]["ufunctions"].append({
                            "name": func_name,
                            "ufunc_params": split_arguments(ufunction_args),
                        })
                        
                        pos = func_decl_end
        except Exception as e:
            print(f"Error processing {file_path}. Please check the file manually.")
                    
    return u_classes


def filter_blueprinttype_classes(u_classes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    blueprinttype_classes: list[dict[str, Any]] = []
    for class_name, class_info in u_classes.items():
        if "BlueprintType" in class_info["uclass_params"]:
            blueprinttype_classes.append({
                "name": class_name,
                "relpath": class_info["relpath"],
                "ufunctions": filter_blueprint_functions(class_info["ufunctions"])
            })
    return blueprinttype_classes


def filter_blueprintable_classes(u_classes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out classes that are not blueprintable."""
    blueprintable_cache: dict[str, bool] = {}
    
    def is_blueprintable(cls_name: str) -> bool:
        # Check cache first
        if cls_name in blueprintable_cache:
            return blueprintable_cache[cls_name]
        
        # Check if class is marked as NotBlueprintable
        if "NotBlueprintable" in [p.split('=')[0].strip() for p in u_classes.get(cls_name, {}).get("uclass_params", [])]:
            blueprintable_cache[cls_name] = False
            return False
        
        # Check current class's UCLASS parameters
        current_class = u_classes.get(cls_name, {})
        if "Blueprintable" in [p.split('=')[0].strip() for p in current_class.get("uclass_params", [])]:
            blueprintable_cache[cls_name] = True
            return True
        
        # Recursively check all parent classes
        for parent in current_class.get("inheritance_list", []):
            if is_blueprintable(parent["name"]):
                blueprintable_cache[cls_name] = True
                return True
        
        # Cache negative result
        blueprintable_cache[cls_name] = False
        return False
    
    # Check all classes and collect qualified ones
    result: list[dict[str, Any]] = []
    for cls_name, cls_info in u_classes.items():
        if is_blueprintable(cls_name):
            result.append({
                "name": cls_name,
                "relpath": cls_info["relpath"],
                "ufunctions": filter_blueprint_functions(cls_info["ufunctions"])
            })
    
    return result


def filter_blueprint_functions(u_functions: list[dict[str, Any]]) -> list[str]:
    blueprint_functions: list[str] = []
    for function in u_functions:
        if "BlueprintCallable" in function["ufunc_params"] or "BlueprintPure" in function["ufunc_params"]:
            blueprint_functions.append(function["name"])
    return blueprint_functions


def diff(prev_list: list[dict[str, Any]], cur_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev_classes = {cls['name']: cls for cls in prev_list}
    cur_classes = {cls['name']: cls for cls in cur_list}
    
    result: list[dict[str, Any]] = []
    
    all_classes = set(prev_classes.keys()).union(cur_classes.keys())
    
    for cls_name in all_classes:
        prev_cls = prev_classes.get(cls_name)
        cur_cls = cur_classes.get(cls_name)
        
        prev_funcs = prev_cls['ufunctions'] if prev_cls else []
        cur_funcs = cur_cls['ufunctions'] if cur_cls else []

        # if prev_cls and cur_cls and prev_cls['relpath'] != cur_cls['relpath']:
        #     print(f"Class '{cls_name}' has changed paths: {prev_cls['relpath']} -> {cur_cls['relpath']}")
        relpath = cur_cls['relpath'] if cur_cls else prev_cls['relpath']

        added = list(set(cur_funcs) - set(prev_funcs))
        removed = list(set(prev_funcs) - set(cur_funcs))
        
        # Only keep classes with actual changes
        if added or removed:  # Check if either list has elements
            result.append({
                'class_name': cls_name,
                'module': relpath.split('\\')[2] + "::" + relpath.split('\\')[3],
                'relpath': relpath,
                'added_functions': sorted(added),
                'removed_functions': sorted(removed)
            })
    
    return result


# TODO: implement more organized output
def diff_to_excel(diff_result: list[dict[str, Any]], output_file: str) -> None:
    # Convert to DataFrame and explode list columns
    df = pd.DataFrame(diff_result)
    
    # Create separate rows for added and removed functions
    added_df = df.explode('added_functions').dropna(subset=['added_functions']).copy()
    added_df['change_type'] = 'Added'
    added_df.rename(columns={'added_functions': 'function'}, inplace=True)
    
    removed_df = df.explode('removed_functions').dropna(subset=['removed_functions']).copy()
    removed_df['change_type'] = 'Removed'
    removed_df.rename(columns={'removed_functions': 'function'}, inplace=True)
    
    # Combine both results
    combined_df = pd.concat([added_df, removed_df], ignore_index=True)
    
    # Reorder and select final columns
    final_df = combined_df[['module', 'relpath', 'class_name', 'function', 'change_type']]
    
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name="API Changes", index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['API Changes']
        for i, col in enumerate(final_df.columns):
            max_len = max(final_df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    
    print(f"Excel report saved to: {output_file}")
    

if __name__ == "__main__":
    prev_u_classes = parse_ue_classes(UE_PREV_ROOT_DIR, UE_PREV_VERSION, DIFF_CHOICE)

    prev_blueprint_classes = list({
        cls["name"]: cls
        for cls in filter_blueprinttype_classes(prev_u_classes) + filter_blueprintable_classes(prev_u_classes)
    }.values())

    # print(json.dumps(prev_blueprint_classes, indent=4))
    
    cur_u_classes = parse_ue_classes(UE_CUR_ROOT_DIR, UE_CUR_VERSION, DIFF_CHOICE)
    
    cur_blueprint_classes = list({
        cls["name"]: cls 
        for cls in filter_blueprinttype_classes(cur_u_classes) + filter_blueprintable_classes(cur_u_classes)
    }.values())

    # print(json.dumps(cur_blueprint_classes, indent=4))

    blueprint_api_diff = diff(prev_blueprint_classes, cur_blueprint_classes)

    # print(json.dumps(blueprint_api_diff, indent=4))

    diff_to_excel(blueprint_api_diff, f"outputs/blueprint_diff_{UE_PREV_VERSION}_{UE_CUR_VERSION}.xlsx")