# 📁 Local File Fallback System - FiveM Red/Green Game Bots

## 📋 Overview

This document explains the local file fallback system implemented for the FiveM Red/Green game bots. When Redis is completely unavailable (like the current `Error 11001: getaddrinfo failed` issue), the system automatically falls back to using local JSON files for data sharing between bots.

## 🚨 **Problem Solved**

**Original Issue:**
```
[EN] Redis connection failed: Error 11001 connecting to redis-19425.c8.us-east-1-3.ec2.redns.redis-cloud.com:19425. getaddrinfo failed.. Using direct API fallback.
[EN] Redis unavailable, skipping Redis update
```

**Root Cause:**
- Redis server `redis-19425.c8.us-east-1-3.ec2.redns.redis-cloud.com:19425` is completely unreachable
- Network connectivity issues or server downtime
- Bots can't share data through Redis

## ✅ **Solution Implemented**

### **Hybrid Data Sharing Strategy**

The system now implements a **three-tier fallback approach**:

1. **Redis First**: Try to use Redis for data sharing
2. **Local File Fallback**: When Redis fails, use local JSON files
3. **Direct API**: When both Redis and local files fail, use direct API calls

## 🏗️ **Architecture Overview**

### **Data Flow with Fallback**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   English Bot   │───▶│  Local File     │───▶│  Other Bots     │
│ (Data Fetcher)  │    │ (Shared Cache)  │    │ (Data Readers)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       │
         ▼                       │                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │   Fallback      │    │   Direct API    │
│  (Primary)      │    │   Strategy      │    │   (Last Resort) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 **Implementation Details**

### **1. Local File Structure**

The English bot creates a comprehensive data structure in a local JSON file:

```json
{
  "timestamp": 1740227344593,
  "game_data": {
    "code": 200,
    "success": true,
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
    "last_update": 1740227344593
  }
}
```

### **2. File Location and Naming**

- **File Name**: `fivem_shared_data.json`
- **Location**: Same directory as the bot files
- **Format**: Human-readable JSON with indentation
- **Permissions**: Readable by all bots

### **3. Data Freshness Check**

All bots check if local file data is fresh (less than 30 seconds old):
```python
if current_time - shared_data["timestamp"] < 30000:
    return shared_data["game_data"]  # Use local file data
else:
    print("[BOT] Local file data is stale, using direct API")
    return None  # Fall back to direct API
```

## 📊 **Data Sharing Process**

### **Step 1: English Bot Fetches Data**
```python
def fetch_data():
    # First try to get data from Redis
    redis_data = read_redis()
    if redis_data:
        return redis_data
    
    # If Redis fails, use direct API call
    print("[EN] Using direct API call as Redis fallback")
    session = requests.Session()
    
    response = session.get(url, headers=headers, params=params, timeout=10)
    api_data = response.json()
    
    # Update both Redis and local file
    update_redis(api_data)
    
    return api_data
```

### **Step 2: English Bot Updates Data Sources**
```python
def update_redis(data_to_fill):
    try:
        r = get_redis_connection()
        if r:
            # Update Redis (primary method)
            # ... Redis update logic ...
            print("[EN] Shared data updated to Redis successfully")
        else:
            print("[EN] Redis unavailable, using local file fallback")
            # Fallback to local file when Redis is unavailable
            update_local_file(data_to_fill)
            
    except Exception as e:
        print(f"[EN] Failed to update Redis: {e}. Using local file fallback.")
        # Fallback to local file when Redis fails
        update_local_file(data_to_fill)
```

### **Step 3: Local File Update**
```python
def update_local_file(data_to_fill):
    """Update local file when Redis is unavailable"""
    try:
        # Create comprehensive shared data structure
        shared_data = {
            "timestamp": int(time.time() * 1000),
            "game_data": data_to_fill,
            "processed_data": {
                "issue_number": latest_issue,
                "colors": colors,
                "result_format": None,
                "game_type": "RG5M",
                "last_update": int(time.time() * 1000)
            }
        }
        
        # Write to local file
        with open("fivem_shared_data.json", "w") as f:
            json.dump(shared_data, f, indent=2)
        
        print("[EN] Shared data updated to local file successfully")
        
    except Exception as e:
        print(f"[EN] Failed to update local file: {e}")
```

### **Step 4: Other Bots Read from Local File**
```python
def read_local_file():
    """Read from local file when Redis is unavailable"""
    try:
        if os.path.exists("fivem_shared_data.json"):
            with open("fivem_shared_data.json", "r") as f:
                shared_data = json.load(f)
            
            # Check if data is fresh (less than 30 seconds old)
            current_time = int(time.time() * 1000)
            if current_time - shared_data["timestamp"] < 30000:
                print(f"[BOT] Data read from local file successfully (updated {current_time - shared_data['timestamp']}ms ago)")
                return shared_data["game_data"]
            else:
                print("[BOT] Local file data is stale, using direct API")
                return None
        else:
            print("[BOT] No local file found, using direct API")
            return None
            
    except Exception as e:
        print(f"[BOT] Failed to read local file: {e}")
        return None
```

## 🔄 **Fallback Strategy**

### **Primary Strategy: Redis First**
1. **Try Redis**: Attempt to read from shared data key
2. **Check Freshness**: Verify data is less than 10 seconds old
3. **Use Data**: Return Redis data if fresh and valid

### **Secondary Strategy: Local File**
1. **Redis Unavailable**: If Redis connection fails
2. **Check Local File**: Look for `fivem_shared_data.json`
3. **Verify Freshness**: Ensure data is less than 30 seconds old
4. **Use Local Data**: Return file data if fresh

### **Tertiary Strategy: Direct API**
1. **Both Redis and Local File Fail**: If neither source works
2. **Direct Call**: Make API request directly to game server
3. **Independent Operation**: Each bot works independently

## 📈 **Benefits of Local File Fallback**

### **1. Reliability**
- **No Network Dependency**: Works even when Redis is completely down
- **Local Access**: Fast file I/O operations
- **Persistent Storage**: Data survives bot restarts

### **2. Performance**
- **Fast Access**: Local file reading is very fast
- **No Network Latency**: Eliminates Redis connection delays
- **Efficient Fallback**: Quick switch when Redis fails

### **3. Data Consistency**
- **Same Data Source**: All bots read from the same file
- **Synchronized Updates**: English bot updates file for all bots
- **Real-time Sharing**: Data is shared within seconds

### **4. Debugging**
- **Human Readable**: JSON files are easy to inspect
- **Data Validation**: Can manually check file contents
- **Error Tracking**: Clear indication of fallback usage

## 🛠️ **Configuration**

### **File Settings**
```python
LOCAL_FILE_CONFIG = {
    "filename": "fivem_shared_data.json",
    "freshness_threshold": 30000,  # 30 seconds in milliseconds
    "indent": 2,  # JSON formatting
    "encoding": "utf-8"
}
```

### **Data Expiration**
- **Redis Data**: 5 minutes (300 seconds)
- **Local File Data**: 30 seconds (30000 milliseconds)
- **Update Frequency**: Every 2-5 seconds (game dependent)

### **Language-Specific Logging**
- **English Bot**: `[EN]` prefix
- **Vietnamese Bot**: `[VI]` prefix
- **Japanese Bot**: `[JP]` prefix
- **Indonesian Bot**: `[ID]` prefix

## 🔍 **Monitoring and Debugging**

### **Local File Status Messages**
```
[EN] Shared data updated to local file successfully
[VI] Data read from local file successfully (updated 1500ms ago)
[JP] Local file data is stale, using direct API
[ID] No local file found, using direct API
```

### **Data Flow Tracking**
1. **English Bot**: Fetches data and updates local file
2. **Other Bots**: Read from local file and display data age
3. **Fallback**: Clear indication when using local file vs direct API
4. **Errors**: Detailed error messages for troubleshooting

### **Performance Metrics**
- **Local File Hit Rate**: Percentage of successful local file reads
- **Data Freshness**: Time since last local file update
- **Fallback Frequency**: How often local file is used
- **Response Times**: Local file vs API performance comparison

## 🧪 **Testing Scenarios**

### **1. Normal Operation (Redis Available)**
- **English Bot**: Fetches data and updates Redis
- **Other Bots**: Read fresh data from Redis
- **Expected**: All bots show same game results

### **2. Redis Unavailable (Local File Active)**
- **English Bot**: Fetches data and updates local file
- **Other Bots**: Read fresh data from local file
- **Expected**: All bots show same game results

### **3. Both Redis and Local File Fail**
- **All Bots**: Fall back to direct API calls
- **Expected**: Bots work independently with direct API

### **4. Data Staleness Detection**
- **Local File Data**: Older than 30 seconds
- **All Bots**: Detect stale data and use direct API
- **Expected**: Fresh data fetched from game server

## ⚠️ **Important Considerations**

### **File Management**
- **Automatic Creation**: File is created automatically when needed
- **Overwrite Strategy**: New data overwrites old data
- **Error Handling**: Graceful fallback if file operations fail

### **Data Consistency**
- **Single Source**: English bot is the authoritative data source
- **Timing**: All bots get data within 30 seconds of each other
- **Validation**: Data structure validation before use

### **Performance**
- **File I/O**: Minimal overhead for file operations
- **Memory Usage**: No additional memory consumption
- **Disk Space**: Very small file size (few KB)

### **Security**
- **Local Access**: Only accessible from local machine
- **Data Exposure**: Only game data, no sensitive information
- **File Permissions**: Standard file system permissions

## 🎯 **Expected Results**

### **Before Implementation**
- **Redis Dependency**: Bots failed when Redis was unavailable
- **No Data Sharing**: Each bot worked independently
- **Inconsistent Results**: Different bots might show different data

### **After Implementation**
- **Redis + Local File**: Dual data sharing mechanisms
- **Consistent Data**: All bots use identical game results
- **Reliable Operation**: Bots work regardless of Redis status

## 🔄 **Maintenance and Updates**

### **Regular Tasks**
- **Monitor File**: Check if `fivem_shared_data.json` is being created
- **Review Logs**: Analyze local file hit/miss rates
- **File Cleanup**: Remove old files if needed
- **Performance Tuning**: Optimize freshness thresholds

### **Troubleshooting**
- **File Issues**: Check file permissions and disk space
- **Data Staleness**: Verify update frequency
- **Performance**: Monitor response times and fallback rates
- **Errors**: Review error logs and fix issues

## 🎯 **Conclusion**

The local file fallback system provides a robust, reliable, and efficient solution for the FiveM Red/Green game bots when Redis is unavailable. By implementing a hybrid approach that combines Redis (when available) with local file storage (as fallback), the system ensures:

- **Data Consistency**: All bots use identical game data regardless of Redis status
- **Reliability**: Continuous operation even when Redis is completely down
- **Performance**: Fast data access through local files
- **Scalability**: Easy to add new language variants
- **Monitoring**: Clear visibility into system performance and fallback usage

This implementation creates a **true resilient architecture** where the English bot serves as the data master, and all other language bots efficiently consume the shared data through either Redis or local files, resulting in a robust and maintainable system that works in all network conditions.
