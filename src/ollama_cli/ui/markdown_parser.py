"""
Markdown parsing utilities for the Ollama CLI TUI application.

This module provides functions to:
1. Fix code block formatting issues where language tags are stuck to code
2. Parse markdown content for display in Textual widgets
3. Handle syntax highlighting for code blocks
"""

import re
from typing import List, Tuple

from textual.widgets import Markdown


def fix_code_block_spacing(text: str) -> str:
    """
    Fix code blocks where language identifier is stuck to the code or code is stuck to closing tag.

    Examples:
        ```pythondef sum(a, b): -> ```python\ndef sum(a, b):
        ```jsfunction test() { -> ```js\nfunction test() {
        return True``` -> return True\n```

    Args:
        text (str): The raw text containing potentially malformed code blocks

    Returns:
        str: Text with properly formatted code blocks
    """
    # List of common programming languages that might get stuck to code
    # Sort by length descending to match longer names first (e.g., "javascript" before "java")
    languages = [
        'javascript', 'typescript', 'python', 'kotlin', 'swift', 'bash', 'yaml',
        'json', 'html', 'ruby', 'java', 'rust', 'dart', 'cpp', 'php', 'sql',
        'css', 'xml', 'yml', 'rb', 'sh', 'go', 'c'
    ]

    # Step 1: Fix opening tags where language is stuck to code (but preserve internal newlines)
    for lang in languages:
        # Pattern: ```language followed immediately by a letter/underscore (indicating stuck code)
        # Use non-greedy matching and preserve all content including newlines
        pattern = f'```{re.escape(lang)}([a-zA-Z_][^`]*?)```'

        # Check if this language exists in text and isn't part of a longer language name
        if f'```{lang}' in text:
            # Only replace if it's not part of a longer language name
            is_standalone = True
            for longer_lang in languages:
                if longer_lang != lang and lang in longer_lang and f'```{longer_lang}' in text:
                    # Skip this language if a longer one containing it exists in the text
                    is_standalone = False
                    break

            if is_standalone:
                # Preserve the original content exactly, just add proper spacing
                replacement = f'```{lang}\n\\1\n```'
                text = re.sub(pattern, replacement, text, flags=re.DOTALL)

    # Step 2: Fix opening tags where language is immediately followed by code
    lang_pattern = '|'.join(re.escape(lang) for lang in languages)
    opening_pattern = f'```({lang_pattern})([a-zA-Z_])'
    text = re.sub(opening_pattern, r'```\1\n\2', text)

    # Step 3: Fix closing tags where code is stuck to ```
    # Pattern: any non-whitespace character followed immediately by ```
    closing_pattern = r'([^\s\n])```'
    text = re.sub(closing_pattern, r'\1\n```', text)

    return text


def fix_malformed_code_blocks(text: str) -> str:
    """
    Advanced fix for malformed code blocks using line-by-line processing.
    This preserves all internal formatting and newlines within code blocks.
    
    Key improvements:
    - Separates language tag processing from code content
    - Preserves exact indentation and whitespace in code
    - Handles stuck language tags and closing markers properly

    Args:
        text (str): The raw text containing potentially malformed code blocks

    Returns:
        str: Text with properly formatted code blocks
    """
    # Define known programming languages (sorted by length to avoid partial matches)
    known_languages = [
        'javascript', 'typescript', 'dockerfile', 'powershell', 'csharp', 
        'python', 'kotlin', 'scala', 'swift', 'html', 'yaml', 'json',
        'bash', 'ruby', 'java', 'rust', 'cpp', 'php', 'sql', 'xml',
        'yml', 'css', 'c++', 'c#', 'go', 'sh', 'js', 'ts', 'py', 'rb', 'c'
    ]
    
    lines = text.split('\n')
    fixed_lines = []
    in_code_block = False
    code_block_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for code block start
        if line.strip().startswith('```') and not in_code_block:
            stripped_line = line.strip()
            
            if len(stripped_line) == 3:
                # Just ``` without language
                fixed_lines.append('```')
                code_block_lines = []
            else:
                # Extract what comes after ```
                after_backticks = stripped_line[3:]
                language = ''
                code_content = ''
                
                # Try to match known languages
                for lang in known_languages:
                    if after_backticks.lower().startswith(lang.lower()):
                        next_pos = len(lang)
                        # Check if this is the complete language (not part of a longer word)
                        if next_pos == len(after_backticks):
                            # Perfect match - just the language
                            language = lang
                            code_content = ''
                            break
                        elif next_pos < len(after_backticks):
                            next_char = after_backticks[next_pos]
                            # For known languages, be more permissive - assume code is stuck
                            # if the next character could be the start of code
                            if (next_char.isalpha() or next_char == '_' or next_char == '(' or 
                                next_char == '{' or next_char == '[' or next_char == ' '):
                                # This looks like stuck code
                                language = lang
                                code_content = after_backticks[next_pos:]
                                break
                            elif not (next_char.isalpha() or next_char.isdigit() or next_char == '_'):
                                # Traditional separator (space, punctuation, etc.)
                                language = lang
                                code_content = after_backticks[next_pos:]
                                break
                
                # If no language detected, try generic detection
                if not language:
                    # Look for pattern: sequence of letters/numbers followed by non-letter
                    match = re.match(r'^([a-zA-Z][a-zA-Z0-9_+-]*?)([^a-zA-Z0-9_+-].*)?$', after_backticks)
                    if match and len(match.group(1)) <= 20:  # Reasonable language name length
                        language = match.group(1).lower()
                        code_content = match.group(2) or ''
                    else:
                        # Treat entire thing as language if short enough, otherwise as malformed
                        if len(after_backticks) <= 20 and after_backticks.isalnum():
                            language = after_backticks.lower()
                            code_content = ''
                        else:
                            # Malformed - treat as code without language
                            language = ''
                            code_content = after_backticks

                # Start code block
                if language:
                    fixed_lines.append(f'```{language}')
                else:
                    fixed_lines.append('```')
                
                # Add any stuck code content
                if code_content and not code_content.isspace():
                    code_block_lines = [code_content]
                else:
                    code_block_lines = []

            in_code_block = True

        # Check for code block end
        elif '```' in line and in_code_block:
            closing_pos = line.find('```')
            
            if line.strip() == '```':
                # Clean closing tag
                fixed_lines.extend(code_block_lines)
                fixed_lines.append('```')
            else:
                # Handle code stuck to closing tag
                if closing_pos > 0:
                    # Code before closing tag
                    code_part = line[:closing_pos]
                    remaining_part = line[closing_pos + 3:]
                    
                    # Add code part (preserve exact whitespace)
                    code_block_lines.append(code_part)
                    
                    # Close code block
                    fixed_lines.extend(code_block_lines)
                    fixed_lines.append('```')
                    
                    # Add remaining content after closing tag if any
                    if remaining_part.strip():
                        fixed_lines.append(remaining_part)
                        
                elif closing_pos == 0:
                    # Closing tag at start, but with content after
                    remaining_part = line[3:]
                    fixed_lines.extend(code_block_lines)
                    fixed_lines.append('```')
                    if remaining_part.strip():
                        fixed_lines.append(remaining_part)
                else:
                    # No ``` found (shouldn't happen), treat as code line
                    code_block_lines.append(line)
                    continue

            in_code_block = False
            code_block_lines = []

        elif in_code_block:
            # Inside code block - preserve exactly as is
            code_block_lines.append(line)
        else:
            # Regular line outside code blocks
            fixed_lines.append(line)

        i += 1

    # Handle unclosed code blocks
    if in_code_block:
        fixed_lines.extend(code_block_lines)
        fixed_lines.append('```')

    return '\n'.join(fixed_lines)


def preserve_code_block_newlines(text: str) -> str:
    """
    Ensure that newlines within code blocks are preserved.
    This is specifically for handling AI responses that might have formatting issues.

    Args:
        text (str): Raw text from AI response

    Returns:
        str: Text with preserved code block newlines
    """
    # Find all code blocks and ensure they maintain proper structure
    pattern = r'```(\w*)\n?(.*?)```'

    def replace_code_block(match):
        language = match.group(1)
        code_content = match.group(2)

        # If code content doesn't start with newline, add one
        if not code_content.startswith('\n'):
            code_content = '\n' + code_content

        # If code content doesn't end with newline, add one
        if not code_content.endswith('\n'):
            code_content = code_content + '\n'

        return f'```{language}{code_content}```'

    return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)


def preprocess_markdown(text: str) -> str:
    """
    Preprocess markdown text to fix common formatting issues.

    This function applies various fixes to ensure markdown renders properly:
    1. Fixes code block spacing issues (both simple and complex cases)
    2. Preserves internal code block formatting and newlines
    3. Normalizes line endings
    4. Handles other common markdown formatting problems

    Args:
        text (str): Raw markdown text from AI response

    Returns:
        str: Preprocessed markdown text ready for rendering
    """
    # Normalize line endings first
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Preserve code block newlines first
    text = preserve_code_block_newlines(text)

    # Apply simple regex fixes (but be careful not to break code blocks)
    text = fix_code_block_spacing(text)

    # Apply advanced line-by-line fixes for complex cases
    text = fix_malformed_code_blocks(text)

    # Ensure proper spacing around headers (but not inside code blocks)
    # Split by code blocks to avoid affecting them
    parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)

    for i in range(0, len(parts), 2):  # Only process non-code-block parts
        if parts[i]:
            # Fix header spacing
            parts[i] = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', parts[i])

    text = ''.join(parts)

    # Ensure proper spacing around code blocks
    text = re.sub(r'\n```', r'\n\n```', text)
    text = re.sub(r'```\n', r'```\n\n', text)

    # Clean up excessive newlines (but preserve single newlines in code)
    parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)

    for i in range(0, len(parts), 2):  # Only process non-code-block parts
        if parts[i]:
            parts[i] = re.sub(r'\n{3,}', '\n\n', parts[i])

    text = ''.join(parts)

    return text.strip()


def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
    """
    Extract code blocks from markdown text, preserving internal formatting.

    Args:
        text (str): Markdown text containing code blocks

    Returns:
        List[Tuple[str, str]]: List of (language, code) tuples with preserved formatting
    """
    pattern = r'```(\w*)\n?(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)

    result = []
    for lang, code in matches:
        # Clean up the code but preserve internal structure
        code = code.strip('\n')  # Remove leading/trailing newlines only
        result.append((lang if lang else 'text', code))

    return result


def create_markdown_widget(content: str) -> Markdown:
    """
    Create a Textual Markdown widget with preprocessed content.

    Args:
        content (str): Raw markdown content from AI response

    Returns:
        Markdown: Textual Markdown widget ready for display
    """
    processed_content = preprocess_markdown(content)
    return Markdown(processed_content)


def is_code_heavy_response(text: str) -> bool:
    """
    Determine if a response is primarily code blocks.

    This can be used to decide whether to use different rendering approaches
    for responses that are mostly code vs mostly text.

    Args:
        text (str): The response text to analyze

    Returns:
        bool: True if response is primarily code blocks
    """
    code_blocks = extract_code_blocks(text)
    if not code_blocks:
        return False

    # Calculate the ratio of code to total content
    total_lines = len(text.split('\n'))
    code_lines = sum(len(code.split('\n')) for _, code in code_blocks)

    # Consider it code-heavy if more than 60% is code
    return (code_lines / total_lines) > 0.6 if total_lines > 0 else False


def debug_code_blocks(text: str) -> str:
    """
    Debug function to help identify code block issues in text.

    Args:
        text (str): Text to analyze

    Returns:
        str: Debug information about code blocks found
    """
    debug_info = []
    debug_info.append("=== CODE BLOCK ANALYSIS ===")
    debug_info.append(f"Original text length: {len(text)} chars")
    debug_info.append(f"Original line count: {len(text.split(chr(10)))}")

    # Find all potential code block markers
    lines = text.split('\n')
    code_block_lines = []
    for i, line in enumerate(lines):
        if '```' in line:
            debug_info.append(f"Line {i+1}: {repr(line)}")
            code_block_lines.append(i+1)

    debug_info.append(f"\nCode block markers found at lines: {code_block_lines}")

    # Extract code blocks
    blocks = extract_code_blocks(text)
    debug_info.append(f"\nExtracted {len(blocks)} code blocks:")
    for i, (lang, code) in enumerate(blocks):
        debug_info.append(f"Block {i+1} ({lang}): {len(code.split(chr(10)))} lines")

    debug_info.append("\n=== AFTER PREPROCESSING ===")
    processed = preprocess_markdown(text)
    debug_info.append(f"Processed text length: {len(processed)} chars")
    debug_info.append(f"Processed line count: {len(processed.split(chr(10)))}")

    lines = processed.split('\n')
    for i, line in enumerate(lines):
        if '```' in line:
            debug_info.append(f"Line {i+1}: {repr(line)}")

    return '\n'.join(debug_info)


def test_code_block_parsing():
    """
    Test function to verify code block parsing works correctly.

    Returns:
        str: Test results
    """
    test_cases = [
        # Case 1: Language stuck to code
        "```pythondef hello():\n    print('world')\n    return True```",

        # Case 2: Code stuck to closing tag
        "```python\ndef hello():\n    print('world')\n    return True```",

        # Case 3: Multiple issues
        "```javascriptfunction test() {\n    console.log('test');\n    return false;}```",

        # Case 4: Proper formatting (should be preserved)
        "```python\ndef hello():\n    print('world')\n    return True\n```"
    ]

    results = []
    for i, test in enumerate(test_cases):
        results.append(f"Test {i+1}:")
        results.append(f"Input: {repr(test)}")
        processed = preprocess_markdown(test)
        results.append(f"Output: {repr(processed)}")
        results.append("")

    return '\n'.join(results)