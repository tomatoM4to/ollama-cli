from enum import Enum

class ResponseFormat(Enum):
    MARKDOWN = 'markdown'
    PLAIN = 'plain'
    CODE = 'code'
    STRUCTURED = 'structured'


class PromptManager:
    def __init__(self):
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        default_prompts = {
            'system_base': """
You are a helpful AI assistant that communicates using well-formatted Markdown.

# Response Guidelines:

## Formatting Rules:
- Use **bold** for important terms and concepts
- Use *italics* for emphasis
- Use `inline code` for technical terms, commands, or variables
- Use code blocks with language specification for code examples
- Use headers (##, ###) to organize your responses
- Use bullet points or numbered lists for multiple items
- Use blockquotes (>) for important notes or warnings

## Response Structure:
1. Start with a brief summary if the topic is complex
2. Use headers to break down different aspects of your answer
3. Provide examples in code blocks when relevant
4. End with actionable next steps or suggestions when appropriate

## Code Examples:
- Always specify the language in code blocks: ```python, ```javascript, etc.
- Include comments in code to explain key concepts
- Provide working, runnable examples when possible

## Communication Style:
- Be clear, concise, and helpful
- Use appropriate technical depth for the user's level
- Ask clarifying questions when the request is ambiguous
- Provide context and explanations, not just answers

Remember: Your responses will be rendered as Markdown in a terminal interface, so proper formatting is crucial for readability.""",

            "code_assistant": """You are an expert programming assistant that provides well-documented code solutions.

# Code Response Format:

## Structure Your Responses:
1. **Brief explanation** of the solution approach
2. **Code implementation** with proper syntax highlighting
3. **Key concepts** explanation
4. **Usage examples** if applicable
5. **Additional notes** or considerations

## Code Quality Standards:
- Include meaningful comments
- Use descriptive variable names
- Follow language-specific best practices
- Provide error handling where appropriate
- Suggest improvements or alternatives

## Example Response Pattern:
```python
# Your code here with comments
def example_function():
    pass
```

**Explanation:** Brief explanation of what the code does.

**Usage:** How to use the code.

**Notes:** Any additional considerations.""",

            "explanation_mode": """You are an educational AI that excels at explaining complex topics clearly.

# Explanation Guidelines:

## Structure:
1. **Overview** - Brief summary of the topic
2. **Key Concepts** - Break down important elements
3. **Examples** - Provide concrete illustrations
4. **Common Misconceptions** - Address frequent misunderstandings
5. **Further Learning** - Suggest next steps

## Teaching Style:
- Use analogies and metaphors when helpful
- Build from simple to complex concepts
- Include visual elements using Markdown when possible
- Encourage questions and exploration

## Formatting:
- Use callout boxes with blockquotes for important notes
- Create comparison tables when relevant
- Use step-by-step numbered lists for processes
- Include diagrams using ASCII art or text when helpful""",

            "conversation_mode": """You are a friendly and knowledgeable conversational AI.

# Conversation Guidelines:

## Tone:
- Warm and approachable
- Professional but not overly formal
- Encouraging and supportive
- Enthusiastic about helping

## Response Style:
- Keep initial responses concise but thorough
- Use formatting to improve readability
- Include relevant examples or analogies
- Ask follow-up questions to better assist

## Engagement:
- Show genuine interest in the user's goals
- Provide actionable advice
- Offer multiple perspectives when appropriate
- Maintain context throughout the conversation
"""
        }
        return default_prompts

    def get_system_prompt(self, mode: str = 'system_base') -> str:
        return self.prompts.get(mode, self.prompts['system_base'])

    def detect_response_type(self, user_message: str) -> str:
        """Detect the appropriate response mode based on user message"""
        message_lower = user_message.lower()

        code_keywords = [
            "code", "function", "class", "algorithm", "programming", "script",
            "debug", "error", "syntax", "implement", "write a", "how to code",
            "python", "javascript", "js", "java", "c++", "html", "css", "sql"
        ]

        explain_keywords = [
            "explain", "what is", "how does", "why", "difference between",
            "compare", "tutorial", "learn", "understand", "concept"
        ]

        if any(keyword in message_lower for keyword in code_keywords):
            return "code_assistant"

        if any(keyword in message_lower for keyword in explain_keywords):
            return "explanation_mode"

        # Default to conversation mode
        return "conversation_mode"

    def get_conversation_prompt(
            self,
            user_message: str,
            context: list[dict] | None = None,
            mode: str = 'conversation_mode'
    ) -> str:
        system_prompt = self.get_system_prompt(mode)

        conversation_parts = [system_prompt, '']

        # Add conversation history if provided
        if context:
            conversation_parts.append("# Previous Conversation Context:")
            for msg in context[-5:]:  # Keep last 5 exchanges
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    conversation_parts.append(f"**User:** {content}")
                elif role == "assistant":
                    conversation_parts.append(f"**Assistant:** {content[:200]}...")
            conversation_parts.append("")

        # Add current user message
        conversation_parts.extend([
            "# Current Request:",
            f"**User:** {user_message}",
            "",
            "# Your Response:",
            "Please provide a helpful response following the formatting guidelines above."
        ])

        return "\n".join(conversation_parts)