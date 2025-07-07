"""
Tests for Telegram bot functionality, specifically the pinning feature.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram_app.telegram_bot import TelegramDigitalTwin
from core.models import Bot


class TestTelegramBotPinning:
    """Test class for Telegram bot pinning functionality."""

    @pytest.fixture
    def mock_bot_info(self):
        """Create a mock bot info object."""
        from uuid import UUID
        return Bot(
            id=UUID("12345678-1234-5678-9012-123456789012"),
            name="Test Bot",
            welcome_message="Welcome to Test Bot!",
            call_to_action="Test CTA"
        )

    @pytest.fixture
    def mock_telegram_bot(self, mock_bot_info):
        """Create a mock TelegramDigitalTwin instance."""
        with patch('telegram_app.telegram_bot.supabase_client') as mock_supabase:
            mock_supabase.get_bot_by_id.return_value = mock_bot_info
            
            with patch('telegram_app.telegram_bot.ConversationalEngine'):
                bot = TelegramDigitalTwin("test-bot-id", "test-token")
                return bot

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram Update object."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram Context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.pin_chat_message = AsyncMock()
        
        # Mock the return value of send_message to have a message_id
        mock_message = MagicMock()
        mock_message.message_id = 67890
        context.bot.send_message.return_value = mock_message
        
        return context

    @pytest.mark.asyncio
    async def test_start_command_pins_instruction_message(self, mock_telegram_bot, mock_update, mock_context):
        """Test that /start command sends welcome message and pins instruction message."""
        # Act
        await mock_telegram_bot.start_command(mock_update, mock_context)

        # Assert
        # Check that welcome message was sent
        mock_update.message.reply_text.assert_called_once_with("Welcome to Test Bot!")
        
        # Check that instruction message was sent
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=12345,
            text="You can also post your own question to me on the chat"
        )
        
        # Check that message was pinned
        mock_context.bot.pin_chat_message.assert_called_once_with(
            chat_id=12345,
            message_id=67890,
            disable_notification=True
        )

    @pytest.mark.asyncio
    async def test_reset_command_pins_instruction_message(self, mock_telegram_bot, mock_update, mock_context):
        """Test that /reset command sends welcome message and pins instruction message."""
        # Mock the reset_conversation method
        mock_telegram_bot.engine.reset_conversation = MagicMock(return_value=True)
        
        # Act
        await mock_telegram_bot.reset_command(mock_update, mock_context)

        # Assert
        # Check that reset success message was sent
        assert mock_update.message.reply_text.call_count == 2
        mock_update.message.reply_text.assert_any_call("✅ Conversation history has been reset!")
        mock_update.message.reply_text.assert_any_call("Welcome to Test Bot!")
        
        # Check that instruction message was sent
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=12345,
            text="You can also post your own question to me on the chat"
        )
        
        # Check that message was pinned
        mock_context.bot.pin_chat_message.assert_called_once_with(
            chat_id=12345,
            message_id=67890,
            disable_notification=True
        )

    @pytest.mark.asyncio
    async def test_pin_instruction_message_handles_errors_gracefully(self, mock_telegram_bot, mock_update, mock_context):
        """Test that pinning errors are handled gracefully without crashing."""
        # Mock pin_chat_message to raise an exception
        mock_context.bot.pin_chat_message.side_effect = Exception("Pin failed")
        
        # Act - should not raise an exception
        await mock_telegram_bot._send_and_pin_instruction_message(mock_update, mock_context)

        # Assert
        # Check that instruction message was still sent
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=12345,
            text="You can also post your own question to me on the chat"
        )
        
        # Check that pin was attempted
        mock_context.bot.pin_chat_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_pin_instruction_message_without_effective_chat(self, mock_telegram_bot, mock_context):
        """Test that pinning handles missing effective_chat gracefully."""
        # Create update without effective_chat
        update = MagicMock(spec=Update)
        update.effective_chat = None
        
        # Act - should not raise an exception
        await mock_telegram_bot._send_and_pin_instruction_message(update, mock_context)

        # Assert
        # Check that no messages were sent
        mock_context.bot.send_message.assert_not_called()
        mock_context.bot.pin_chat_message.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
