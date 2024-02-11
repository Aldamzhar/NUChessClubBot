from telegram import Update, Bot
from config import LICHESS_TOKEN
from telegram.ext import CommandHandler, CallbackContext, Application
import httpx

async def challenge(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) >= 1:
        # Parse the time format argument
        time_format = args[0]  # e.g., "3+2"
        try:
            minutes, increment = map(int, time_format.split('+'))
            clock_limit = minutes * 60  # Convert minutes to seconds
            clock_increment = increment
        except ValueError:
            await update.message.reply_text("Invalid time format. Please use the format 'minutes+increment'.")
            return

        # Prepare the LiChess API call
        url = "https://lichess.org/api/challenge/open"
        data = {
            "clock.limit": clock_limit,
            "clock.increment": clock_increment
        }

        # Perform the API call
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)

        if response.status_code == 200:
            game_url = response.json()['challenge']['url']
            username = update.effective_user.username
            await update.message.reply_text(f"Challenge created by @{username} on LiChess!\n{game_url}")
        else:
            await update.message.reply_text(f"Failed to create the challenge on LiChess. {response}")
    else:
        await update.message.reply_text("Please specify the time format for the game (e.g., /challenge 3+2).")


def main() -> None:
    bot_token = LICHESS_TOKEN
    application = Application.builder().token(bot_token).build()

    challenge_handler = CommandHandler('challenge', challenge)
    application.add_handler(challenge_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
