# src/advanced/stop_limit.py
# This module implements Stop-Limit orders for Binance Futures Testnet.

from binance import Client
from binance.exceptions import BinanceAPIException
import math

from src.config import BINANCE_API_KEY, BINANCE_API_SECRET
from src.logger import logger
from src.market_orders import get_exchange_info # Reusing for symbol info and filters

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

def validate_stop_limit_inputs(symbol: str, side: str, quantity: float, stop_price: float, limit_price: float) -> bool:
    """
    Validates inputs for a Stop-Limit order against Binance Futures exchange rules.
    Checks include:
    - Symbol, side, quantity validity (using existing logic).
    - Stop price and limit price validity against min/max/tickSize.
    - Logical relationship between stop price, limit price, and current market price.
    """
    logger.info(f"VALIDATING inputs for Stop-Limit Order: Symbol={symbol}, Side={side}, Quantity={quantity}, StopPrice={stop_price}, LimitPrice={limit_price}")

    symbol_info = get_exchange_info(symbol)
    if not symbol_info:
        logger.error(f"VALIDATION ERROR | Could not retrieve exchange info for symbol: {symbol}. Cannot validate Stop-Limit order.")
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

    if stop_price <= 0 or limit_price <= 0:
        logger.error(f"VALIDATION ERROR | Stop price and Limit price must be positive.")
        return False

    # --- Quantity Validation (re-using LOT_SIZE filter logic) ---
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
        logger.error(f"VALIDATION ERROR | Could not find LOT_SIZE filter for {symbol}. Cannot validate quantity for Stop-Limit.")
        return False

    if quantity < min_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is less than minimum allowed ({min_qty}) for {symbol} (Stop-Limit).")
        return False

    if quantity > max_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is greater than maximum allowed ({max_qty}) for {symbol} (Stop-Limit).")
        return False

    if step_size > 0 and math.fmod(quantity, step_size) > 1e-8 and abs(step_size - math.fmod(quantity, step_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is not a valid increment of stepSize ({step_size}) for {symbol} (Stop-Limit).")
        return False

    # --- Price Validation (re-using PRICE_FILTER logic) ---
    min_price_filter = 0.0
    max_price_filter = float('inf')
    tick_size = 0.0
    for f in symbol_info['filters']:
        if f['filterType'] == 'PRICE_FILTER':
            min_price_filter = float(f['minPrice'])
            max_price_filter = float(f['maxPrice'])
            tick_size = float(f['tickSize'])
            break

    if tick_size == 0.0 and min_price_filter == 0.0:
        logger.error(f"VALIDATION ERROR | Could not find PRICE_FILTER for {symbol}. Cannot validate Stop-Limit prices.")
        return False

    # Validate stop_price and limit_price against min/max price filter and tickSize.
    for price_val, price_name in [(stop_price, "Stop Price"), (limit_price, "Limit Price")]:
        if price_val < min_price_filter:
            logger.error(f"VALIDATION ERROR | {price_name} {price_val} is less than minimum allowed ({min_price_filter}) for {symbol}.")
            return False
        if price_val > max_price_filter:
            logger.error(f"VALIDATION ERROR | {price_name} {price_val} is greater than maximum allowed ({max_price_filter}) for {symbol}.")
            return False
        if tick_size > 0 and math.fmod(price_val, tick_size) > 1e-8 and abs(tick_size - math.fmod(price_val, tick_size)) > 1e-8:
            logger.error(f"VALIDATION ERROR | {price_name} {price_val} is not a valid increment of tickSize ({tick_size}) for {symbol}.")
            return False

    # --- Logical Price Validation for Stop-Limit ---
    # Get current mark price for logical checks.
    current_mark_price = None
    try:
        mark_price_response = client.futures_mark_price(symbol=symbol)
        current_mark_price = float(mark_price_response['markPrice'])
        logger.info(f"DEBUG | Current Mark Price for Stop-Limit validation: {current_mark_price}")
    except Exception as e:
        logger.error(f"ERROR | Could not fetch current mark price for Stop-Limit validation: {e}. Cannot perform logical price checks.")
        current_mark_price = None # Cannot perform this specific check without current price.

    if current_mark_price:
        if side == 'BUY': # For a BUY Stop-Limit order
            # Stop price must be GREATER than current mark price
            if stop_price < current_mark_price:
                logger.error(f"VALIDATION ERROR | For BUY Stop-Limit, Stop Price ({stop_price}) must be GREATER than current Mark Price ({current_mark_price}).")
                return False
            # Limit price must be >= stop price (for positive slippage) or can be slightly lower but > current
            if limit_price < stop_price: # Or often limit_price <= stop_price for typical stop-limit.
                                        # Binance allows limit < stop for BUY, but usually it's > or = for "better" fill.
                                        # Let's enforce limit_price >= stop_price for safety unless specific strategy.
                                        # For now, let's keep it simple with limit_price >= stop_price.
                logger.error(f"VALIDATION ERROR | For BUY Stop-Limit, Limit Price ({limit_price}) must be GREATER THAN or EQUAL TO Stop Price ({stop_price}).")
                return False
        elif side == 'SELL': # For a SELL Stop-Limit order
            # Stop price must be LESS than current mark price
            if stop_price > current_mark_price:
                logger.error(f"VALIDATION ERROR | For SELL Stop-Limit, Stop Price ({stop_price}) must be LESS than current Mark Price ({current_mark_price}).")
                return False
            # Limit price must be <= stop price (for positive slippage) or can be slightly higher but < current
            if limit_price > stop_price: # Or often limit_price <= stop_price for typical stop-limit.
                                        # Binance allows limit > stop for SELL, but usually it's < or = for "better" fill.
                                        # Let's enforce limit_price <= stop_price.
                logger.error(f"VALIDATION ERROR | For SELL Stop-Limit, Limit Price ({limit_price}) must be LESS THAN or EQUAL TO Stop Price ({stop_price}).")
                return False
    else:
        logger.warning("WARNING | Could not perform logical price validation for Stop-Limit due to missing current mark price.")


    logger.info(f"VALIDATION SUCCESS | All inputs for Stop-Limit Order ({symbol} {side} {quantity} at {limit_price} with stop {stop_price}) are valid.")
    return True

def place_stop_limit_order(symbol: str, side: str, quantity: float, stop_price: float, limit_price: float):
    """
    Places a Stop-Limit order on Binance Futures Testnet.
    This order type triggers a limit order when the market price reaches the stop price.
    """
    logger.info(f"Attempting to place STOP_LIMIT order: {symbol} {side} {quantity} at LimitPrice={limit_price} with StopPrice={stop_price}")

    # --- Step 1: Input Validation ---
    if not validate_stop_limit_inputs(symbol, side, quantity, stop_price, limit_price):
        logger.error(f"STOP_LIMIT ORDER FAILED | Inputs for {symbol} failed validation. Order not placed.")
        return None

    try:
        # --- Step 2: Log the REQUEST ---
        request_params = f"symbol={symbol}, side={side}, type=STOP, quantity={quantity}, price={limit_price}, stopPrice={stop_price}, timeInForce=GTC"
        logger.info(f"REQUEST | POST /fapi/v1/order | params: {request_params}")

        # --- Step 3: Place the Order (API Call) ---
        response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='STOP', # 'STOP' type is used for Stop-Limit orders on Binance Futures
            quantity=quantity,
            price=limit_price, # The limit price for the triggered order
            stopPrice=stop_price, # The trigger price for the stop order
            timeInForce='GTC' # Good Till Cancelled for the limit order component
        )

        # --- Step 4: Log the RESPONSE ---
        order_id = response.get('orderId', 'N/A')
        status = response.get('status', 'N/A')

        logger.info(f"RESPONSE | Stop-Limit Order: orderId:{order_id}, status:{status}")
        logger.info(f"SUCCESS | Stop-Limit order placed for {symbol} {side} {quantity} at {limit_price} with stop {stop_price}. Order ID: {order_id}")
        return response

    except BinanceAPIException as e:
        logger.error(f"ERROR | BinanceAPIException during Stop-Limit order placement: status_code={e.status_code}, message={e.message}")
        return None
    except Exception as e:
        logger.error(f"ERROR | Unexpected error during Stop-Limit order placement: {e}")
        return None

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("\n--- Running Stop-Limit Order Module Tests ---")

    TEST_SYMBOL = "BTCUSDT"
    TEST_QUANTITY = 0.001

    current_mark_price = None
    try:
        mark_price_response = client.futures_mark_price(symbol=TEST_SYMBOL)
        current_mark_price = float(mark_price_response['markPrice'])
        print(f"Current Mark Price for {TEST_SYMBOL}: {current_mark_price}")
    except Exception as e:
        logger.error(f"ERROR | Could not fetch current mark price for Stop-Limit test: {e}. Using fallback price.")
        current_mark_price = 30000.0 # Fallback

    symbol_info = get_exchange_info(TEST_SYMBOL)
    tick_size = 0.1 # Default, will be updated from exchangeInfo
    if symbol_info:
        for f in symbol_info['filters']:
            if f['filterType'] == 'PRICE_FILTER':
                tick_size = float(f['tickSize'])
                break
    price_precision = len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0

    import time
    time.sleep(1)

    # --- Test 1: Valid BUY Stop-Limit Order (e.g., for breaking out of resistance) ---
    # Stop price > Current price. Limit price >= Stop price.
    buy_stop_price = round(current_mark_price * 1.005, price_precision) # 0.5% above current
    buy_limit_price = round(current_mark_price * 1.006, price_precision) # slightly above stop price
    if buy_limit_price < buy_stop_price: # Ensure limit price is not below stop price
        buy_limit_price = buy_stop_price + tick_size

    print(f"\nAttempting valid BUY Stop-Limit: Qty={TEST_QUANTITY}, Stop={buy_stop_price}, Limit={buy_limit_price}")
    buy_response = place_stop_limit_order(TEST_SYMBOL, "BUY", TEST_QUANTITY, buy_stop_price, buy_limit_price)
    if buy_response:
        print(f"BUY Stop-Limit Order placed successfully! Order ID: {buy_response.get('orderId')}")
    else:
        print("BUY Stop-Limit Order failed.")

    time.sleep(2)

    # --- Test 2: Valid SELL Stop-Limit Order (e.g., for breaking below support) ---
    # Stop price < Current price. Limit price <= Stop price.
    sell_stop_price = round(current_mark_price * 0.995, price_precision) # 0.5% below current
    sell_limit_price = round(current_mark_price * 0.994, price_precision) # slightly below stop price
    if sell_limit_price > sell_stop_price: # Ensure limit price is not above stop price
        sell_limit_price = sell_stop_price - tick_size

    print(f"\nAttempting valid SELL Stop-Limit: Qty={TEST_QUANTITY}, Stop={sell_stop_price}, Limit={sell_limit_price}")
    sell_response = place_stop_limit_order(TEST_SYMBOL, "SELL", TEST_QUANTITY, sell_stop_price, sell_limit_price)
    if sell_response:
        print(f"SELL Stop-Limit Order placed successfully! Order ID: {sell_response.get('orderId')}")
    else:
        print("SELL Stop-Limit Order failed.")

    time.sleep(2)

    # --- Test 3: Invalid BUY Stop-Limit (Stop Price < Current Price) ---
    print("\nAttempting BUY Stop-Limit with INVALID Stop Price (less than current market)")
    invalid_buy_stop = round(current_mark_price * 0.99, price_precision)
    place_stop_limit_order(TEST_SYMBOL, "BUY", TEST_QUANTITY, invalid_buy_stop, invalid_buy_stop + tick_size)

    time.sleep(2)

    # --- Test 4: Invalid SELL Stop-Limit (Limit Price > Stop Price) ---
    print("\nAttempting SELL Stop-Limit with INVALID Limit Price (greater than Stop Price)")
    invalid_sell_limit = round(sell_stop_price + tick_size, price_precision)
    place_stop_limit_order(TEST_SYMBOL, "SELL", TEST_QUANTITY, sell_stop_price, invalid_sell_limit)