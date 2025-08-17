import json
import time
import os
import threading
from typing import Dict, Any, Optional
import asyncio

class BotCommunication:
    """Lightweight inter-bot communication system using file-based messaging"""
    
    def __init__(self, communication_file: str = "bot_signals.json"):
        self.communication_file = communication_file
        self.lock = threading.Lock()
        
    def send_signal(self, group_id: str, game: str, signal: str, issue_number: str, current_stage: int = 1, strategy: str = "random"):
        """Send a signal from signal bot to trading bot"""
        try:
            with self.lock:
                # Read existing signals
                signals = self._read_signals()
                
                # Create new signal entry
                signal_data = {
                    "timestamp": time.time(),
                    "group_id": group_id,
                    "game": game,
                    "signal": signal,
                    "issue_number": issue_number,
                    "current_stage": current_stage,
                    "strategy": strategy,
                    "processed": False
                }
                
                # Add to signals list
                signals.append(signal_data)
                
                # Keep only last 100 signals to prevent file from growing too large
                if len(signals) > 100:
                    signals = signals[-100:]
                
                # Write back to file
                self._write_signals(signals)
                
                print(f"Signal sent: {game} {signal}x{current_stage} to group {group_id}")
                return True
                
        except Exception as e:
            print(f"Error sending signal: {e}")
            return False
    
    def get_pending_signals(self) -> list:
        """Get all pending (unprocessed) signals"""
        try:
            with self.lock:
                signals = self._read_signals()
                return [s for s in signals if not s.get("processed", False)]
        except Exception as e:
            print(f"Error getting pending signals: {e}")
            return []
    
    def mark_signal_processed(self, timestamp: float):
        """Mark a signal as processed"""
        try:
            with self.lock:
                signals = self._read_signals()
                
                # Find and mark the signal as processed
                for signal in signals:
                    if abs(signal.get("timestamp", 0) - timestamp) < 0.1:  # Allow small time difference
                        signal["processed"] = True
                        break
                
                # Write back to file
                self._write_signals(signals)
                
        except Exception as e:
            print(f"Error marking signal as processed: {e}")
    
    def _read_signals(self) -> list:
        """Read signals from file"""
        try:
            if os.path.exists(self.communication_file):
                with open(self.communication_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error reading signals file: {e}")
            return []
    
    def _write_signals(self, signals: list):
        """Write signals to file"""
        try:
            with open(self.communication_file, 'w', encoding='utf-8') as f:
                json.dump(signals, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing signals file: {e}")
    
    def clear_old_signals(self, max_age_hours: int = 24):
        """Clear signals older than specified hours"""
        try:
            with self.lock:
                signals = self._read_signals()
                current_time = time.time()
                cutoff_time = current_time - (max_age_hours * 3600)
                
                # Keep only recent signals
                signals = [s for s in signals if s.get("timestamp", 0) > cutoff_time]
                
                # Write back to file
                self._write_signals(signals)
                
        except Exception as e:
            print(f"Error clearing old signals: {e}")
    
    def clear_all_signals(self):
        """Clear all signals from the file"""
        try:
            with self.lock:
                self._write_signals([])
                print("All signals cleared from communication file")
        except Exception as e:
            print(f"Error clearing all signals: {e}")

# Global instance
bot_comm = BotCommunication()

# Signal types mapping
SIGNAL_TYPES = {
    "red_green": {
        "r": "red",
        "g": "green"
    },
    "blocks": {
        "b": "big",
        "s": "small"
    },
    "dices": {
        "o": "odd",
        "e": "even"
    }
}

def get_signal_command(game: str, signal: str, current_stage: int) -> str:
    """Convert signal to command format for trading bot"""
    if game == "red_green":
        return f"{signal.upper()}x{current_stage}"
    elif game == "blocks":
        return f"{signal.upper()}x{current_stage}"
    elif game == "dices":
        return f"{signal.upper()}x{current_stage}"
    return f"{signal.upper()}x{current_stage}"

# Background cleaner thread
def start_cleaner_thread():
    """Start background thread to clean old signals"""
    def cleaner():
        while True:
            try:
                bot_comm.clear_old_signals()
                time.sleep(3600)  # Run every hour
            except Exception as e:
                print(f"Error in cleaner thread: {e}")
                time.sleep(3600)
    
    thread = threading.Thread(target=cleaner, daemon=True)
    thread.start()
    return thread 