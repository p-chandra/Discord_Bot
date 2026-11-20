import os
import asyncio
import random
import shutil
import traceback
from importlib.util import find_spec
from pathlib import Path
from weakref import WeakKeyDictionary

import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
MUSIC_DIR = BASE_DIR / "Music"
IPOD_DIR = Path(os.getenv("IPOD_MUSIC_DIR", r"E:\Music-Old-IPod"))
BUNDLED_FFMPEG = BASE_DIR / "FFmpeg" / "bin" / "ffmpeg.exe"
FFMPEG_PATH = str(BUNDLED_FFMPEG) if os.name == "nt" and BUNDLED_FFMPEG.is_file() else shutil.which("ffmpeg")

RULES_FILE = BASE_DIR / "rules.txt"

load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in the .env file.")

# Do not print the token directly; it is sensitive.
print("Discord token loaded; starting bot...")

# pip install 'discord.py[voice]>=2.7' 'davey>=0.1.6,<0.2' python-dotenv

# Commands use the "." prefix, as in .play.
bot = commands.Bot(command_prefix=".", intents=discord.Intents.all(), help_command=None)
voice_history = WeakKeyDictionary()


def read_text_file(path):
    return path.read_text(encoding="utf-8")


def list_files(directory):
    if not directory.exists():
        return []
    return [path for path in directory.iterdir() if path.is_file()]


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
        "`.play` — Play a random local song in voice. I'll join your channel if needed.\n"
        "`.play <song name>` — Find and play a local MP3 in voice.\n"
        "`.download` — Upload the currently playing song to #general.\n"
        "`.resume` — Resume paused audio.\n"
        "`.pause` — Pause voice playback.\n"
        "`.next` — Play another random local song.\n"
        "`.back` — Replay the previous song.\n"
        "`.leave` — Disconnect from voice.\n"
        "\n**Chat and server**\n"
        "`.info` — Show information about this server.\n"
        "`.rules <number|all>` (`.rule`) — Show one server rule or all rules.\n"
        "\n**Utilities**\n"
        "`.arg <words>` — Count and echo the arguments you enter.\n"
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


async def play_voice_track(ctx, voice_client, track, *, back=False):
    if not FFMPEG_PATH:
        return await ctx.send("FFmpeg is required to play music.")

    source = None
    try:
        source = FFmpegPCMAudio(str(track), executable=FFMPEG_PATH)
        voice_client.stop()
        voice_client.play(source)
    except (OSError, discord.DiscordException):
        if source is not None:
            source.cleanup()
        traceback.print_exc()
        return await ctx.send("I couldn't start playback. Check the bot logs for details.")

    history = voice_history.setdefault(voice_client, [])
    if back:
        history.pop()
    else:
        history.append(track)
    await ctx.send(f"Now playing: `{track.name}`")


async def join_and_play(ctx, track):
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

    await play_voice_track(ctx, voice_client, track)


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
    query = (search or "").strip().lower()
    if query in ("", "vc"):
        files = list_files(MUSIC_DIR)
        if not files:
            return await ctx.send("No local music files found.")
        return await join_and_play(ctx, random.choice(files))

    files = list(IPOD_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.mp3"))
    match = next((path for path in files if query in path.name.lower()), None)

    if not match:
        return await ctx.send(f"No matching MP3 found for `{search}`.")
    
    await join_and_play(ctx, match)


@bot.command()
async def download(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected() or not voice_client.is_playing():
        return await ctx.send("There's no song playing to download.")

    history = voice_history.get(voice_client)
    if not history or not history[-1].is_file():
        return await ctx.send("The currently playing song isn't available to download.")

    general = discord.utils.get(ctx.guild.text_channels, name="general")
    if general is None:
        return await ctx.send("I couldn't find a #general text channel in this server.")

    try:
        await general.send(file=discord.File(history[-1]))
    except discord.Forbidden:
        return await ctx.send("I need permission to send messages and attach files in #general.")


@bot.command()
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("Use `.play` to connect me first.")

    if not voice_client.is_playing():
        return await ctx.send("Nothing is playing.")

    voice_client.pause()
    await ctx.send("Playback paused. Use `.resume` to resume.")


@bot.command()
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("Use `.play` to connect me first.")
    if not voice_client.is_paused():
        return await ctx.send("Nothing is paused. Use `.play` to start a song.")
    voice_client.resume()
    await ctx.send("Playback resumed.")


@bot.command(name="next")
async def next_track(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("Use `.play` to connect me first.")

    history = voice_history.get(voice_client, [])
    current = history[-1] if history else None
    tracks = [track for track in list_files(MUSIC_DIR) if track != current]
    if not tracks:
        return await ctx.send("No other local songs found.")

    await play_voice_track(ctx, voice_client, random.choice(tracks))


@bot.command()
async def back(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("Use `.play` to connect me first.")

    history = voice_history.get(voice_client, [])
    if len(history) < 2:
        return await ctx.send("There's no previous song in this voice session.")

    await play_voice_track(ctx, voice_client, history[-2], back=True)

#USEFUL debugging command. This command counts the number of arguements passed to arg.
@bot.command()
async def arg(ctx, *args):
    await ctx.send(f"{len(args)} arguments: {', '.join(args)}")






# PLEASE READ THIS
### EMAIL ###
# THIS command goes to my email, looks for emails from steam and prints the first few lines


bot.run(TOKEN)
