import os
import time
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, CommandHandler

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
UPDATE_INTERVAL = 60  # Time to wait between requests in seconds


class Monitor:
    """A Web page monitor."""

    def __init__(self, year_month, day, bot, chat_id):
        self.year_month = year_month
        self.day = day
        self.bot = bot
        self.chat_id = chat_id
        self.is_running = True

    async def send_message(self, text):
        """Send a message to the chat."""
        await self.bot.send_message(chat_id=self.chat_id, text=text)

    async def run(self):
        """Run monitor thread."""
        url = f"https://sankan.kunaicho.go.jp/register/frame/1001?ym={self.year_month}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
        }

        while self.is_running:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.encoding = "utf-8"
                page = response.text
            except requests.exceptions.RequestException as e:
                print(e)
                await self.send_message(
                    f"No data found for {self.year_month}{self.day}. Try again."
                )
                return

            soup = BeautifulSoup(page, "html.parser")
            cell = soup.find("b", string=self.day)
            if not cell:
                print("No table found")
                await self.send_message(
                    f"No data found for {self.year_month}{self.day}. Try again."
                )
                return

            row = cell.find_parent("tr")
            morning_cell = row.find_all("td")[3]
            afternoon_cell = row.find_all("td")[4]

            morning_slots = int(morning_cell.text.strip().split("(")[-1].split("人")[0])
            afternoon_slots = int(
                afternoon_cell.text.strip().split("(")[-1].split("人")[0]
            )

            current_time = time.strftime("%H:%M:%S", time.localtime())
            print(
                f"{current_time} Tokyo Imperial Palace {self.year_month}{self.day} has {morning_slots} 10:00 slots and {afternoon_slots} 13:30 slots available."
            )

            if morning_slots > 0 or afternoon_slots > 0:
                message = f"[{current_time}] Slots available for {self.year_month}{self.day}!\n10:10: {morning_slots} slots\n13:30: {afternoon_slots} slots"
                await self.send_message(message)
            # else:
            #     message = f"[{current_time}] No slots available for {self.year_month}{self.day}."

            await asyncio.sleep(UPDATE_INTERVAL)

    def stop(self):
        self.is_running = False


async def start(update, context):
    await update.message.reply_text(
        "Hello! I'm your Tokyo Imperial Palace ticket notification bot. Use /setup to start monitoring."
    )


async def setup(update, context):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Please provide year-month and day. Example: /setup 202409 06"
        )
        return
    year_month, day = context.args
    monitor = Monitor(year_month, day, context.bot, update.effective_chat.id)

    if "monitors" not in context.chat_data:
        context.chat_data["monitors"] = set()
    context.chat_data["monitors"].add(monitor)

    await update.message.reply_text(f"Monitoring set up for {year_month}{day}")
    asyncio.create_task(monitor.run())


async def stop(update, context):
    if context.chat_data["monitors"]:
        # Stop and remove all monitors
        for monitor in context.chat_data["monitors"]:
            monitor.stop()
        context.chat_data["monitors"].clear()

        await update.message.reply_text("All monitoring stopped.")
    else:
        await update.message.reply_text("No active monitoring to stop.")


def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connection_pool_size(1024)
        .pool_timeout(20)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("stop", stop))

    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
