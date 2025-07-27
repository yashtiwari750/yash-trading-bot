# src/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
BINANCE_API_KEY = os.getenv('BINANCE_TESTNET_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_TESTNET_SECRET_KEY')

# Base URL for the Binance Futures Testnet API
BINANCE_TESTNET_BASE_URL = "https://testnet.binancefuture.com"

# Check if API keys are loaded.
if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    print("CRITICAL ERROR: Binance API keys not found in environment variables.")
    print("Please ensure BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_SECRET_KEY are set in your .env file.")
    exit(1)

print("Configuration loaded successfully from src/config.py.")