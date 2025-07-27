# src/config.py
import os # Provides a way to interact with the operating system, like reading environment variables.
from dotenv import load_dotenv # Used to load variables from our .env file.

# 1. Load environment variables from .env file:
# This line executes the function to load the API_KEY and API_SECRET that you put in your .env file.
load_dotenv()

# 2. Get API keys from environment variables:
# We use os.getenv() to safely retrieve the values.
# If the variables are not found (e.g., .env file is missing or variables are not named correctly),
# these will be `None`.
BINANCE_API_KEY = os.getenv('BINANCE_TESTNET_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_TESTNET_SECRET_KEY')

# 3. Define the Binance Testnet Base URL:
# This is a constant string for the API endpoint. Putting it here centralizes configuration.
BINANCE_TESTNET_BASE_URL = "https://testnet.binancefuture.com"

# 4. Critical check for loaded keys:
# This acts as a safeguard. If for some reason the API keys aren't loaded,
# we'll print an error and stop the program, preventing later failures.
if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    print("CRITICAL ERROR: Binance API keys not found in environment variables.")
    print("Please ensure BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_SECRET_KEY are set in your .env file.")
    exit(1) # exit(1) means the program is exiting with an error status.

print("Configuration loaded successfully from src/config.py.")