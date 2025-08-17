#!/usr/bin/env python3
"""
Test script to verify bot integration works correctly
Run this to test if your bot can receive signals from the signal bot
"""

import asyncio
import json
import time
from bot_communication import bot_comm, get_signal_command

async def test_signal_sending():
    """Test sending signals to the communication file"""
    print("🧪 Testing signal sending...")
    
    # Test signals for each game
    test_signals = [
        {
            "group_id": "123456789",
            "game": "red_green", 
            "signal": "R",
            "issue_number": "12345",
            "current_stage": 1,
            "strategy": "random"
        },
        {
            "group_id": "123456789",
            "game": "blocks",
            "signal": "B", 
            "issue_number": "12346",
            "current_stage": 2,
            "strategy": "formula"
        },
        {
            "group_id": "123456789",
            "game": "dices",
            "signal": "O",
            "issue_number": "12347", 
            "current_stage": 1,
            "strategy": "random"
        }
    ]
    
    for signal in test_signals:
        print(f"📤 Sending {signal['game']} signal: {signal['signal']}x{signal['current_stage']}")
        bot_comm.send_signal(**signal)
        await asyncio.sleep(0.5)
    
    print("✅ Test signals sent successfully!")

async def test_signal_processing():
    """Test processing signals from the communication file"""
    print("🧪 Testing signal processing...")
    
    # Get pending signals
    pending = bot_comm.get_pending_signals()
    print(f"📥 Found {len(pending)} pending signals")
    
    for signal in pending:
        command = get_signal_command(signal['game'], signal['signal'], signal['current_stage'])
        print(f"🔄 Processing: {signal['game']} {signal['signal']}x{signal['current_stage']} → {command}")
        
        # Mark as processed
        bot_comm.mark_signal_processed(signal['timestamp'])
    
    print("✅ Signal processing test completed!")

async def test_command_formatting():
    """Test command formatting for different games"""
    print("🧪 Testing command formatting...")
    
    test_cases = [
        ("red_green", "R", 1, "Rx1"),
        ("red_green", "G", 2, "Gx2"),
        ("blocks", "B", 1, "Bx1"),
        ("blocks", "S", 3, "Sx3"),
        ("dices", "O", 1, "Ox1"),
        ("dices", "E", 2, "Ex2"),
    ]
    
    for game, signal, stage, expected in test_cases:
        result = get_signal_command(game, signal, stage)
        status = "✅" if result == expected else "❌"
        print(f"{status} {game} {signal}x{stage} → {result} (expected: {expected})")

def test_file_operations():
    """Test file operations"""
    print("🧪 Testing file operations...")
    
    # Test reading/writing
    test_data = {"test": "data", "timestamp": time.time()}
    
    # Write test data
    with open("bot_signals.json", "w") as f:
        json.dump([test_data], f)
    
    # Read test data
    with open("bot_signals.json", "r") as f:
        data = json.load(f)
    
    if data == [test_data]:
        print("✅ File operations working correctly!")
    else:
        print("❌ File operations failed!")

async def main():
    """Run all tests"""
    print("🚀 Starting bot integration tests...\n")
    
    # Test file operations
    test_file_operations()
    print()
    
    # Test command formatting
    await test_command_formatting()
    print()
    
    # Test signal sending
    await test_signal_sending()
    print()
    
    # Test signal processing
    await test_signal_processing()
    print()
    
    print("🎉 All tests completed!")
    print("\n📋 Next steps:")
    print("1. Add the integration code to your bot.py file")
    print("2. Start your signal bot: python signal_auto_bot_pyrogram.py")
    print("3. Start your trading bot: python bot.py")
    print("4. Send a signal through the signal bot interface")
    print("5. Watch your trading bot automatically process it!")

if __name__ == "__main__":
    asyncio.run(main()) 