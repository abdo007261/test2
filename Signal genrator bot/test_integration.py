#!/usr/bin/env python3
"""
Test script for bot communication system
This script tests the communication between signal bot and trading bot
"""

import asyncio
import time
import json
from bot_communication import bot_comm, get_signal_command
from trading_bot_receiver import TradingBotReceiver

class MockTradingBot:
    """Mock trading bot for testing"""
    
    def __init__(self):
        self.processed_signals = []
    
    async def send_message(self, chat_id, text):
        """Mock send message function"""
        print(f"[MOCK BOT] Would send to {chat_id}: {text}")
        self.processed_signals.append({
            'chat_id': chat_id,
            'text': text,
            'timestamp': time.time()
        })

async def test_signal_sending():
    """Test sending signals from signal bot"""
    print("=== Testing Signal Sending ===")
    
    # Test signals for different games
    test_signals = [
        {
            'group_id': '-1001234567890',
            'game': 'red_green',
            'signal': 'r',
            'issue_number': '12345',
            'current_stage': 1,
            'strategy': 'random'
        },
        {
            'group_id': '-1001234567890',
            'game': 'blocks',
            'signal': 'b',
            'issue_number': '12346',
            'current_stage': 2,
            'strategy': 'formula'
        },
        {
            'group_id': '-1001234567890',
            'game': 'dices',
            'signal': 'o',
            'issue_number': '12347',
            'current_stage': 3,
            'strategy': 'random'
        }
    ]
    
    for signal_data in test_signals:
        print(f"\nSending signal: {signal_data['game']} {signal_data['signal']}x{signal_data['current_stage']}")
        success = bot_comm.send_signal(**signal_data)
        if success:
            print("✅ Signal sent successfully")
        else:
            print("❌ Failed to send signal")
    
    # Wait a moment for file to be written
    await asyncio.sleep(0.1)

async def test_signal_receiving():
    """Test receiving signals in trading bot"""
    print("\n=== Testing Signal Receiving ===")
    
    # Create mock trading bot
    mock_bot = MockTradingBot()
    
    # Create receiver
    receiver = TradingBotReceiver(mock_bot, check_interval=0.1)
    
    # Start monitoring for a short time
    print("Starting signal monitoring...")
    monitoring_task = asyncio.create_task(receiver.start_monitoring())
    
    # Let it run for a few seconds
    await asyncio.sleep(3)
    
    # Stop monitoring
    receiver.stop_monitoring()
    monitoring_task.cancel()
    
    # Check results
    print(f"\nProcessed {len(mock_bot.processed_signals)} signals:")
    for signal in mock_bot.processed_signals:
        print(f"  - {signal['text']} to {signal['chat_id']}")

async def test_command_formatting():
    """Test signal command formatting"""
    print("\n=== Testing Command Formatting ===")
    
    test_cases = [
        ('red_green', 'r', 1),
        ('red_green', 'g', 2),
        ('blocks', 'b', 1),
        ('blocks', 's', 3),
        ('dices', 'o', 1),
        ('dices', 'e', 2)
    ]
    
    for game, signal, stage in test_cases:
        command = get_signal_command(game, signal, stage)
        print(f"{game} {signal}x{stage} -> {command}")

async def test_file_operations():
    """Test file operations"""
    print("\n=== Testing File Operations ===")
    
    # Check if file exists
    import os
    if os.path.exists('bot_signals.json'):
        print("✅ Communication file exists")
        
        # Read and display current signals
        with open('bot_signals.json', 'r') as f:
            signals = json.load(f)
        
        print(f"📄 File contains {len(signals)} signals")
        for i, signal in enumerate(signals[-3:], 1):  # Show last 3
            print(f"  {i}. {signal['game']} {signal['signal']}x{signal['current_stage']} -> {signal['group_id']}")
    else:
        print("❌ Communication file not found")

async def main():
    """Run all tests"""
    print("🤖 Bot Communication System Test")
    print("=" * 50)
    
    # Test command formatting
    await test_command_formatting()
    
    # Test signal sending
    await test_signal_sending()
    
    # Test file operations
    await test_file_operations()
    
    # Test signal receiving
    await test_signal_receiving()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\nTo test with real bots:")
    print("1. Start signal bot: python signal_auto_bot_pyrogram.py")
    print("2. Start trading bot: python bot.py")
    print("3. Send signals through the signal bot interface")

if __name__ == "__main__":
    asyncio.run(main()) 