import time
import threading
import instaloader
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

# Set up bot token
TOKEN = "7695353877:AAG66W5rnym8b2tpUaeVB9oyAfpP0jZRymU"

# Initialize Instaloader
loader = instaloader.Instaloader()

# Dictionary to store tracking details {username: start_time}
tracking_accounts = {}

# Function to fetch Instagram profile details using Instaloader
def get_instagram_details(username):
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        return {
            "name": profile.full_name,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount
        }
    except Exception:
        return None  # Profile not found, banned, or private
    
def format_time(elapsed_seconds):
    days, rem = divmod(elapsed_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    time_parts = []
    if days > 0:
        time_parts.append(f"{int(days)}d")
    if hours > 0:
        time_parts.append(f"{int(hours)}h")
    if minutes > 0:
        time_parts.append(f"{int(minutes)}m")
    if seconds > 0:
        time_parts.append(f"{int(seconds)}s")

    return " ".join(time_parts)

def track_account(username, update: Update, context: CallbackContext, track_type):
    start_time = time.time()
    tracking_accounts[username] = start_time
    
    while True:
        profile_data = get_instagram_details(username)
        
        if track_type == "ban" and profile_data is None:
            elapsed_time = time.time() - start_time
            formatted_time = format_time(elapsed_time)

            update.message.reply_text(f"Eliminated: @{username} (Took {formatted_time})")
            tracking_accounts.pop(username, None)
            break
        
        elif track_type == "unban" and profile_data is not None:
            elapsed_time = time.time() - start_time
            formatted_time = format_time(elapsed_time)

            # Create an inline button for profile link
            keyboard = [[InlineKeyboardButton("🔗 View Profile", url=f"https://www.instagram.com/{username}/")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                f"@{username} is back! (Took {formatted_time})",
                reply_markup=reply_markup
            )
            tracking_accounts.pop(username, None)
            break
        
        time.sleep(60)   # Check every minute 

# Command to start tracking for ban
def ban(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("⚠️ Please provide an Instagram username.\nUsage: /ban @username")
        return
    
    username = context.args[0].lstrip("@")
    
    if username in tracking_accounts:
        update.message.reply_text(f"🔄 Already tracking @{username} for ban.")
        return
    
    profile_data = get_instagram_details(username)
    
    if profile_data is not None:
        update.message.reply_text(
            f"@{username} Tracking for ban..."
        )
        threading.Thread(target=track_account, args=(username, update, context, "ban"), daemon=True).start()
    else:
        update.message.reply_text(f"@{username} is already banned.")

# Command to start tracking for unban
def unban(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("⚠️ Please provide an Instagram username.\nUsage: /unban @username")
        return
    
    username = context.args[0].lstrip("@")
    
    if username in tracking_accounts:
        update.message.reply_text(f"Already tracking @{username} for unban.")
        return
    
    profile_data = get_instagram_details(username)
    
    if profile_data is None:
        update.message.reply_text(f"@{username} Tracking for unban...")
        threading.Thread(target=track_account, args=(username, update, context, "unban"), daemon=True).start()
    else:
        update.message.reply_text(
            f" @{username} is already active.']"
        )

# Command to check current tracking accounts
def tracking_list(update: Update, context: CallbackContext):
    if not tracking_accounts:
        update.message.reply_text("📡 No accounts are currently being tracked.")
    else:
        tracked = "\n".join([f"🔍 @{user}" for user in tracking_accounts])
        update.message.reply_text(f"📡 Currently tracking:\n{tracked}")

# Command to stop tracking an account
def stop(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("⚠️ Please provide an Instagram username.\nUsage: /stop @username")
        return
    
    username = context.args[0].lstrip("@")
    
    if username in tracking_accounts:
        tracking_accounts.pop(username, None)
        update.message.reply_text(f"🛑 Stopped tracking @{username}.")
    else:
        update.message.reply_text(f"⚠️ @{username} is not being tracked.")

# Start the bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(CommandHandler("unban", unban))
    dp.add_handler(CommandHandler("tracking", tracking_list))
    dp.add_handler(CommandHandler("stop", stop))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
