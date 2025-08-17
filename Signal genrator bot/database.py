import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class Database:
    def __init__(self, db_file="data.json"):
        self.db_file = db_file
        self.data = self.load_data()
    
    def load_data(self) -> Dict:
        """Load data from JSON file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure the default admin is always added
                    if "admins" in data and 1602528125 not in data["admins"]:
                        data["admins"].append(1602528125)
                    # Convert online_users list back to set
                    if "online_users" in data:
                        data["online_users"] = set(data["online_users"])
                    else:
                        data["online_users"] = set()
                    return data
            except:
                pass
        return {
            "users": {},
            "admins": [1602528125],  # Default admin ID
            "groups": {},
            "sessions": {},
            "user_languages": {},
            "online_users": set()
        }
    
    def save_data(self):
        """Save data to JSON file"""
        # Convert sets to lists for JSON serialization
        data_to_save = self.data.copy()
        data_to_save["online_users"] = list(self.data["online_users"])
        
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    
    def add_user(self, user_id: int, username: str, password: str):
        """Add a new user"""
        self.data["users"][username] = {
            "user_id": user_id,
            "password": password,
            "created_at": datetime.now().isoformat(),
            "is_admin": False
        }
        self.save_data()
    
    def add_admin(self, user_id: int):
        """Add a new admin"""
        if user_id not in self.data["admins"]:
            self.data["admins"].append(user_id)
            self.save_data()
    
    def remove_admin(self, user_id: int):
        """Remove an admin"""
        if user_id in self.data["admins"]:
            self.data["admins"].remove(user_id)
            self.save_data()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.data["admins"]
    
    def validate_user(self, username: str, password: str) -> bool:
        """Validate user credentials"""
        user = self.data["users"].get(username)
        return user and user["password"] == password
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user data by username"""
        return self.data["users"].get(username)
    
    def create_session(self, user_id: int, username: str):
        """Create user session (valid for 3 days)"""
        expiry = datetime.now() + timedelta(days=3)
        # Ensure user_id is stored as string to avoid type issues
        user_id_str = str(user_id)
        self.data["sessions"][user_id_str] = {
            "username": username,
            "expires_at": expiry.isoformat()
        }
        print(f"Creating session for user {user_id} with username {username}")
        print(f"Session data: {self.data['sessions'][user_id_str]}")
        self.save_data()
        print(f"Session saved to database")
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Get user session"""
        user_id_str = str(user_id)
        print(f"Getting session for user {user_id}")
        print(f"All sessions: {self.data['sessions']}")
        session = self.data["sessions"].get(user_id_str)
        print(f"Found session: {session}")
        if session:
            expires_at = datetime.fromisoformat(session["expires_at"])
            print(f"Session expires at: {expires_at}")
            if datetime.now() < expires_at:
                print(f"Session is valid")
                return session
            else:
                # Session expired
                print(f"Session expired")
                del self.data["sessions"][user_id_str]
                self.save_data()
        return None
    
    def remove_session(self, user_id: int):
        """Remove user session"""
        user_id_str = str(user_id)
        if user_id_str in self.data["sessions"]:
            del self.data["sessions"][user_id_str]
            self.save_data()
    
    def set_user_language(self, user_id: int, language: str):
        """Set user language preference"""
        self.data["user_languages"][user_id] = language
        self.save_data()
    
    def get_user_language(self, user_id: int) -> str:
        """Get user language preference"""
        return self.data["user_languages"].get(user_id, "en")

    # --- GROUP LANGUAGE SUPPORT ---
    def set_group_language(self, group_id: int, language: str):
        """Set chat language preference (works for groups, supergroups, and channels)"""
        print(f"DEBUG: set_group_language called with group_id={group_id}, language={language}")
        if "group_languages" not in self.data:
            self.data["group_languages"] = {}
        self.data["group_languages"][str(group_id)] = language
        print(f"DEBUG: Stored language '{language}' for group '{group_id}' in DB")
        print(f"DEBUG: Current group_languages: {self.data['group_languages']}")
        self.save_data()

    def get_group_language(self, group_id: int) -> str:
        """Get chat language preference (works for groups, supergroups, and channels)"""
        print(f"DEBUG: get_group_language called with group_id={group_id}")
        if "group_languages" in self.data:
            language = self.data["group_languages"].get(str(group_id), "en")
            print(f"DEBUG: Retrieved language '{language}' for group '{group_id}'")
            return language
        print(f"DEBUG: No group_languages in DB, returning 'en'")
        return "en"
    
    def get_group_language_by_name(self, group_name: str) -> str:
        """Get group language by group name"""
        if "group_languages_by_name" not in self.data:
            self.data["group_languages_by_name"] = {}
        return self.data["group_languages_by_name"].get(group_name, "en")
    
    def set_group_language_by_name(self, group_name: str, language: str):
        """Set group language by group name"""
        if "group_languages_by_name" not in self.data:
            self.data["group_languages_by_name"] = {}
        self.data["group_languages_by_name"][group_name] = language
        self.save_data()
    
    def add_group(self, group_name: str, description: str = None):
        """Add a new group"""
        self.data["groups"][group_name] = {
            "description": description or group_name,
            "created_at": datetime.now().isoformat()
        }
        self.save_data()
    
    def remove_group(self, group_name: str):
        """Remove a group"""
        if group_name in self.data["groups"]:
            del self.data["groups"][group_name]
            self.save_data()
    
    def update_group_description(self, group_name: str, description: str):
        """Update group description"""
        if group_name in self.data["groups"]:
            self.data["groups"][group_name]["description"] = description
            self.save_data()
    
    def get_groups(self) -> Dict:
        """Get all groups"""
        return self.data["groups"]
    
    def get_users(self) -> Dict:
        """Get all users"""
        return self.data["users"]
    
    def get_admins(self) -> List[int]:
        """Get all admin IDs"""
        return self.data["admins"]
    
    def add_online_user(self, user_id: int):
        """Add user to online list"""
        self.data["online_users"].add(user_id)
        self.save_data()
    
    def remove_online_user(self, user_id: int):
        """Remove user from online list"""
        self.data["online_users"].discard(user_id)
        self.save_data()
    
    def get_online_users(self) -> set:
        """Get online users"""
        return self.data["online_users"]
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information"""
        user = self.data["users"].get(username)
        if user:
            user_id = user["user_id"]
            is_online = user_id in self.data["online_users"]
            return {
                "username": username,
                "user_id": user_id,
                "is_online": is_online,
                "created_at": user["created_at"],
                "is_admin": user["is_admin"]
            }
        return None

    # --- COINVID CREDENTIALS MANAGEMENT ---
    def save_coinvid_credentials(self, user_id: int, username: str, password: str, blade_auth: str = None):
        """Save Coinvid credentials for a user"""
        if "coinvid_credentials" not in self.data:
            self.data["coinvid_credentials"] = {}
        
        self.data["coinvid_credentials"][user_id] = {
            "username": username,
            "password": password,
            "blade_auth": blade_auth,
            "saved_at": datetime.now().isoformat()
        }
        self.save_data()
    
    def get_coinvid_credentials(self, user_id: int) -> Optional[Dict]:
        """Get Coinvid credentials for a user"""
        if "coinvid_credentials" in self.data:
            # Try both string and integer keys
            user_id_str = str(user_id)
            return self.data["coinvid_credentials"].get(user_id_str) or self.data["coinvid_credentials"].get(user_id)
        return None
    
    def update_blade_auth(self, user_id: int, blade_auth: str):
        """Update blade_auth token for a user"""
        if "coinvid_credentials" in self.data:
            user_id_str = str(user_id)
            # Try both string and integer keys
            if user_id_str in self.data["coinvid_credentials"]:
                self.data["coinvid_credentials"][user_id_str]["blade_auth"] = blade_auth
                self.data["coinvid_credentials"][user_id_str]["saved_at"] = datetime.now().isoformat()
                self.save_data()
            elif user_id in self.data["coinvid_credentials"]:
                self.data["coinvid_credentials"][user_id]["blade_auth"] = blade_auth
                self.data["coinvid_credentials"][user_id]["saved_at"] = datetime.now().isoformat()
                self.save_data()
    
    def save_user_selected_group(self, user_id: int, group_name: str):
        """Save which group a user is copying from"""
        if "user_selected_groups" not in self.data:
            self.data["user_selected_groups"] = {}
        
        # Store as string key for consistency
        self.data["user_selected_groups"][str(user_id)] = group_name
        self.save_data()
    
    def get_user_selected_group(self, user_id: int) -> Optional[str]:
        """Get which group a user is copying from"""
        if "user_selected_groups" in self.data:
            # Try both string and integer keys
            user_id_str = str(user_id)
            return self.data["user_selected_groups"].get(user_id_str) or self.data["user_selected_groups"].get(user_id)
        return None
    
    def set_user_trading_status(self, user_id: int, is_trading: bool):
        """Set user's trading status"""
        if "user_trading_status" not in self.data:
            self.data["user_trading_status"] = {}
        
        # Store as string key for consistency
        self.data["user_trading_status"][str(user_id)] = is_trading
        self.save_data()
    
    def get_user_trading_status(self, user_id: int) -> bool:
        """Get user's trading status"""
        if "user_trading_status" in self.data:
            # Try both string and integer keys
            user_id_str = str(user_id)
            return self.data["user_trading_status"].get(user_id_str, False) or self.data["user_trading_status"].get(user_id, False)
        return False

    # --- INITIAL BALANCE MANAGEMENT ---
    def set_user_initial_balance(self, user_id: int, balance: float):
        """Set the user's initial balance when trading starts"""
        if "user_initial_balance" not in self.data:
            self.data["user_initial_balance"] = {}
        self.data["user_initial_balance"][str(user_id)] = balance
        self.save_data()

    def get_user_initial_balance(self, user_id: int) -> float:
        """Get the user's initial balance for trading session"""
        if "user_initial_balance" in self.data:
            return self.data["user_initial_balance"].get(str(user_id))
        return None 