import pytest
from DiffTool import *

# Test basic functionality
def test_simple_parentheses():
    s = "func(arg1, arg2)"
    assert read_arguments(s, 4) == "arg1, arg2"

# Test nested parentheses
def test_nested_parentheses():
    s = "a(b(c(d)))"
    assert read_arguments(s, 1) == "b(c(d))"

# Test with string literals containing brackets
def test_parentheses_in_strings():
    s = 'call("(not counted)", 5)'
    assert read_arguments(s, 4) == '"(not counted)", 5'

# Test escaped quotes in strings
def test_escaped_quotes():
    s = r"test('escaped \" quote', 3)"
    assert read_arguments(s, 4) == r"'escaped \" quote', 3"

# Test error conditions
def test_invalid_index():
    with pytest.raises(ValueError) as exc:
        read_arguments("test", 3)
    assert "must point to '('" in str(exc.value)

def test_unbalanced_parentheses():
    s = "func(arg1, (arg2)"
    with pytest.raises(ValueError) as exc:
        read_arguments(s, 4)
    assert "Unbalanced parentheses" in str(exc.value)

# Test edge cases
def test_empty_parentheses():
    s = "empty()"
    assert read_arguments(s, 5) == ""

def test_deep_nesting():
    s = "a(b(c(d(e(f)))))"
    assert read_arguments(s, 1) == "b(c(d(e(f))))"

def test_mixed_quotes():
    s = """mix('("quotes")', "('in') strings")"""
    assert read_arguments(s, 3) == """'("quotes")', "('in') strings\""""

# Test maximum truncation in error message
def test_error_truncation():
    long_str = "a(" + "b" * 100
    with pytest.raises(ValueError) as exc:
        read_arguments(long_str, 1)
    assert "..." in str(exc.value)
    assert len(exc.value.args[0]) == 50 + len("Unbalanced parentheses in string: ...")

# Test special characters
def test_special_characters():
    s = r"(\n\t\\\'\"特殊字符)"
    assert read_arguments(s, 0) == r"\n\t\\\'\"特殊字符"
