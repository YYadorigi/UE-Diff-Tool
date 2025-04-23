import pytest
from DiffTool import *

# Test normal function declarations
def test_basic_function_declaration():
    func_decl = "int myFunction() {}"
    result = parse_function_declaration(func_decl)
    
    assert result == {
        'name': 'myFunction',
        'type': 'int',
        'params': []
    }

def test_function_with_parameters():
    func_decl = "void calculate(float a, const std::string& b) {}"
    result = parse_function_declaration(func_decl)
    
    assert result['name'] == 'calculate'
    assert result['type'] == 'void'
    assert len(result['params']) == 2
    assert result['params'][0] == {'type': 'float', 'name': 'a'}
    assert result['params'][1] == {'type': 'const std::string&', 'name': 'b'}

# Test complex return types
def test_complex_return_type():
    func_decl = "const std::vector<unsigned int>& MyClass::getValues() {}"
    result = parse_function_declaration(func_decl)
    
    assert result['name'] == 'MyClass::getValues'
    assert result['type'] == 'const std::vector<unsigned int>&'
    assert result['params'] == []

# Test template types
def test_template_parameters():
    func_decl = "template<typename T> T process(std::map<int, T*> data) {}"
    result = parse_function_declaration(func_decl)
    
    assert result['name'] == 'process'
    assert result['type'] == 'T'
    assert result['params'][0]['type'] == 'std::map<int, T*>'
    assert result['params'][0]['name'] == 'data'

# Test edge cases
def test_no_parameters():
    func_decl = "bool isEmpty() {}"
    result = parse_function_declaration(func_decl)
    
    assert result['name'] == 'isEmpty'
    assert result['type'] == 'bool'
    assert result['params'] == []

def test_pointer_return_type():
    func_decl = "MyClass* createInstance(int version) {}"
    result = parse_function_declaration(func_decl)
    
    assert result['type'] == 'MyClass*'
    assert result['params'][0]['type'] == 'int'

# Test nested templates
def test_nested_template_parameters():
    func_decl = "std::pair<std::vector<int>, std::map<std::string, double>> parseData() {}"
    result = parse_function_declaration(func_decl)
    
    expected_type = "std::pair<std::vector<int>, std::map<std::string, double>>"
    assert result['type'] == expected_type

# Test reference parameters
def test_reference_parameters():
    func_decl = "void modify(int& input, const std::string& output) {}"
    result = parse_function_declaration(func_decl)
    
    assert result['params'][0]['type'] == 'int&'
    assert result['params'][1]['type'] == 'const std::string&'

# Test static functions
def test_static_function():
    func_decl = "static int counter() {}"
    result = parse_function_declaration(func_decl)
    
    assert result['name'] == 'counter'
    assert result['type'] == 'int'

# Test array parameters
def test_array_parameters():
    func_decl = "void process(int data[], char* buffer[]) {}"
    result = parse_function_declaration(func_decl)
    
    assert result['params'][0]['type'] == 'int[]'
    assert result['params'][1]['type'] == 'char*[]'
