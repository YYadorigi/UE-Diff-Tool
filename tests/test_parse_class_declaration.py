import pytest
from DiffTool import *

@pytest.mark.parametrize("declaration, expected", [
    (
        "class MyClass : public Base1, protected Base2, private Base3 {};",
        {
            'name': 'MyClass',
            'bases': [
                {'access': 'public', 'name': 'Base1'},
                {'access': 'protected', 'name': 'Base2'},
                {'access': 'private', 'name': 'Base3'}
            ]
        }
    ),
    (
        "class NS1::NS2::MyClass : private NS3::BaseClass {};",
        {
            'name': 'NS1::NS2::MyClass',
            'bases': [{'access': 'private', 'name': 'NS3::BaseClass'}]
        }
    ),
    (
        "class Container : public Base<std::vector<int>> {};",
        {
            'name': 'Container',
            'bases': [{'access': 'public', 'name': 'Base<std::vector<int>>'}]
        }
    ),
    (
        "class StandaloneClass {};",
        {
            'name': 'StandaloneClass',
            'bases': []
        }
    ),
    (
        "class Foo : public Bar<Map<Key,Value>, std::list<int>> {};",
        {
            'name': 'Foo',
            'bases': [{'access': 'public', 'name': 'Bar<Map<Key, Value>, std::list<int>>'}]
        }
    )
])

def test_valid_class_declarations(declaration, expected):
    """Test various valid class declarations"""
    result = parse_class_declaration(declaration)
    assert result['name'] == expected['name']
    assert len(result['bases']) == len(expected['bases'])
    
    for actual_base, expected_base in zip(result['bases'], expected['bases']):
        assert actual_base['access'] == expected_base['access']
        assert actual_base['name'] == expected_base['name']

def test_whitespace_handling():
    """Test handling of irregular whitespace"""
    declaration = """
    class  MyClass   :   
    public  Base1  ,
    protected   Base2  {};  
    """
    result = parse_class_declaration(declaration)
    assert result['name'] == 'MyClass'
    assert [b['name'] for b in result['bases']] == ['Base1', 'Base2']

def test_nested_template_base():
    """Test base class with nested templates"""
    declaration = "class Test : public A<B<C<D>>> {};"
    result = parse_class_declaration(declaration)
    assert result['bases'][0]['name'] == 'A<B<C<D>>>'
