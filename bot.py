import os
import requests
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import aiohttp
import asyncio

# Replace 'YOUR_BOT_TOKEN' with the actual token you get from BotFather
TOKEN = '7207269548:AAFgfArYdtO4tZl1U7jHoFQMFf3tEds-Rp0'

async def check_trades():
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
                    
                    if pelosi_trades:
                        latest_trade = pelosi_trades[0]
                        
                        # Extract total loss if present in the description
                        description = latest_trade.get('asset_description', 'N/A')
                        total_loss = ''
                        if 'Total loss of' in description:
                            total_loss = description.split('Total loss of')[-1].strip()
                            description = description.split('Total loss of')[0].strip()
                        
                        trade_info = f"📅 Date: {latest_trade.get('transaction_date', 'N/A')}\n" \
                                     f"🏷️ Ticker: {latest_trade.get('ticker', 'N/A')}\n" \
                                     f"📊 Type: {latest_trade.get('type', 'N/A')}\n" \
                                     f"💰 Amount: {latest_trade.get('amount', 'N/A')}\n" \
                                     f"📝 Description: {description}"
                        
                        if total_loss:
                            trade_info += f"\n💸 Total Loss: {total_loss}"
                        
                        print(f"Trade found: {trade_info}")
                        return trade_info
                    else:
                        print("No trades found for Nancy Pelosi")
                        return None
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    print(f"Response content: {await response.text()}")
                    return None
            else:
                print(f"Failed to fetch data: HTTP {response.status}")
                return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Latest Trade", callback_data='latest_trade')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "I'm a bot that tracks Nancy Pelosi's stock trades! What would you like to do?",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'latest_trade':
        loading_message = await query.edit_message_text(text="🚀 Fetching the latest trade... Please wait.")
        try:
            trade = await check_trades()
            if trade:
                message = f"Here is the latest trade:\n\n{trade}"
            else:
                message = "No recent trades found or there was an issue fetching the data. Please try again later."
        except Exception as e:
            print(f"Error in button handler: {e}")
            message = "An error occurred while fetching the data. Please try again later."
        await loading_message.edit_text(text=message, parse_mode='HTML')

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()