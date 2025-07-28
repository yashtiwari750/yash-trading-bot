# src/advanced/oco.py
# This module implements OCO-like functionality for Binance Futures Testnet,
# placing a Stop-Loss (STOP_MARKET) and a Take-Profit (TAKE_PROFIT_MARKET) order.

from binance import Client
from binance.exceptions import BinanceAPIException
import math

from src.config import BINANCE_API_KEY, BINANCE_API_SECRET
from src.logger import logger
from src.market_orders import get_exchange_info # Reusing for symbol info and filters

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

def validate_oco_inputs(symbol: str, side: str, quantity: float, stop_price: float, take_profit_price: float) -> bool:
    """
    Validates inputs for OCO-like orders (Stop-Loss and Take-Profit) against Binance Futures exchange rules.
    - 'side' here refers to the side of the order to *close* the position (opposite of entry).
    - Prices are validated against PRICE_FILTER (min, max, tickSize).
    - Quantity is validated against LOT_SIZE filter.
    - Stop/Take Profit prices must make logical sense relative to each other and current market.
    """
    logger.info(f"VALIDATING inputs for OCO (Stop-Loss/Take-Profit): Symbol={symbol}, Side={side}, Quantity={quantity}, StopPrice={stop_price}, TakeProfitPrice={take_profit_price}")

    symbol_info = get_exchange_info(symbol)
    if not symbol_info:
        logger.error(f"VALIDATION ERROR | Could not retrieve exchange info for symbol: {symbol}. Cannot validate OCO orders.")
        return False

    if symbol_info['status'] != 'TRADING':
        logger.error(f"VALIDATION ERROR | Symbol '{symbol}' is not currently tradable (status: {symbol_info['status']}).")
        return False

    # 'side' for these orders is the side to *close* a position.
    # If your initial position was BUY, your SL/TP would be SELL. If initial was SELL, SL/TP would be BUY.
    if side not in ['BUY', 'SELL']:
        logger.error(f"VALIDATION ERROR | Invalid side: '{side}'. Must be 'BUY' or 'SELL'. (This is the closing side)")
        return False

    if quantity <= 0:
        logger.error(f"VALIDATION ERROR | Quantity must be positive. Received: {quantity}")
        return False

    if stop_price <= 0 or take_profit_price <= 0:
        logger.error(f"VALIDATION ERROR | Stop price and Take Profit price must be positive.")
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
        logger.error(f"VALIDATION ERROR | Could not find LOT_SIZE filter for {symbol}. Cannot validate quantity for OCO.")
        return False

    if quantity < min_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is less than minimum allowed ({min_qty}) for {symbol} (OCO).")
        return False

    if quantity > max_qty:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is greater than maximum allowed ({max_qty}) for {symbol} (OCO).")
        return False

    if step_size > 0 and math.fmod(quantity, step_size) > 1e-8 and abs(step_size - math.fmod(quantity, step_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Quantity {quantity} is not a valid increment of stepSize ({step_size}) for {symbol} (OCO).")
        return False

    # --- Price Validation (re-using PRICE_FILTER logic) ---
    min_price_filter = 0.0 # Renamed to avoid conflict with function param 'min_price' if exists
    max_price_filter = float('inf')
    tick_size = 0.0
    for f in symbol_info['filters']:
        if f['filterType'] == 'PRICE_FILTER':
            min_price_filter = float(f['minPrice'])
            max_price_filter = float(f['maxPrice'])
            tick_size = float(f['tickSize'])
            break

    if tick_size == 0.0 and min_price_filter == 0.0:
        logger.error(f"VALIDATION ERROR | Could not find PRICE_FILTER for {symbol}. Cannot validate OCO prices.")
        return False

    # Validate stop_price and take_profit_price against min/max price filter and tickSize.
    for price_val, price_name in [(stop_price, "Stop Price"), (take_profit_price, "Take Profit Price")]:
        if price_val < min_price_filter:
            logger.error(f"VALIDATION ERROR | {price_name} {price_val} is less than minimum allowed ({min_price_filter}) for {symbol}.")
            return False
        if price_val > max_price_filter:
            logger.error(f"VALIDATION ERROR | {price_name} {price_val} is greater than maximum allowed ({max_price_filter}) for {symbol}.")
            return False
        if tick_size > 0 and math.fmod(price_val, tick_size) > 1e-8 and abs(tick_size - math.fmod(price_val, tick_size)) > 1e-8:
            logger.error(f"VALIDATION ERROR | {price_name} {price_val} is not a valid increment of tickSize ({tick_size}) for {symbol}.")
            return False

    # --- Logical Price Validation for OCO ---
    # Get current mark price to ensure logical order placement relative to current market.
    current_mark_price = None
    try:
        mark_price_response = client.futures_mark_price(symbol=symbol)
        current_mark_price = float(mark_price_response['markPrice'])
        logger.info(f"DEBUG | Current Mark Price for OCO validation: {current_mark_price}")
    except Exception as e:
        logger.error(f"ERROR | Could not fetch current mark price for OCO validation: {e}. Cannot perform logical price checks.")
        # We can't do the logical checks without current price, but we'll still pass if other validations are okay.
        # In a production bot, you'd likely fail here or use a stale price.
        current_mark_price = None

    if current_mark_price:
        if side == 'BUY': # If we are placing BUY orders (to close a SELL position)
            if stop_price > current_mark_price:
                logger.error(f"VALIDATION ERROR | For BUY (closing SELL) OCO, Stop Price ({stop_price}) must be less than current Mark Price ({current_mark_price}).")
                return False
            if take_profit_price < current_mark_price:
                logger.error(f"VALIDATION ERROR | For BUY (closing SELL) OCO, Take Profit Price ({take_profit_price}) must be greater than current Mark Price ({current_mark_price}).")
                return False
        elif side == 'SELL': # If we are placing SELL orders (to close a BUY position)
            if stop_price < current_mark_price:
                logger.error(f"VALIDATION ERROR | For SELL (closing BUY) OCO, Stop Price ({stop_price}) must be greater than current Mark Price ({current_mark_price}).")
                return False
            if take_profit_price > current_mark_price:
                logger.error(f"VALIDATION ERROR | For SELL (closing BUY) OCO, Take Profit Price ({take_profit_price}) must be less than current Mark Price ({current_mark_price}).")
                return False
    else:
        logger.warning("WARNING | Could not perform logical price validation for OCO due to missing current mark price.")


    logger.info(f"VALIDATION SUCCESS | All inputs for OCO (Stop-Loss/Take-Profit) are valid.")
    return True

def place_oco_orders(symbol: str, side: str, quantity: float, stop_price: float, take_profit_price: float):
    """
    Places OCO-like orders on Binance Futures Testnet.
    This involves placing a STOP_MARKET order (for stop-loss)
    and a TAKE_PROFIT_MARKET order (for take-profit) simultaneously.
    The 'side' determines if these orders are to close a BUY or SELL position.
    """
    logger.info(f"Attempting to place OCO (Stop-Loss/Take-Profit) orders for: {symbol} {side} {quantity}, SL at {stop_price}, TP at {take_profit_price}")

    # --- Step 1: Input Validation ---
    if not validate_oco_inputs(symbol, side, quantity, stop_price, take_profit_price):
        logger.error(f"OCO ORDER FAILED | Inputs for {symbol} failed validation. Orders not placed.")
        return None # Return None to indicate failure

    order_responses = [] # To store responses of both orders.

    try:
        # --- Place Stop-Loss Order (STOP_MARKET) ---
        # STOP_MARKET requires 'stopPrice'. It triggers a market order when 'stopPrice' is reached.
        stop_loss_request_params = f"symbol={symbol}, side={side}, type=STOP_MARKET, quantity={quantity}, stopPrice={stop_price}, closePosition=False"
        logger.info(f"REQUEST | POST /fapi/v1/order (Stop-Loss) | params: {stop_loss_request_params}")

        stop_loss_response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='STOP_MARKET',
            quantity=quantity,
            stopPrice=stop_price, # The price at which the stop market order becomes active.
            closePosition=False # False because we define quantity, not closing all.
        )
        order_responses.append(stop_loss_response)
        logger.info(f"RESPONSE | Stop-Loss Order: orderId:{stop_loss_response.get('orderId', 'N/A')}, status:{stop_loss_response.get('status', 'N/A')}")
        logger.info(f"SUCCESS | Stop-Loss order placed for {symbol} {side} {quantity} at {stop_price}. Order ID: {stop_loss_response.get('orderId')}")

    except BinanceAPIException as e:
        logger.error(f"ERROR | BinanceAPIException during Stop-Loss order placement: status_code={e.status_code}, message={e.message}")
        return None # Fail early if Stop-Loss fails.
    except Exception as e:
        logger.error(f"ERROR | Unexpected error during Stop-Loss order placement: {e}")
        return None # Fail early if Stop-Loss fails.

    try:
        # --- Place Take-Profit Order (TAKE_PROFIT_MARKET) ---
        # TAKE_PROFIT_MARKET also requires 'stopPrice' (which acts as trigger price for TP).
        take_profit_request_params = f"symbol={symbol}, side={side}, type=TAKE_PROFIT_MARKET, quantity={quantity}, stopPrice={take_profit_price}, closePosition=False"
        logger.info(f"REQUEST | POST /fapi/v1/order (Take-Profit) | params: {take_profit_request_params}")

        take_profit_response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='TAKE_PROFIT_MARKET',
            quantity=quantity,
            stopPrice=take_profit_price, # The price at which the take profit market order becomes active.
            closePosition=False
        )
        order_responses.append(take_profit_response)
        logger.info(f"RESPONSE | Take-Profit Order: orderId:{take_profit_response.get('orderId', 'N/A')}, status:{take_profit_response.get('status', 'N/A')}")
        logger.info(f"SUCCESS | Take-Profit order placed for {symbol} {side} {quantity} at {take_profit_price}. Order ID: {take_profit_response.get('orderId')}")

    except BinanceAPIException as e:
        logger.error(f"ERROR | BinanceAPIException during Take-Profit order placement: status_code={e.status_code}, message={e.message}")
        # Log the failure but don't re-raise if Stop-Loss succeeded.
        # However, for hiring task simplicity, we'll return None if either fails after validation.
        return None
    except Exception as e:
        logger.error(f"ERROR | Unexpected error during Take-Profit order placement: {e}")
        return None

    logger.info(f"OCO-like orders (Stop-Loss and Take-Profit) placed successfully for {symbol}.")
    return order_responses # Return both responses if successful.

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("\n--- Running OCO Order Module Tests ---")

    TEST_SYMBOL = "BTCUSDT"
    TEST_QUANTITY = 0.001

    # Fetch current mark price to set logical stop/take profit prices
    current_mark_price = None
    try:
        mark_price_response = client.futures_mark_price(symbol=TEST_SYMBOL)
        current_mark_price = float(mark_price_response['markPrice'])
        print(f"Current Mark Price for {TEST_SYMBOL}: {current_mark_price}")
    except Exception as e:
        logger.error(f"ERROR | Could not fetch current mark price for OCO test: {e}. Cannot perform logical price checks.")
        current_mark_price = 30000.0 # Fallback placeholder

    # Determine tick_size for accurate price calculation
    symbol_info = get_exchange_info(TEST_SYMBOL)
    tick_size = 0.1 # Default for BTCUSDT Futures, will be updated from exchangeInfo
    if symbol_info:
        for f in symbol_info['filters']:
            if f['filterType'] == 'PRICE_FILTER':
                tick_size = float(f['tickSize'])
                break

    # Define prices relative to current mark price based on side
    # For a simulated BUY position (we want to SELL to close)
    # Stop-loss would be BELOW current price, Take-profit ABOVE current price
    sell_sl_price = round(current_mark_price * 0.99, len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0)
    sell_tp_price = round(current_mark_price * 1.01, len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0)

    # For a simulated SELL position (we want to BUY to close)
    # Stop-loss would be ABOVE current price, Take-profit BELOW current price
    buy_sl_price = round(current_mark_price * 1.01, len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0)
    buy_tp_price = round(current_mark_price * 0.99, len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0)

    import time
    time.sleep(1)

    # --- Test 1: Place OCO (Stop-Loss and Take-Profit) for a simulated BUY position (closing with SELL) ---
    print(f"\nAttempting OCO for simulated BUY position (closing with SELL): SL at {sell_sl_price}, TP at {sell_tp_price}")
    oco_sell_response = place_oco_orders(TEST_SYMBOL, "SELL", TEST_QUANTITY, sell_sl_price, sell_tp_price)
    if oco_sell_response:
        print(f"OCO (Stop-Loss/Take-Profit) orders placed successfully for SELL side!")
        for res in oco_sell_response:
            print(f"  Order ID: {res.get('orderId')}, Type: {res.get('type')}, Status: {res.get('status')}")
    else:
        print("OCO (Stop-Loss/Take-Profit) orders for SELL side failed.")

    time.sleep(2)

    # --- Test 2: Place OCO (Stop-Loss and Take-Profit) for a simulated SELL position (closing with BUY) ---
    print(f"\nAttempting OCO for simulated SELL position (closing with BUY): SL at {buy_sl_price}, TP at {buy_tp_price}")
    oco_buy_response = place_oco_orders(TEST_SYMBOL, "BUY", TEST_QUANTITY, buy_sl_price, buy_tp_price)
    if oco_buy_response:
        print(f"OCO (Stop-Loss/Take-Profit) orders placed successfully for BUY side!")
        for res in oco_buy_response:
            print(f"  Order ID: {res.get('orderId')}, Type: {res.get('type')}, Status: {res.get('status')}")
    else:
        print("OCO (Stop-Loss/Take-Profit) orders for BUY side failed.")

    time.sleep(2)

    # --- Test 3: Invalid OCO (Stop Price too high for SELL position) ---
    print("\nAttempting OCO with INVALID STOP PRICE (too high for SELL position)")
    place_oco_orders(TEST_SYMBOL, "SELL", TEST_QUANTITY, current_mark_price * 1.1, sell_tp_price) # SL above market for SELL

    time.sleep(2)

    # --- Test 4: Invalid OCO (Quantity not step size compliant) ---
    print("\nAttempting OCO with INVALID QUANTITY (not step size compliant, e.g., 0.0015)")
    place_oco_orders(TEST_SYMBOL, "SELL", 0.0015, sell_sl_price, sell_tp_price)