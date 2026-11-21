# Setup for the Discord bot
#
# Install Python 3, FFmpeg, and Node.js. This setup was tested with Python 3.14
# and Node.js 22. On Ubuntu/Debian, install FFmpeg with sudo apt install ffmpeg.
# Make sure both ffmpeg and node are on PATH.
#
# Install the Python packages with the same interpreter that runs this script.
#   python3 -m pip install 'discord.py[voice]==2.7.1' 'davey>=0.1.6,<0.2' python-dotenv 'yt-dlp[default]'
#
# The voice extra installs PyNaCl. Keep davey below 0.2 with discord.py 2.7.1
# to avoid silent voice playback. The yt-dlp default extra includes the
# YouTube challenge scripts, which this bot can run with Node.js.
#
# Put DISCORD_TOKEN=your_bot_token in a .env file beside this script.
# Enable Presence, Server Members, and Message Content in the Discord
# Developer Portal. Give the bot View Channel, Connect, and Speak permissions
# in the voice channel, then start it with python3 2025-Discord.py.

import os
import asyncio
import shutil
import traceback
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
BUNDLED_FFMPEG = BASE_DIR / "FFmpeg" / "bin" / "ffmpeg.exe"
FFMPEG_PATH = str(BUNDLED_FFMPEG) if os.name == "nt" and BUNDLED_FFMPEG.is_file() else shutil.which("ffmpeg")

RULES_FILE = BASE_DIR / "rules.txt"

load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in the .env file.")

# Do not print the token directly; it is sensitive.
print("Discord token loaded; starting bot...")

# Commands use the "." prefix, as in .play.
bot = commands.Bot(command_prefix=".", intents=discord.Intents.all(), help_command=None)


@dataclass(frozen=True)
class YouTubeTrack:
    title: str
    page_url: str


def resolve_youtube(query):
    from yt_dlp import YoutubeDL

    options = {
        "format": "bestaudio[protocol=https]/best[protocol=https]",
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 10,
        "retries": 1,
    }
    if node := shutil.which("node"):
        options["js_runtimes"] = {"node": {"path": node}}

    with YoutubeDL(options) as downloader:
        result = downloader.extract_info(query, download=False)

    if result and "entries" in result:
        result = next(iter(result["entries"]), None)
    if not result or not result.get("url", "").startswith("https://"):
        raise ValueError("No playable YouTube result.")

    return YouTubeTrack(result["title"], result["webpage_url"]), result["url"]


def read_text_file(path):
    return path.read_text(encoding="utf-8")


# When bot is online print ready
@bot.event
async def on_ready(): 
    print("Bot is Ready!")


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Error in event {event}:")
    traceback.print_exc()


@bot.command(name="help")
async def show_help(ctx):
    await ctx.send(
        "**Voice and local music**\n"
        "`.play <song name>` — Search YouTube and play the first result in voice.\n"
        "`.resume` — Resume paused audio.\n"
        "`.pause` — Pause voice playback.\n"
        "`.leave` — Disconnect from voice.\n"
        "\n**Chat and server**\n"
        "`.info` — Show information about this server.\n"
        "`.rules <number|all>` (`.rule`) — Show one server rule or all rules.\n"
        "\n**Utilities**\n"
        "`.help` — Show this command list."
    )


@bot.command()
async def info(ctx):
    guild = ctx.guild
    if guild is None:
        return await ctx.send("Use `.info` in a server to see its information.")

    overview = discord.Embed(title=guild.name, description=guild.description)
    if guild.icon:
        overview.set_thumbnail(url=guild.icon.url)

    overview.add_field(name="Server ID", value=str(guild.id))
    overview.add_field(name="Owner", value=f"<@{guild.owner_id}>")
    overview.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, "D"))
    overview.add_field(name="Members", value=str(guild.member_count or len(guild.members)))
    overview.add_field(name="Roles", value=str(len(guild.roles) - 1))
    overview.add_field(name="Emojis", value=str(len(guild.emojis)))
    overview.add_field(
        name="Channels",
        value=f"{len(guild.text_channels)} text · {len(guild.voice_channels)} voice · "
              f"{len(guild.stage_channels)} stage · {len(guild.forums)} forum · "
              f"{len(guild.categories)} categories",
        inline=False,
    )
    overview.add_field(name="Boost level", value=f"Level {guild.premium_tier} · {guild.premium_subscription_count or 0} boosts")
    overview.add_field(name="Verification level", value=str(guild.verification_level).replace("_", " ").title())
    await ctx.send(embed=overview)


# This command displays the rules for the server.
@bot.command(aliases=['rules'])
async def rule(ctx, *, number):
    try:
        rules = [line for line in read_text_file(RULES_FILE).splitlines() if line.strip()]
    except FileNotFoundError:
        await ctx.send("rules.txt not found.")
        return

    count = len(rules)

    # check if the rule number argument is a numeric value.
    if number.isnumeric():
        idx = int(number) - 1
        if 0 <= idx < count:
            await ctx.send(rules[idx])
        else:
            await ctx.send(f"There is no rule {number}. So far there are only {count} rules.")
    # the number argument is a string so check to if string equals "all".
    elif number.lower() == "all":
        for rule_text in rules:
            await ctx.send(rule_text)
    else:
        await ctx.send("Please provide a rule number or `all`.")


@rule.error
async def rule_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You need to type in '.rules #'")


async def play_voice_track(ctx, voice_client, track, *, stream_url):
    source = None
    try:
        source = FFmpegPCMAudio(
            stream_url,
            executable=FFMPEG_PATH,
            before_options=(
                "-rw_timeout 10000000 -reconnect 1 -reconnect_on_network_error 1 "
                "-reconnect_streamed 1 -reconnect_delay_max 5 -reconnect_max_retries 3"
            ),
        )
        voice_client.stop()
        voice_client.play(source)
    except (OSError, discord.DiscordException):
        if source is not None:
            source.cleanup()
        traceback.print_exc()
        return await ctx.send("I couldn't start playback. Check the bot logs for details.")

    title = discord.utils.escape_markdown(track.title)
    await ctx.send(f"Now playing: {title} (<{track.page_url}>)", allowed_mentions=discord.AllowedMentions.none())


async def join_and_play(ctx, track, *, stream_url):
    if not FFMPEG_PATH:
        return await ctx.send("FFmpeg is required to play music.")

    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        voice = getattr(ctx.author, "voice", None)
        if voice is None or voice.channel is None:
            return await ctx.send("Join a server voice channel first, then retry your command.")

        if discord.version_info[:2] < (2, 7) or find_spec("davey") is None:
            print(f"Discord voice requires DAVE support. Loaded discord.py {discord.__version__} from {discord.__file__}.")
            print("Install 'discord.py[voice]>=2.7' and 'davey>=0.1.6,<0.2' for this Python interpreter, then restart it.")
            return await ctx.send("Voice requires Discord's DAVE encryption support. Check the bot terminal for details.")

        channel = voice.channel
        permissions = channel.permissions_for(ctx.guild.me)
        if not (permissions.view_channel and permissions.connect and permissions.speak):
            return await ctx.send("I need View Channel, Connect, and Speak permissions in your voice channel.")

        try:
            voice_client = await channel.connect()
        except (asyncio.TimeoutError, discord.DiscordException):
            traceback.print_exc()
            return await ctx.send("I couldn't connect to your voice channel. Check the bot logs for details.")

    await play_voice_track(ctx, voice_client, track, stream_url=stream_url)


#(PART 3) Make discord bot leave VC
@bot.command(pass_context=True)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Adios :)")
    else:
        await ctx.send("Something went wrong and I cant leave")

#(PART 4) Play a song in VC
@bot.command(pass_context=True)
async def play(ctx, *, search: str = None):
    query = (search or "").strip()
    if not query:
        return await ctx.send("Enter a song name, for example `.play The Summoning`.")

    if find_spec("yt_dlp") is None:
        return await ctx.send("Install yt-dlp to enable YouTube search.")
    try:
        async with ctx.typing():
            track, stream_url = await asyncio.to_thread(resolve_youtube, f"ytsearch1:{query}")
    except Exception:
        traceback.print_exc()
        return await ctx.send("I couldn't find a playable YouTube result. Check the bot logs for details.")

    await join_and_play(ctx, track, stream_url=stream_url)


@bot.command()
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("Use `.play <song name>` to connect me first.")

    if not voice_client.is_playing():
        return await ctx.send("Nothing is playing.")

    voice_client.pause()
    await ctx.send("Playback paused. Use `.resume` to resume.")


@bot.command()
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("Use `.play <song name>` to connect me first.")
    if not voice_client.is_paused():
        return await ctx.send("Nothing is paused. Use `.play <song name>` to start a song.")
    voice_client.resume()
    await ctx.send("Playback resumed.")


# PLEASE READ THIS
### EMAIL ###
# THIS command goes to my email, looks for emails from steam and prints the first few lines


bot.run(TOKEN)
