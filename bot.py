import os
from dotenv import load_dotenv
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import json
import threading
import asyncio

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Get the token from environment variable
TOKEN = os.getenv('TOKEN')

def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("Latest Trade", callback_data='latest_trade')],
        [InlineKeyboardButton("Latest 3 Trades", callback_data='latest_3_trades')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi there, I'm a bot that tracks famous politicians' stock trades! What would you like to do?",
        reply_markup=get_keyboard()
    )

async def get_trades(num_trades=1):
    url = 'https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json'
    
    print(f"Fetching data from {url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"Response status code: {response.status}")
            if response.status == 200:
                try:
                    data = await response.json()
                    print(f"Total trades fetched: {len(data)}")
                    
                    pelosi_trades = [trade for trade in data if 'pelosi' in trade.get('representative', '').lower()]
                    print(f"Pelosi trades found: {len(pelosi_trades)}")
                    
                    trades_info = []
                    for trade in pelosi_trades[:num_trades]:
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

    if query.data == 'latest_trade':
        loading_message = await query.edit_message_text(text="🚀 Fetching the latest trade... Please wait.")
        trades = await get_trades(1)
        if trades:
            message = f"Here is the latest trade:\n\n{trades[0]}"
        else:
            message = "No recent trades found or there was an issue fetching the data. Please try again later."
    elif query.data == 'latest_3_trades':
        loading_message = await query.edit_message_text(text="🚀 Fetching the latest 3 trades... Please wait.")
        trades = await get_trades(3)
        if trades:
            message = "Here are the latest 3 trades:\n\n" + "\n\n".join(trades)
        else:
            message = "No recent trades found or there was an issue fetching the data. Please try again later."
    
    await loading_message.edit_text(text=message, reply_markup=get_keyboard())

@app.route('/')
def home():
    return "Bot is running!"

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# Start the bot in a separate thread
bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)