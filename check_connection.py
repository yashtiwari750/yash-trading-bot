#!/usr/bin/env python3
"""
Binance API Connection Test
This script tests the connection to Binance API and verifies API credentials.
"""

import os
import sys
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException

def test_connection():
    """Test connection to Binance API"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API credentials
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not secret_key:
            print("❌ Error: API credentials not found in .env file")
            print("Please add your BINANCE_API_KEY and BINANCE_SECRET_KEY to .env file")
            return False
        
        # Initialize client
        client = Client(api_key, secret_key)
        
        # Test connection by getting server time
        server_time = client.get_server_time()
        print(f"✅ Successfully connected to Binance API")
        print(f"Server time: {server_time}")
        
        # Test account info
        account_info = client.get_account()
        print(f"Account status: {account_info['status']}")
        
        return True
        
    except BinanceAPIException as e:
        print(f"❌ Binance API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Binance API connection...")
    success = test_connection()
    
    if success:
        print("\n🎉 Connection test passed! Your API credentials are working.")
    else:
        print("\n💥 Connection test failed! Please check your API credentials.")
        sys.exit(1) 