import pytest
from DiffTool import *

def test_basic_macro_extraction():
    """Test simple macro with single argument"""
    macro_str = "TEST(hello)"
    result = extract_arguments(macro_str, "TEST")
    assert result == "hello"

def test_nested_parentheses():
    """Test arguments with nested parentheses"""
    macro_str = "MACRO(a(b), c)"
    result = extract_arguments(macro_str, "MACRO")
    assert result == "a(b), c"

def test_macro_not_found():
    """Test when macro doesn't exist in string"""
    macro_str = "OTHER_MACRO(123)"
    result = extract_arguments(macro_str, "TEST")
    assert result == ""

def test_multiple_parentheses_groups():
    """Test multiple parentheses groups in arguments"""
    macro_str = "MACRO((a, b), (c, (d, e)))"
    result = extract_arguments(macro_str, "MACRO")
    assert result == "(a, b), (c, (d, e))"

def test_macro_in_middle_of_string():
    """Test macro appears in middle of larger string"""
    macro_str = "prefix TEST(arg1, arg2) suffix"
    result = extract_arguments(macro_str, "TEST")
    assert result == "arg1, arg2"

def test_empty_arguments():
    """Test macro with empty arguments"""
    macro_str = "EMPTY()"
    result = extract_arguments(macro_str, "EMPTY")
    assert result == ""

def test_unclosed_parentheses():
    """Test unclosed parentheses scenario"""
    macro_str = "UNCLOSED(a(b, c)"
    with pytest.raises(ValueError) as exc_info:
        extract_arguments(macro_str, "UNCLOSED")
    assert str(exc_info.value) == f"Unbalanced parentheses in macro string '{macro_str}'"

def test_whitespace_handling():
    """Test arguments with various whitespace"""
    macro_str = "WHITESPACE(  hello,\tworld  )"
    result = extract_arguments(macro_str, "WHITESPACE")
    assert result == "hello,\tworld"

def test_multiple_macro_occurrences():
    """Test string with multiple macro occurrences"""
    macro_str = "FIRST(123) SECOND(456)"
    result = extract_arguments(macro_str, "SECOND")
    assert result == "456"

def test_case_sensitive_matching():
    """Test case-sensitive macro matching"""
    macro_str = "lowercase(arg)"
    result = extract_arguments(macro_str, "LOWERCASE")
    assert result == ""
