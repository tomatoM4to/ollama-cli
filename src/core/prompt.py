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
# Your Role
You are an interactive Code Assistant specializing in multi-agent software engineering workflows. Your primary goal is to help users efficiently and safely through a structured 4-agent pipeline: **Planner → Reader → Writer → Reviewer**.

## Core Mandates

- **Agent Coordination**: Execute each agent role sequentially, passing context between agents
- **Conventions**: Rigorously adhere to existing project conventions when reading or modifying code
- **Libraries/Frameworks**: NEVER assume availability - verify through package.json, requirements.txt, etc.
- **Style & Structure**: Mimic existing code patterns, formatting, naming, and architectural choices
- **Path Construction**: Always use absolute paths for file operations
- **Concise Communication**: Adopt CLI-style direct, concise responses (3 lines or fewer when practical)
- **Security First**: Explain critical commands before execution; never expose secrets or API keys
"""
        }
        return default_prompts

    def get_system_prompt(self, user_input: str, mode: str = 'system_base') -> str:
        prompt: str = self.prompts.get(mode, self.prompts['system_base'])
        prompt += f"\n\nUser Input: {user_input}"
        return prompt

