# USA Politicians & Representative's Stock Trades tracker Bot 📈

## Overview

This Telegram bot provides real-time information on stock trades made by USA politicians. Stay informed about the financial activities of your representatives with ease!

## Features

- 📊 View the latest trade from any representative
- 🔍 Check recent trades of specific politicians
- 💼 Get detailed information on each trade
- 🚀 Real-time updates from official data sources

## How It Works

The bot fetches data from the [House Stock Watcher](https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json) API, which provides up-to-date information on stock trades made by US representatives. Users can interact with the bot through a simple interface to access this information quickly and easily.

## Commands

- `/start` - Initiates the bot and displays the main menu
- `/help` - Provides information on how to use the bot

## Usage

1. Start a chat with the bot on Telegram
2. Use the `/start` command to see the main menu
3. Choose from the following options:
   - View the latest trade from any representative
   - Select a specific representative to see their recent trades
4. The bot will fetch and display the requested information

## Technical Details

- Built with Python 3.11
- Uses the `python-telegram-bot` library for Telegram integration
- Asynchronous programming with `aiohttp` for efficient API requests
- Caching implemented with `functools.lru_cache` to optimize performance

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/us-rep-stock-trades-bot.git
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Telegram Bot Token:
   - Create a `.env` file in the project root
   - Add your token: `TOKEN=your_telegram_bot_token_here`

4. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment

This bot is designed to be easily deployed on platforms like Render. Make sure to set the environment variables and use the correct start command (`python bot.py`) when deploying.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This bot is for informational purposes only. It does not provide financial advice, and users should not make investment decisions based solely on the information provided by this bot.

## Contact

For any questions or suggestions, please open an issue on this repository or contact [@YourUsername](https://t.me/YourUsername) on Telegram.
