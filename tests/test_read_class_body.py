import pytest
from DiffTool import *

def test_basic_brace_extraction():
    """Test simple single-level brace extraction"""
    s = "class { content here }"
    result = read_class_body(s, s.index('{'))
    assert result == "content here"

def test_nested_braces():
    """Test extraction with nested braces"""
    s = "outer { level1 { level2 } }"
    result = read_class_body(s, s.index('{'))
    assert result == "level1 { level2 }"

def test_string_literals_with_braces():
    """Test braces inside string literals should be ignored"""
    s = '{ str = "ignore { }"; real = { inner } }'
    result = read_class_body(s, s.index('{'))
    assert result == 'str = "ignore { }"; real = { inner }'

def test_escaped_quotes():
    """Test properly handle escaped quotes in strings"""
    s = r'{ quote = "escaped \" quote"; value = 42 }'
    result = read_class_body(s, s.index('{'))
    assert result == r'quote = "escaped \" quote"; value = 42'

def test_unbalanced_braces():
    """Test detection of unbalanced braces"""
    s = "unbalanced { { brace "
    with pytest.raises(ValueError) as excinfo:
        read_class_body(s, s.index('{'))
    assert "Unbalanced braces" in str(excinfo.value)

def test_invalid_start_index():
    """Test invalid start index handling"""
    s = "some content"
    with pytest.raises(ValueError) as excinfo:
        read_class_body(s, 100)
    assert "Index must point to '{' character" in str(excinfo.value)

def test_mixed_nesting_and_strings():
    """Test complex scenario with mixed nesting and strings"""
    s = '''
    {
        obj = {
            key = "value with { }",
            arr = [
                { item: "}" }
            ]
        }
    }'''
    result = read_class_body(s, s.index('{'))
    expected = '''obj = {
            key = "value with { }",
            arr = [
                { item: "}" }
            ]
        }'''
    assert result.strip() == expected.strip()

def test_immediate_closing_brace():
    """Test empty content case"""
    s = "{ }"
    result = read_class_body(s, 0)
    assert result == ""

def test_string_with_quotes():
    """Test string containing matching quotes"""
    s = '{ str = "quoted \\" string" }'
    result = read_class_body(s, 0)
    assert result == 'str = "quoted \\" string"'

def test_multiple_nesting_levels():
    """Test multiple levels of nesting"""
    s = "{{{{deep}}}}"
    result = read_class_body(s, 0)
    assert result == "{{{deep}}}"

def test_code_after_closing_brace():
    """Test content continues after closing brace"""
    s = "prefix { valid } suffix"
    result = read_class_body(s, s.index('{'))
    assert result == "valid"
