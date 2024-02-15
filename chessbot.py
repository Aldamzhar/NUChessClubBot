from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, filters
import httpx
import asyncio
import logging
import random
from config import LICHESS_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global list to store offline users and a lock for thread-safe operations
offline_users = []
private_challenge_lst = []
lock = asyncio.Lock()

time_formats = ['1+0', '2+1', '3+0', '3+2', '5+0', '5+3', '10+0', '10+5', '15+10', '30+0', '30+20']

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Offline", callback_data='offline'),
                 InlineKeyboardButton("Online", callback_data='online')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose your mode:', reply_markup=reply_markup)

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user  # Access the whole User object

    keyboard = [[InlineKeyboardButton("Offline", callback_data='offline'),
                                 InlineKeyboardButton("Online", callback_data='online')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    async with lock:
        if data == 'offline':
            if user.username not in [u.username for u in offline_users]:  # Check by username
                offline_users.append(user)  # Store the whole User object
                logger.info(f"User {user.username} added to offline list: {[u.username for u in offline_users]}")
                await context.bot.send_message(chat_id=user.id, text="You are added to the waiting room! Please wait for the pairing message.")
                if len(offline_users) >= 2:
                    user1 = offline_users.pop(0)
                    user2 = offline_users.pop(0)
                
                    logger.info(f"Pairing {user1.username} with {user2.username}")
                    
                    # Prepare the message
                    pairing_message = f"@{user1.username} and @{user2.username}, you are paired for an offline game!\nIf you want, you can meet at 27.151"
                    
                    # Send a message to both users
                    
                    await context.bot.send_message(chat_id=user1.id, text=pairing_message, reply_markup=reply_markup)
                    await context.bot.send_message(chat_id=user2.id, text=pairing_message, reply_markup=reply_markup)
                    
                    logger.info(f"Current offline list: {[u.username for u in offline_users]}")
            else:
                await context.bot.send_message(chat_id=user.id, text="You are already in the waiting room. Please wait for the pairing to complete", reply_markup=reply_markup)
        elif data == 'online':
            await context.bot.send_message(chat_id=user.id, text="Join this Telegram chat for offline and online challenges with fellow members! https://t.me/+cAgv-cStR0RjOWUy", reply_markup=reply_markup)
            # Present the initial choice buttons again
            

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

async def private_challenge(update: Update, context: CallbackContext) -> None:
    global private_challenge_lst  # Add this line to use the global variable
    user = update.effective_user
    
    async with lock:
        if user not in private_challenge_lst:
            private_challenge_lst.append(user)
            await update.message.reply_text("You've been added to the private challenge list.")
            
            if len(private_challenge_lst) >= 2:
                player1, player2 = private_challenge_lst[:2]
                private_challenge_lst = private_challenge_lst[2:]  # Modify the global list
                
                # Select a random time format
                time_format = random.choice(time_formats)
                minutes, increment = map(int, time_format.split('+'))
                clock_limit = minutes * 60
                clock_increment = increment
                
                # Create a LiChess challenge
                url = "https://lichess.org/api/challenge/open"
                data = {
                    "clock.limit": clock_limit,
                    "clock.increment": clock_increment
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    game_url = response.json()['challenge']['url']
                    message = f"@{player1.username} and @{player2.username}, you've been paired for a private online game!\nGame URL: {game_url}"
                    await context.bot.send_message(chat_id=player1.id, text=message)
                    await context.bot.send_message(chat_id=player2.id, text=message)
                else:
                    logger.error("Failed to create LiChess challenge")
        else:
            await update.message.reply_text("You're already in the private challenge list.")


def main() -> None:
    bot_token = LICHESS_TOKEN
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler('challenge', challenge, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('privateChallenge', private_challenge))

    application.run_polling()

if __name__ == '__main__':
    main()
