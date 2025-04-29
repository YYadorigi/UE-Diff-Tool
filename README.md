# UE Diff Tool

## Installation

To use the UE Diff Tool, you'll need to have Python 3.10 or later installed on your system.

Once you have Python installed, you can install the required dependencies by running the following command in your terminal or command prompt:

```
pip install -r requirements.txt
```

This will install the necessary packages for this tool.

## Usage

The UE Diff Tool is designed to analyze Unreal Engine (UE) C++ APIs and generate a report of changes between two versions of the engine. Here's how you can use it:

### Blueprint C++ API Diffs

1. Update the following variables in the `blueprint_diff.py` file to match your setup:
   - `UE_PREV_ROOT_DIR`: The path to the previous version of the Unreal Engine installation.
   - `UE_CUR_ROOT_DIR`: The path to the current version of the Unreal Engine installation.
   - `UE_PREV_VERSION`: The version number of the previous Unreal Engine installation.
   - `UE_CUR_VERSION`: The version number of the current Unreal Engine installation.
   - `DIFF_CHOICE`: The choice of whether to analyze the "Plugins" or "Source" directories.

2. Run the `blueprint_diff.py` script:

   ```
   python blueprint_diff.py
   ```

   This will generate an Excel report named `blueprint_diff_{UE_PREV_VERSION}_{UE_CUR_VERSION}.xlsx` in the `outputs` directory. The report will contain information about the added and removed `BlueprintCallable` or `BlueprintPure` UFunctions in `Blueprintable` or `blueprintType` UClasses between the two Unreal Engine versions.

3. Resolve unparseable files manually: Occasionally, certain files may not be automatically parsed by the script. In such cases, you'll need to manually inspect and address the issues according to the relative path information printed in the terminal.

### Deprecated C++ APIs in the Newest Version

1. Update the following variables in the `deprecations.py` file to match your setup:

   - `UE_ROOT_DIR`: The path to the newest version of the Unreal Engine installation.
   - `UE_VERSION`: The version number of the newest Unreal Engine installation.
   - `DEPRECATION_CHOICE `: The choice of whether to analyze the "Plugins" or "Source" directories.

2. Run the `deprecations.py` script:

   ```
   python deprecations.py
   ```

   This will generate an Excel report named `UE_DEPRECATED_{UE_VERSION}.csv` in the `outputs` directory. The report will contain information about the deprecated C++ APIs in the newest version.

## License

This project is licensed under the [MIT License](LICENSE).

## Testing

To run the tests for the UE Diff Tool, you can simply use the following command:

```
pytest
```

This will run the test suite and generate a coverage report.