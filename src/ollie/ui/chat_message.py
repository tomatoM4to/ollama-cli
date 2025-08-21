from datetime import datetime
from enum import Enum

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, LoadingIndicator, Markdown


class ChatType(Enum):
    USER = 'user'
    SYSTEM = 'system'
    AI = 'ai'
    ERROR = 'error'

class ChatMessage(Vertical):
    """
    A custom widget for displaying chat messages with enhanced formatting and styling.

    Each message shows:
    - The sender's name with appropriate styling
    - A formatted timestamp
    - The message content with proper formatting (supports markdown)
    - Different visual styles based on sender type

    Args:
        sender (str): Name of the message sender ('You', 'Bot', 'System', 'Error')
        message (str): Content of the message
        message_type (str): Type of message for styling ('user', 'bot', 'system', 'error', 'typing')
        use_markdown (bool): Whether to render message as markdown (default: False for non-bot messages)
    """

    def __init__(
            self,
            sender: ChatType,
            message: str,
            model: str,
            message_type: str ='bot',
            use_markdown: bool = False,
        ) -> None:
        super().__init__()

        # Determine if we should use markdown rendering
        if not use_markdown:
            # Use markdown for bot responses by default, plain text for others
            use_markdown = (sender == ChatType.AI and message_type not in ["typing"])

        # Format timestamp with better styling
        current_time = datetime.now().strftime("%H:%M:%S")

        # Create header with sender and timestamp
        header_text = Text()

        # Add sender name with appropriate styling
        if sender == ChatType.USER:
            header_text.append("👤 ", style="bold cyan")
            header_text.append('User', style="bold bright_white")
        elif sender == ChatType.AI:
            header_text.append("🤖 ", style="bold bright_cyan")
            header_text.append(model, style="bold bright_cyan")
        elif sender == ChatType.SYSTEM:
            header_text.append("ℹ️  ", style="bold green")
            header_text.append("Ollama CLI", style="bold green")
        elif sender == ChatType.ERROR:
            header_text.append("❌ ", style="bold red")
            header_text.append('Error', style="bold red")
        else:
            header_text.append(sender, style="bold")

        # Add timestamp with subtle styling
        header_text.append(f" • {current_time}", style="dim italic")

        # Create header label
        self.header_label = Label(header_text)

        # Create content widget based on message type and markdown preference
        if message_type == "typing":
            # Use LoadingIndicator for typing animation
            self.content_widget = LoadingIndicator()
            self.content_widget.add_class("typing-loading")
        elif use_markdown:
            # Use markdown widget for bot responses
            try:
                # processed_message = preprocess_markdown(message)
                self.content_widget = Markdown(message)
            except Exception:
                # Fallback to plain text if markdown parsing fails
                self.content_widget = Label(message)
        else:
            # Use plain text for user messages and simple responses
            self.content_widget = Label(message)

        # Add CSS classes for styling
        if sender == ChatType.USER:
            self.add_class("user-message")
        elif sender == ChatType.AI:
            self.add_class("bot-message")
        elif sender == ChatType.SYSTEM:
            self.add_class("welcome-message")
        elif sender == ChatType.ERROR:
            self.add_class("error-message")

        if message_type == "typing":
            self.add_class("typing-indicator")

    def compose(self) -> ComposeResult:
        """Compose the message widget with header and content."""
        yield self.header_label
        yield self.content_widget
