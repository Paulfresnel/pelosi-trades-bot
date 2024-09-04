import os
import requests
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, CommandHandler
import time

# Replace 'YOUR_BOT_TOKEN' with the actual token you get from BotFather
TOKEN = '7207269548:AAFgfArYdtO4tZl1U7jHoFQMFf3tEds-Rp0'

async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot that tracks Nancy Pelosi's stock trades!")

def check_trades():
    # URL of the page with Nancy Pelosi's trades
    url = 'https://www.quiverquant.com/congresstrading/politician/Nancy%20Pelosi-P000197'
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    trades = []
    trade_rows = soup.select('#tradeTable tbody tr')
    
    for row in trade_rows:
        cells = row.find_all('td')
        if len(cells) >= 6:
            ticker = cells[0].find('strong').text.strip()
            transaction = cells[1].find('strong').text.strip()
            amount = cells[1].find('span').text.strip()
            date = cells[3].find('strong').text.strip()
            description = cells[4].find('span').text.strip()
            
            trade_info = f"Ticker: {ticker}\nTransaction: {transaction}\nAmount: {amount}\nDate: {date}\nDescription: {description}"
            trades.append(trade_info)
    
    return trades

async def send_updates(context):
    trades = check_trades()
    for trade in trades:
        await context.bot.send_message(chat_id='5619051853', text=f"New trade:\n\n{trade}")

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # Check if job queue is available
    if application.job_queue:
        # Check for updates every hour
        application.job_queue.run_repeating(send_updates, interval=3600, first=0)
    else:
        print("Warning: JobQueue is not available. Scheduled updates will not run.")

    application.run_polling()

if __name__ == '__main__':
    main()