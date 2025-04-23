import os
import re
from pathlib import Path
import pandas as pd
from DiffTool import *

# Configure the path to the Unreal Engine source code directory
UE_PREV_SOURCE_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.4\\Engine\\Source")
UE_CUR_SOURCE_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.5\\Engine\\Source")

def parse_ue_classes_and_functions(UEpath: Path) -> tuple[dict[str, dict[str, any]], dict[str, dict[str, any]]]:
    u_classes: dict[str, dict[str, any]] = {}
    u_functions: dict[str, dict[str, any]] = {}

    UE_DEVELOPER_DIR = os.path.join(UEpath, "Developer")
    UE_EDITOR_DIR = os.path.join(UEpath, "Editor")
    UE_RUNTIME_DIR = os.path.join(UEpath, "Runtime")
    # UE_PLUGINS_DIR = os.path.join(UEpath, "Plugins")

    # Traverse the UE source code directory
    for target_dir in [UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR, ]:
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".h"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                            # Extract all UCLASS macro definitions
                            class_matches = re.finditer(
                                r'UCLASS\s*\((.*?)\)\s*'      # Capture UCLASS parameters
                                r'class\s+(.*?)\s*([{;])',    # Capture class declaration until { or ;
                                content,
                                re.DOTALL
                            )

                            for class_match in class_matches:
                                uclass_params = split_arguments(extract_arguments('UCLASS(' + class_match.group(1) + ')', 'UCLASS'))

                                class_decl = (lambda decl: 
                                    'class ' + re.sub(r'\b[A-Z_]+_API\s*', '', decl.strip()) + ' {};'
                                )(class_match.group(2))

                                try:
                                    class_decl_parsed = parse_class_declaration(class_decl)
                                except:
                                    print("File directory: ", file_path)
                                    print(class_match.group(0))
                                    print('-' * 80)
                                    print(class_decl)
                                    print('-' * 80)
                                    print(class_decl_parsed)
                                    
                                continue

                                class_name = class_decl_parsed["name"]
                                inheritance_list = class_decl_parsed["bases"]

                                u_classes[class_name] = {
                                    "uclass_params": uclass_params,
                                    "inheritance_list": inheritance_list
                                }
                            
                                class_body = content[class_match.end():]

                                if class_body.startswith(';'):
                                    continue

                                # Find class body boundaries
                                brace_level = 0
                                i = 0
                                while i < len(class_body):
                                    if class_body[i] == '{':
                                        brace_level += 1
                                    elif class_body[i] == '}':
                                        brace_level -= 1
                                        if brace_level == 0:
                                            break
                                    i += 1
                                class_body = class_body[:(i + 1)]
                            
                                # Find all UFUNCTION declarations in class body
                                function_matches = re.finditer(
                                    r'UFUNCTION.*?(?=\{|;)',     # Function declaration ending
                                    class_body,
                                    re.DOTALL
                                )

                                for func_match in function_matches:
                                    ufunction_str = extract_arguments(func_match.group(0), 'UFUNCTION')
                                    ufunction_params = split_arguments(ufunction_str)

                                    match = re.search(
                                        r'UFUNCTION\s*\(.*?{}.*?\)'.format(re.escape(ufunction_str)),
                                        func_match.group(0), 
                                        re.DOTALL
                                    )

                                    func_decl = func_match.group(0)[len(match.group(0)):]
                                
                                    func_decl = (lambda decl: 
                                        re.sub(r'\)\s*(const|explicit|virtual|inline|noexcept|final|override)*\s*', ')', decl, flags=re.DOTALL) + ' {}'
                                    )(func_decl)

                                    func_decl = re.sub(r'\bvirtual\b\s*', '', func_decl)
                                
                                    func_info = parse_function_declaration(func_decl)

                                    if not func_info:
                                        continue

                                    func_name = class_name + "::" + func_info["name"]

                                    u_functions[func_name] = {
                                        'ufunc_params': ufunction_params,
                                        'return_type': func_info["type"],
                                        'func_params': func_info["params"]
                                    }
                    except Exception as e:
                        print(e)
                        continue

    return u_classes, u_functions


def filter_blueprinttype_classes(u_classes: dict[str, dict[str, any]]) -> list[str]:
    blueprinttype_classes: list[str] = []
    for class_name, class_info in u_classes.items():
        if "BlueprintType" in class_info["uclass_params"]:
            blueprinttype_classes.append(class_name)
    return blueprinttype_classes


def filter_blueprintable_classes(u_classes: dict[str, dict[str, any]]) -> list[str]:
    # Build inheritance graph and cache blueprintable status
    blueprintable_cache = {}
    
    def is_blueprintable(cls_name: str) -> bool:
        # Check cache first
        if cls_name in blueprintable_cache:
            return blueprintable_cache[cls_name]
        
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
    result = []
    for cls_name in u_classes:
        if is_blueprintable(cls_name):
            result.append(cls_name)
    
    return result


def filter_blueprintcallable_functions(u_functions: dict[str, dict[str, any]]):
    blueprintcallable_functions: list[str] = []
    for function_name, function_info in u_functions.items():
        if "BlueprintCallable" in function_info["ufunc_params"]:
            blueprintcallable_functions.append(function_name)
    return blueprintcallable_functions


def filter_blueprintimplementableevent_functions(u_functions: dict[str, dict[str, any]]):
    blueprintimplementableevent_functions: list[str] = []
    for function_name, function_info in u_functions.items():
        if "BlueprintImplementableEvent" in function_info["ufunc_params"]:
            blueprintimplementableevent_functions.append(function_name)
    return blueprintimplementableevent_functions


def diff(prev_list, cur_list):
    prev_set = set(prev_list)
    cur_set = set(cur_list)
    
    added = sorted(list(cur_set - prev_set))
    removed = sorted(list(prev_set - cur_set))
    
    return {
        'added': added,
        'removed': removed,
        'modified': [item for item in cur_list if item not in prev_set and item not in removed],
    }


def diff_to_excel(prev_list, cur_list, output_path="api_diff.xlsx"):
    diff_result = diff(prev_list, cur_list)
    
    added_df = pd.DataFrame({"Added APIs": diff_result['added']})
    removed_df = pd.DataFrame({"Removed APIs": diff_result['removed']})
    
    with pd.ExcelWriter(output_path) as writer:
        added_df.to_excel(writer, sheet_name="Added", index=False)
        removed_df.to_excel(writer, sheet_name="Removed", index=False)
    
    print(f"Excel output: {output_path}")


if __name__ == "__main__":
    prev_u_classes, prev_u_functions = parse_ue_classes_and_functions(UE_PREV_SOURCE_DIR)

    prev_blueprinttype_classes = filter_blueprinttype_classes(prev_u_classes)
    prev_blueprintable_classes = filter_blueprintable_classes(prev_u_classes)
    prev_blueprintcallable_functions = filter_blueprintcallable_functions(prev_u_functions)

    cur_u_classes, cur_u_functions = parse_ue_classes_and_functions(UE_CUR_SOURCE_DIR)

    cur_blueprinttype_classes = filter_blueprinttype_classes(cur_u_classes)
    cur_blueprintable_classes = filter_blueprintable_classes(cur_u_classes)
    cur_blueprintcallable_functions = filter_blueprintcallable_functions(cur_u_functions)

    blueprinttype_diff = diff(prev_blueprinttype_classes, cur_blueprinttype_classes)
    blueprintable_diff = diff(prev_blueprintable_classes, cur_blueprintable_classes)
    blueprintcallable_diff = diff(prev_blueprintcallable_functions, cur_blueprintcallable_functions)

    print("Previous BlueprintType classes: ", len(prev_blueprinttype_classes))
    print("Current BlueprintType classes: ", len(cur_blueprinttype_classes))

    print("Previous Blueprintable classes: ", len(prev_blueprintable_classes))
    print("Current Blueprintable classes: ", len(cur_blueprintable_classes))

    print("Previous BlueprintCallable functions: ", len(prev_blueprintcallable_functions))
    print("Current BlueprintCallable functions: ", len(cur_blueprintcallable_functions))

    diff_to_excel(prev_blueprinttype_classes, cur_blueprinttype_classes, "outputs/BlueprintType.xlsx")
    diff_to_excel(prev_blueprintable_classes, cur_blueprintable_classes, "outputs/Blueprintable.xlsx")
    diff_to_excel(prev_blueprintcallable_functions, cur_blueprintcallable_functions, "outputs/BlueprintCallable.xlsx")
