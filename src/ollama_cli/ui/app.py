"""
A Text User Interface (TUI) chat application built with the Textual framework.
This module implements a chat interface that allows users to interact with a chatbot
in a terminal-based environment. It features real-time message display, background
processing, and event logging.

Key components:
- ChatMessage: Custom widget for displaying formatted chat messages
- ChatInterface: Main application class handling the UI and bot interactions
- Background processing: Asynchronous message handling to keep UI responsive

Original code by oneryalcin - https://github.com/oneryalcin/blog_textual_observer
Modified by Me
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Header, Input, Label, Markdown
from textual.worker import Worker, WorkerState

from ollama_cli.ui.bot import OllamaBot
from ollama_cli.ui.callbacks import FileLogCallback, TuiCallback
from ollama_cli.ui.markdown_parser import create_markdown_widget, preprocess_markdown


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

    def __init__(self, sender: str, message: str, message_type: str = "bot", use_markdown: bool | None = None) -> None:
        super().__init__()

        # Determine if we should use markdown rendering
        if use_markdown is None:
            # Use markdown for bot responses by default, plain text for others
            use_markdown = (sender == "Bot" and message_type not in ["typing"])

        # Format timestamp with better styling
        current_time = datetime.now().strftime("%H:%M:%S")

        # Create header with sender and timestamp
        header_text = Text()

        # Add sender name with appropriate styling
        if sender == "You":
            header_text.append("👤 ", style="bold cyan")
            header_text.append(sender, style="bold bright_white")
        elif sender == "Bot":
            header_text.append("🤖 ", style="bold bright_cyan")
            header_text.append(sender, style="bold bright_cyan")
        elif sender == "System":
            header_text.append("ℹ️  ", style="bold green")
            header_text.append(sender, style="bold green")
        elif sender == "Error":
            header_text.append("❌ ", style="bold red")
            header_text.append(sender, style="bold red")
        else:
            header_text.append(sender, style="bold")

        # Add timestamp with subtle styling
        header_text.append(f" • {current_time}", style="dim italic")

        # Create header label
        self.header_label = Label(header_text)

        # Create content widget based on message type and markdown preference
        if message_type == "typing":
            content_text = Text()
            content_text.append("💭 ", style="dim")
            content_text.append(message, style="italic dim")
            self.content_widget = Label(content_text)
        elif use_markdown:
            # Use markdown widget for bot responses
            try:
                processed_message = preprocess_markdown(message)
                self.content_widget = Markdown(processed_message)
            except Exception:
                # Fallback to plain text if markdown parsing fails
                self.content_widget = Label(message)
        else:
            # Use plain text for user messages and simple responses
            self.content_widget = Label(message)

        # Add CSS classes for styling
        if sender == "You":
            self.add_class("user-message")
        elif sender == "Bot":
            self.add_class("bot-message")
        elif sender == "System":
            self.add_class("welcome-message")
        elif sender == "Error":
            self.add_class("error-message")

        if message_type == "typing":
            self.add_class("typing-indicator")

    def compose(self) -> ComposeResult:
        """Compose the message widget with header and content."""
        yield self.header_label
        yield self.content_widget

class ChatInterface(App):
    """
    Main TUI application class implementing the chat interface.

    Features:
    - Real-time message display
    - Background message processing
    - Keyboard shortcuts
    - Event logging
    - Scrollable message history

    The interface is styled using CSS defined in static/styles.css
    """

    # Path to CSS file for styling the interface
    CSS_PATH = Path(__file__).parent / "styles.css"

    # Define keyboard shortcuts
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    def __init__(self, model: str) -> None:
        """Initialize the chat interface with an OllamaBot instance."""
        super().__init__()
        # Use OllamaBot instead of SimpleBot for streaming responses
        self.bot = OllamaBot(model=model)
        # Fallback to SimpleBot if Ollama is not available
        # self.bot = SimpleBot()

    def on_mount(self) -> None:
        """
        Set up callbacks after the app is mounted.

        Initializes:
        1. TUI callback for updating the interface
        2. File logging callback for event tracking


        Timing:
        - on_mount is called after all widgets are created and mounted
        - It's safe to query and reference widgets here
        - Perfect place for post-initialization setup

        Widget Access:
        - query_one("#message-container") works here because widgets exist
        - Would fail if called in __init__ (widgets don't exist yet)

        Lifecycle Order:
        - Textual App Lifecycle
            1. __init__()           # Initial setup
            2. compose()           # Create widgets
            3. on_mount()         # Post-mount setup
            4. on_ready()        # App ready for user interaction

        Best Practices:
        - Use __init__ for basic initialization
        - Use compose for widget creation
        - Use on_mount for:
            - Widget queries
            - Event handlers setup
            - Callback registration
            - Post-initialization configuration

        This method is crucial for proper initialization timing in Textual applications, ensuring all components are properly set up after the UI is ready.
        """
        message_container = self.query_one("#message-container")

        # Add TUI callback to handle bot events and update the interface
        tui_callback = TuiCallback(self, message_container, ChatMessage)
        self.bot.add_callback(tui_callback)

        # Set up file logging for events
        log_path = Path(__file__).parent / "events.log"
        file_callback = FileLogCallback(str(log_path))
        self.bot.add_callback(file_callback)

    def compose(self) -> ComposeResult:
        """
        Create and arrange the UI widgets with enhanced styling.

        Layout:
        - Styled header at the top
        - Enhanced chat container with:
            - Scrollable message history with custom styling
            - Modern input field at the bottom
        """
        yield Header()
        with Container(id="chat-container"):
            with ScrollableContainer(id="message-container"):
                # Display enhanced welcome message
                welcome_msg = "🎉 Welcome to the AI Chat Interface! 🎉\n\n💬 I'm here to help you with any questions or tasks.\n✨ Type your message below and press Enter to start chatting!"
                yield ChatMessage("System", welcome_msg, "system")
            with Container(id="input-container"):
                yield Input(
                    placeholder="💭 Type your message here and press Enter to chat...",
                    id="user-input"
                )


    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes with enhanced messaging.

        Args:
            event (Worker.StateChanged): The worker state change event

        Notes:
        1. on_worker_state_changed is a Textual event handler (main thread)
        2. Direct UI updates are safe in the main thread
        3. Worker state changes provide a reliable way to handle completion

        This pattern follows Textual's thread safety model:
        - Event handlers → Direct UI updates
        - Background operations → Use call_from_thread
        - Worker state changes → Already in main thread

        """
        message_container = self.query_one("#message-container")

        if event.worker.name in ["bot_processing", "bot_streaming"]:
            if event.worker.state == WorkerState.SUCCESS:
                # For streaming, we don't need to add the final response since it's already been streamed
                # For non-streaming, we still add the complete response
                if event.worker.name == "bot_processing":
                    result: Any = event.worker.result
                    message_container.mount(ChatMessage("Bot", result, "bot"))
                    message_container.scroll_end(animate=False)
            elif event.worker.state == WorkerState.ERROR:
                error_message = "⚠️ Oops! Something went wrong while processing your message.\n🔄 Please try again or rephrase your question."
                message_container.mount(ChatMessage("Error", error_message, "error"))
                message_container.scroll_end(animate=False)


    def process_message_in_background(self, user_input: str) -> Worker:
        """Process user messages in a background thread to keep UI responsive.

        Args:
            user_input (str): The message from the user

        Returns:
            Worker: A background worker processing the message
        """
        message_container = self.query_one("#message-container")
        message_container.mount(ChatMessage("You", user_input, "user"))
        message_container.scroll_end(animate=False)

        # Create worker for background processing
        worker = self.run_worker(
            lambda: self.bot.process_message(user_input),
            name="bot_processing",  # Important for identifying our worker
            thread=True
        )
        return worker

    def process_message_stream_in_background(self, user_input: str) -> Worker:
        """Process user messages with streaming in a background thread.

        Args:
            user_input (str): The message from the user

        Returns:
            Worker: A background worker processing the streaming message
        """
        message_container = self.query_one("#message-container")
        message_container.mount(ChatMessage("You", user_input, "user"))

        # Add typing indicator
        typing_indicator = ChatMessage("Bot", "Thinking...", "typing")
        message_container.mount(typing_indicator)
        message_container.scroll_end(animate=False)

        def stream_processing():
            """Handle streaming message processing with enhanced error handling."""
            try:
                # Notify start of streaming
                self.bot.notify_callbacks(ChatEvent.STREAM_START, "")

                # Process streaming response
                response_parts = []
                for chunk in self.bot.process_message_stream(user_input):
                    response_parts.append(chunk)
                    # Notify each chunk
                    self.bot.notify_callbacks(ChatEvent.STREAM_CHUNK, chunk)

                # Remove typing indicator and notify end of streaming
                message_container.remove_children([typing_indicator])
                self.bot.notify_callbacks(ChatEvent.STREAM_END, "")
                return ''.join(response_parts)

            except Exception as e:
                # Remove typing indicator on error
                message_container.remove_children([typing_indicator])
                error_message = f"🔌 Connection issue: {str(e)}\n💡 Please check your connection and try again."
                self.bot.notify_callbacks(ChatEvent.ERROR, error_message)
                return "⚠️ I encountered a technical difficulty. Please try your request again."

        # Import ChatEvent here to avoid circular imports
        from ollama_cli.ui.callbacks import ChatEvent

        # Create worker for background streaming processing
        worker = self.run_worker(
            stream_processing,
            name="bot_streaming",
            thread=True
        )
        return worker


    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle user input submission when Enter is pressed.

        Args:
            event (Input.Submitted): The input submission event
        """
        user_input = event.value
        if not user_input.strip():
            return

        # Clear input field after submission
        input_widget = self.query_one("#user-input", Input)
        input_widget.value = ""

        # Process message with streaming asynchronously
        self.process_message_stream_in_background(user_input)
