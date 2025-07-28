# Binance Futures Order Bot

## Project Description
This project develops a Command-Line Interface (CLI)-based trading bot designed for the Binance USDT-M Futures Testnet. The bot supports a variety of order types, implements robust input validation, maintains structured logging, and demonstrates a modular, production-ready code architecture [cite: 3, Final PM Guidance].

## Features

### Core Order Types (Mandatory)
The bot provides reliable execution for fundamental trading operations [cite: 5, Basic Orders]:
* **Market Orders:** Execute trades immediately at the best available current market price.
* **Limit Orders:** Place orders to be executed at a specified price or better.

### Advanced Order Types (Bonus)
To demonstrate advanced capabilities, the bot includes implementations of high-priority order types [cite: 8, Advanced Orders, Scoring Boosters]:
* **OCO (One-Cancels-the-Other):** Functionality to place a Stop-Loss (`STOP_MARKET`) order and a Take-Profit (`TAKE_PROFIT_MARKET`) order simultaneously. This manages a position with two contingent orders, where the execution of one conceptually implies the cancellation of the other.
* **Stop-Limit Orders:** Triggers a limit order when a specified stop price is hit, offering more control over execution price than a simple market stop.
* **TWAP (Time-Weighted Average Price):** A simplified implementation that breaks down a larger total order into smaller market orders executed at regular time intervals. This demonstrates understanding of time-based execution strategies.
* **Grid Orders:** A simplified implementation for placing an initial grid of buy and sell limit orders at predefined price intervals within a specified range. This showcases understanding of grid placement logic.

### Robustness & Best Practices
The bot is built with a focus on reliability, security, and maintainability [cite: Final PM Guidance]:
* **Comprehensive Input Validation:** All order parameters (symbol, quantity, price, stop price, etc.) are rigorously validated against Binance exchange rules (e.g., `minQty`, `stepSize`, `tickSize`, `minPrice`, `maxPrice`) *before* API calls are made [cite: 14, Input Validation, Validation Rigor]. This prevents common errors and ensures defensive coding [cite: Automatic Rejection Triggers].
* **Structured Logging:** All bot actions, including API requests, responses, and errors, are logged in a structured, timestamped format to `bot.log` [cite: 15, Logging Quality, Logging Standards]. This provides a clear audit trail and aids debugging.
* **Graceful Error Handling:** Specific Binance API exceptions (`BinanceAPIException`) and general Python exceptions are caught and logged with detailed messages, preventing crashes and ensuring continuous operation [cite: Evaluation Criteria, Automatic Rejection Triggers].
* **Secure API Key Management:** API keys are loaded securely from environment variables using `python-dotenv` and are never hardcoded into the source code [cite: Phase 1: Account Setup, Automatic Rejection Triggers].
* **Modular Code Architecture:** The codebase is organized into logical modules (e.g., `config`, `logger`, `market_orders`, `limit_orders`, `advanced/`) to ensure separation of concerns and enhance maintainability [cite: Automatic Rejection Triggers, Final PM Guidance].

## Installation & Setup

To get the bot up and running on your local machine, follow these steps:

### Prerequisites
* **Python 3.8+** (or the specific version you are using)
* **Binance Futures Testnet Account:**
    1.  Register at [https://testnet.binancefuture.com](https://testnet.binancefuture.com) [cite: Phase 1: Account Setup].
    2.  Generate your API Key and Secret Key from your Testnet account settings.
    3.  Fund your Testnet account with test USDT from the "Deposit" or "Faucet" option on the Testnet platform.

### Secure API Key Configuration (`.env`)
Your API keys must be stored securely and not directly in the code [cite: Automatic Rejection Triggers].
1.  Create a file named `.env` in the **root directory** of this project.
2.  Add your Binance Testnet API Key and Secret Key to this file in the following format:
    ```
    BINANCE_TESTNET_API_KEY="YOUR_API_KEY_HERE"
    BINANCE_TESTNET_SECRET_KEY="YOUR_SECRET_KEY_HERE"
    ```
3.  **Important:** Replace `"YOUR_API_KEY_HERE"` and `"YOUR_SECRET_KEY_HERE"` with your actual keys. This `.env` file is listed in `.gitignore` and will not be committed to your repository, ensuring your credentials remain private [cite: Phase 1: Account Setup].

### Virtual Environment & Dependencies
It's recommended to use a Python virtual environment to manage dependencies.
1.  Navigate to your project's root directory in your terminal.
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    ```
3.  Activate the virtual environment:
    * **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
    (You should see `(venv)` in your terminal prompt when active.)
4.  Install the required Python libraries using the provided `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    (This will install `python-binance`, `python-dotenv`, and any other necessary libraries specified with their exact versions [cite: python-binance==1.0.22, python-dotenv==1.0.1].)

## How to Run the Bot (Usage)

All commands must be executed from the **project's root directory** with the virtual environment activated.

### General Help
* To see the main commands:
    ```bash
    python bot.py --help
    ```
* To get help for a specific command (e.g., `market-order`):
    ```bash
    python bot.py market-order --help
    ```

### Available Commands

1.  **Check Balance**
    Checks and displays your Binance Futures Testnet account's USDT balance.
    ```bash
    python bot.py check-balance
    ```

2.  **Place Market Order**
    Executes a market order immediately.
    ```bash
    python bot.py market-order --symbol BTCUSDT --side BUY --quantity 0.001
    ```
    * `--symbol`: Trading pair (e.g., `BTCUSDT`, `ETHUSDT`).
    * `--side`: Order side (`BUY` or `SELL`).
    * `--quantity`: Quantity of the base asset to trade.

3.  **Place Limit Order**
    Places a limit order at a specified price.
    ```bash
    python bot.py limit-order --symbol BTCUSDT --side SELL --quantity 0.001 --price 120000.0
    ```
    * `--symbol`: Trading pair.
    * `--side`: Order side (`BUY` or `SELL`).
    * `--quantity`: Quantity of the base asset.
    * `--price`: Desired price for the limit order.

4.  **Place OCO Order (Bonus)**
    Places a One-Cancels-the-Other (OCO) set of orders (Stop-Loss and Take-Profit Market orders) to manage an open position.
    ```bash
    python bot.py oco-order --symbol BTCUSDT --side SELL --quantity 0.001 --stop-price 116000.0 --take-profit-price 118000.0
    ```
    * `--symbol`: Trading pair.
    * `--side`: Order side for closing the position (`BUY` to close a SELL position, `SELL` to close a BUY position).
    * `--quantity`: Quantity of the base asset for the position.
    * `--stop-price`: Price at which the stop-loss order is triggered.
    * `--take-profit-price`: Price at which the take-profit order is triggered.

5.  **Place Stop-Limit Order (Bonus)**
    Places a Stop-Limit order, which triggers a limit order when the market price reaches the stop price.
    ```bash
    python bot.py stop-limit-order --symbol BTCUSDT --side BUY --quantity 0.001 --stop-price 117500.0 --limit-price 117510.0
    ```
    * `--symbol`: Trading pair.
    * `--side`: Order side (`BUY` or `SELL`).
    * `--quantity`: Quantity of the base asset.
    * `--stop-price`: Price at which the order becomes active (trigger).
    * `--limit-price`: Desired limit price for the triggered order.

6.  **Execute TWAP Order (Bonus)**
    Executes a Time-Weighted Average Price (TWAP) strategy by breaking down a total quantity into smaller market orders over specified intervals.
    ```bash
    python bot.py twap-order --symbol BTCUSDT --side BUY --total-quantity 0.003 --num-intervals 3 --interval-seconds 5
    ```
    * `--symbol`: Trading pair.
    * `--side`: Order side (`BUY` or `SELL`).
    * `--total-quantity`: Total quantity to trade over the TWAP duration.
    * `--num-intervals`: Number of smaller orders to break the total into.
    * `--interval-seconds`: Seconds to wait between each smaller order execution.

7.  **Place Grid Orders (Bonus)**
    Places an initial set of buy and sell limit orders within a defined price range for a grid trading strategy.
    ```bash
    python bot.py grid-order --symbol BTCUSDT --min-price 110000.0 --max-price 120000.0 --num-buy-orders 3 --num-sell-orders 3 --quantity-per-order 0.001
    ```
    * `--symbol`: Trading pair.
    * `--min-price`: Bottom price of the grid range.
    * `--max-price`: Top price of the grid range.
    * `--num-buy-orders`: Number of buy limit orders to place.
    * `--num-sell-orders`: Number of sell limit orders to place.
    * `--quantity-per-order`: Quantity for each individual buy/sell order.

### Logging
All bot activities, including API requests, responses, order placements, and errors, are logged in a structured format to `bot.log` located in the project's root directory [cite: 15, Logging Standards].

## Project Structure
.
├── bot.py                # Main CLI entry point for the bot
├── .env                  # Environment variables (API keys - NOT committed to Git)
├── .gitignore            # Specifies files/folders to ignore in Git
├── bot.log               # Detailed log file for all bot operations
├── check_connection.py   # Script to verify initial API connectivity
├── venv/                 # Python virtual environment directory (ignored by Git)
├── src/                  # Source code directory
│   ├── init.py       # Makes 'src' a Python package
│   ├── config.py         # Handles API key loading and general configurations
│   ├── logger.py         # Configures the structured logging system
│   ├── market_orders.py  # Logic for placing market orders
│   ├── limit_orders.py   # Logic for placing limit orders
│   ├── pycache/      # Python cache directory (ignored by Git)
│   └── advanced/         # Directory for advanced order types (bonus features)
│       ├── pycache/  # Python cache directory (ignored by Git)
│       ├── oco.py        # Implementation for OCO-like orders (Stop-Loss/Take-Profit)
│       ├── stop_limit.py # Implementation for Stop-Limit orders
│       ├── twap.py       # Implementation for TWAP strategy (simplified)
│       └── grid.py       # Implementation for Grid strategy (simplified)

**Key changes and why:**

* **`bot.log`:** Moved it to the root level, as that's where your `logger.py` is configured to create it.
* **`check_connection.py`:** Added it to the root level, as it's a standalone script for initial setup.
* **`venv/`:** Included it to show the virtual environment, but clarified it's ignored by Git.
* **`__pycache__/`:** Included these directories to reflect their presence in your actual structure, and clarified they are ignored by Git.
* **`report.pdf` and `requirements.txt`:** These are not in your screenshot, but they are required for the submission [cite: Killer Demo Package]. I've assumed they will be at the root level alongside `bot.py`, `.env`, etc., as is standard. If you've placed them elsewhere, adjust accordingly.
