# src/advanced/twap.py
# This module implements a simplified Time-Weighted Average Price (TWAP) strategy
# for Binance Futures Testnet. It breaks a large order into smaller market orders
# executed over a specified time.

import time # Used for pausing execution between orders.
from binance import Client
from binance.exceptions import BinanceAPIException
import math

from src.config import BINANCE_API_KEY, BINANCE_API_SECRET
from src.logger import logger
from src.market_orders import get_exchange_info # Reusing for symbol info and filters
from src.market_orders import place_market_order # Reusing our market order function

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

def validate_twap_inputs(symbol: str, side: str, total_quantity: float, num_intervals: int, interval_seconds: int) -> bool:
    """
    Validates inputs for a TWAP order.
    Checks for:
    - Symbol, side, total_quantity validity.
    - Positive num_intervals and interval_seconds.
    - Ensures total_quantity can be cleanly divided into interval_quantity based on stepSize.
    """
    logger.info(f"VALIDATING inputs for TWAP Order: Symbol={symbol}, Side={side}, TotalQty={total_quantity}, Intervals={num_intervals}, IntervalSec={interval_seconds}")

    # Basic validations for num_intervals and interval_seconds
    if num_intervals <= 0:
        logger.error(f"VALIDATION ERROR | Number of intervals must be positive. Received: {num_intervals}")
        return False
    if interval_seconds < 0:
        logger.error(f"VALIDATION ERROR | Interval seconds cannot be negative. Received: {interval_seconds}")
        return False

    # Get exchange info to validate total_quantity and calculate interval_quantity
    symbol_info = get_exchange_info(symbol)
    if not symbol_info:
        logger.error(f"VALIDATION ERROR | Could not retrieve exchange info for symbol: {symbol}. Cannot validate TWAP order.")
        return False

    if symbol_info['status'] != 'TRADING':
        logger.error(f"VALIDATION ERROR | Symbol '{symbol}' is not currently tradable (status: {symbol_info['status']}).")
        return False

    if side not in ['BUY', 'SELL']:
        logger.error(f"VALIDATION ERROR | Invalid side: '{side}'. Must be 'BUY' or 'SELL'.")
        return False

    if total_quantity <= 0:
        logger.error(f"VALIDATION ERROR | Total quantity must be positive. Received: {total_quantity}")
        return False

    # --- Quantity Validation (re-using LOT_SIZE filter logic for total_quantity) ---
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
        logger.error(f"VALIDATION ERROR | Could not find LOT_SIZE filter for {symbol}. Cannot validate quantity for TWAP.")
        return False

    if total_quantity < min_qty:
        logger.error(f"VALIDATION ERROR | Total quantity {total_quantity} is less than minimum allowed ({min_qty}) for {symbol}.")
        return False

    if total_quantity > max_qty:
        logger.error(f"VALIDATION ERROR | Total quantity {total_quantity} is greater than maximum allowed ({max_qty}) for {symbol}.")
        return False

    # Validate total_quantity step size
    if step_size > 0 and math.fmod(total_quantity, step_size) > 1e-8 and abs(step_size - math.fmod(total_quantity, step_size)) > 1e-8:
        logger.error(f"VALIDATION ERROR | Total quantity {total_quantity} is not a valid increment of stepSize ({step_size}) for {symbol}.")
        return False

    # Calculate quantity per interval and validate its step size
    if num_intervals > 0:
        interval_quantity_raw = total_quantity / num_intervals
        # Round interval_quantity to the correct precision based on step_size
        if step_size > 0:
            # Find precision of step_size
            step_precision = len(str(step_size).split('.')[1]) if '.' in str(step_size) else 0
            interval_quantity = round(interval_quantity_raw, step_precision)
        else:
            interval_quantity = interval_quantity_raw # Should not happen if LOT_SIZE found

        # Re-check if the rounded interval_quantity is still a valid step
        if step_size > 0 and math.fmod(interval_quantity, step_size) > 1e-8 and abs(step_size - math.fmod(interval_quantity, step_size)) > 1e-8:
            logger.error(f"VALIDATION ERROR | Calculated interval quantity {interval_quantity} is not a valid increment of stepSize ({step_size}) for {symbol}.")
            return False

        if interval_quantity < min_qty:
            logger.error(f"VALIDATION ERROR | Calculated interval quantity {interval_quantity} is less than minimum allowed ({min_qty}) per order for {symbol}.")
            return False

        # Check if total quantity can be reconstructed from rounded interval quantity
        # This is to catch cases where rounding might cause a final sum mismatch
        reconstructed_total_quantity = interval_quantity * num_intervals
        if abs(reconstructed_total_quantity - total_quantity) > step_size * 0.5: # Allow small discrepancy
            logger.warning(f"WARNING | Reconstructed total quantity {reconstructed_total_quantity} differs from original total quantity {total_quantity} due to rounding. Check TWAP logic.")
            # We won't make this a hard fail for the hiring task unless it's a huge difference.

    logger.info(f"VALIDATION SUCCESS | All inputs for TWAP Order are valid. Interval Quantity: {interval_quantity if num_intervals > 0 else 'N/A'}")
    return True

def execute_twap_order(symbol: str, side: str, total_quantity: float, num_intervals: int, interval_seconds: int):
    """
    Executes a simplified TWAP order strategy.
    Breaks down the total_quantity into num_intervals and places market orders
    at regular interval_seconds.
    """
    logger.info(f"Attempting to execute TWAP Order: {symbol} {side} {total_quantity} over {num_intervals} intervals ({interval_seconds}s each).")

    # --- Step 1: Input Validation ---
    if not validate_twap_inputs(symbol, side, total_quantity, num_intervals, interval_seconds):
        logger.error(f"TWAP ORDER FAILED | Inputs for {symbol} failed validation. TWAP not executed.")
        return None

    # Determine step_size for rounding interval quantity precisely
    symbol_info = get_exchange_info(symbol)
    step_size = 0.0
    if symbol_info:
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])
                break

    step_precision = len(str(step_size).split('.')[1]) if '.' in str(step_size) else 0

    # Calculate quantity per interval
    if num_intervals > 0:
        interval_quantity = round(total_quantity / num_intervals, step_precision)
    else:
        logger.error("TWAP EXECUTION ERROR | Number of intervals must be greater than zero.")
        return None

    executed_total_quantity = 0.0
    successful_orders = []

    logger.info(f"TWAP Strategy: Placing {num_intervals} market orders of {interval_quantity} {symbol} every {interval_seconds} seconds.")

    for i in range(num_intervals):
        logger.info(f"TWAP Interval {i+1}/{num_intervals}: Attempting to place market order for {interval_quantity} {symbol}.")

        # Use our existing place_market_order function for consistency and reusability.
        order_response = place_market_order(symbol, side, interval_quantity)

        if order_response and order_response.get('status') == 'FILLED': # Check if the order was immediately filled
            executed_total_quantity += float(order_response.get('executedQty', 0.0))
            successful_orders.append(order_response)
            logger.info(f"TWAP Interval {i+1} SUCCESS | Order filled. Executed Qty: {order_response.get('executedQty')}")
        elif order_response: # Order placed but not necessarily filled immediately (e.g., status: NEW)
            executed_total_quantity += float(order_response.get('executedQty', 0.0)) # Add any partially filled quantity
            successful_orders.append(order_response)
            logger.info(f"TWAP Interval {i+1} ORDER PLACED | Status: {order_response.get('status')}. Executed Qty: {order_response.get('executedQty')}")
        else:
            logger.error(f"TWAP Interval {i+1} FAILED | Market order failed. See previous logs for details.")
            # For a simplified TWAP, we might just log and continue, or stop based on requirements.
            # For this task, we'll log and continue to attempt subsequent intervals.

        # Wait for the specified interval, unless it's the last interval.
        if i < num_intervals - 1:
            logger.info(f"TWAP Interval {i+1}: Waiting for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
        else:
            logger.info(f"TWAP execution completed.")

    logger.info(f"TWAP Execution Summary for {symbol}: Total requested {total_quantity}, Total executed {executed_total_quantity} across {len(successful_orders)} successful orders.")

    # A full TWAP would return detailed execution report. For this, return success status.
    return executed_total_quantity > 0 # Return True if any part of the TWAP was executed.

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("\n--- Running TWAP Order Module Tests ---")

    TEST_SYMBOL = "BTCUSDT"
    TEST_TOTAL_QUANTITY = 0.003 # This will be 3 x 0.001 orders
    TEST_NUM_INTERVALS = 3
    TEST_INTERVAL_SECONDS = 5 # 5 seconds between orders

    print(f"\nAttempting TWAP for {TEST_SYMBOL} BUY {TEST_TOTAL_QUANTITY} over {TEST_NUM_INTERVALS} intervals of {TEST_INTERVAL_SECONDS}s.")
    twap_success = execute_twap_order(TEST_SYMBOL, "BUY", TEST_TOTAL_QUANTITY, TEST_NUM_INTERVALS, TEST_INTERVAL_SECONDS)
    if twap_success:
        print("TWAP execution completed successfully (at least partially). Check logs for details.")
    else:
        print("TWAP execution failed or no orders were placed.")

    time.sleep(5) # Give some time after the first TWAP test.

    print("\n--- Testing TWAP with INVALID TOTAL QUANTITY (not multiple of step size) ---")
    # Assuming step_size is 0.001, 0.0035 should fail if it results in non-step interval.
    execute_twap_order(TEST_SYMBOL, "BUY", 0.0035, TEST_NUM_INTERVALS, TEST_INTERVAL_SECONDS)

    time.sleep(5)

    print("\n--- Testing TWAP with INVALID NUMBER OF INTERVALS ---")
    execute_twap_order(TEST_SYMBOL, "SELL", TEST_TOTAL_QUANTITY, 0, TEST_INTERVAL_SECONDS)

    print("\n--- Testing TWAP with Interval Quantity too low ---")
    # Make a large total quantity, many intervals, so interval_qty is below min_qty
    execute_twap_order(TEST_SYMBOL, "BUY", 0.002, 10, 1) # This should result in 0.0002 per order, typically below minQty