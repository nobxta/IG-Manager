import time
import threading
import sqlite3
import instaloader
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext

# Set up bot token
TOKEN = "7695353877:AAG66W5rnym8b2tpUaeVB9oyAfpP0jZRymU"


# Initialize Instaloader
loader = instaloader.Instaloader()


# Connect to SQLite database
def get_db_connection():
    return sqlite3.connect("tracking.db", check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS tracking (
    user_id INTEGER,
    username TEXT,
    track_type TEXT,
    start_time REAL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    user_id INTEGER,
    username TEXT,
    event TEXT,
    timestamp REAL
)
""")
conn.commit()

def get_instagram_details(username):
    loader = instaloader.Instaloader()
    
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        return {
            "username": username,
            "name": profile.full_name,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "verified": profile.is_verified,
            "private": profile.is_private,
            "profile_pic_url": profile.profile_pic_url  # ✅ Fetch Profile Pic
        }
    except Exception as e:
        print(f"❌ Error fetching Instagram data: {e}")
        return None


# Function to format elapsed time properly
def format_time(elapsed_seconds):
    minutes, seconds = divmod(int(elapsed_seconds), 60)
    return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

# Function to track Instagram accounts for ban/unban
def track_account(user_id, username, track_type, context: CallbackContext):
    conn_thread = get_db_connection()  # Create a new DB connection for each thread
    cursor_thread = conn_thread.cursor()
    
    start_time = time.time()
    
    cursor_thread.execute("INSERT INTO tracking VALUES (?, ?, ?, ?)", (user_id, username, track_type, start_time))
    conn_thread.commit()
    
    while True:
        profile_data = get_instagram_details(username)
        elapsed_time = format_time(time.time() - start_time)

        if track_type == "ban" and profile_data is None:
            context.bot.send_message(user_id, f"✱ Eliminated: @{username} (Took {elapsed_time})")
            cursor_thread.execute("DELETE FROM tracking WHERE user_id=? AND username=?", (user_id, username))
            cursor_thread.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (user_id, username, "banned", time.time()))
            conn_thread.commit()
            break
        elif track_type == "unban" and profile_data is not None:
            keyboard = [[InlineKeyboardButton("➢ View Profile", url=f"https://www.instagram.com/{username}/")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(user_id, f"☯ @{username} is back! (Took {elapsed_time})", reply_markup=reply_markup)
            cursor_thread.execute("DELETE FROM tracking WHERE user_id=? AND username=?", (user_id, username))
            cursor_thread.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (user_id, username, "unbanned", time.time()))
            conn_thread.commit()
            break
        time.sleep(60)

    conn_thread.close()  # Close DB connection for this thread

# Command handlers
def ban(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("✱ Provide an Instagram username: /ban @username")
        return
    username = context.args[0].lstrip("@")
    user_id = update.message.chat_id

    if get_instagram_details(username) is not None:
        update.message.reply_text(f"✈ Tracking @{username} for ban...")
        threading.Thread(target=track_account, args=(user_id, username, "ban", context), daemon=True).start()
    else:
        update.message.reply_text(f"✱ @{username} is already banned.")

def unban(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("✱ Provide an Instagram username: /unban @username")
        return

    username = context.args[0].lstrip("@")
    user_id = update.message.chat_id

    if get_instagram_details(username) is None:
        update.message.reply_text(f"★ Tracking @{username} for unban...")
        threading.Thread(target=track_account, args=(user_id, username, "unban", context), daemon=True).start()
    else:
        keyboard = [[InlineKeyboardButton("➢ View Profile", url=f"https://www.instagram.com/{username}/")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f"✱ @{username} is already active.", reply_markup=reply_markup)



def tracking_list(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    cursor.execute("SELECT username FROM tracking WHERE user_id=?", (user_id,))
    accounts = cursor.fetchall()
    if not accounts:
        update.message.reply_text("☀ No accounts currently being tracked.")
    else:
        update.message.reply_text("☀ Currently tracking:\n" + "\n".join([f"✱ @{a[0]}" for a in accounts]))

def history(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    cursor.execute("SELECT username, event, timestamp FROM history WHERE user_id=? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    records = cursor.fetchall()
    if not records:
        update.message.reply_text("❖ No tracking history available.")
    else:
        history_text = "\n".join([f"✈ @{r[0]} ➢ {r[1]} ({time.strftime('%b %d', time.localtime(r[2]))})" for r in records])
        update.message.reply_text(f"☯ Tracking History ☯\n{history_text}")

def stop(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("✱ Provide an Instagram username: /stop @username")
        return
    username = context.args[0].lstrip("@")
    user_id = update.message.chat_id
    cursor.execute("DELETE FROM tracking WHERE user_id=? AND username=?", (user_id, username))
    conn.commit()
    update.message.reply_text(f"❖ Stopped tracking @{username}.")
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import requests

def info(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Provide an Instagram username: /info @username")
        return
    
    username = context.args[0].lstrip("@")
    
    try:
        data = get_instagram_details(username)  # Fetch Instagram profile details
        
        if data:
            # **1. Get Profile Picture URL**
            profile_pic_url = data.get("profile_pic_url")
            
            # **2. Handle Missing Data**
            name = data.get("name", "N/A") or "N/A"  # If name is empty, show "N/A"
            
            # **3. Prepare Profile Information**
            response_text = (
                f"**User Information**\n"
                f"\n"
                f"**Username:** @{username}\n"
                f"**Name:** {name}\n"
                f"**Followers:** {data['followers']:,}\n"
                f"**Following:** {data['following']:,}\n"
                f"**Posts:** {data['posts']}\n"
                f"**Verified:** {'Yes' if data['verified'] else 'No'}\n"
                f"**Account Type:** {'Private' if data['private'] else 'Public'}\n"
            )
            
            # **4. Add Profile Picture Download Link (Hide Preview)**
            if profile_pic_url:
                response_text += f"\n**Profile Pic:** [Download Link]({profile_pic_url})"

            # **5. Send Profile Info with Clickable Profile Picture Link**
            keyboard = [[InlineKeyboardButton("View Profile", url=f"https://www.instagram.com/{username}/")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                response_text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
                disable_web_page_preview=True  # ✅ Hides link preview
            )

        else:
            update.message.reply_text(f"Unable to fetch info for @{username}. This might be a private or non-existent account.")

    except Exception as e:
        update.message.reply_text(f"Error fetching details for @{username}. Try again later.")
        print(f"Error in /info command: {e}")  # Logs error for debugging


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(CommandHandler("unban", unban))
    dp.add_handler(CommandHandler("tracking", tracking_list))
    dp.add_handler(CommandHandler("history", history))
    dp.add_handler(CommandHandler("info", info))
    dp.add_handler(CommandHandler("stop", stop))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
