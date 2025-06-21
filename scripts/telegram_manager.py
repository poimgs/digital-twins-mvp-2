"""
Telegram Bot Management Utility

This script helps manage Telegram bot tokens and provides utilities for running
Telegram bots for different digital twins.
"""

import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from core.supabase_client import supabase_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBotManager:
    """Manager for Telegram bot operations."""
    
    def __init__(self):
        """Initialize the Telegram bot manager."""
        self.bot_tokens: Dict[str, str] = {}
        self.running_processes: Dict[str, subprocess.Popen] = {}
    
    def list_available_bots(self):
        """List all available bots that can be used with Telegram."""
        try:
            bots = supabase_client.get_bots(active_only=True)
            
            print("\n" + "="*60)
            print("🤖 AVAILABLE DIGITAL TWINS FOR TELEGRAM")
            print("="*60)
            
            if not bots:
                print("No active bots found.")
                print("Use scripts/bot_manager.py to create bots first.")
                return []
            
            for i, bot in enumerate(bots, 1):
                print(f"\n{i}. {bot.name}")
                print(f"   ID: {bot.id}")
                print(f"   Description: {bot.description or 'No description'}")
                print(f"   Welcome: {bot.welcome_message[:100]}...")
                print("-" * 40)
            
            return bots
            
        except Exception as e:
            logger.error(f"Error listing bots: {e}")
            print(f"❌ Error listing bots: {e}")
            return []
    
    def start_telegram_bot(self, bot_id: str, telegram_token: str):
        """Start a Telegram bot for a specific digital twin."""
        try:
            # Validate bot exists
            bot = supabase_client.get_bot_by_id(bot_id)
            if not bot:
                print(f"❌ Bot with ID {bot_id} not found.")
                return False
            
            if not bot.is_active:
                print(f"❌ Bot {bot.name} is not active.")
                return False
            
            # Check if bot is already running
            if bot_id in self.running_processes:
                print(f"⚠️  Bot {bot.name} is already running.")
                return False
            
            print(f"🚀 Starting Telegram bot for: {bot.name}")
            print(f"Bot ID: {bot_id}")
            print(f"Token: {telegram_token[:10]}...")
            
            # Start the Telegram bot process
            telegram_script = project_root / "telegram_app" / "telegram_bot.py"
            cmd = [sys.executable, str(telegram_script), bot_id, telegram_token]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.running_processes[bot_id] = process
            self.bot_tokens[bot_id] = telegram_token
            
            print(f"✅ Telegram bot started successfully!")
            print(f"Process ID: {process.pid}")
            print(f"To stop the bot, use the stop command or press Ctrl+C")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
            print(f"❌ Error starting Telegram bot: {e}")
            return False
    
    def stop_telegram_bot(self, bot_id: str):
        """Stop a running Telegram bot."""
        try:
            if bot_id not in self.running_processes:
                print(f"❌ No running bot found with ID: {bot_id}")
                return False
            
            process = self.running_processes[bot_id]
            process.terminate()
            
            # Wait for process to terminate
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            del self.running_processes[bot_id]
            if bot_id in self.bot_tokens:
                del self.bot_tokens[bot_id]
            
            print(f"✅ Telegram bot stopped successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
            print(f"❌ Error stopping Telegram bot: {e}")
            return False
    
    def list_running_bots(self):
        """List currently running Telegram bots."""
        print("\n" + "="*60)
        print("🤖 RUNNING TELEGRAM BOTS")
        print("="*60)
        
        if not self.running_processes:
            print("No Telegram bots are currently running.")
            return
        
        for bot_id, process in self.running_processes.items():
            try:
                bot = supabase_client.get_bot_by_id(bot_id)
                bot_name = bot.name if bot else "Unknown"
                
                # Check if process is still running
                if process.poll() is None:
                    status = "✅ Running"
                else:
                    status = "❌ Stopped"
                
                print(f"\nBot: {bot_name}")
                print(f"ID: {bot_id}")
                print(f"PID: {process.pid}")
                print(f"Status: {status}")
                print(f"Token: {self.bot_tokens.get(bot_id, 'Unknown')[:10]}...")
                print("-" * 40)
                
            except Exception as e:
                print(f"Error getting info for bot {bot_id}: {e}")
    
    def interactive_mode(self):
        """Run interactive mode for managing Telegram bots."""
        print("\n" + "="*60)
        print("🤖 TELEGRAM BOT MANAGER")
        print("="*60)
        print("1. List available bots")
        print("2. Start Telegram bot")
        print("3. Stop Telegram bot")
        print("4. List running bots")
        print("5. Exit")
        print("="*60)
        
        while True:
            try:
                choice = input("\nSelect an option (1-5): ").strip()
                
                if choice == "1":
                    self.list_available_bots()
                
                elif choice == "2":
                    bots = self.list_available_bots()
                    if not bots:
                        continue
                    
                    try:
                        bot_choice = input("\nSelect bot number: ").strip()
                        bot_index = int(bot_choice) - 1
                        
                        if 0 <= bot_index < len(bots):
                            selected_bot = bots[bot_index]
                            telegram_token = input("Enter Telegram bot token: ").strip()
                            
                            if telegram_token:
                                self.start_telegram_bot(str(selected_bot.id), telegram_token)
                            else:
                                print("❌ Token cannot be empty.")
                        else:
                            print("❌ Invalid bot selection.")
                    except ValueError:
                        print("❌ Please enter a valid number.")
                
                elif choice == "3":
                    self.list_running_bots()
                    if self.running_processes:
                        bot_id = input("\nEnter bot ID to stop: ").strip()
                        if bot_id:
                            self.stop_telegram_bot(bot_id)
                
                elif choice == "4":
                    self.list_running_bots()
                
                elif choice == "5":
                    # Stop all running bots before exiting
                    for bot_id in list(self.running_processes.keys()):
                        self.stop_telegram_bot(bot_id)
                    print("\n👋 Goodbye!")
                    break
                
                else:
                    print("❌ Invalid choice. Please select 1-5.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                # Stop all running bots
                for bot_id in list(self.running_processes.keys()):
                    self.stop_telegram_bot(bot_id)
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main function for Telegram bot management."""
    try:
        # Validate configuration
        settings.validate()
        
        manager = TelegramBotManager()
        
        # Check command line arguments
        if len(sys.argv) == 4 and sys.argv[1] == "start":
            # Direct start mode: python telegram_manager.py start <bot_id> <token>
            bot_id = sys.argv[2]
            telegram_token = sys.argv[3]
            manager.start_telegram_bot(bot_id, telegram_token)
        else:
            # Interactive mode
            manager.interactive_mode()
        
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    except Exception as e:
        logger.error(f"Error in Telegram bot manager: {e}")
        print(f"\n❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
