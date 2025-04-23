import pytest
from DiffTool import *

@pytest.mark.parametrize("input_str, expected", [
    # Basic cases
    ("a,b,c", ["a", "b", "c"]),
    ("  hello  ", ["hello"]),  # Single argument with spaces
    
    # Nested parentheses
    ("func(1,2),b", ["func(1,2)", "b"]),
    ("test((1,2),3),next(arg)", ["test((1,2),3)", "next(arg)"]),
    ("a,(b,c(d,e)),f", ["a", "(b,c(d,e))", "f"]),
    
    # Edge cases
    ("", []),  # Empty string
    ("a,,b", ["a", "b"]),  # Empty argument
    ("a,b,", ["a", "b"]),  # Trailing comma
    
    # With spaces
    ("  a ,  b  ", ["a", "b"]),
    ("  func( 1 ) ,  ( 2 ) ", ["func( 1 )", "( 2 )"]),
    
    # Complex nesting
    ("nested((a,b),c(d(e))),end", ["nested((a,b),c(d(e)))", "end"]),
    ("start,(middle,(deep)),(shallow)", ["start", "(middle,(deep))", "(shallow)"]),
    
    # Real-world examples
    ("TArray<int32>,FMyStruct", ["TArray<int32>", "FMyStruct"]),
    ("TMap<FString, FVector>,UObject*", ["TMap<FString, FVector>", "UObject*"])
])

def test_split_arguments(input_str, expected):
    """Test various argument splitting scenarios"""
    assert split_arguments(input_str) == expected

def test_unbalanced_parentheses_handling():
    """Should handle balanced parentheses (actual error checking is done in extract_macro_arguments)"""
    # This case is valid as parentheses are balanced
    valid_case = "a,(b,c),d"
    assert split_arguments(valid_case) == ["a", "(b,c)", "d"]
    
    # These cases should raise errors
    invalid_case = "a,(b,c"
    with pytest.raises(ValueError) as exc_info:
        split_arguments(invalid_case)
    assert str(exc_info.value) == f"Unbalanced parentheses or brackets in argument string '{invalid_case}'"

    invalid_case = "a,b)"
    with pytest.raises(ValueError) as exc_info:
        split_arguments(invalid_case)
    assert str(exc_info.value) == f"Unbalanced parentheses or brackets in argument string '{invalid_case}'"
