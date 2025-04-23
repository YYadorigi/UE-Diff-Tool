import json
from cxxheaderparser.types import *
from cxxheaderparser.simple import parse_string
from DiffTool.utils import *

def parse_type_specifier(type_specifier: PQNameSegment) -> str:
    # Extract base type name
    type_name = type_specifier.name

    if isinstance(type_specifier, FundamentalSpecifier):
        return type_name
    
    # Handle template specialization
    if type_specifier.specialization:
        # Process each template argument
        template_args = []
        for template_arg in type_specifier.specialization.args:
            # Handle Type arguments
            if isinstance(template_arg.arg, DecoratedType):
                template_args.append(parse_type(template_arg.arg))
            # Handle Value arguments with tokens
            elif isinstance(template_arg.arg, Value):
                # Concatenate token values while preserving original format
                template_args.append("".join(t.value for t in template_arg.arg.tokens))
            # Handle other argument types (fallback)
            else:
                template_args.append(str(template_arg.arg))
        
        # Combine template arguments with proper syntax
        type_name += f"<{', '.join(template_args)}>"
    
    return type_name


def parse_typename(typename: PQName) -> str:
    return '::'.join([parse_type_specifier(segment) for segment in typename.segments])


def parse_type(type: DecoratedType) -> str:
    # Handle nested type modifiers recursively
    type_str = ""
    
    if isinstance(type, Reference):
        # Handle reference first, then process underlying type
        type_str = parse_type(type.ref_to) + "&"
    elif isinstance(type, MoveReference):
        # Handle move reference first, then process underlying type
        type_str = parse_type(type.moveref_to) + "&&"
    elif isinstance(type, Pointer):
        # Handle pointer, then process underlying type
        type_str = parse_type(type.ptr_to) + "*"
    elif isinstance(type, Array):
        # Handle array (keep base type first)
        type_str = parse_type(type.array_of) + "[]"
    elif isinstance(type, Type):
        # Base case: parse the actual typename
        type_str = parse_typename(type.typename)
        if type.const == True:
            type_str = "const " + type_str
        if type.volatile == True:
            type_str = "volatile " + type_str
    else:
        # Fallback for unknown types
        type_str = str(type)
    
    return type_str


def parse_class_declaration(class_decl: str) -> dict[str, any]:
    """
    Parses a C++ class declaration into its components.
        
    Args:
        class_decl (str): A string representing a C++ class declaration
            Example: `class MyNameSpace::MyClass : public A::B::BaseClass1, protected BaseClass2, private BaseClass3 {};`
            Note: The declaration must begin with 'class', with the class name following it, and end with `{};`

    Returns:
        dict[str, any]: A dictionary containing the parsed components, including the class name and its base classes
    """
    parsed = parse_string(class_decl)

    if not parsed.namespace.classes:
        raise ValueError("No classes found in the provided declaration")
    elif len(parsed.namespace.classes) > 1:
        raise ValueError("Multiple classes found in the provided declaration")

    parsed = parsed.namespace.classes[0].class_decl

    result = {
        'name': parse_typename(parsed.typename),
        'bases': [
            {
                'access': base.access,
                'name': parse_typename(base.typename)
            } for base in parsed.bases
        ]
    }

    # print(json.dumps(result, indent=4))
    
    return result


def parse_function_declaration(func_decl: str) -> dict[str, any]:
    """
    Parses a C++ function declaration into its components.

    Args:
        func_decl (str): A string representing a C++ function declaration
            Example: `static const std::vector<unsigned int>& MyClass::myFunction(float delta) {}`
            Note: The declaration must end with braces, between which and the parentheses there shouldn't be any keywords

    Returns:
        dict[str, any]: A dictionary containing the parsed components, including the function name, return type, and parameters
    """
    parsed = parse_string(func_decl)

    try:
        if parsed.namespace.method_impls:
            if len(parsed.namespace.method_impls) > 1:
                raise ValueError("Multiple methods found in the provided declaration")
            parsed = parsed.namespace.method_impls[0]
        else:
            raise AttributeError
    except AttributeError:
        try:
            if not parsed.namespace.functions:
                raise ValueError("No functions found in the provided declaration")
            if len(parsed.namespace.functions) > 1:
                raise ValueError("Multiple functions found in the provided declaration")
            parsed = parsed.namespace.functions[0]
        except AttributeError as e:
            raise ValueError("No valid function/method declaration found") from e
    
    result = {
        'name': parse_typename(parsed.name),
        'type': parse_type(parsed.return_type),
        'params': [
            {
                'type': parse_type(param.type),
                'name': param.name
            } for param in parsed.parameters
        ]
    }

    # print(json.dumps(result, indent=4))

    return result
