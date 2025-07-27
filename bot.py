# bot.py
# This is the main Command-Line Interface (CLI) entry point for your trading bot.

import argparse # Python's standard library for parsing command-line arguments.

# Import functions and client from our modules within the src/ package.
# Note: We directly import the functions we need, not the whole module object.
from binance import Client # Imported to allow checking balance
from binance.exceptions import BinanceAPIException
from src.config import BINANCE_API_KEY, BINANCE_API_SECRET # For initializing client
from src.logger import logger # Our centralized logger
from src.market_orders import place_market_order # Our market order function
from src.limit_orders import place_limit_order # Our limit order function

# Initialize Binance Client for operations that need it (like check_balance).
# This will be used by some CLI commands directly.
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)


def check_balance():
    """
    Fetches and prints the user's Binance Futures Testnet account balance.
    """
    logger.info("Attempting to fetch account balance.")
    try:
        # Log the request for account balance.
        logger.info(f"REQUEST | GET /fapi/v2/account | params: None")
        account_balance = client.futures_account_balance()
        
        logger.info(f"RESPONSE | Successfully fetched account balance.")
        print("\n--- Your Binance Futures Testnet Account Balance ---")
        found_assets = False
        for item in account_balance:
            # Convert balance to float for comparison.
            if float(item['balance']) > 0:
                print(f"  Asset: {item['asset']}, Balance: {float(item['balance']):.8f} USDT")
                found_assets = True
        if not found_assets:
            print("  No assets with positive balance found. Please fund your testnet account.")
        print("---------------------------------------------------\n")

    except BinanceAPIException as e:
        logger.error(f"ERROR | BinanceAPIException during balance check: status_code={e.status_code}, message={e.message}")
        print(f"Error checking balance: {e.message}")
    except Exception as e:
        logger.error(f"ERROR | Unexpected error during balance check: {e}")
        print(f"An unexpected error occurred: {e}")


def main():
    """
    Main function to parse command-line arguments and execute bot commands.
    """
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawTextHelpFormatter # Keeps help messages formatted nicely.
    )

    # Create subcommands for different order types and actions.
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Subparser for Market Orders ---
    market_parser = subparsers.add_parser(
        "market-order", 
        help="Place a market order (immediate execution at current price)."
    )
    market_parser.add_argument("--symbol", type=str, required=True, help="Trading pair (e.g., BTCUSDT).")
    market_parser.add_argument("--side", type=str, required=True, choices=["BUY", "SELL"], help="Order side (BUY or SELL).")
    market_parser.add_argument("--quantity", type=float, required=True, help="Quantity of the base asset to trade (e.g., 0.001 for BTCUSDT).")
    # Set the function to call when 'market-order' is used.
    market_parser.set_defaults(func=lambda args: place_market_order(args.symbol, args.side, args.quantity))

    # --- Subparser for Limit Orders ---
    limit_parser = subparsers.add_parser(
        "limit-order", 
        help="Place a limit order (executes at a specified price or better)."
    )
    limit_parser.add_argument("--symbol", type=str, required=True, help="Trading pair (e.g., BTCUSDT).")
    limit_parser.add_argument("--side", type=str, required=True, choices=["BUY", "SELL"], help="Order side (BUY or SELL).")
    limit_parser.add_argument("--quantity", type=float, required=True, help="Quantity of the base asset to trade.")
    limit_parser.add_argument("--price", type=float, required=True, help="Desired price for the limit order.")
    # Set the function to call when 'limit-order' is used.
    limit_parser.set_defaults(func=lambda args: place_limit_order(args.symbol, args.side, args.quantity, args.price))

    # --- Subparser for Check Balance ---
    balance_parser = subparsers.add_parser(
        "check-balance",
        help="Check your Binance Futures Testnet account balance."
    )
    # Set the function to call when 'check-balance' is used.
    balance_parser.set_defaults(func=lambda args: check_balance())


    # Parse the arguments provided by the user.
    args = parser.parse_args()

    # If a subcommand was specified, call its associated function.
    if hasattr(args, "func"):
        args.func(args) # Call the function associated with the subcommand.
    else:
        # If no subcommand is given (e.g., just 'python bot.py'), show help message.
        parser.print_help()

if __name__ == "__main__":
    main()