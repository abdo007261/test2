import asyncio
import json
import time
import threading
from typing import Dict, Any, Optional
import logging
from bot_communication import bot_comm, get_signal_command
from database import Database

class TradingBotReceiver:
    """Receiver for trading bot to process signals from signal bot"""
    
    def __init__(self, trading_bot_client, check_interval: float = 0.1):
        self.trading_bot_client = trading_bot_client
        self.check_interval = check_interval
        self.running = False
        self.processed_signals = set()
        self.startup_timestamp = None  # Will be set when monitoring starts
        
    async def start_monitoring(self):
        """Start monitoring for signals from signal bot"""
        self.running = True
        self.startup_timestamp = time.time()  # Set startup timestamp
        print(f"[TRADING BOT] Signal monitoring started at {self.startup_timestamp}")
        
        # Clear old signals when starting to prevent processing old signals
        await self.clear_old_signals_on_startup()
        
        while self.running:
            try:
                # Get pending signals
                pending_signals = bot_comm.get_pending_signals()
                
                for signal in pending_signals:
                    signal_id = f"{signal['timestamp']}_{signal['group_id']}_{signal['game']}_{signal['signal']}"
                    
                    # Skip if already processed
                    if signal_id in self.processed_signals:
                        continue
                    
                    # Skip if signal is older than startup timestamp (bending signal)
                    signal_timestamp = signal.get('timestamp', 0)
                    if signal_timestamp < self.startup_timestamp:
                        print(f"[TRADING BOT] Skipping bending signal (old signal): {signal['game']} {signal['signal']} from {signal_timestamp} (bot started at {self.startup_timestamp})")
                        # Mark old signal as processed to avoid checking it again
                        bot_comm.mark_signal_processed(signal['timestamp'])
                        self.processed_signals.add(signal_id)
                        continue
                    
                    # Process the signal (only real-time signals)
                    print(f"[TRADING BOT] Processing real-time signal: {signal['game']} {signal['signal']} from {signal_timestamp}")
                    await self.process_signal(signal)
                    
                    # Mark as processed
                    bot_comm.mark_signal_processed(signal['timestamp'])
                    self.processed_signals.add(signal_id)
                    
                    # Keep processed signals list manageable
                    if len(self.processed_signals) > 1000:
                        self.processed_signals.clear()
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"[TRADING BOT] Error in signal monitoring: {e}")
                await asyncio.sleep(1)
    
    async def clear_old_signals_on_startup(self):
        """Clear old signals when bot starts to prevent processing bending signals"""
        try:
            print("[TRADING BOT] Clearing ALL old signals on startup to prevent bending signals...")
            
            # Clear all signals from the file to ensure no old signals are processed
            bot_comm.clear_all_signals()
            
            print("[TRADING BOT] All old signals cleared successfully - only real-time signals will be processed")
        except Exception as e:
            print(f"[TRADING BOT] Error clearing old signals: {e}")
    
    async def process_signal(self, signal: Dict[str, Any]):
        """Process a signal from the signal bot"""
        try:
            group_id = signal['group_id']
            game = signal['game']
            signal_text = signal['signal']
            current_stage = signal['current_stage']
            strategy = signal['strategy']
            
            print(f"[TRADING BOT] Processing signal: {game} {signal_text}x{current_stage} for group {group_id}")
            print(f"[TRADING BOT] Signal details: {signal}")
            
            # Convert signal to command format
            command = get_signal_command(game, signal_text, current_stage)
            print(f"[TRADING BOT] Converted command: {command}")
            
            # Send the command to the group as if it was typed by a user
            await self.send_command_to_group(group_id, command, game)
            
        except Exception as e:
            print(f"[TRADING BOT] Error processing signal: {e}")
            import traceback
            print(f"[TRADING BOT] Traceback: {traceback.format_exc()}")
    
    async def send_command_to_group(self, group_id: str, command: str, game: str):
        """Send command to group as if it was typed by a user"""
        try:
            print(f"[TRADING BOT] send_command_to_group: group_id={group_id}, command={command}, game={game}")
            
            # Create a fake message object that simulates a user sending the command
            class FakeMessage:
                def __init__(self, chat_id, text):
                    # Get the actual group name from the database
                    group_name = self.get_group_name_by_id(chat_id)
                    
                    # Create a fake chat object with both id and title
                    self.chat = type('Chat', (), {
                        'id': chat_id,
                        'title': group_name,  # Use actual group name
                        'type': 'group'  # Add chat type
                    })()
                    self.text = text
                    self.from_user = type('User', (), {'id': 123456789})()  # Fake user ID
                
                def get_group_name_by_id(self, chat_id):
                    """Get group name by chat ID from database"""
                    try:
                        # Create database instance and load data
                        db_instance = Database()
                        data = db_instance.data
                        if 'groups' in data:
                            for group_name, group_info in data['groups'].items():
                                if 'description' in group_info:
                                    # Extract chat ID from description like "Chat ID: -1002377721796"
                                    desc = group_info['description']
                                    if 'Chat ID:' in desc:
                                        group_chat_id = desc.split('Chat ID:')[-1].strip()
                                        if group_chat_id == str(chat_id):
                                            return group_name
                        # Fallback to generic name if not found
                        return f"Group {chat_id}"
                    except Exception as e:
                        print(f"[TRADING BOT] Error getting group name: {e}")
                        return f"Group {chat_id}"
            
            fake_message = FakeMessage(int(group_id), command)
            print(f"[TRADING BOT] Created fake message: chat_id={fake_message.chat.id}, title={fake_message.chat.title}, type={fake_message.chat.type}")
            
            # Route to appropriate handler based on game and command format
            if game == "red_green":
                if command.startswith(('/red_green', '/redgreen')):
                    # Full command - call red_green_command
                    await self.handle_red_green_command(fake_message)
                else:
                    # Signal format (Rx1, Gx2) - call process_trading_signal
                    await self.handle_red_green_signal(fake_message)
            elif game == "blocks":
                if command.startswith(('/blocks')):
                    # Full command - call blocks_command
                    await self.handle_blocks_command(fake_message)
                else:
                    # Signal format (Bx1, Sx2) - call process_blocks_signal
                    await self.handle_blocks_signal(fake_message)
            elif game == "dices":
                if command.startswith(('/dices')):
                    # Full command - call dices_command
                    await self.handle_dices_command(fake_message)
                else:
                    # Signal format (Ox1, Ex2) - call process_dices_signal
                    await self.handle_dices_signal(fake_message)
            else:
                print(f"[TRADING BOT] Unknown game type: {game}")
                
        except Exception as e:
            print(f"[TRADING BOT] Error sending command to group: {e}")
    
    async def handle_red_green_signal(self, message):
        """Handle red-green signal (Rx1, Gx2, etc.)"""
        try:
            print(f"[TRADING BOT] Processing red-green signal: {message.text}")
            print(f"[TRADING BOT] Message chat info: id={message.chat.id}, title={getattr(message.chat, 'title', 'NO_TITLE')}, type={getattr(message.chat, 'type', 'NO_TYPE')}")
            
            # Call the actual process_trading_signal from bot.py
            from bot import process_trading_signal
            await process_trading_signal(self.trading_bot_client, message, message.text)
            
        except Exception as e:
            print(f"[TRADING BOT] Error handling red-green signal: {e}")
            import traceback
            print(f"[TRADING BOT] Traceback: {traceback.format_exc()}")
    
    async def handle_blocks_signal(self, message):
        """Handle blocks signal (Bx1, Sx2, etc.)"""
        try:
            print(f"[TRADING BOT] Processing blocks signal: {message.text}")
            print(f"[TRADING BOT] Message chat info: id={message.chat.id}, title={getattr(message.chat, 'title', 'NO_TITLE')}, type={getattr(message.chat, 'type', 'NO_TYPE')}")
            
            # Call the actual process_blocks_signal from bot.py
            from bot import process_blocks_signal
            await process_blocks_signal(self.trading_bot_client, message, message.text)
            
        except Exception as e:
            print(f"[TRADING BOT] Error handling blocks signal: {e}")
            import traceback
            print(f"[TRADING BOT] Traceback: {traceback.format_exc()}")
    
    async def handle_dices_signal(self, message):
        """Handle dices signal (Ox1, Ex2, etc.)"""
        try:
            print(f"[TRADING BOT] Processing dices signal: {message.text}")
            print(f"[TRADING BOT] Message chat info: id={message.chat.id}, title={getattr(message.chat, 'title', 'NO_TITLE')}, type={getattr(message.chat, 'type', 'NO_TYPE')}")
            
            # Call the actual process_dices_signal from bot.py
            from bot import process_dices_signal
            await process_dices_signal(self.trading_bot_client, message, message.text)
            
        except Exception as e:
            print(f"[TRADING BOT] Error handling dices signal: {e}")
            import traceback
            print(f"[TRADING BOT] Traceback: {traceback.format_exc()}")
    
    async def handle_red_green_command(self, message):
        """Handle red-green game command"""
        try:
            print(f"[TRADING BOT] Processing red-green command: {message.text}")
            
            # Call the actual red_green_command from bot.py
            from bot import red_green_command
            await red_green_command(self.trading_bot_client, message)
            
        except Exception as e:
            print(f"[TRADING BOT] Error handling red-green command: {e}")
    
    async def handle_blocks_command(self, message):
        """Handle blocks game command"""
        try:
            print(f"[TRADING BOT] Processing blocks command: {message.text}")
            
            # Call the actual blocks_command from bot.py
            from bot import blocks_command
            await blocks_command(self.trading_bot_client, message)
            
        except Exception as e:
            print(f"[TRADING BOT] Error handling blocks command: {e}")
    
    async def handle_dices_command(self, message):
        """Handle dices game command"""
        try:
            print(f"[TRADING BOT] Processing dices command: {message.text}")
            
            # Call the actual dices_command from bot.py
            from bot import dices_command
            await dices_command(self.trading_bot_client, message)
            
        except Exception as e:
            print(f"[TRADING BOT] Error handling dices command: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring for signals"""
        self.running = False
        print("[TRADING BOT] Signal monitoring stopped")

# Integration helper functions
def integrate_with_bot(bot_client):
    """Integrate the trading bot receiver with the main bot"""
    receiver = TradingBotReceiver(bot_client)
    
    # Start monitoring in a separate task
    async def start_receiver():
        await receiver.start_monitoring()
    
    # Return the receiver and start function for integration
    return receiver, start_receiver

# Example usage for standalone testing
async def test_receiver():
    """Test the receiver functionality"""
    class MockClient:
        pass
    
    client = MockClient()
    receiver = TradingBotReceiver(client)
    
    print("Starting test receiver...")
    await receiver.start_monitoring()

if __name__ == "__main__":
    # Test the receiver
    asyncio.run(test_receiver()) 