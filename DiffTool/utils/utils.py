import re


def remove_string_literals(code: str) -> str:
    """Remove all string literals from code while preserving other content
    
    Args:
        code: Input source code string
        
    Returns:
        Code with all string literals removed
    """
    # Match all string literals with handling for:
    # - Single/double/triple quotes
    # - Escaped quotes
    # - Raw/f-strings prefixes
    # - Multiline strings
    pattern = re.compile(r'''
        (                           # Capture group for entire string
            (?:                     # Non-capturing group for prefixes
                (?:r|u|f|fr|rf|TEXT\s*\()  # String prefixes (including TEXT macro)
            )?
            (                       # String content group
                (?:                 # Triple quoted strings
                    "{3}            # Triple double quotes
                    (?:\\"|.)*?     # Content (allow escaped quotes)
                    (?<!\\)"{3}     # Closing quotes (not escaped)
                    | '{3}          # Triple single quotes
                    (?:\\'|.)*?     # Content
                    (?<!\\)'{3}     # Closing quotes
                )
                |                   # Single line strings
                "(?:\\"|[^"])*?     # Double quoted
                (?<!\\)"            # Closing quote (not escaped)
                | '(?:\\'|[^'])*?   # Single quoted
                (?<!\\)'            # Closing quote (not escaped)
            )
        )
    ''', re.VERBOSE | re.DOTALL)
    
    return pattern.sub("\"\"", code)


def extract_arguments(sentence: str, keyword: str) -> str:
    """
    Extracts the arguments inside the parentheses from a given string formed as `XXX(...)`
    
    Args:
        sentence (str): The string containing the assigned keyword and its corresponding arguments
        keyword (str): The name of the keyword
        
    Returns:
        str: The extracted arguments between parentheses, excluding outer brackets
    """
    pattern = re.compile(rf"{re.escape(keyword)}\s*\(")
    match = pattern.search(sentence)
    if not match:
        return ''

    start = match.end()
    nesting = 1
    chars = []
    i = start
    in_string = False   # Track string literals
    quote_char = None   # Track which quote started the string
    prev_char = None    # Track previous character for escape detection

    while i < len(sentence) and nesting > 0:
        char = sentence[i]
        
        # Handle string literals
        if char in ('"', "'") and prev_char != '\\':
            if not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char:
                in_string = False
                quote_char = None
        elif in_string:
            # Skip bracket counting inside strings
            prev_char = char
            chars.append(char)
            i += 1
            continue

        # Update bracket counters only when not in string
        if not in_string:
            if char == '(':
                nesting += 1
            elif char == ')':
                nesting -= 1

        if nesting > 0:
            chars.append(char)
            
        prev_char = char
        i += 1

    if nesting != 0:
        raise ValueError(f"Unbalanced parentheses in macro string '{sentence}'")
    return ''.join(chars).strip()


def read_arguments(s: str, index: int) -> str:
    """
    Extracts nested parentheses content starting from given index (which should point to '(')
    
    Args:
        s: The input string containing parentheses
        index: Start position (must point to '(' character)
        
    Returns:
        Extracted content between parentheses (excluding outer brackets)
    
    Raises:
        ValueError: If invalid index or unbalanced parentheses
    """
    if index >= len(s) or s[index] != '(':
        raise ValueError("Index must point to '(' character")
    
    nesting = 1
    chars = []
    i = index + 1   # Start after initial '('
    in_string = False
    quote_char = None
    prev_char = None
    
    while i < len(s) and nesting > 0:
        char = s[i]
        
        # Handle string literals
        if char in ('"', "'") and prev_char != '\\':
            if not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char:
                in_string = False
                quote_char = None
        elif in_string:
            # Skip bracket counting inside strings
            prev_char = char
            chars.append(char)
            i += 1
            continue

        # Update bracket counters when not in string
        if not in_string:
            if char == '(':
                nesting += 1
            elif char == ')':
                nesting -= 1

        if nesting > 0:  # Only collect until final closing bracket
            chars.append(char)
            
        prev_char = char
        i += 1

    if nesting != 0:
        raise ValueError(f"Unbalanced parentheses in string: {s[index:index+50]}...")
    
    return ''.join(chars).strip()


def split_arguments(arg_str: str) -> list[str]:
    """
    Splits an arg string into a list of arguments by commas, handling nested parentheses and angle brackets.

    Args:
        args (str): The string containing the arguments separated by commas

    Returns:
        list[str]: A list of arguments
    """
    args = []
    current = []
    paren_nesting = 0   # Track parentheses ()
    angle_nesting = 0   # Track angle brackets <>
    in_string = False   # Track string literals
    quote_char = None   # Track which quote started the string
    prev_char = None    # Track previous character for escape detection

    for char in arg_str:
        # Handle string literals
        if char in ('"', "'") and prev_char != '\\':
            if not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char:
                in_string = False
                quote_char = None
        elif in_string:
            # Skip bracket counting inside strings
            prev_char = char
            current.append(char)
            continue

        # Update bracket counters only when not in string
        if not in_string:
            if char == '(':
                paren_nesting += 1
            elif char == ')':
                paren_nesting -= 1
            elif char == '<':
                angle_nesting += 1
            elif char == '>':
                angle_nesting -= 1

        # Split on commas only when not nested and not in string
        if char == ',' and paren_nesting == 0 and angle_nesting == 0 and not in_string:
            if current:
                args.append(''.join(current).strip())
                current = []
        else:
            current.append(char)

        prev_char = char

    if current:
        args.append(''.join(current).strip())
    if paren_nesting != 0 or angle_nesting != 0:
        raise ValueError(f"Unbalanced parentheses or brackets in argument string '{arg_str}'")
    return args


def read_class_body(s: str, index: int) -> str:
    """
    Extracts nested braces content starting from given index (which should point to '{')
    
    Args:
        s: The input string containing braces
        index: Start position (must point to '{' character)
        
    Returns:
        Extracted content between braces (excluding outer braces)
    
    Raises:
        ValueError: If invalid index or unbalanced braces
    """
    if index >= len(s) or s[index] != '{':
        raise ValueError("Index must point to '{' character")
    
    nesting = 1
    chars = []
    i = index + 1   # Start after initial '{'
    in_string = False
    quote_char = None
    prev_char = None
    
    while i < len(s) and nesting > 0:
        char = s[i]
        
        # Handle string literals
        if char in ('"', "'") and prev_char != '\\':
            if not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char:
                in_string = False
                quote_char = None
        elif in_string:
            # Skip brace counting inside strings
            prev_char = char
            chars.append(char)
            i += 1
            continue

        # Update brace counters when not in string
        if not in_string:
            if char == '{':
                nesting += 1
            elif char == '}':
                nesting -= 1

        if nesting > 0:  # Only collect until final closing brace
            chars.append(char)
            
        prev_char = char
        i += 1

    if nesting != 0:
        raise ValueError(f"Unbalanced braces in string: {s[index:]}...")
    
    return ''.join(chars).strip()