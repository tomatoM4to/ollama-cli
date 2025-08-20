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

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.widgets import Button, Header, Input
from textual.worker import Worker, WorkerState

from core.config import ChatMode, Config
from ollama_cli.ui.bot import OllamaBot
from ollama_cli.ui.callbacks import ChatEvent, TuiCallback
from ollama_cli.ui.chat_message import ChatMessage, ChatType


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

    def __init__(self, config: Config) -> None:
        """Initialize the chat interface with an OllamaBot instance."""
        super().__init__()
        # Use OllamaBot instead of SimpleBot for streaming responses
        self.bot = OllamaBot(config=config)
        self.config = config

        # Variables for continuous processing
        self.current_user_input = ""
        self.current_iteration = 0
        self.max_iterations = 5
        self.continue_message_widget: ChatMessage | None = None

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
        tui_callback = TuiCallback(self, message_container, config=self.config)
        self.bot.add_callback(tui_callback)

        # Set up file logging for events
        # log_path = Path(__file__).parent / "events.log"
        # file_callback = FileLogCallback(str(log_path))
        # self.bot.add_callback(file_callback)

    def compose(self) -> ComposeResult:
        """
        Create and arrange the UI widgets with enhanced styling.

        Layout:
        - Styled header at the top
        - Enhanced chat container with:
            - Scrollable message history with custom styling
            - Modern input field at the bottom
            - Small control buttons below input
        """
        yield Header()
        with Container(id="chat-container"):
            with ScrollableContainer(id="message-container"):
                # Display enhanced welcome message
                welcome_msg = "Welcome to the AI Chat Interface!\n\nI'm here to help you with any questions or tasks.\nType your message below and press Enter to start chatting!"
                yield ChatMessage(
                    sender=ChatType.SYSTEM,
                    message=welcome_msg,
                    model=self.config.get_model(),
                    message_type='system'
                )
                # yield ChatMessage("Ollama CLI", welcome_msg, "system", self.config.get_model())
        with Container(id="input-container"):
            yield Input(
                placeholder="Type your message here and press Enter to chat...",
                id="user-input"
            )
            with Container(id="button-container"):
                yield Button(f"Mode: {self.config.get_chat_mode().value.upper()}", id="mode-button", variant="primary")
                yield Button(f"Stream: {'ON' if self.config.get_stream() else 'OFF'}", id="stream-button", variant="default")
                yield Button("Clear Chat", id="clear-button", variant="error")


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
                if event.worker.name == "bot_processing":
                    # Get result from worker
                    worker_result = event.worker.result

                    if isinstance(worker_result, tuple) and len(worker_result) == 2:
                        result, thinking_indicator = worker_result

                        # Remove the thinking indicator
                        try:
                            message_container.remove_children([thinking_indicator])
                        except:
                            # If indicator removal fails, find and remove typing indicators
                            for child in message_container.children:
                                if hasattr(child, 'classes') and 'typing-indicator' in child.classes:
                                    message_container.remove_children([child])
                                    break

                        # Add the actual bot response
                        message_container.mount(ChatMessage(
                            sender=ChatType.AI,
                            message=result,
                            model=self.config.get_model(),
                        ))
                        # message_container.mount(ChatMessage("Bot", result, "bot"))
                    else:
                        # Fallback: just add the result as is
                        message_container.mount(ChatMessage(
                            sender=ChatType.AI,
                            message=str(worker_result),
                            model=self.config.get_model()
                        ))
                        # message_container.mount(ChatMessage("Bot", str(worker_result), "bot"))

                    message_container.scroll_end(animate=False)

                    # Check if we should continue processing
                    self.current_iteration += 1
                    if self.current_iteration < self.max_iterations:
                        # Show continue message
                        self.show_continue_message()
                    else:
                        # Reset for next user input
                        self.reset_continuous_processing()

                elif event.worker.name == "bot_streaming":
                    # For streaming, responses are already displayed via callbacks
                    # Just ensure we scroll to the end
                    message_container.scroll_end(animate=False)

                    # Check if we should continue processing (same as non-streaming)
                    self.current_iteration += 1
                    if self.current_iteration < self.max_iterations:
                        # Show continue message
                        self.show_continue_message()
                    else:
                        # Reset for next user input
                        self.reset_continuous_processing()
            elif event.worker.state == WorkerState.ERROR:
                # Try to remove thinking indicator if it exists
                try:
                    # Find and remove any typing indicators
                    for child in message_container.children:
                        if hasattr(child, 'classes') and 'typing-indicator' in child.classes:
                            message_container.remove_children([child])
                            break
                except:
                    pass

                error_message = "⚠️ Oops! Something went wrong while processing your message.\n🔄 Please try again or rephrase your question."
                message_container.mount(ChatMessage(
                    sender=ChatType.ERROR,
                    message=error_message,
                    model=self.config.get_model()
                ))
                # message_container.mount(ChatMessage("Error", error_message, "error"))
                message_container.scroll_end(animate=False)


    def process_message_in_background(self, user_input: str, show_user_message: bool = True) -> Worker:
        """Process user messages in a background thread to keep UI responsive.

        Args:
            user_input (str): The message from the user
            show_user_message (bool): Whether to display the user message

        Returns:
            Worker: A background worker processing the message
        """
        message_container = self.query_one("#message-container")

        # Only show user message if requested
        if show_user_message:
            message_container.mount(ChatMessage(
                sender=ChatType.USER,
                message=user_input,
                model=self.config.get_model()
            ))
            # message_container.mount(ChatMessage("You", user_input, "user"))

        # Add thinking indicator immediately
        thinking_indicator = ChatMessage(
            sender=ChatType.AI,
            message="AI 연산중...",
            model=self.config.get_model(),
            message_type='typing'
        )
        # thinking_indicator = ChatMessage("Bot", "AI 연산중...", "typing")
        message_container.mount(thinking_indicator)
        message_container.scroll_end(animate=False)

        def process_with_indicator():
            """Process message and return both result and thinking indicator for cleanup."""
            try:
                result = self.bot.process_message(user_input)
                return result, thinking_indicator
            except Exception as e:
                return f"⚠️ 오류가 발생했습니다: {str(e)}", thinking_indicator

        # Create worker for background processing
        worker = self.run_worker(
            process_with_indicator,
            name="bot_processing",  # Important for identifying our worker
            thread=True
        )
        return worker

    def process_message_stream_in_background(self, user_input: str, show_user_message: bool = True) -> Worker:
        """Process user messages with streaming in a background thread.

        Args:
            user_input (str): The message from the user
            show_user_message (bool): Whether to display the user message

        Returns:
            Worker: A background worker processing the streaming message
        """
        message_container = self.query_one("#message-container")

        # Only show user message if requested
        if show_user_message:
            # message_container.mount(ChatMessage("You", user_input, "user"))
            message_container.mount(ChatMessage(
                sender=ChatType.USER,
                message=user_input,
                model=self.config.get_model()
            ))
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

                # Notify end of streaming
                self.bot.notify_callbacks(ChatEvent.STREAM_END, "")
                return ''.join(response_parts)

            except Exception as e:
                error_message = f"🔌 Connection issue: {str(e)}\n💡 Please check your connection and try again."
                self.bot.notify_callbacks(ChatEvent.ERROR, error_message)
                return "⚠️ I encountered a technical difficulty. Please try your request again."

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

        # Check if we're in continue mode
        if self.continue_message_widget is not None:
            # Handle continue response
            should_continue = self.handle_continue_response(user_input)
            if should_continue:
                # Continue with the same input but don't show user message again
                if self.config.get_stream():
                    self.process_message_stream_in_background(self.current_user_input, show_user_message=False)
                else:
                    self.process_message_in_background(self.current_user_input, show_user_message=False)
            return

        # New user input - start the continuous processing
        self.current_user_input = user_input
        self.current_iteration = 0

        if self.config.get_stream():
            self.process_message_stream_in_background(user_input)
            return

        self.process_message_in_background(user_input)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "mode-button":
            # Toggle between ASK and AGENT mode
            current_mode = self.config.get_chat_mode()
            new_mode = ChatMode.AGENT if current_mode == ChatMode.ASK else ChatMode.ASK
            self.config.set_chat_mode(new_mode.value)

            # Update button text
            event.button.label = f"Mode: {new_mode.value.upper()}"

        elif event.button.id == "stream-button":
            # Toggle stream mode
            current_stream = self.config.get_stream()
            self.config.set_stream(not current_stream)

            # Update button text
            event.button.label = f"Stream: {'ON' if not current_stream else 'OFF'}"

        elif event.button.id == "clear-button":
            # Clear chat messages
            message_container = self.query_one("#message-container")
            message_container.remove_children()

            # Reset continuous processing state
            self.reset_continuous_processing()

            # Add welcome message back
            welcome_msg = "Welcome to the AI Chat Interface!\n\nI'm here to help you with any questions or tasks.\nType your message below and press Enter to start chatting!"
            # message_container.mount(ChatMessage("Ollama CLI", welcome_msg, "system"))
            message_container.mount(ChatMessage(
                sender=ChatType.SYSTEM,
                message=welcome_msg,
                model=self.config.get_model()
            ))

    def show_continue_message(self) -> None:
        """Show a continue message and wait for user response."""
        message_container = self.query_one("#message-container")

        continue_msg = f"계속하시겠습니까? ({self.current_iteration}/{self.max_iterations}) [Y/n]"
        self.continue_message_widget = ChatMessage(
            sender=ChatType.SYSTEM,
            message=continue_msg,
            model=self.config.get_model(),
            message_type='system'
        )
        message_container.mount(self.continue_message_widget)
        message_container.scroll_end(animate=False)

        # Set focus to input for user response
        input_widget = self.query_one("#user-input", Input)
        input_widget.focus()

    def reset_continuous_processing(self) -> None:
        """Reset the continuous processing state."""
        self.current_user_input = ""
        self.current_iteration = 0
        self.continue_message_widget = None

    def handle_continue_response(self, response: str) -> bool:
        """Handle user response to continue message. Returns True if should continue."""
        response = response.strip().lower()

        # Remove the continue message
        if self.continue_message_widget:
            message_container = self.query_one("#message-container")
            try:
                message_container.remove_children([self.continue_message_widget])
            except:
                pass
            self.continue_message_widget = None

        # Check if user wants to continue
        if response in ['y', 'yes', '예', '네', ''] or response == '':  # Default to yes
            return True
        else:
            self.reset_continuous_processing()
            return False
