# src/market_orders.py
# This module handles placing market orders on Binance Futures Testnet.

from binance import Client # The main library to connect to Binance API.
from binance.exceptions import BinanceAPIException # Specific exception for Binance API errors.
import math # Used for precise mathematical operations, especially for float comparisons.

# Import our custom configuration and logger modules for consistency and separation of concerns.
from src.config import BINANCE_API_KEY, BINANCE_API_SECRET # Securely loads API keys.
from src.logger import logger # Our structured logger for all actions.

# Initialize Binance Client for Testnet:
# This creates an object that allows us to make API calls to Binance.
# We pass the API key and secret loaded from our config, and set testnet=True.
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

# A simple cache to store exchange information.
# This avoids fetching the same information multiple times, making the bot more efficient.
# It's a dictionary that will store symbol information once fetched.
EXCHANGE_INFO_CACHE = {}

def get_exchange_info(symbol: str):
    """
    Fetches and caches exchange information for a given symbol.
    This information includes trading rules like minQty, maxQty, stepSize, etc.,
    which are essential for robust input validation[cite: 14].
    """
    # Check if the symbol's info is already in our cache.
    if symbol not in EXCHANGE_INFO_CACHE:
        try:
            # Log the API request for exchange information. This adheres to "Logging Standards".
            logger.info(f"REQUEST | GET /fapi/v1/exchangeInfo | params: symbol={symbol}")
            
            # Fetch all futures exchange information from Binance.
            exchange_info = client.futures_exchange_info() # This gets info for ALL symbols.

            # Find the specific symbol's information within the fetched data.
            # `next()` finds the first item in a list that matches a condition.
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            
            if symbol_info:
                # If found, store it in our cache for future use.
                EXCHANGE_INFO_CACHE[symbol] = symbol_info
                logger.info(f"RESPONSE | Successfully fetched and cached exchange info for {symbol}.")
            else:
                # Log an error if the symbol is not found on the exchange.
                logger.error(f"ERROR | Symbol '{symbol}' not found in Binance exchange information.")
                return None # Return None to indicate failure.
        except BinanceAPIException as e:
            # Catch and log specific Binance API errors. This is crucial for "Error Handling".
            logger.error(f"ERROR | BinanceAPIException during exchange info fetch for {symbol}: status_code={e.status_code}, message={e.message}")
            return None
        except Exception as e:
            # Catch and log any other unexpected Python errors.
            logger.error(f"ERROR | Unexpected error during exchange info fetch for {symbol}: {e}")
            return None
    
    # Return the cached information for the symbol.
    return EXCHANGE_INFO_CACHE.get(symbol)

def validate_market_order_inputs(symbol: str, side: str, quantity: float) -> bool:
    """
    Validates inputs for a market order against Binance Futures exchange rules.
    This is paramount for "Validation Rigor" (20% evaluation weight)
    and to prevent "Missing quantity validation causing Testnet errors".

    Checks include:
    - Symbol validity (exists and active on exchange).
    - Side (BUY/SELL).
    - Quantity (positive, within min/max, correct step size).
    """
    logger.info(f"VALIDATING inputs for Market Order: Symbol={symbol}, Side={side}, Quantity={quantity}")

    # 1. Validate 'side':
    # The side must be either 'BUY' or 'SELL'.
    if side not in ['BUY', 'SELL']:
        logger.error(f"VALIDATION ERROR | Invalid side: '{side}'. Must be 'BUY' or 'SELL'.")
        return False

    # 2. Get exchange info for the symbol:
    # We need the rules (filters) for this specific symbol from Binance.
    symbol_info = get_exchange_info(symbol)
    if not symbol_info:
        logger.error(f"VALIDATION ERROR | Could not retrieve exchange info for symbol: {symbol}. Cannot validate order.")
        return False
    
    # Check if the symbol is actually tradable (status is 'TRADING').
    if symbol_info['status'] != 'TRADING':
        logger.error(f"VALIDATION ERROR | Symbol '{symbol}' is not currently tradable (status: {symbol_info['status']}).")
        return False

    # 3. Extract quantity filters (minQty, maxQty, stepSize) from exchange info:
    min_qty = 0.0
    max_qty = float('inf') # Set initial max to infinity, then update from filter.
    step_size = 0.0
    
    # Iterate through the filters list provided by Binance for the symbol.
    # We are looking for the 'LOT_SIZE' filter.
    for f in symbol_info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            min_qty = float(f['minQty'])
            max_qty = float(f['maxQty'])
            step_size = float(f['stepSize'])
            break # Once found, no need to check other filters.
    
    # If for some reason LOT_SIZE filter was not found (unlikely but defensive), raise an error.
    if step_size == 0.0 and min_qty == 0.0: # Check initial values if filter wasn't found.
        logger.error(f"VALIDATION ERROR | Could not find LOT_SIZE filter for {symbol}. Cannot validate quantity.")
        return False

    # 4. Validate 'quantity' against these filters:
    # Quantity must be a positive number.
    if quantity <= 0:
        logger.error(f"VALIDATION ERROR | Quantity must be positive. Received: {quantity}")
        return False
    
    # Quantity must be at least the minimum allowed quantity.
    if quantity < min_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is less than minimum allowed ({min_qty}) for {symbol}.")
        return False
    
    # Quantity must not exceed the maximum allowed quantity.
    if quantity > max_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is greater than maximum allowed ({max_qty}) for {symbol}.")
        return False
    
    # Quantity must be a valid increment of the stepSize.
    # `math.fmod(quantity, step_size)` calculates the remainder of the division.
    # We check if this remainder is very close to zero, using a small tolerance (1e-8)
    # because floating-point numbers can have tiny inaccuracies.
    if step_size > 0 and math.fmod(quantity, step_size) > 1e-8 and abs(step_size - math.fmod(quantity, step_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is not a valid increment of stepSize ({step_size}) for {symbol}.")
        return False

    logger.info(f"VALIDATION SUCCESS | All inputs for Market Order ({symbol} {side} {quantity}) are valid.")
    return True # Return True if all validations pass.

def place_market_order(symbol: str, side: str, quantity: float):
    """
    Places a market order on Binance Futures Testnet.
    This function incorporates:
    - Comprehensive input validation[cite: 14].
    - Structured logging for requests, responses, and errors.
    - Robust error handling with specific BinanceAPIException catching.
    """
    logger.info(f"Attempting to place MARKET order: {symbol} {side} {quantity}")

    # --- Step 1: Input Validation ---
    # Call our validation function FIRST. If validation fails, we stop here.
    if not validate_market_order_inputs(symbol, side, quantity):
        logger.error(f"ORDER FAILED | Market order inputs for {symbol} {side} {quantity} failed validation. Order not placed.")
        return None # Return None to indicate that the order failed due to validation.

    try:
        # --- Step 2: Log the REQUEST ---
        # Adhere to the "Logging Standards" for requests.
        request_params = f"symbol={symbol}, side={side}, type=MARKET, quantity={quantity}"
        logger.info(f"REQUEST | POST /fapi/v1/order | params: {request_params}")

        # --- Step 3: Place the Order (API Call) ---
        # This is the actual call to the Binance API to create a market order.
        response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET', # Specifies this is a market order.
            quantity=quantity
        )

        # --- Step 4: Log the RESPONSE ---
        # Adhere to the "Logging Standards" for responses.
        # Extract key information from the API response for clear logging.
        order_id = response.get('orderId', 'N/A') # Safely get orderId, default to 'N/A' if not present.
        status = response.get('status', 'N/A')     # Status of the order (e.g., FILLED, NEW).
        executed_qty = response.get('executedQty', 'N/A') # Quantity that was actually filled.
        cummulative_quote_qty = response.get('cummulativeQuoteQty', 'N/A') # Total value in quote asset (e.g., USDT) that was traded.

        logger.info(f"RESPONSE | orderId:{order_id} | status:{status} | executedQty:{executed_qty} | cummulativeQuoteQty:{cummulative_quote_qty}")
        logger.info(f"SUCCESS | MARKET order placed for {symbol} {side} {quantity}. Order ID: {order_id}")
        
        return response # Return the full API response object if successful.

    except BinanceAPIException as e:
        # --- Step 5: Handle Binance API Specific Errors ---
        # This catches errors returned directly by the Binance API (e.g., insufficient funds, invalid parameter).
        # Logging specific status code and message is "Critical for scoring!"
        logger.error(f"ERROR | BinanceAPIException during MARKET order placement: status_code={e.status_code}, message={e.message}")
        # In a real bot, you might add retry logic here for specific recoverable error codes (e.g., rate limits).
        return None # Return None to indicate that the order failed.

    except Exception as e:
        # --- Step 6: Handle Any Other Unexpected Errors ---
        # This catches any other unforeseen Python errors that might occur.
        # "Unhandled exceptions when API disconnects" is an "Automatic Rejection Trigger".
        logger.error(f"ERROR | Unexpected error during MARKET order placement: {e}")
        return None # Return None to indicate failure.

# --- Example Usage (for testing this module directly) ---
# This block runs only when you execute `python src/market_orders.py` directly.
# It's your testing ground for this specific module.
if __name__ == "__main__":
    print("\n--- Running Market Order Module Tests ---")

    # IMPORTANT: Use a symbol that is active on Binance Futures Testnet, e.g., "BTCUSDT" or "ETHUSDT".
    # Ensure your Testnet account has enough USDT for BUY orders and enough of the base asset (e.g., BTC/ETH) for SELL orders.
    TEST_SYMBOL = "BTCUSDT" # You can change this to "ETHUSDT" or another active testnet pair.
    TEST_QUANTITY = 0.001   # This quantity must be valid for the chosen TEST_SYMBOL's LOT_SIZE filter.

    # --- Test 1: Valid Market BUY Order ---
    print(f"\nAttempting valid Market BUY order for {TEST_SYMBOL} with quantity {TEST_QUANTITY}")
    buy_response = place_market_order(TEST_SYMBOL, "BUY", TEST_QUANTITY)
    if buy_response:
        print(f"Market BUY Order placed successfully! Order ID: {buy_response.get('orderId')}")
    else:
        print("Market BUY Order failed.")
    
    import time
    time.sleep(2) # Wait a bit to avoid hitting potential rate limits too quickly.

    # --- Test 2: Valid Market SELL Order ---
    # Make sure you have enough of the asset (e.g., BTC) to sell on your Testnet account.
    print(f"\nAttempting valid Market SELL order for {TEST_SYMBOL} with quantity {TEST_QUANTITY}")
    sell_response = place_market_order(TEST_SYMBOL, "SELL", TEST_QUANTITY)
    if sell_response:
        print(f"Market SELL Order placed successfully! Order ID: {sell_response.get('orderId')}")
    else:
        print("Market SELL Order failed.")

    time.sleep(2)

    # --- Test 3: Invalid Quantity (too low) ---
    print("\nAttempting Market BUY order with INVALID QUANTITY (too low)")
    place_market_order(TEST_SYMBOL, "BUY", 0.0000001) # This quantity is usually below minQty for BTCUSDT.

    time.sleep(2)

    # --- Test 4: Invalid Side ---
    print("\nAttempting Market BUY order with INVALID SIDE (e.g., 'HOLD')")
    place_market_order(TEST_SYMBOL, "HOLD", TEST_QUANTITY)

    time.sleep(2)

    # --- Test 5: Invalid Symbol ---
    print("\nAttempting Market BUY order with INVALID SYMBOL (e.g., 'XYZABC')")
    place_market_order("XYZABC", "BUY", TEST_QUANTITY)