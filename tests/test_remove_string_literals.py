import pytest
from DiffTool import *

def test_basic_strings():
    # Test basic string variations
    code = '''print("hello") + 'world'"""
    triple quotes
    """'''
    expected = "print(\"\") + \"\"\"\""
    assert remove_string_literals(code) == expected

def test_escaped_quotes():
    # Test escaped quotes inside strings
    code = r'''var = "He said \"Hello\""; res = 'Don\'t'"""
    This is \"triple\" quoted
    """'''
    expected = "var = \"\"; res = \"\"\"\""
    assert remove_string_literals(code) == expected

def test_string_prefixes():
    # Test different string prefixes
    code = '''fr"Formatted {string}" + rf'raw formatted' + u"Unicode"'''
    expected = "\"\" + \"\" + \"\""
    assert remove_string_literals(code) == expected

def test_multiline_strings():
    # Test multiline string handling
    code = '''def func():
        s = """First line
        Second line"""
        return s'''
    
    expected = '''def func():
        s = \"\"
        return s'''
    assert remove_string_literals(code) == expected

def test_mixed_content():
    # Test code with mixed strings and other content
    code = '''class MyClass:
        def __init__(self):
            self.name = "Test"
            self.desc = 'Long\\'s description'
            self.template = """
                Template content
            """'''
    
    expected = '''class MyClass:
        def __init__(self):
            self.name = \"\"
            self.desc = \"\"
            self.template = \"\"'''
    assert remove_string_literals(code) == expected

def test_edge_cases():
    # Test edge cases
    code = '''empty = ""; quotes_in_code = "a"+"b" # "comment"'''
    expected = "empty = \"\"; quotes_in_code = \"\"+\"\" # \"\""
    assert remove_string_literals(code) == expected

def test_no_strings():
    # Test code without any strings
    code = '''import re\n\nprint(123 + 456)'''
    assert remove_string_literals(code) == code

def test_incomplete_strings():
    # Test handling of unterminated strings
    code = '''bad_string = "unterminated\nanother = 'valid' '''
    expected = '''bad_string = "unterminated\nanother = \"\" '''
    assert remove_string_literals(code) == expected
