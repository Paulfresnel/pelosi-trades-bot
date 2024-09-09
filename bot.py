import os
import logging
import time
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import json
from datetime import datetime
from functools import lru_cache

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the token from environment variable
TOKEN = os.getenv('TOKEN')

# List of main representatives to track
MAIN_REPRESENTATIVES = ['Pelosi', 'Green', 'Higgins', 'Graves']

def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Latest Trade (Any Representative)", callback_data='latest_any')]
    ] + [
        [InlineKeyboardButton(f"🔍 {rep}'s Trades", callback_data=rep.lower())] for rep in MAIN_REPRESENTATIVES
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro_message = (
        "*Welcome to the US Representative's Stock Trades Bot!* 🇺🇸📈\n\n"
        "This bot provides real-time information on stock trades made by US politicians. "
        "Stay informed about the financial activities of your representatives!\n\n"
        "*Features:*\n"
        "• View the latest trade from any representative\n"
        "• Check recent trades of specific politicians\n"
        "• Get detailed information on each trade\n\n"
        "To get started, simply choose an option below or type /help for more information."
    )
    await update.message.reply_text(
        intro_message,
        reply_markup=get_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*US Representative's Stock Trades Bot - Help*\n\n"
        "Here's how to use the bot:\n\n"
        "• Click on 'Latest Trade' to see the most recent trade from any representative\n"
        "• Select a specific representative to view their latest 3 trades\n"
        "For any issues or suggestions, please contact @YourUsername"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

@lru_cache(maxsize=32)
async def fetch_trades_data():
    url = 'https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

async def get_trades(representative=None, num_trades=3):
    try:
        data = await fetch_trades_data()
        if data is None:
            print("Failed to fetch trade data")
            return None

        if representative:
            filtered_trades = [
                trade for trade in data 
                if representative.lower() in trade.get('representative', '').lower()
            ]
        else:
            filtered_trades = data

        filtered_trades.sort(
            key=lambda x: datetime.strptime(x['transaction_date'], '%Y-%m-%d'),
            reverse=True
        )
        print(f"Filtered trades: {len(filtered_trades)}")

        trades_info = []
        for trade in filtered_trades[:num_trades]:
            description = trade.get('asset_description', 'N/A')
            total_loss = ''
            if 'Total loss of' in description:
                total_loss = description.split('Total loss of')[-1].strip()
                description = description.split('Total loss of')[0].strip()

            amount = trade.get('amount', 'N/A')
            if amount.endswith('-'):
                amount += ' (incomplete data)'

            # Determine transaction type and corresponding emoji
            transaction_type = trade.get('type', 'N/A')
            if transaction_type.lower() == 'purchase':
                type_emoji = '🟢'
            elif transaction_type.lower() == 'sale_full':
                type_emoji = '🔴'
                transaction_type = 'SALE'
            else:
                type_emoji = '⚪'  # Neutral color for other types

            trade_info = f"👤 Representative: {trade.get('representative', 'N/A')}\n" \
                         f"📅 Date: {trade.get('transaction_date', 'N/A')}\n" \
                         f"🏷️ Ticker: {trade.get('ticker', 'N/A')}\n" \
                         f"{type_emoji} Type: {transaction_type}\n" \
                         f"💰 Amount: {amount}\n" \
                         f"📝 Description: {description}"

            if total_loss:
                trade_info += f"\n💸 Total Loss: {total_loss}"

            trades_info.append(trade_info)

        return trades_info
    except Exception as e:
        print(f"Error in get_trades: {e}")
        return None

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        if query.data == 'latest_any':
            loading_message = await query.edit_message_text(text="🚀 Fetching the latest trade from any representative... Please wait.")
            trades = await get_trades(representative=None, num_trades=1)
            if trades:
                message = f"*Here is the latest trade:*\n\n{trades[0]}"
            else:
                message = "No recent trades found or there was an issue fetching the data. Please try again later."
        else:
            representative = query.data.capitalize()
            loading_message = await query.edit_message_text(text=f"🚀 Fetching the latest 3 trades for {representative}... Please wait.")
            trades = await get_trades(representative, 3)
            if trades:
                message = f"*Here are the latest 3 trades for {representative}:*\n\n" + "\n\n".join(trades)
            else:
                message = f"No recent trades found for {representative} or there was an issue fetching the data. Please try again later."
    
        await loading_message.edit_text(
            text=message,
            reply_markup=get_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        error_message = "An error occurred. Please try again later or contact support."
        await query.edit_message_text(text=error_message, reply_markup=get_keyboard())
        print(f"Error in button handler: {e}")

def run_bot():
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            application = ApplicationBuilder().token(TOKEN).build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CallbackQueryHandler(button))
            logger.info("Starting bot...")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except telegram.error.Conflict as e:
            logger.error(f"Conflict error: {e}")
            retry_count += 1
            wait_time = 2 ** retry_count  # Exponential backoff
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            break
    else:
        logger.error("Max retries reached. Unable to start the bot.")

if __name__ == '__main__':
    run_bot()