#!/usr/bin/env python3
"""
Unified Bot Launcher
===================

This script launches all the bots in the workspace simultaneously.
Each bot runs in its own process to ensure isolation and stability.

Usage:
    python launch_all_bots.py
    or
    python launch_all_bots.py --config-only  # Only show configuration
    or
    python launch_all_bots.py --debug-mode   # Open each bot in separate window
"""

import os
import sys
import subprocess
import threading
import time
import signal
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import json
import platform

# Fix Windows console encoding issues
if platform.system() == "Windows":
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except:
        # Fallback: use cp65001 (UTF-8) code page
        os.system('chcp 65001 >nul 2>&1')

class BotLauncher:
    def __init__(self):
        self.workspace_root = Path(__file__).parent
        self.running_processes = []
        self.bot_configs = {}
        self.debug_mode = False
        self.load_bot_configurations()
        
    def load_bot_configurations(self):
        """Load all bot configurations from the workspace"""
        self.bot_configs = {
            # PyroBuddy bot
            "pyrobuddy": {
                "name": "PyroBuddy Bot",
                "path": self.workspace_root / "PyroBuddy" / "bot.py",
                "working_dir": self.workspace_root / "PyroBuddy",
                "description": "Pyrogram-based trading signal bot",
                "type": "pyrogram"
            },
            
            # # 55BTC bot
            # "55btc": {
            #     "name": "55BTC Bot",
            #     "path": self.workspace_root / "55BTC" / "55btcbot.py",
            #     "working_dir": self.workspace_root / "55BTC",
            #     "description": "55BTC trading bot",
            #     "type": "pyrogram"
            # },
            
            # # Signal Generator Bot - Pyrogram Version
            # "signal_generator_pyrogram": {
            #     "name": "Signal Generator Bot (Pyrogram)",
            #     "path": self.workspace_root / "Signal genrator bot" / "signal_auto_bot_pyrogram.py",
            #     "working_dir": self.workspace_root / "Signal genrator bot",
            #     "description": "Pyrogram-based signal generation bot with advanced features",
            #     "type": "pyrogram"
            # },
            
            # Signal Generator Bot - Copy Trading
            "signal_generator_copytrading": {
                "name": "Signal Generator Bot (Copy Trading)",
                "path": self.workspace_root / "Signal genrator bot" / "bot.py",
                "working_dir": self.workspace_root / "Signal genrator bot",
                "description": "Copy trading bot with signal processing",
                "type": "pyrogram"
            },
            
            # HelloGreeter bot
            "hellogreeter": {
                "name": "HelloGreeter Bot",
                "path": self.workspace_root / "HelloGreeter" / "bot.py",
                "working_dir": self.workspace_root / "HelloGreeter",
                "description": "Scheduler and greeting bot",
                "type": "pyrogram"
            },
            
            # New All In One bots
            "dices": {
                "name": "Dices Bot",
                "path": self.workspace_root / "new all in one" / "dices.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "Dice game bot",
                "type": "aiogram"
            },
            
            "number_guessing": {
                "name": "Number Guessing Bot",
                "path": self.workspace_root / "new all in one" / "number_gussing.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "Number guessing game bot",
                "type": "aiogram"
            },
            
            "blocks_bot": {
                "name": "Blocks Bot",
                "path": self.workspace_root / "new all in one" / "blocks_bot.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "Blocks game bot",
                "type": "aiogram"
            },
            
            "red_green": {
                "name": "Red Green Bot",
                "path": self.workspace_root / "new all in one" / "red_green.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "Red/Green trading bot",
                "type": "aiogram"
            },
            
            # FiveM individual bots
            "fivem_en": {
                "name": "FiveM English Bot",
                "path": self.workspace_root / "new all in one" / "fivem_r_g_en_bot.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "FiveM English red/green bot",
                "type": "aiogram"
            },
            
            "fivem_indonesia": {
                "name": "FiveM Indonesia Bot",
                "path": self.workspace_root / "new all in one" / "fivem_r_g_indonisia_bot.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "FiveM Indonesia red/green bot",
                "type": "aiogram"
            },
            
            "fivem_vietnam": {
                "name": "FiveM Vietnam Bot",
                "path": self.workspace_root / "new all in one" / "fivem_r_g_vitname_bot.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "FiveM Vietnam red/green bot",
                "type": "aiogram"
            },
            
            "fivem_japan": {
                "name": "FiveM Japan Bot",
                "path": self.workspace_root / "new all in one" / "fivem_r_g_Jabanise_bot.py",
                "working_dir": self.workspace_root / "new all in one",
                "description": "FiveM Japan red/green bot",
                "type": "aiogram"
            }
        }
    
    def check_bot_availability(self) -> Dict[str, bool]:
        """Check which bots are available to run"""
        availability = {}
        for bot_id, config in self.bot_configs.items():
            path = config["path"]
            availability[bot_id] = path.exists()
        return availability
    
    def show_configuration(self):
        """Display all bot configurations"""
        print("🤖 Bot Launcher Configuration")
        print("=" * 50)
        
        availability = self.check_bot_availability()
        
        for bot_id, config in self.bot_configs.items():
            status = "✅ Available" if availability[bot_id] else "❌ Not Found"
            print(f"\n📋 {config['name']}")
            print(f"   Type: {config['type']}")
            print(f"   Path: {config['path']}")
            print(f"   Status: {status}")
            print(f"   Description: {config['description']}")
        
        print(f"\n📊 Summary:")
        available_count = sum(availability.values())
        total_count = len(self.bot_configs)
        print(f"   Available: {available_count}/{total_count} bots")
        
        if self.debug_mode:
            print(f"   🐛 Debug Mode: Each bot will open in separate window")
        
        return availability
    
    def start_bot(self, bot_id: str, config: dict) -> Optional[subprocess.Popen]:
        """Start a single bot in a subprocess (Railway-safe version)"""
        try:
            if not config["path"].exists():
                print(f"❌ {config['name']}: File not found at {config['path']}")
                return None

            # Create environment with proper working directory
            env = os.environ.copy()
            env['PYTHONPATH'] = str(config['working_dir'])

            if self.debug_mode:
                # Debug mode: local debugging with new terminal
                if platform.system() == "Windows":
                    process = subprocess.Popen(
                        ["start", "cmd", "/k", "python", str(config['path'])],
                        cwd=str(config['working_dir']),
                        env=env,
                        shell=True
                    )
                    print(f"🚀 Started {config['name']} in new window (Debug Mode)")
                    return process
                else:
                    try:
                        process = subprocess.Popen(
                            ["xterm", "-title", config['name'], "-e", f"cd {config['working_dir']} && python {config['path']}; exec bash"],
                            env=env
                        )
                        print(f"🚀 Started {config['name']} in new terminal (Debug Mode)")
                        return process
                    except FileNotFoundError:
                        print(f"⚠️  xterm not found, starting {config['name']} in background")
                        process = subprocess.Popen(
                            [sys.executable, str(config['path'])],
                            cwd=str(config['working_dir']),
                            env=env
                        )
                        print(f"🚀 Started {config['name']} (PID: {process.pid})")
                        return process
            else:
                # Normal mode: Railway-safe (no stdout/stderr PIPEs)
                process = subprocess.Popen(
                    [sys.executable, str(config['path'])],
                    cwd=str(config['working_dir']),
                    env=env
                )

                print(f"🚀 Started {config['name']} (PID: {process.pid})")
                return process

        except Exception as e:
            print(f"❌ Failed to start {config['name']}: {e}")
            return None

    
    def start_all_bots(self, exclude: List[str] = None):
        """Start all available bots"""
        if exclude is None:
            exclude = []
        
        print("🚀 Starting All Bots...")
        print("=" * 30)
        
        if self.debug_mode:
            print("🐛 DEBUG MODE: Each bot will open in its own window/console")
            print("💡 You can now see each bot's output separately for debugging")
            print("=" * 30)
        
        availability = self.check_bot_availability()
        
        # Special handling for FiveM bots - start English bot first
        fivem_bots = ["fivem_en", "fivem_indonesia", "fivem_vietnam", "fivem_japan"]
        other_bots = [bot_id for bot_id in self.bot_configs.keys() if bot_id not in fivem_bots]
        
        # Start FiveM English bot first (data master)
        if "fivem_en" in self.bot_configs and availability.get("fivem_en", False):
            if "fivem_en" not in exclude:
                print("🎯 Starting FiveM English Bot first (Data Master)...")
                process = self.start_bot("fivem_en", self.bot_configs["fivem_en"])
                if process:
                    self.running_processes.append({
                        'bot_id': "fivem_en",
                        'config': self.bot_configs["fivem_en"],
                        'process': process
                    })
                # Wait a bit for English bot to initialize
                time.sleep(3)
            else:
                print("⏭️  Skipping FiveM English Bot (excluded)")
        
        # Start other FiveM bots
        for bot_id in fivem_bots[1:]:  # Skip English bot (already started)
            if bot_id in exclude:
                print(f"⏭️  Skipping {self.bot_configs[bot_id]['name']} (excluded)")
                continue
                
            if not availability.get(bot_id, False):
                print(f"❌ Skipping {self.bot_configs[bot_id]['name']} (not available)")
                continue
            
            process = self.start_bot(bot_id, self.bot_configs[bot_id])
            if process:
                self.running_processes.append({
                    'bot_id': bot_id,
                    'config': self.bot_configs[bot_id],
                    'process': process
                })
            
            # Small delay between FiveM bot starts
            time.sleep(2)
        
        # Start all other bots
        for bot_id in other_bots:
            if bot_id in exclude:
                print(f"⏭️  Skipping {self.bot_configs[bot_id]['name']} (excluded)")
                continue
                
            if not availability.get(bot_id, False):
                print(f"❌ Skipping {self.bot_configs[bot_id]['name']} (not available)")
                continue
            
            process = self.start_bot(bot_id, self.bot_configs[bot_id])
            if process:
                self.running_processes.append({
                    'bot_id': bot_id,
                    'config': self.bot_configs[bot_id],
                    'process': process
                })
            
            # Small delay between starts to avoid overwhelming the system
            time.sleep(1)
        
        if self.debug_mode:
            print(f"\n✅ Started {len(self.running_processes)} bots in separate windows!")
            print("📊 Each bot is now running in its own console window.")
            print("💡 You can debug each bot individually in their respective windows.")
            print("🛑 Close individual bot windows to stop them, or use Ctrl+C here to stop all.")
        else:
            print(f"\n✅ Started {len(self.running_processes)} bots successfully!")
            print("📊 Monitor the processes above for any errors.")
            print("💡 Press Ctrl+C to stop all bots.")
            print("🎯 FiveM bots started in correct order for data sharing!")
    
    def stop_all_bots(self):
        """Stop all running bots"""
        print("\n🛑 Stopping all bots...")
        
        for bot_info in self.running_processes:
            process = bot_info['process']
            config = bot_info['config']
            
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    print(f"🛑 Terminated {config['name']} (PID: {process.pid})")
                    
                    # Wait a bit for graceful shutdown
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        print(f"💀 Force killed {config['name']} (PID: {process.pid})")
                else:
                    print(f"✅ {config['name']} already stopped")
                    
            except Exception as e:
                print(f"❌ Error stopping {config['name']}: {e}")
        
        self.running_processes.clear()
        print("✅ All bots stopped.")
    
    def monitor_bots(self):
        """Monitor running bots and restart if needed"""
        if self.debug_mode:
            print("🐛 Debug Mode: Bots are running in separate windows.")
            print("💡 Monitor each bot in its own window for debugging.")
            print("🔄 This launcher will continue running for management purposes.")
            print("💡 Press Ctrl+C to stop all bots and close all windows.")
            
            # In debug mode, just keep the launcher running
            try:
                while True:
                    time.sleep(10)
                    print("💡 Launcher is still running. Press Ctrl+C to stop all bots.")
            except KeyboardInterrupt:
                print("\n🛑 Stopping all bots...")
                self.stop_all_bots()
                return
        
        # Normal monitoring mode
        while self.running_processes:
            for bot_info in self.running_processes[:]:  # Copy list to avoid modification during iteration
                process = bot_info['process']
                config = bot_info['config']
                
                if process.poll() is not None:  # Process has ended
                    print(f"⚠️  {config['name']} has stopped (exit code: {process.returncode})")
                    self.running_processes.remove(bot_info)
                    
                    # Optionally restart the bot
                    print(f"🔄 Restarting {config['name']}...")
                    new_process = self.start_bot(bot_info['bot_id'], config)
                    if new_process:
                        bot_info['process'] = new_process
                        self.running_processes.append(bot_info)
            
            time.sleep(5)  # Check every 5 seconds
    
    def run(self, exclude: List[str] = None, config_only: bool = False, debug_mode: bool = False):
        """Main run method"""
        self.debug_mode = debug_mode
        
        if config_only:
            self.show_configuration()
            return
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n📡 Received signal {signum}")
            self.stop_all_bots()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Show configuration first
            self.show_configuration()
            
            # Start all bots
            self.start_all_bots(exclude)
            
            # Monitor bots
            self.monitor_bots()
            
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
            self.stop_all_bots()
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            self.stop_all_bots()
            raise

def main():
    parser = argparse.ArgumentParser(description="Launch all bots in the workspace")
    parser.add_argument("--config-only", action="store_true", 
                       help="Only show bot configuration without starting")
    parser.add_argument("--exclude", nargs="+", 
                       help="Exclude specific bots from starting")
    parser.add_argument("--list", action="store_true",
                       help="List all available bots")
    parser.add_argument("--debug-mode", action="store_true",
                       help="Start each bot in separate window/console for debugging")
    
    args = parser.parse_args()
    
    launcher = BotLauncher()
    
    if args.list:
        launcher.show_configuration()
        return
    
    if args.config_only:
        launcher.show_configuration()
        return
    
    # Start all bots
    launcher.run(exclude=args.exclude, debug_mode=args.debug_mode)

if __name__ == "__main__":
    main()
