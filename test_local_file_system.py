#!/usr/bin/env python3
"""
Test Script for Local File Fallback System
This script tests the local file data sharing mechanism for FiveM Red/Green game bots.
"""

import json
import time
import os

def test_local_file_system():
    """Test the local file fallback system"""
    
    print("🧪 Testing Local File Fallback System")
    print("=" * 50)
    
    # Test 1: Check if shared data file exists
    print("\n1️⃣ Testing File Existence:")
    if os.path.exists("fivem_shared_data.json"):
        print("✅ fivem_shared_data.json exists")
        
        # Test 2: Check file content
        print("\n2️⃣ Testing File Content:")
        try:
            with open("fivem_shared_data.json", "r") as f:
                data = json.load(f)
            
            print("✅ File is valid JSON")
            print(f"📊 File size: {os.path.getsize('fivem_shared_data.json')} bytes")
            
            # Test 3: Check data structure
            print("\n3️⃣ Testing Data Structure:")
            required_keys = ["timestamp", "game_data", "processed_data"]
            for key in required_keys:
                if key in data:
                    print(f"✅ Key '{key}' exists")
                else:
                    print(f"❌ Key '{key}' missing")
            
            # Test 4: Check data freshness
            print("\n4️⃣ Testing Data Freshness:")
            current_time = int(time.time() * 1000)
            data_age = current_time - data["timestamp"]
            print(f"📅 Data timestamp: {data['timestamp']}")
            print(f"🕐 Current time: {current_time}")
            print(f"⏱️  Data age: {data_age}ms ({data_age/1000:.1f}s)")
            
            if data_age < 30000:  # 30 seconds
                print("✅ Data is fresh (< 30 seconds old)")
            else:
                print("⚠️  Data is stale (> 30 seconds old)")
            
            # Test 5: Check game data structure
            print("\n5️⃣ Testing Game Data Structure:")
            if "game_data" in data and "data" in data["game_data"]:
                print("✅ Game data structure is valid")
                if "records" in data["game_data"]["data"]:
                    print("✅ Records array exists")
                    records = data["game_data"]["data"]["records"]
                    if records:
                        print(f"✅ Found {len(records)} record(s)")
                        latest_record = records[0]
                        if "issue" in latest_record:
                            print(f"✅ Latest issue: {latest_record['issue']}")
                        if "value" in latest_record:
                            print(f"✅ Latest value: {latest_record['value']}")
                    else:
                        print("⚠️  No records found")
                else:
                    print("❌ Records array missing")
            else:
                print("❌ Game data structure is invalid")
            
            # Test 6: Check processed data
            print("\n6️⃣ Testing Processed Data:")
            if "processed_data" in data:
                processed = data["processed_data"]
                if "issue_number" in processed:
                    print(f"✅ Issue number: {processed['issue_number']}")
                if "colors" in processed:
                    print(f"✅ Colors: {processed['colors']}")
                if "game_type" in processed:
                    print(f"✅ Game type: {processed['game_type']}")
            else:
                print("❌ Processed data missing")
                
        except json.JSONDecodeError as e:
            print(f"❌ File is not valid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    
    else:
        print("❌ fivem_shared_data.json does not exist")
        print("💡 This is normal if the English bot hasn't run yet")
    
    # Test 7: Simulate data reading
    print("\n7️⃣ Testing Data Reading Simulation:")
    try:
        if os.path.exists("fivem_shared_data.json"):
            with open("fivem_shared_data.json", "r") as f:
                shared_data = json.load(f)
            
            current_time = int(time.time() * 1000)
            if current_time - shared_data["timestamp"] < 30000:
                print("✅ Data read from local file successfully")
                print(f"📊 Data age: {current_time - shared_data['timestamp']}ms")
                return shared_data["game_data"]
            else:
                print("⚠️  Local file data is stale, would use direct API")
                return None
        else:
            print("⚠️  No local file found, would use direct API")
            return None
            
    except Exception as e:
        print(f"❌ Error in data reading simulation: {e}")
        return None

def create_sample_data():
    """Create a sample shared data file for testing"""
    print("\n🔧 Creating Sample Data File:")
    
    sample_data = {
        "timestamp": int(time.time() * 1000),
        "game_data": {
            "code": 200,
            "success": True,
            "data": {
                "records": [
                    {
                        "issue": 2031700177,
                        "value": "4",
                        "resultFormatValueI18n": ["红", "", "", "", "", "", "", "4", "", "", "", "", ""]
                    }
                ]
            }
        },
        "processed_data": {
            "issue_number": 2031700177,
            "colors": "RED   🔴",
            "result_format": "4",
            "game_type": "RG5M",
            "last_update": int(time.time() * 1000)
        }
    }
    
    try:
        with open("fivem_shared_data.json", "w") as f:
            json.dump(sample_data, f, indent=2)
        print("✅ Sample data file created successfully")
        print("📁 File: fivem_shared_data.json")
    except Exception as e:
        print(f"❌ Failed to create sample file: {e}")

if __name__ == "__main__":
    print("🚀 FiveM Red/Green Bots - Local File System Test")
    print("=" * 60)
    
    # Check if sample file exists, if not create one
    if not os.path.exists("fivem_shared_data.json"):
        print("📝 No shared data file found. Creating sample data...")
        create_sample_data()
    
    # Run the test
    result = test_local_file_system()
    
    print("\n" + "=" * 60)
    if result:
        print("🎉 Test completed successfully!")
        print("✅ Local file system is working correctly")
    else:
        print("⚠️  Test completed with warnings")
        print("💡 Local file system may need attention")
    
    print("\n📋 Next Steps:")
    print("1. Run the English bot to update the shared data file")
    print("2. Run other language bots to test data reading")
    print("3. Check the console output for data sharing messages")
    print("4. Monitor the fivem_shared_data.json file for updates")
