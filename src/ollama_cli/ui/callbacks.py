import logging
from abc import ABC, abstractmethod
from enum import Enum

from textual.app import App


class ChatEvent(Enum):
    START_PROCESSING = "start_processing"
    THINKING = "thinking"
    PROCESSING_COMPLETE = "processing_complete"
    ERROR = "error"
    STREAM_CHUNK = "stream_chunk"
    STREAM_START = "stream_start"
    STREAM_END = "stream_end"

class ChatCallback(ABC):
    """Abstract base class for chat callbacks."""

    @abstractmethod
    def on_event(self, event: ChatEvent, message: str) -> None:
        """Handle chat events."""
        pass

class FileLogCallback(ChatCallback):
    """Callback that logs events to a file."""

    def __init__(self, log_file: str = "events.log") -> None:
        self.logger = logging.getLogger("ChatEvents")
        self.logger.setLevel(logging.INFO)

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(file_handler)

    def on_event(self, event: ChatEvent, message: str) -> None:
        self.logger.info(f"Event: {event.value} - Message: {message}")

class TuiCallback(ChatCallback):
    """Callback that updates the TUI interface."""

    def __init__(self, app: App, message_container, create_message_func) -> None:
        self.app = app
        self.message_container = message_container
        self.create_message = create_message_func
        self.current_bot_message = None  # Track current streaming message
        self.current_content = ""  # Track streaming content separately

    def on_event(self, event: ChatEvent, message: str) -> None:
        def update_ui() -> None:
            if event == ChatEvent.START_PROCESSING:
                processing_msg = self.create_message("System", "🤔 Processing your message...", "system")
                self.message_container.mount(processing_msg)
            elif event == ChatEvent.THINKING:
                thinking_msg = self.create_message("Bot", f"💭 {message}", "typing")
                self.message_container.mount(thinking_msg)
            elif event == ChatEvent.ERROR:
                error_msg = self.create_message("Error", f"❌ {message}", "error")
                self.message_container.mount(error_msg)
            elif event == ChatEvent.PROCESSING_COMPLETE:
                complete_msg = self.create_message("System", "✅ Response complete", "system")
                self.message_container.mount(complete_msg)
            elif event == ChatEvent.STREAM_START:
                # Create a new bot message for streaming
                self.current_content = ""  # Reset content
                self.current_bot_message = self.create_message("Bot", "", "bot")
                self.message_container.mount(self.current_bot_message)
            elif event == ChatEvent.STREAM_CHUNK:
                # Update the current bot message with new content
                if self.current_bot_message:
                    # Safely append the new chunk to our content
                    self.current_content += message

                    # Update the content widget directly
                    if hasattr(self.current_bot_message, 'content_widget'):
                        # For markdown content, recreate the widget
                        if hasattr(self.current_bot_message.content_widget, 'update'):
                            try:
                                from ollama_cli.ui.markdown_parser import (
                                    preprocess_markdown,
                                )
                                processed_content = preprocess_markdown(self.current_content)
                                self.current_bot_message.content_widget.update(processed_content)
                            except Exception:
                                # Fallback to plain text update
                                from rich.text import Text
                                content_text = Text(self.current_content)
                                if hasattr(self.current_bot_message.content_widget, 'renderable'):
                                    self.current_bot_message.content_widget.renderable = content_text
            elif event == ChatEvent.STREAM_END:
                # Mark streaming as complete
                self.current_bot_message = None
                self.current_content = ""

            # Ensure the message container scrolls to show new messages
            self.message_container.scroll_end(animate=False)
            # Force a refresh of the screen
            self.message_container.refresh()

        # Call the UI update from the main thread
        """
        This pattern is essential because:
        - Bot processing happens in background threads
        - UI updates must be thread-safe
        - Prevents race conditions and UI corruption
        - Maintains responsiveness of the application

        The call_from_thread method essentially queues the UI update to be executed safely on the main thread, where all UI operations should occur.

        Key Reasons:
        - Thread Confinement: Most GUI frameworks (including Textual) are not thread-safe
        - Single Thread Model: UI operations must happen on the main thread
        - Race Conditions: Direct updates from background threads can corrupt UI state
        """
        self.app.call_from_thread(update_ui)
