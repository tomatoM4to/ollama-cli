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
        'css', 'xml', 'yml', 'ts', 'js', 'py', 'rb', 'sh', 'go', 'c'
    ]

    # Step 1: Fix opening tags where language is stuck to code
    for lang in languages:
        # Pattern: ```language followed immediately by a letter/underscore (indicating stuck code)
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
                replacement = f'```{lang}\n\\1\n```'
                text = re.sub(pattern, replacement, text, flags=re.DOTALL)

    # Step 2: Fix cases where code blocks don't have proper newlines
    # This handles cases like ```python def main(): or return True```

    # Fix opening: ```language<code> -> ```language\n<code>
    lang_pattern = '|'.join(re.escape(lang) for lang in languages)
    opening_pattern = f'```({lang_pattern})([a-zA-Z_])'
    text = re.sub(opening_pattern, r'```\1\n\2', text)

    # Step 3: Fix closing tags where code is stuck to ```
    # Pattern: any non-whitespace character followed immediately by ```
    closing_pattern = r'([^\s\n])```'
    text = re.sub(closing_pattern, r'\1\n```', text)

    # Step 4: Handle edge cases where there might be multiple spaces or inconsistent formatting
    # Normalize multiple newlines after opening tags
    text = re.sub(r'```(\w+)\n\n+', r'```\1\n', text)

    # Normalize multiple newlines before closing tags
    text = re.sub(r'\n\n+```', r'\n```', text)

    return text


def fix_malformed_code_blocks(text: str) -> str:
    """
    Advanced fix for malformed code blocks using more sophisticated pattern matching.

    This function handles complex cases where simple regex might not work.

    Args:
        text (str): The raw text containing potentially malformed code blocks

    Returns:
        str: Text with properly formatted code blocks
    """
    lines = text.split('\n')
    fixed_lines = []
    in_code_block = False
    current_language = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for code block start
        if line.startswith('```') and not in_code_block:
            # Extract language and potential stuck code
            match = re.match(r'```(\w+)(.+)?', line)
            if match:
                language = match.group(1)
                stuck_code = match.group(2)

                # Add proper opening
                fixed_lines.append(f'```{language}')

                # If there's stuck code, add it on next line
                if stuck_code and stuck_code.strip():
                    fixed_lines.append(stuck_code.strip())

                in_code_block = True
                current_language = language
            else:
                # Just ```
                fixed_lines.append(line)
                in_code_block = True

        # Check for code block end
        elif '```' in line and in_code_block:
            # Check if code is stuck to closing tag
            if not line.strip() == '```':
                # Split the line at ```
                parts = line.split('```')
                if len(parts) == 2:
                    code_part = parts[0]
                    after_part = parts[1]

                    # Add code part if it exists
                    if code_part.strip():
                        fixed_lines.append(code_part)

                    # Add closing tag
                    fixed_lines.append('```')

                    # Add any content after closing tag
                    if after_part.strip():
                        fixed_lines.append(after_part)
                else:
                    # Multiple ``` in line, handle carefully
                    fixed_lines.append(line)
            else:
                # Properly formatted closing tag
                fixed_lines.append(line)

            in_code_block = False
            current_language = None

        else:
            # Regular line
            fixed_lines.append(line)

        i += 1

    return '\n'.join(fixed_lines)


def preprocess_markdown(text: str) -> str:
    """
    Preprocess markdown text to fix common formatting issues.

    This function applies various fixes to ensure markdown renders properly:
    1. Fixes code block spacing issues (both simple and complex cases)
    2. Normalizes line endings
    3. Handles other common markdown formatting problems

    Args:
        text (str): Raw markdown text from AI response

    Returns:
        str: Preprocessed markdown text ready for rendering
    """
    # Normalize line endings first
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Apply simple regex fixes first
    text = fix_code_block_spacing(text)

    # Apply advanced line-by-line fixes for complex cases
    text = fix_malformed_code_blocks(text)

    # Ensure proper spacing around headers
    text = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', text)

    # Ensure proper spacing around code blocks (but don't add too much)
    text = re.sub(r'\n(```)', r'\n\n\1', text)
    text = re.sub(r'(```)\n', r'\1\n\n', text)

    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
    """
    Extract code blocks from markdown text.

    Args:
        text (str): Markdown text containing code blocks

    Returns:
        List[Tuple[str, str]]: List of (language, code) tuples
    """
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [(lang if lang else 'text', code.strip()) for lang, code in matches]


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

    # Find all potential code block markers
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if '```' in line:
            debug_info.append(f"Line {i+1}: {repr(line)}")

    debug_info.append("\n=== AFTER PREPROCESSING ===")
    processed = preprocess_markdown(text)

    lines = processed.split('\n')
    for i, line in enumerate(lines):
        if '```' in line:
            debug_info.append(f"Line {i+1}: {repr(line)}")

    return '\n'.join(debug_info)