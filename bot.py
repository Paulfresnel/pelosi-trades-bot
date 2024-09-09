import os
from dotenv import load_dotenv
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import json
from datetime import datetime
import threading

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Get the token from environment variable
TOKEN = os.getenv('TOKEN')

# List of main representatives to track
MAIN_REPRESENTATIVES = ['Pelosi', 'Crenshaw', 'Tuberville']

def get_keyboard():
    keyboard = [
        [InlineKeyboardButton(rep, callback_data=rep.lower())] for rep in MAIN_REPRESENTATIVES
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the US Representative's Stock Trades bot! Which representative's trades would you like to see?",
        reply_markup=get_keyboard()
    )

async def get_trades(representative, num_trades=3):
    url = 'https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json'
    
    print(f"Fetching data from {url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"Response status code: {response.status}")
            if response.status == 200:
                try:
                    data = await response.json()
                    print(f"Total trades fetched: {len(data)}")
                    
                    # Filter for the specific representative's trades and sort by date
                    rep_trades = [
                        trade for trade in data 
                        if representative.lower() in trade.get('representative', '').lower()
                    ]
                    rep_trades.sort(
                        key=lambda x: datetime.strptime(x['transaction_date'], '%Y-%m-%d'),
                        reverse=True
                    )
                    print(f"{representative} trades found: {len(rep_trades)}")
                    
                    trades_info = []
                    for trade in rep_trades[:num_trades]:
                        description = trade.get('asset_description', 'N/A')
                        total_loss = ''
                        if 'Total loss of' in description:
                            total_loss = description.split('Total loss of')[-1].strip()
                            description = description.split('Total loss of')[0].strip()
                        
                        amount = trade.get('amount', 'N/A')
                        if amount.endswith('-'):
                            amount += ' (incomplete data)'
                        
                        trade_info = f"📅 Date: {trade.get('transaction_date', 'N/A')}\n" \
                                     f"🏷️ Ticker: {trade.get('ticker', 'N/A')}\n" \
                                     f"📊 Type: {trade.get('type', 'N/A')}\n" \
                                     f"💰 Amount: {amount}\n" \
                                     f"📝 Description: {description}"
                        
                        if total_loss:
                            trade_info += f"\n💸 Total Loss: {total_loss}"
                        
                        trades_info.append(trade_info)
                    
                    return trades_info
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    return None
            else:
                print(f"Failed to fetch data: HTTP {response.status}")
                return None

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    representative = query.data.capitalize()
    loading_message = await query.edit_message_text(text=f"🚀 Fetching the latest 3 trades for {representative}... Please wait.")
    trades = await get_trades(representative, 3)
    if trades:
        message = f"Here are the latest 3 trades for {representative}:\n\n" + "\n\n".join(trades)
    else:
        message = f"No recent trades found for {representative} or there was an issue fetching the data. Please try again later."
    
    await loading_message.edit_text(text=message, reply_markup=get_keyboard())

@app.route('/')
def home():
    return "US Representative's Stock Trades bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Run the bot in the main thread
    run_bot()