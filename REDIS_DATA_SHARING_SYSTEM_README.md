# 🔄 Redis Data Sharing System - FiveM Red/Green Game Bots

## 📋 Overview

This document explains the Redis data sharing system implemented for the FiveM Red/Green game bots. The system ensures that all language variants of the bots can access the same real-time game data through a centralized Redis cache, improving efficiency and data consistency.

## 🏗️ **Architecture Overview**

### **Data Flow**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   English Bot   │───▶│     Redis       │───▶│  Other Bots     │
│ (Data Fetcher)  │    │  (Shared Cache) │    │ (Data Readers)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Bot Roles**
- **English Bot (`fivem_r_g_en_bot.py`)**: Primary data fetcher and Redis updater
- **Vietnamese Bot (`fivem_r_g_vitname_bot.py`)**: Data reader from Redis
- **Japanese Bot (`fivem_r_g_Jabanise_bot.py`)**: Data reader from Redis
- **Indonesian Bot (`fivem_r_g_indonisia_bot.py`)**: Data reader from Redis

## 🔧 **Implementation Details**

### **1. Redis Data Structure**

The English bot creates a comprehensive data structure in Redis:

```json
{
  "timestamp": 1740227344593,
  "game_data": {
    "data": {
      "records": [
        {
          "issue": 12345,
          "value": "123",
          "resultFormatValueI18n": ["Red", "Green"]
        }
      ]
    }
  },
  "processed_data": {
    "issue_number": 12345,
    "colors": "GREEN   🟢",
    "result_format": "123",
    "game_type": "RG5M",
    "last_update": 1740227344593
  }
}
```

### **2. Redis Keys**

- **Primary Key**: `fivem_red_green_shared_data` - Comprehensive shared data
- **Legacy Key**: `api_response` - Backward compatibility
- **Expiration**: 5 minutes (300 seconds) to ensure data freshness

### **3. Data Freshness Check**

All bots check if Redis data is fresh (less than 10 seconds old):
```python
if int(time.time() * 1000) - shared_info['timestamp'] < 10000:
    return shared_info['game_data']  # Use Redis data
else:
    print("[BOT] Redis data is stale, using direct API")
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
    
    # Update Redis for other bots
    update_redis(api_data)
    
    return api_data
```

### **Step 2: English Bot Updates Redis**
```python
def update_redis(data_to_fill):
    try:
        r = get_redis_connection()
        if r:
            # Create comprehensive shared data structure
            shared_data = {
                "timestamp": int(time.time() * 1000),
                "game_data": data_to_fill,
                "processed_data": {
                    "issue_number": latest_issue,
                    "colors": colors,
                    "result_format": result_format,
                    "game_type": "RG5M",
                    "last_update": int(time.time() * 1000)
                }
            }
            
            # Update shared Redis key
            r.set("fivem_red_green_shared_data", json.dumps(shared_data))
            r.expire("fivem_red_green_shared_data", 300)
            print("[EN] Shared data updated to Redis successfully")
            
    except Exception as e:
        print(f"[EN] Failed to update Redis: {e}")
```

### **Step 3: Other Bots Read from Redis**
```python
def read_redis():
    try:
        r = get_redis_connection()
        if r:
            # Read from shared data key
            shared_data = r.get("fivem_red_green_shared_data")
            if shared_data:
                shared_info = json.loads(shared_data)
                
                # Check data freshness
                if int(time.time() * 1000) - shared_info['timestamp'] < 10000:
                    return shared_info['game_data']
                else:
                    print("[BOT] Redis data is stale, using direct API")
                    return None
            else:
                # Fallback to legacy key
                raw_data = r.get("api_response")
                if raw_data:
                    return json.loads(raw_data)
                else:
                    return None
                    
    except Exception as e:
        print(f"[BOT] Failed to read from Redis: {e}")
        return None
```

## 🔄 **Fallback Strategy**

### **Primary Strategy: Redis First**
1. **Try Redis**: Attempt to read from shared data key
2. **Check Freshness**: Verify data is less than 10 seconds old
3. **Use Data**: Return Redis data if fresh and valid

### **Fallback Strategy: Direct API**
1. **Redis Unavailable**: If Redis connection fails
2. **Stale Data**: If Redis data is older than 10 seconds
3. **No Data**: If Redis has no data
4. **Direct Call**: Make API request directly to game server

### **Error Handling**
- **Redis Failures**: Gracefully fall back to direct API
- **API Failures**: Retry with exponential backoff
- **Data Validation**: Ensure data structure is correct
- **Timeout Protection**: 5-second Redis timeout, 10-second API timeout

## 📈 **Benefits of Data Sharing**

### **1. Efficiency**
- **Single API Call**: Only English bot makes API requests
- **Reduced Load**: Less strain on game servers
- **Faster Response**: Other bots get data instantly from Redis

### **2. Consistency**
- **Same Data**: All bots use identical game data
- **Synchronized**: No timing differences between bots
- **Reliable**: Centralized data source

### **3. Scalability**
- **Multiple Bots**: Can add more language variants easily
- **Load Distribution**: Redis handles multiple readers efficiently
- **Resource Optimization**: Shared connection pool

### **4. Monitoring**
- **Data Freshness**: Track when data was last updated
- **Usage Patterns**: Monitor Redis hit/miss rates
- **Performance Metrics**: Measure response times

## 🛠️ **Configuration**

### **Redis Settings**
```python
REDIS_CONFIG = {
    "host": "redis-19425.c8.us-east-1-3.ec2.redns.redis-cloud.com",
    "port": 19425,
    "username": "default",
    "password": "wm3WGUb0VbsZ8drJQro7jkTQwOCFzxV3",
    "timeout": 5,  # 5 seconds
    "connect_timeout": 5
}
```

### **Data Expiration**
- **Shared Data**: 5 minutes (300 seconds)
- **Freshness Threshold**: 10 seconds
- **Update Frequency**: Every 2-5 seconds (game dependent)

### **Language-Specific Logging**
- **English Bot**: `[EN]` prefix
- **Vietnamese Bot**: `[VI]` prefix
- **Japanese Bot**: `[JP]` prefix
- **Indonesian Bot**: `[ID]` prefix

## 🔍 **Monitoring and Debugging**

### **Redis Status Messages**
```
[EN] Shared data updated to Redis successfully
[VI] Shared data read from Redis successfully (updated 1500ms ago)
[JP] Redis data is stale, using direct API
[ID] Redis unavailable, using direct API
```

### **Data Flow Tracking**
1. **English Bot**: Fetches data and updates Redis
2. **Other Bots**: Read from Redis and display data age
3. **Fallback**: Clear indication when using direct API
4. **Errors**: Detailed error messages for troubleshooting

### **Performance Metrics**
- **Redis Hit Rate**: Percentage of successful Redis reads
- **Data Freshness**: Time since last Redis update
- **Fallback Frequency**: How often direct API is used
- **Response Times**: Redis vs API performance comparison

## 🧪 **Testing Scenarios**

### **1. Normal Operation**
- **English Bot**: Fetches data and updates Redis
- **Other Bots**: Read fresh data from Redis
- **Expected**: All bots show same game results

### **2. Redis Unavailable**
- **English Bot**: Falls back to direct API
- **Other Bots**: Fall back to direct API
- **Expected**: All bots continue working independently

### **3. Stale Data**
- **Redis Data**: Older than 10 seconds
- **All Bots**: Detect stale data and use direct API
- **Expected**: Fresh data fetched from game server

### **4. Network Issues**
- **Connection Problems**: Timeout or connection errors
- **Fallback Strategy**: Retry with exponential backoff
- **Expected**: Graceful degradation and recovery

## ⚠️ **Important Considerations**

### **Data Consistency**
- **Single Source**: English bot is the authoritative data source
- **Timing**: All bots get data within 10 seconds of each other
- **Validation**: Data structure validation before use

### **Error Handling**
- **Redis Failures**: Don't break bot operation
- **API Failures**: Graceful fallback and retry
- **Data Corruption**: Validation and fallback mechanisms

### **Performance**
- **Redis Timeout**: 5 seconds to prevent hanging
- **API Timeout**: 10 seconds for game server requests
- **Retry Limits**: Maximum 5 attempts to prevent infinite loops

### **Security**
- **Redis Access**: Secure connection with authentication
- **Data Exposure**: Only game data, no sensitive information
- **Access Control**: Bots can only read shared data

## 🎯 **Expected Results**

### **Before Implementation**
- **Multiple API Calls**: Each bot made separate requests
- **Inconsistent Data**: Different bots might get different results
- **Higher Load**: More strain on game servers
- **Slower Response**: Each bot waited for API response

### **After Implementation**
- **Single API Call**: Only English bot fetches data
- **Consistent Data**: All bots use identical game results
- **Reduced Load**: Less strain on game servers
- **Faster Response**: Other bots get data instantly from Redis

## 🔄 **Maintenance and Updates**

### **Regular Tasks**
- **Monitor Redis**: Check connection status and performance
- **Review Logs**: Analyze Redis hit/miss rates
- **Update Credentials**: Keep Redis authentication current
- **Performance Tuning**: Optimize timeout and retry settings

### **Troubleshooting**
- **Redis Issues**: Check connection and authentication
- **Data Staleness**: Verify update frequency
- **Performance**: Monitor response times and fallback rates
- **Errors**: Review error logs and fix issues

## 🎯 **Conclusion**

The Redis data sharing system provides a robust, efficient, and scalable solution for the FiveM Red/Green game bots. By centralizing data fetching in the English bot and sharing results through Redis, the system ensures:

- **Data Consistency**: All bots use identical game data
- **Efficiency**: Reduced API calls and server load
- **Reliability**: Graceful fallback when Redis is unavailable
- **Scalability**: Easy to add new language variants
- **Monitoring**: Clear visibility into system performance

This implementation creates a true "master-slave" architecture where the English bot serves as the data master, and all other language bots efficiently consume the shared data through Redis, resulting in a more robust and maintainable system.
