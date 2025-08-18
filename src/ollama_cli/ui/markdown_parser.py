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
    Fix code blocks where language identifier is stuck to the code.

    Examples:
        ```pythondef sum(a, b): -> ```python\ndef sum(a, b):
        ```jsfunction test() { -> ```js\nfunction test() {

    Args:
        text (str): The raw text containing potentially malformed code blocks

    Returns:
        str: Text with properly formatted code blocks
    """
    # List of common programming languages that might get stuck to code
    # Sort by length descending to match longer names first (e.g., "javascript" before "java")
    languages = ['javascript', 'python', 'kotlin', 'swift', 'bash', 'yaml', 'json', 'html', 'ruby', 'java', 'rust', 'dart', 'cpp', 'php', 'sql', 'css', 'xml', 'yml', 'ts', 'js', 'py', 'rb', 'sh', 'go', 'c']

    # Process each language
    for lang in languages:
        # Pattern: ```language followed immediately by a letter/underscore (indicating stuck code)
        # This specifically looks for cases where there's no newline after the language tag
        pattern = f'```{re.escape(lang)}([a-zA-Z_][^`]*?)```'

        # Check if this matches by looking for no preceding matches of longer language names
        if lang in text:
            # Only replace if it's not part of a longer language name
            # For example, don't replace "py" in "python"
            for longer_lang in languages:
                if longer_lang != lang and lang in longer_lang and longer_lang in text:
                    # Skip this language if a longer one containing it exists in the text
                    break
            else:
                # Safe to replace
                replacement = f'```{lang}\n\\1```'
                text = re.sub(pattern, replacement, text, flags=re.DOTALL)

    return text


def preprocess_markdown(text: str) -> str:
    """
    Preprocess markdown text to fix common formatting issues.

    This function applies various fixes to ensure markdown renders properly:
    1. Fixes code block spacing issues
    2. Normalizes line endings
    3. Handles other common markdown formatting problems

    Args:
        text (str): Raw markdown text from AI response

    Returns:
        str: Preprocessed markdown text ready for rendering
    """
    # Fix code block spacing issues
    text = fix_code_block_spacing(text)

    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Ensure proper spacing around headers
    text = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', text)

    # Ensure proper spacing around code blocks
    text = re.sub(r'\n(```)', r'\n\n\1', text)
    text = re.sub(r'(```)\n', r'\1\n\n', text)

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