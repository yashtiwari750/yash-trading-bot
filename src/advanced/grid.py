# src/advanced/grid.py
# This module implements a simplified Grid Trading strategy for Binance Futures Testnet.
# It focuses on placing the initial set of buy and sell limit orders within a defined price range.

from binance import Client
from binance.exceptions import BinanceAPIException
import math

from src.config import BINANCE_API_KEY, BINANCE_API_SECRET
from src.logger import logger
from src.market_orders import get_exchange_info # Reusing for symbol info and filters
from src.limit_orders import place_limit_order # Reusing our limit order function

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

def validate_grid_inputs(symbol: str, min_price: float, max_price: float, num_buy_orders: int, num_sell_orders: int, quantity_per_order: float) -> bool:
    """
    Validates inputs for a Grid order strategy.
    Checks for:
    - Symbol validity.
    - Logical price range (min_price < max_price).
    - Positive number of orders and quantity.
    - Price levels adhere to tickSize, and quantities adhere to stepSize.
    """
    logger.info(f"VALIDATING inputs for Grid Order: Symbol={symbol}, MinPrice={min_price}, MaxPrice={max_price}, BuyOrders={num_buy_orders}, SellOrders={num_sell_orders}, QtyPerOrder={quantity_per_order}")

    if min_price <= 0 or max_price <= 0 or min_price >= max_price:
        logger.error(f"VALIDATION ERROR | Invalid price range. min_price ({min_price}) must be positive and less than max_price ({max_price}).")
        return False

    if num_buy_orders <= 0 or num_sell_orders <= 0:
        logger.error(f"VALIDATION ERROR | Number of buy and sell orders must be positive.")
        return False

    if quantity_per_order <= 0:
        logger.error(f"VALIDATION ERROR | Quantity per order must be positive. Received: {quantity_per_order}")
        return False

    # Get exchange info for validation
    symbol_info = get_exchange_info(symbol)
    if not symbol_info:
        logger.error(f"VALIDATION ERROR | Could not retrieve exchange info for symbol: {symbol}. Cannot validate Grid order.")
        return False

    if symbol_info['status'] != 'TRADING':
        logger.error(f"VALIDATION ERROR | Symbol '{symbol}' is not currently tradable (status: {symbol_info['status']}).")
        return False

    # --- Extract filters ---
    min_qty = 0.0
    max_qty = float('inf')
    step_size = 0.0
    min_price_filter = 0.0
    max_price_filter = float('inf')
    tick_size = 0.0

    for f in symbol_info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            min_qty = float(f['minQty'])
            max_qty = float(f['maxQty'])
            step_size = float(f['stepSize'])
        elif f['filterType'] == 'PRICE_FILTER':
            min_price_filter = float(f['minPrice'])
            max_price_filter = float(f['maxPrice'])
            tick_size = float(f['tickSize'])

    if step_size == 0.0 or tick_size == 0.0:
        logger.error(f"VALIDATION ERROR | Could not find LOT_SIZE or PRICE_FILTER for {symbol}. Cannot validate Grid order.")
        return False

    # Validate quantity_per_order
    if quantity_per_order < min_qty:
        logger.error(f"VALIDATION ERROR | Quantity per order {quantity_per_order} is less than minimum allowed ({min_qty}) for {symbol}.")
        return False
    if quantity_per_order > max_qty:
        logger.error(f"VALIDATION ERROR | Quantity per order {quantity_per_order} is greater than maximum allowed ({max_qty}) for {symbol}.")
        return False
    if math.fmod(quantity_per_order, step_size) > 1e-8 and abs(step_size - math.fmod(quantity_per_order, step_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Quantity per order {quantity_per_order} is not a valid increment of stepSize ({step_size}) for {symbol}.")
        return False

    # Validate min_price and max_price against exchange's overall price filter
    if min_price < min_price_filter or max_price > max_price_filter:
        logger.error(f"VALIDATION ERROR | Grid range [{min_price}, {max_price}] is outside exchange's allowed price range [{min_price_filter}, {max_price_filter}] for {symbol}.")
        return False

    # --- Validate Grid Spacing & Price Adherence to Tick Size ---
    # Calculate price precision
    price_precision = len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0

    # Attempt to calculate grid levels and validate them
    try:
        # For simplicity, we'll aim for even spacing from min_price to max_price
        # Central price can be used to set buy/sell divergence

        # Buy orders go from min_price up towards the midpoint
        if num_buy_orders > 1:
            buy_price_step = (max_price - min_price) / (num_buy_orders + num_sell_orders - 1) # Simple uniform step over full range
            if buy_price_step < tick_size:
                logger.error(f"VALIDATION ERROR | Buy order price step ({buy_price_step}) is smaller than tickSize ({tick_size}). Reduce num_buy_orders or increase range.")
                return False

        # Sell orders go from max_price down towards the midpoint
        if num_sell_orders > 1:
            sell_price_step = (max_price - min_price) / (num_buy_orders + num_sell_orders - 1) # Simple uniform step
            if sell_price_step < tick_size:
                logger.error(f"VALIDATION ERROR | Sell order price step ({sell_price_step}) is smaller than tickSize ({tick_size}). Reduce num_sell_orders or increase range.")
                return False

        # Check if calculated prices would adhere to tick_size (approximate check)
        # This is a basic check. Actual generated prices need more careful rounding.
        if tick_size > 0 and (max_price - min_price) % tick_size > 1e-8:
             # This check is too strict if num_orders doesn't perfectly align.
             # Let's trust the rounding in the placement function for now,
             # but ensure start/end points adhere to tick_size.
            if math.fmod(min_price, tick_size) > 1e-8 and abs(tick_size - math.fmod(min_price, tick_size)) > 1e-8:
                logger.error(f"VALIDATION ERROR | min_price {min_price} is not a valid increment of tickSize ({tick_size}).")
                return False
            if math.fmod(max_price, tick_size) > 1e-8 and abs(tick_size - math.fmod(max_price, tick_size)) > 1e-8:
                logger.error(f"VALIDATION ERROR | max_price {max_price} is not a valid increment of tickSize ({tick_size}).")
                return False

    except Exception as e:
        logger.error(f"VALIDATION ERROR | Error calculating grid levels for validation: {e}")
        return False

    logger.info(f"VALIDATION SUCCESS | All inputs for Grid Order are valid.")
    return True

def place_grid_orders(symbol: str, min_price: float, max_price: float, num_buy_orders: int, num_sell_orders: int, quantity_per_order: float):
    """
    Places a simplified Grid of Limit Orders on Binance Futures Testnet.
    It calculates buy and sell price levels within the min/max range
    and attempts to place limit orders at each level.
    Does NOT implement dynamic management (filling and re-placing).
    """
    logger.info(f"Attempting to place Grid Orders for {symbol} from {min_price} to {max_price} "
                f"with {num_buy_orders} BUYs and {num_sell_orders} SELLs, Qty per order: {quantity_per_order}.")

    # --- Step 1: Input Validation ---
    if not validate_grid_inputs(symbol, min_price, max_price, num_buy_orders, num_sell_orders, quantity_per_order):
        logger.error(f"GRID ORDER FAILED | Inputs for {symbol} failed validation. Grid not placed.")
        return None

    placed_orders = []

    # Get exchange info to calculate price precision correctly
    symbol_info = get_exchange_info(symbol)
    tick_size = 0.0
    if symbol_info:
        for f in symbol_info['filters']:
            if f['filterType'] == 'PRICE_FILTER':
                tick_size = float(f['tickSize'])
                break
    price_precision = len(str(tick_size).split('.')[1]) if '.' in str(tick_size) else 0

    # Calculate central price for the grid
    grid_center = (min_price + max_price) / 2

    # Calculate step size for grid prices.
    # We'll distribute orders evenly within their respective halves (buy below center, sell above center)
    # Or, a simpler approach: distribute all orders evenly across the min-max range.
    # Let's use the simpler even distribution across the entire range for this task.
    total_orders = num_buy_orders + num_sell_orders
    if total_orders <= 1: # Avoid division by zero if only 1 order or less is requested
         logger.error("GRID ORDER FAILED | Total number of buy and sell orders must be greater than 1 for a grid.")
         return None

    price_step = (max_price - min_price) / (total_orders - 1)

    # --- Place Buy Orders ---
    logger.info(f"GRID: Placing {num_buy_orders} BUY orders...")
    for i in range(num_buy_orders):
        # Prices go from min_price upwards
        buy_price = min_price + (i * price_step)
        buy_price = round(buy_price / tick_size) * tick_size # Round to nearest tick_size
        buy_price = round(buy_price, price_precision) # Ensure correct decimal places

        if buy_price >= max_price: # Don't place buy orders above max_price
            logger.warning(f"GRID BUY WARNING | Calculated buy price {buy_price} is outside max_price {max_price}. Stopping buy order placement.")
            break

        logger.info(f"GRID BUY {i+1}/{num_buy_orders}: Attempting to place limit BUY order at price {buy_price}")
        order_response = place_limit_order(symbol, "BUY", quantity_per_order, buy_price)
        if order_response:
            placed_orders.append(order_response)
            logger.info(f"GRID BUY {i+1} SUCCESS | Order ID: {order_response.get('orderId')}, Price: {order_response.get('price')}")
        else:
            logger.error(f"GRID BUY {i+1} FAILED | See previous logs for details.")

    # --- Place Sell Orders ---
    logger.info(f"GRID: Placing {num_sell_orders} SELL orders...")
    for i in range(num_sell_orders):
        # Prices go from max_price downwards
        sell_price = max_price - (i * price_step)
        sell_price = round(sell_price / tick_size) * tick_size # Round to nearest tick_size
        sell_price = round(sell_price, price_precision) # Ensure correct decimal places

        if sell_price <= min_price: # Don't place sell orders below min_price
            logger.warning(f"GRID SELL WARNING | Calculated sell price {sell_price} is outside min_price {min_price}. Stopping sell order placement.")
            break

        logger.info(f"GRID SELL {i+1}/{num_sell_orders}: Attempting to place limit SELL order at price {sell_price}")
        order_response = place_limit_order(symbol, "SELL", quantity_per_order, sell_price)
        if order_response:
            placed_orders.append(order_response)
            logger.info(f"GRID SELL {i+1} SUCCESS | Order ID: {order_response.get('orderId')}, Price: {order_response.get('price')}")
        else:
            logger.error(f"GRID SELL {i+1} FAILED | See previous logs for details.")

    logger.info(f"Grid Order placement attempt completed for {symbol}. Total orders attempted: {total_orders}, Total placed: {len(placed_orders)}.")
    return placed_orders # Return list of responses for placed orders.

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("\n--- Running Grid Order Module Tests ---")

    TEST_SYMBOL = "BTCUSDT"
    TEST_QTY_PER_ORDER = 0.001

    # Fetch current mark price to set a reasonable grid range
    current_mark_price = None
    try:
        mark_price_response = client.futures_mark_price(symbol=TEST_SYMBOL)
        current_mark_price = float(mark_price_response['markPrice'])
        print(f"Current Mark Price for {TEST_SYMBOL}: {current_mark_price}")
    except Exception as e:
        logger.error(f"ERROR | Could not fetch current mark price for Grid test: {e}. Using fallback price.")
        current_mark_price = 30000.0 # Fallback

    # Define a grid range around the current price
    # Adjust these values based on current BTCUSDT testnet price.
    # Make sure the range is wide enough for the number of orders, relative to tick_size.
    grid_min_price = round(current_mark_price * 0.99, 1)  # 1% below
    grid_max_price = round(current_mark_price * 1.01, 1)  # 1% above

    import time
    time.sleep(1)

    # --- Test 1: Place a valid Grid ---
    print(f"\nAttempting to place a valid Grid for {TEST_SYMBOL} from {grid_min_price} to {grid_max_price}")
    placed_grid_orders = place_grid_orders(TEST_SYMBOL, grid_min_price, grid_max_price, 3, 3, TEST_QTY_PER_ORDER)
    if placed_grid_orders:
        print(f"Grid orders placed successfully! Total {len(placed_grid_orders)} orders.")
    else:
        print("Grid order placement failed.")

    # NOTE: Manually cancel these orders on Binance Testnet if you don't want them open.
    print("REMINDER: Manually cancel open orders on Binance Testnet after testing if desired.")

    time.sleep(5)

    # --- Test 2: Invalid Grid (Min Price > Max Price) ---
    print("\nAttempting to place Grid with INVALID PRICE RANGE (min_price > max_price)")
    place_grid_orders(TEST_SYMBOL, grid_max_price, grid_min_price, 2, 2, TEST_QTY_PER_ORDER)

    time.sleep(5)

    # --- Test 3: Invalid Quantity Per Order ---
    print("\nAttempting to place Grid with INVALID QUANTITY PER ORDER (too low)")
    place_grid_orders(TEST_SYMBOL, grid_min_price, grid_max_price, 2, 2, 0.0000001)