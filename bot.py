import os
import logging
import asyncio
import aiohttp
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import NetworkError, Conflict
from functools import lru_cache
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the token from environment variable
TOKEN = os.getenv('TOKEN')

# Create Flask app
app = Flask(__name__)

# Create a global variable for the application
application = None

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

# Modify the fetch_trades_data function
last_fetch_time = None
cached_data = None

@lru_cache(maxsize=32)
async def fetch_trades_data():
    global last_fetch_time, cached_data
    current_time = datetime.now()
    
    if last_fetch_time is None or (current_time - last_fetch_time) > timedelta(minutes=5):
        url = 'https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        cached_data = await response.json()
                        last_fetch_time = current_time
                        logger.info("Fetched new data from API")
                    else:
                        logger.error(f"Failed to fetch data: HTTP {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("Timeout while fetching data from API")
            return None
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    else:
        logger.info("Using cached data")
    
    return cached_data

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
            logger.info(f"Fetched trades for latest_any: {trades}")
        else:
            representative = query.data.capitalize()
            loading_message = await query.edit_message_text(text=f"🚀 Fetching the latest 3 trades for {representative}... Please wait.")
            trades = await get_trades(representative, 3)
            logger.info(f"Fetched trades for {representative}: {trades}")

        if trades:
            message = "*Here are the latest trades:*\n\n" + "\n\n".join(trades)
        else:
            message = "No recent trades found or there was an issue fetching the data. Please try again later."

        await loading_message.edit_text(
            text=message,
            reply_markup=get_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error in button handler: {e}", exc_info=True)
        error_message = "An error occurred. Please try again later or contact support."
        await query.edit_message_text(text=error_message, reply_markup=get_keyboard())

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, Conflict):
        # If we get a conflict error, wait for a bit and then exit
        await asyncio.sleep(30)
        os._exit(1)

async def ping_self(context: ContextTypes.DEFAULT_TYPE):
    url = os.getenv('RENDER_EXTERNAL_URL')
    if url:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    logger.info(f"Self-ping status: {response.status}")
            except Exception as e:
                logger.error(f"Self-ping failed: {e}")

@app.route('/')
def home():
    return "Bot is running!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if application:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
    return 'OK'

async def setup_webhook(app):
    global application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))

    # Add error handler
    application.add_error_handler(error_handler)

    # Add job to ping self every 14 minutes
    application.job_queue.run_repeating(ping_self, interval=840, first=10)

    # Set webhook
    webhook_url = f"{os.getenv('RENDER_EXTERNAL_URL')}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    return application

@app.before_first_request
def before_first_request():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook(app))

if __name__ == '__main__':
    # Run Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)