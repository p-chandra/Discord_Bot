import os
import asyncio
import random
import traceback
from pathlib import Path

import discord
import spotipy
from discord import FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_DIR = Path(__file__).resolve().parent
FRIENDS_DIR = BASE_DIR / "Friends"
MUSIC_DIR = BASE_DIR / "music"
IPOD_DIR = Path(os.getenv("IPOD_MUSIC_DIR", r"E:\Music-Old-IPod"))
FFMPEG_PATH = BASE_DIR / "FFmpeg" / "bin" / "ffmpeg.exe"

RULES_FILE = BASE_DIR / "rules.txt"
SKIN_CARE_FILE = BASE_DIR / "Skin_Care.txt"
HAPPY_FILE = BASE_DIR / "happy.txt"
COCONUT_IMAGE = BASE_DIR / "coconut.png"
GMAIL_TOKEN_FILE = BASE_DIR / "token.json"
GMAIL_CREDENTIALS_FILE = BASE_DIR / "credentials.json"

load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in the .env file.")

# Do not print the token directly; it is sensitive.
print("Discord token loaded; starting bot...")

# pip install pynacl python-dotenv discord.py spotipy
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SPOTIFY_SCOPE = "user-modify-playback-state user-read-playback-state"

# BOT PREFIX as in this is the symbol you must enter before a command. Ex .join .play
bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())


def read_text_file(path):
    return path.read_text(encoding="utf-8")


def list_files(directory):
    if not directory.exists():
        return []
    return [path for path in directory.iterdir() if path.is_file()]


def get_spotify_client():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        return None

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SPOTIFY_SCOPE,
        )
    )


# When bot is online print ready
@bot.event
async def on_ready(): 
    print("Bot is Ready!")


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Error in event {event}:")
    traceback.print_exc()


# This command responds to the user who says hello
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}")


# aliases just means that you can call this function with other names. 
# In this case I gave the aliase a list of names I can use to call this function
@bot.command(aliases=["gm", "morning"])
async def goodmorning(ctx):
    await ctx.send(f"Good Morning, {ctx.author.mention}!")

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

#This command tells you what skin care you should use
@bot.command(aliases=['skinroutine','skin'])
async def skincare(ctx):
    try:
        skin_routine = read_text_file(SKIN_CARE_FILE)
    except FileNotFoundError:
        await ctx.send("Skin_Care.txt not found.")
        return

    await ctx.send(skin_routine)


@bot.command(aliases=['suicide'])
async def kms(ctx):
    try:
        lines = [line.strip() for line in read_text_file(HAPPY_FILE).splitlines() if line.strip()]
    except FileNotFoundError:
        await ctx.send("happy.txt not found.")
        return

    if not lines:
        await ctx.send("happy.txt is empty.")
        return

    await ctx.send(random.choice(lines))


#This is just to show a picture of coconut. you can type .theboy or .cocoboy
@bot.command(aliases=["theboy","cocoboy"])
async def coconut(ctx):
    await ctx.send(file=discord.File(COCONUT_IMAGE))

# This command goes inside the directory declare above "friends" and pics a picture open up randomly
# Though its odd because I dont specify the file type, it just opens up that file regardless 
#
# files = [f for f in files if os.path.isfile(os.path.join(directory, f))] 
#
# line 64 filters out directories and keeps only files so it opens only files
@bot.command()
async def friends(ctx):
    files = list_files(FRIENDS_DIR)
    if not files:
        await ctx.send("No friend pictures found.")
        return

    await ctx.send(file=discord.File(random.choice(files)))

#(PART 1) This command goes to my local folder and plays a song
@bot.command()
async def music(ctx):
    files = list_files(MUSIC_DIR)
    if not files:
        await ctx.send("No local music files found.")
        return

    await ctx.send(file=discord.File(random.choice(files)))

#(PART 2) Have discord bot join VC. Note you must be in VC for it to join
@bot.command(pass_context=True)
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("You gotta be in VC so I can join panget!")

    if ctx.voice_client and ctx.voice_client.is_connected():
        return await ctx.send("I am already in a voice channel.")

    channel = ctx.message.author.voice.channel
    await channel.connect()
    await asyncio.sleep(0.5)  # Wait for the voice client to be fully connected

    # if you check ffmpeg --version it will not show up. You need to add it to the path or point to the executable.
    hello_mp3_path = MUSIC_DIR / "hello.mp3"
    source = FFmpegPCMAudio(str(hello_mp3_path), executable=str(FFMPEG_PATH))  # Plays this audio upon joining
    ctx.voice_client.play(source)

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
    if not search:
        return await ctx.send("Please provide a song name, like `.play song_name`.")

    if not ctx.author.voice:
        return await ctx.send("You need to join a voice channel first.")

    if ctx.voice_client is None:
        return await ctx.send("I'm not connected to a voice channel. Use `.join` first.")

    # Search for file (case-insensitive match)
    files = list(IPOD_DIR.glob("*.mp3"))
    match = next((path for path in files if search.lower() in path.name.lower()), None)

    if not match:
        return await ctx.send(f"No matching MP3 found for `{search}`.")
    
    source = discord.FFmpegPCMAudio(str(match), executable=str(FFMPEG_PATH))
    ctx.voice_client.stop()  # stop any current audio
    ctx.voice_client.play(source)

    await ctx.send(f"Now playing: `{match.name}`")

#USEFUL debugging command. This command counts the number of arguements passed to arg.
@bot.command()
async def arg(ctx, *args):
    await ctx.send(f"{len(args)} arguments: {', '.join(args)}")






# PLEASE READ THIS
### EMAIL ###
# THIS command goes to my email, looks for emails from steam and prints the first few lines


@bot.command()
async def email(ctx):
    # Define the scope for Gmail API
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    query = f'subject:"{"Steam"}"'
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if GMAIL_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GMAIL_CREDENTIALS_FILE.exists():
                await ctx.send("credentials.json not found.")
                return

            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        GMAIL_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    try:
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
        messages = results.get('messages', [])

        if not messages:
            await ctx.send('No emails found')
            return

        latest_message_id = messages[0]['id']
        msg = service.users().messages().get(userId='me', id=latest_message_id).execute()

        # Extract and print email details
        headers = msg['payload'].get('headers', [])
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
        snippet = msg.get('snippet', '')

        await ctx.send(f"Subject: {subject}")
        await ctx.send(f"Snippet: {snippet}")
        # Reading all emails associated with the subject
        #for message in messages:
        #    msg = service.users().messages().get(userId='me', id=message['id']).execute()
        #    headers = msg['payload'].get('headers', [])
        #    for header in headers:
        #        if header['name'] == 'Subject':
        #            print(f"Subject: {header['value']}")
        #    snippet = msg.get('snippet', '')
        #    print(f"Snippet: {snippet}")

    except HttpError as error:
        await ctx.send(f"An error occurred: {error}")





# PLEASE READ
### SPOTIFY ###
# This feature allows you to control your spotify with your discord bot
# It unfortunately cannot play music through discord


@bot.command(name="playsp")
async def playsp(ctx, *, query: str):
    """Play a song on Spotify"""
    sp = get_spotify_client()
    if sp is None:
        await ctx.send("Spotify credentials are not configured.")
        return

    results = sp.search(q=query, type="track", limit=1)
    if results["tracks"]["items"]:
        track = results["tracks"]["items"][0]
        track_uri = track["uri"]
        
        devices = sp.devices()
        if not devices["devices"]:
            await ctx.send("No active Spotify device found. Open Spotify on a device.")
            return
        
        device_id = devices["devices"][0]["id"]
        sp.start_playback(device_id=device_id, uris=[track_uri])

        await ctx.send(f"Now playing: {track['name']} by {track['artists'][0]['name']}")
    else:
        await ctx.send("Song not found.")

@bot.command(name="pause")
async def pausesp(ctx):
    """Pause playback on Spotify"""
    sp = get_spotify_client()
    if sp is None:
        await ctx.send("Spotify credentials are not configured.")
        return

    sp.pause_playback()
    await ctx.send("Playback paused.")

@bot.command(name="resume")
async def resumesp(ctx):
    """Resume playback on Spotify"""
    sp = get_spotify_client()
    if sp is None:
        await ctx.send("Spotify credentials are not configured.")
        return

    sp.start_playback()
    await ctx.send("Playback resumed.")

@bot.command(name="skip")
async def skipsp(ctx):
    """Skip to the next song"""
    sp = get_spotify_client()
    if sp is None:
        await ctx.send("Spotify credentials are not configured.")
        return

    sp.next_track()
    await ctx.send("Skipped to the next track.")
    
bot.run(TOKEN)
