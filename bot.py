import discord
import asyncio
import sqlite3
import instaloader
import time
import requests

from discord.ext import commands, tasks

# Discord Bot Token
TOKEN = "MTM0ODM3ODExNDIxMTcwOTAzOA.GP6mBs._9kNWmPzJC_bcZ7rWDEsfnE7DRbvcSj_IOTWWA"

# Set up Discord Bot with Intents
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="/", intents=intents)

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


async def get_instagram_details(username):
    """Fetch Instagram details using Instaloader."""
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        return {
            "username": username,
            "name": profile.full_name if profile.full_name else "N/A",
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "verified": profile.is_verified,
            "private": profile.is_private,
            "profile_pic_url": profile.profile_pic_url
        }
    except Exception as e:
        print(f"❌ Error fetching Instagram data: {e}")
        return None


def format_time(elapsed_seconds):
    """Format elapsed time properly."""
    minutes, seconds = divmod(int(elapsed_seconds), 60)
    return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"


async def track_account(ctx, username, track_type):
    """Track Instagram account for ban/unban."""
    conn_thread = get_db_connection()
    cursor_thread = conn_thread.cursor()
    
    start_time = time.time()
    cursor_thread.execute("INSERT INTO tracking VALUES (?, ?, ?, ?)", (ctx.author.id, username, track_type, start_time))
    conn_thread.commit()

    while True:
        profile_data = await get_instagram_details(username)
        elapsed_time = format_time(time.time() - start_time)

        if track_type == "ban" and profile_data is None:
            await ctx.send(f"✱ Eliminated: @{username} (Took {elapsed_time})")
            cursor_thread.execute("DELETE FROM tracking WHERE user_id=? AND username=?", (ctx.author.id, username))
            cursor_thread.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (ctx.author.id, username, "banned", time.time()))
            conn_thread.commit()
            break
        elif track_type == "unban" and profile_data is not None:
            await ctx.send(f"☯ @{username} is back! (Took {elapsed_time})\n🔗 **View Profile:** [Click Here](https://www.instagram.com/{username}/)")
            cursor_thread.execute("DELETE FROM tracking WHERE user_id=? AND username=?", (ctx.author.id, username))
            cursor_thread.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (ctx.author.id, username, "unbanned", time.time()))
            conn_thread.commit()
            break
        await asyncio.sleep(60)

    conn_thread.close()


@bot.command()
async def ban(ctx, username: str):
    """Track an Instagram account for banning."""
    username = username.lstrip("@")

    if await get_instagram_details(username) is not None:
        await ctx.send(f"✈ Tracking @{username} for ban...")
        bot.loop.create_task(track_account(ctx, username, "ban"))
    else:
        await ctx.send(f"✱ @{username} is already banned.")


@bot.command()
async def unban(ctx, username: str):
    """Track an Instagram account for unban."""
    username = username.lstrip("@")

    if await get_instagram_details(username) is None:
        await ctx.send(f"★ Tracking @{username} for unban...")
        bot.loop.create_task(track_account(ctx, username, "unban"))
    else:
        await ctx.send(f"✱ @{username} is already active.\n🔗 **View Profile:** [Click Here](https://www.instagram.com/{username}/)")


@bot.command()
async def tracking(ctx):
    """Show currently tracked accounts."""
    cursor.execute("SELECT username FROM tracking WHERE user_id=?", (ctx.author.id,))
    accounts = cursor.fetchall()
    if not accounts:
        await ctx.send("☀ No accounts currently being tracked.")
    else:
        await ctx.send("☀ Currently tracking:\n" + "\n".join([f"✱ @{a[0]}" for a in accounts]))


@bot.command()
async def history(ctx):
    """Show tracking history."""
    cursor.execute("SELECT username, event, timestamp FROM history WHERE user_id=? ORDER BY timestamp DESC LIMIT 10", (ctx.author.id,))
    records = cursor.fetchall()
    if not records:
        await ctx.send("❖ No tracking history available.")
    else:
        history_text = "\n".join([f"✈ @{r[0]} ➢ {r[1]} ({time.strftime('%b %d', time.localtime(r[2]))})" for r in records])
        await ctx.send(f"☯ Tracking History ☯\n{history_text}")


@bot.command()
async def stop(ctx, username: str):
    """Stop tracking an account."""
    username = username.lstrip("@")
    cursor.execute("DELETE FROM tracking WHERE user_id=? AND username=?", (ctx.author.id, username))
    conn.commit()
    await ctx.send(f"❖ Stopped tracking @{username}.")


@bot.command()
async def info(ctx, username: str):
    """Fetch and display Instagram profile information."""
    username = username.lstrip("@")

    try:
        data = await get_instagram_details(username)

        if data:
            profile_pic_url = data.get("profile_pic_url")

            response_text = (
                f"**User Information**\n"
                f"\n"
                f"**Username:** @{username}\n"
                f"**Name:** {data.get('name', 'N/A')}\n"
                f"**Followers:** {data['followers']:,}\n"
                f"**Following:** {data['following']:,}\n"
                f"**Posts:** {data['posts']}\n"
                f"**Verified:** {'Yes' if data['verified'] else 'No'}\n"
                f"**Account Type:** {'Private' if data['private'] else 'Public'}\n"
            )

            if profile_pic_url:
                response_text += f"\n**Profile Pic:** [Download Link]({profile_pic_url})"

            await ctx.send(response_text, suppress_embeds=True)
        else:
            await ctx.send(f"Unable to fetch info for @{username}. This might be a private or non-existent account.")

    except Exception as e:
        await ctx.send(f"Error fetching details for @{username}. Try again later.")
        print(f"Error in /info command: {e}")  # Logs error for debugging


# Run the bot
bot.run(TOKEN)
