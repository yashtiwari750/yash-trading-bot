# src/limit_orders.py
# This module handles placing limit orders on Binance Futures Testnet.

from binance import Client
from binance.exceptions import BinanceAPIException
import math

from src.config import BINANCE_API_KEY, BINANCE_API_SECRET
from src.logger import logger
# We can reuse get_exchange_info from market_orders, demonstrating modularity.
from src.market_orders import get_exchange_info # Reusing for symbol info and filters

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

def validate_limit_order_inputs(symbol: str, side: str, quantity: float, price: float) -> bool:
    """
    Validates inputs for a limit order against Binance Futures exchange rules.
    Extends validation to include price against minPrice, maxPrice, and tickSize.
    """
    logger.info(f"VALIDATING inputs for Limit Order: Symbol={symbol}, Side={side}, Quantity={quantity}, Price={price}")

    # Reuse common validations from market orders (side, quantity, symbol info)
    # Note: get_exchange_info handles symbol existence and status
    symbol_info = get_exchange_info(symbol)
    if not symbol_info:
        logger.error(f"VALIDATION ERROR | Could not retrieve exchange info for symbol: {symbol}. Cannot validate limit order.")
        return False

    if symbol_info['status'] != 'TRADING':
        logger.error(f"VALIDATION ERROR | Symbol '{symbol}' is not currently tradable (status: {symbol_info['status']}).")
        return False

    if side not in ['BUY', 'SELL']:
        logger.error(f"VALIDATION ERROR | Invalid side: '{side}'. Must be 'BUY' or 'SELL'.")
        return False

    if quantity <= 0:
        logger.error(f"VALIDATION ERROR | Quantity must be positive. Received: {quantity}")
        return False

    if price <= 0:
        logger.error(f"VALIDATION ERROR | Price must be positive. Received: {price}")
        return False

    # --- Validate Quantity (re-using LOT_SIZE filter logic) ---
    min_qty = 0.0
    max_qty = float('inf')
    step_size = 0.0
    for f in symbol_info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            min_qty = float(f['minQty'])
            max_qty = float(f['maxQty'])
            step_size = float(f['stepSize'])
            break

    if step_size == 0.0 and min_qty == 0.0:
        logger.error(f"VALIDATION ERROR | Could not find LOT_SIZE filter for {symbol}. Cannot validate quantity.")
        return False

    if quantity < min_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is less than minimum allowed ({min_qty}) for {symbol}.")
        return False

    if quantity > max_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is greater than maximum allowed ({max_qty}) for {symbol}.")
        return False

    if step_size > 0 and math.fmod(quantity, step_size) > 1e-8 and abs(step_size - math.fmod(quantity, step_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is not a valid increment of stepSize ({step_size}) for {symbol}.")
        return False

    # --- Validate Price (using PRICE_FILTER logic) ---
    min_price = 0.0
    max_price = float('inf')
    tick_size = 0.0
    for f in symbol_info['filters']:
        if f['filterType'] == 'PRICE_FILTER':
            min_price = float(f['minPrice'])
            max_price = float(f['maxPrice'])
            tick_size = float(f['tickSize'])
            break

    if tick_size == 0.0 and min_price == 0.0:
        logger.error(f"VALIDATION ERROR | Could not find PRICE_FILTER for {symbol}. Cannot validate price.")
        return False

    if price < min_price:
        logger.error(f"VALIDATION ERROR | Price {price} is less than minimum allowed ({min_price}) for {symbol}.")
        return False

    if price > max_price:
        logger.error(f"VALIDATION ERROR | Price {price} is greater than maximum allowed ({max_price}) for {symbol}.")
        return False

    # Validate tick size: price must be an increment of tickSize
    # Similar to step_size, checking if remainder is close to zero.
    if tick_size > 0 and math.fmod(price, tick_size) > 1e-8 and abs(tick_size - math.fmod(price, tick_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Price {price} is not a valid increment of tickSize ({tick_size}) for {symbol}.")
        return False

    logger.info(f"VALIDATION SUCCESS | All inputs for Limit Order ({symbol} {side} {quantity} at {price}) are valid.")
    return True

def place_limit_order(symbol: str, side: str, quantity: float, price: float):
    """
    Places a limit order on Binance Futures Testnet.
    Includes comprehensive input validation, structured logging, and error handling.
    """
    logger.info(f"Attempting to place LIMIT order: {symbol} {side} {quantity} at {price}")

    # --- Step 1: Input Validation ---
    if not validate_limit_order_inputs(symbol, side, quantity, price):
        logger.error(f"ORDER FAILED | Limit order inputs for {symbol} {side} {quantity} at {price} failed validation. Order not placed.")
        return None

    try:
        # --- Step 2: Log the REQUEST ---
        request_params = f"symbol={symbol}, side={side}, type=LIMIT, quantity={quantity}, price={price}, timeInForce=GTC"
        logger.info(f"REQUEST | POST /fapi/v1/order | params: {request_params}")

        # --- Step 3: Place the Order (API Call) ---
        response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT', # Specifies this is a limit order.
            quantity=quantity,
            price=price,
            timeInForce='GTC' # Good Till Cancelled: order remains active until cancelled or filled.
                            # This is a common timeInForce for limit orders.
        )

        # --- Step 4: Log the RESPONSE ---
        order_id = response.get('orderId', 'N/A')
        status = response.get('status', 'N/A')
        executed_qty = response.get('executedQty', 'N/A')
        cummulative_quote_qty = response.get('cummulativeQuoteQty', 'N/A')

        logger.info(f"RESPONSE | orderId:{order_id} | status:{status} | executedQty:{executed_qty} | cummulativeQuoteQty:{cummulative_quote_qty}")
        logger.info(f"SUCCESS | LIMIT order placed for {symbol} {side} {quantity} at {price}. Order ID: {order_id}")
        return response

    except BinanceAPIException as e:
        # --- Step 5: Handle Binance API Specific Errors ---
        logger.error(f"ERROR | BinanceAPIException during LIMIT order placement: status_code={e.status_code}, message={e.message}")
        return None

    except Exception as e:
        # --- Step 6: Handle Any Other Unexpected Errors ---
        logger.error(f"ERROR | Unexpected error during LIMIT order placement: {e}")
        return None

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("\n--- Running Limit Order Module Tests ---")

    TEST_SYMBOL = "BTCUSDT"
    TEST_QUANTITY = 0.001

    # To test limit orders, we need a realistic price.
    # We'll fetch the current mark price and set our limit prices slightly away from it.
    current_mark_price = None
    try:
        # Fetch the current mark price for the symbol.
        mark_price_response = client.futures_mark_price(symbol=TEST_SYMBOL)
        current_mark_price = float(mark_price_response['markPrice'])
        print(f"Current Mark Price for {TEST_SYMBOL}: {current_mark_price}")
        # Adjust prices for testing: Buy slightly below, Sell slightly above.
        # We use math.floor/ceil and multiplication by tick_size to ensure the price adheres to tick size
        symbol_info = get_exchange_info(TEST_SYMBOL)
        tick_size = 0.0
        if symbol_info:
            for f in symbol_info['filters']:
                if f['filterType'] == 'PRICE_FILTER':
                    tick_size = float(f['tickSize'])
                    break

        if tick_size > 0:
            buy_price = math.floor((current_mark_price * 0.99) / tick_size) * tick_size # Set 1% below current
            sell_price = math.ceil((current_mark_price * 1.01) / tick_size) * tick_size # Set 1% above current
        else:
            buy_price = round(current_mark_price * 0.99, 2) # Fallback rounding if tick_size isn't found
            sell_price = round(current_mark_price * 1.01, 2)

        # Ensure price is formatted to correct precision (number of decimal places in tick_size)
        price_precision = 0
        if '.' in str(tick_size):
            price_precision = len(str(tick_size).split('.')[1])
        buy_price = round(buy_price, price_precision)
        sell_price = round(sell_price, price_precision)


    except Exception as e:
        logger.error(f"ERROR | Could not fetch current mark price for {TEST_SYMBOL}: {e}. Using fallback prices.")
        buy_price = 29000.00 # Fallback values if API call fails
        sell_price = 31000.00

    import time
    time.sleep(1) # Small delay before testing orders

    # --- Test 1: Valid Limit BUY Order ---
    print(f"\nAttempting valid Limit BUY order for {TEST_SYMBOL} with quantity {TEST_QUANTITY} at price {buy_price}")
    buy_response = place_limit_order(TEST_SYMBOL, "BUY", TEST_QUANTITY, buy_price)
    if buy_response:
        print(f"Limit BUY Order placed successfully! Order ID: {buy_response.get('orderId')}")
    else:
        print("Limit BUY Order failed.")

    time.sleep(2)

    # --- Test 2: Valid Limit SELL Order ---
    print(f"\nAttempting valid Limit SELL order for {TEST_SYMBOL} with quantity {TEST_QUANTITY} at price {sell_price}")
    sell_response = place_limit_order(TEST_SYMBOL, "SELL", TEST_QUANTITY, sell_price)
    if sell_response:
        print(f"Limit SELL Order placed successfully! Order ID: {sell_response.get('orderId')}")
    else:
        print("Limit SELL Order failed.")

    time.sleep(2)

    # --- Test 3: Invalid Price (too low) ---
    print("\nAttempting Limit BUY order with INVALID PRICE (too low)")
    place_limit_order(TEST_SYMBOL, "BUY", TEST_QUANTITY, 0.0000001)

    time.sleep(2)

    # --- Test 4: Invalid Quantity (not step size compliant) ---
    print("\nAttempting Limit SELL order with INVALID QUANTITY (not step size compliant, e.g., 0.0015)")
    place_limit_order(TEST_SYMBOL, "SELL", 0.0015, sell_price) # Assuming 0.001 is step size, this should fail

    time.sleep(2)

    # --- Test 5: Invalid Price (not tick size compliant) ---
    print("\nAttempting Limit BUY order with INVALID PRICE (not tick size compliant, e.g., 30000.005 if tick=0.01)")
    # This price needs to be carefully chosen based on the actual tick size of the symbol
    invalid_tick_price = buy_price + (tick_size / 2) if tick_size > 0 else 29500.005
    place_limit_order(TEST_SYMBOL, "BUY", TEST_QUANTITY, invalid_tick_price)