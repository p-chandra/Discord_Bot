import os
import discord
from discord.ext import commands
import random

from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user.name} Bot is ready.")


# Input a even number of elements in a list and displays two teams of random elements
@bot.command()
async def team(ctx, *players):
    if len(players) % 2 != 0:
        await ctx.send("Please enter an even number of members.")
        return

    player_list = list(players)
    random.shuffle(player_list)
    half = len(player_list) // 2

    await ctx.send("*Team One   --vs--   Team Two*\n")
    for left, right in zip(player_list[:half], player_list[half:]):
        await ctx.send(f"|{left:^20}  ----  {right:^20}|")


# Displays the creator of this bot
@bot.command()
async def creator(ctx):
    await ctx.reply("Hi, I am a coding bot created by Sphrial")


# Displays a list of all the server this bot is connected to
@bot.command()
async def getserver(ctx):
    for guild in bot.guilds:
        await ctx.send(str(guild))


# Enter a channel name and it will display the userID of that channel
@bot.command()
async def getchanuserid(ctx, name: str):
    channels = [channel for guild in bot.guilds for channel in guild.channels]
    channel = discord.utils.find(lambda c: c.name == name, channels)
    if channel is not None:
        await ctx.send(str(channel.id))


# Enter a members name and it will display the userID of that member
@bot.command()
async def getmemuserid(ctx, name: str):
    members = [member for guild in bot.guilds for member in guild.members]
    member = discord.utils.find(lambda m: m.name == name, members)
    if member is not None:
        await ctx.send(str(member.id))


# Displays a list of all members and their status
@bot.command()
async def getmem(ctx):
    for guild in bot.guilds:
        for member in guild.members:
            await ctx.send(f"{member.status:<15} -- {member.name}")


# Displays a list of all members that are online
@bot.command()
async def online(ctx):
    for guild in bot.guilds:
        for member in guild.members:
            if member.status == discord.Status.online:
                await ctx.send(f"{member.name} -- {member.status}")


# Displays a list of all members that are online
@bot.command()
async def offline(ctx):
    for guild in bot.guilds:
        for member in guild.members:
            if member.status == discord.Status.offline:
                await ctx.send(f"{member.name} -- {member.status}")


# Displays a list of all members that are offline
@bot.command()
async def getchan(ctx):
    for guild in bot.guilds:
        for channel in guild.channels:
            await ctx.send(str(channel))


# Displays a list of all the voice channels
@bot.command()
async def getvoicechan(ctx):
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type == discord.ChannelType.voice:
                await ctx.send(str(channel))


# Enter a @username and channel name that you would like to move them too
@bot.command()
async def move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    await member.move_to(channel)
    await ctx.send(f"Moved {member.display_name} to {channel.name}.")


@bot.command()
async def custom(ctx):
    await ctx.send("Type 'join' to enter the game and 'done' once done with the list")
    teamlist = []

    def teamcheck(msg):
        return msg.channel == ctx.channel and msg.content in {"join", "done"}

    while len(teamlist) <= 12:
        teamplayer = await bot.wait_for("message", check=teamcheck)
        if teamplayer.content == "done":
            await ctx.send("Getting Teams Ready")
            break
        if teamplayer.author not in teamlist:
            teamlist.append(teamplayer.author)
            await ctx.send(f"{len(teamlist)} player(s) in")
        else:
            await ctx.send("User already in team")

    random.shuffle(teamlist)
    channels = [channel for guild in bot.guilds for channel in guild.channels]
    channel = discord.utils.find(lambda c: c.name == "Overwatch 2", channels)

    if channel is None:
        await ctx.send("Could not find the Overwatch 2 voice channel.")
        return

    for index, player in enumerate(teamlist):
        if index % 2 == 0 and isinstance(player, discord.Member):
            await player.move_to(channel)


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in the .env file.")

bot.run(TOKEN)
