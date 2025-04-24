import os
import re
from pathlib import Path
import pandas as pd
from DiffTool import *

# Configure the path to the Unreal Engine source code directory
UE_PREV_ROOT_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.4")
UE_CUR_ROOT_DIR = Path("E:\\Program Files\\Epic Games\\UE_5.5")

def parse_ue_classes(UEpath: Path, UEversion: str):
    u_classes: dict[str, dict[str, any]] = {}

    deprecated_functions: dict[str, list[any]] = {}

    UE_SOURCE_DIR = Path("Engine\\Source")
    UE_DEVELOPER_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Developer")
    UE_EDITOR_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Editor")
    UE_RUNTIME_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Runtime")
    UE_PLUGINS_DIR = os.path.join(UEpath, UE_SOURCE_DIR, "Plugins")

    # Traverse the UE source code directory
    for target_dir in [UE_DEVELOPER_DIR, UE_EDITOR_DIR, UE_RUNTIME_DIR, UE_PLUGINS_DIR]:
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".h"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                            # Read the file content
                            content = f.read()

                            # Preprocessing
                            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)    # Remove C-style comments
                            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)     # Remove C++ comments
                            content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)      # Remove preprocessor directives
    
                            # Extract all UCLASS macro definitions
                            class_matches = re.finditer(
                                r'UCLASS\s*\((.*?)\)\s*'
                                r'class\s+(.*?)\s*([{;])',    # Skip content between #if and #endif
                                content,
                                re.DOTALL
                            )

                            for class_match in class_matches:
                                uclass_params = split_arguments(extract_arguments('UCLASS(' + class_match.group(1) + ')', 'UCLASS'))

                                class_decl = (lambda decl: 
                                    'class ' + re.sub(r'\b[A-Z_]+_API\s*', '', decl.strip()) + ' {};'
                                )(class_match.group(2))

                                # Match UE_DEPRECATED macro
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
                            
                                class_body = content[class_match.end() - 1:]
                                if class_body.startswith(';'):
                                    continue
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
                                class_body = class_body[:(i+1)]
                            
                                # Find all UFUNCTION declarations in class body
                                function_matches = re.finditer(
                                    r'UFUNCTION.*?(?=\{|;)',     # Function declaration ending
                                    class_body,
                                    re.DOTALL
                                )

                                for func_match in function_matches:
                                    ufunction_str = extract_arguments(func_match.group(0), 'UFUNCTION')
                                    ufunction_params = split_arguments(ufunction_str)

                                    ufunction_macro = re.search(
                                        r'UFUNCTION\s*\(\s*?{}\s*?\)'.format(re.escape(ufunction_str)),
                                        func_match.group(0), 
                                        re.DOTALL
                                    )

                                    func_decl = func_match.group(0)[len(ufunction_macro.group(0)):].strip()

                                    func_name = func_decl[:func_decl.find('(')].strip().split()[-1]

                                    # Add function name to list
                                    u_classes[class_name]["ufunctions"].append({
                                        "name": func_name,
                                        "ufunc_params": ufunction_params
                                    })
                                
                                # Find all UE_DEPRECATED declarations in class body
                                class_body = re.sub(r'^\s*UFUNCTION\S+.*\n?', '', class_body, flags=re.MULTILINE)
                                
                                deprecated_matches = re.finditer(
                                    r'(UE_DEPRECATED\s*\(\s*(\d+\.\d+)\s*,\s*\"(.*?)\"\s*\))(.*?)(?=\{|;)',
                                    class_body,
                                    re.DOTALL
                                )

                                for deprecated_match in deprecated_matches:
                                    deprecated_version = deprecated_match.group(2)
                                    deprecated_reason = deprecated_match.group(3)

                                    func_decl = deprecated_match.group(4).strip()

                                    func_name = func_decl[:func_decl.find('(')].strip().split()[-1]
                                    # print(f"{func_decl} -> {func_name}: {deprecated_reason}")

                                    # if func_name not in u_classes[class_name]["ufunctions"]:
                                    #     pass
                                    

                                    if float(deprecated_version) == float(UEversion):
                                        # print(f"{UEversion} {func_name} deprecated in {deprecated_version}: {deprecated_reason}")
                                        if class_name not in deprecated_functions:
                                            deprecated_functions[class_name] = []
                                        deprecated_functions[class_name].append({
                                            "name": func_name,
                                            "reason": deprecated_reason
                                        })

                    except Exception as e:
                        continue

    return u_classes, deprecated_functions


def filter_blueprinttype_classes(u_classes: dict[str, dict[str, any]]):
    blueprinttype_classes = []
    for class_name, class_info in u_classes.items():
        if "BlueprintType" in class_info["uclass_params"]:
            blueprinttype_classes.append({
                "name": class_name,
                "relpath": class_info["relpath"],
                "ufunctions": filter_blueprint_functions(class_info["ufunctions"])
            })
    return blueprinttype_classes


def filter_blueprintable_classes(u_classes: dict[str, dict[str, any]]):
    blueprintable_cache = {}
    
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
    result = []
    for cls_name, cls_info in u_classes.items():
        if is_blueprintable(cls_name):
            result.append({
                "name": cls_name,
                "relpath": cls_info["relpath"],
                "ufunctions": filter_blueprint_functions(cls_info["ufunctions"])
            })
    
    return result


def filter_blueprint_functions(u_functions: list[dict[str, any]]) -> list[str]:
    blueprint_functions: list[str] = []
    for function in u_functions:
        if "BlueprintCallable" in function["ufunc_params"] or "BlueprintPure" in function["ufunc_params"]:
            blueprint_functions.append(function["name"])
    return blueprint_functions


def diff(prev_list, cur_list):
    prev_classes = {cls['name']: cls for cls in prev_list}
    cur_classes = {cls['name']: cls for cls in cur_list}
    
    result = []
    
    all_classes = set(prev_classes.keys()).union(cur_classes.keys())
    
    for cls_name in all_classes:
        prev_cls = prev_classes.get(cls_name)
        cur_cls = cur_classes.get(cls_name)
        
        prev_funcs = prev_cls['ufunctions'] if prev_cls else []
        cur_funcs = cur_cls['ufunctions'] if cur_cls else []
        
        added = list(set(cur_funcs) - set(prev_funcs))
        removed = list(set(prev_funcs) - set(cur_funcs))
        
        # Only keep classes with actual changes
        if added or removed:  # Check if either list has elements
            result.append({
                'class_name': cls_name,
                'module': cur_cls['relpath'].split('\\')[2] + "::" + cur_cls['relpath'].split('\\')[3],
                'relpath': cur_cls['relpath'],
                'added_functions': sorted(added),
                'removed_functions': sorted(removed)
            })
    
    return result


def diff_to_excel(diff_result, output_file):
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
    final_df = combined_df[['class_name', 'module', 'relpath', 'change_type', 'function']]
    
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name="API Changes", index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['API Changes']
        for i, col in enumerate(final_df.columns):
            max_len = max(final_df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    
    print(f"Excel report saved to: {output_file}")
    

if __name__ == "__main__":
    prev_u_classes, _ = parse_ue_classes(UE_PREV_ROOT_DIR, "5.4")

    prev_blueprint_classes = list({
        cls["name"]: cls
        for cls in filter_blueprinttype_classes(prev_u_classes) + filter_blueprintable_classes(prev_u_classes)
    }.values())
    
    # Parse current classes
    cur_u_classes, deprecated_funcs = parse_ue_classes(UE_CUR_ROOT_DIR, "5.5")
    
    # Merge and deduplicate current classes
    cur_blueprint_classes = list({
        cls["name"]: cls 
        for cls in filter_blueprinttype_classes(cur_u_classes) + filter_blueprintable_classes(cur_u_classes)
    }.values())

    blueprint_api_diff = diff(prev_blueprint_classes, cur_blueprint_classes)

    # import json
    # print(json.dumps(blueprint_api_diff, indent=4))

    diff_to_excel(blueprint_api_diff, "outputs/diff.xlsx")

    # print deprecated funcs
    import json
    print(json.dumps(deprecated_funcs, indent=4))