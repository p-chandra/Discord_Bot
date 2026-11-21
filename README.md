# Discord-Bot---Python

## Raspberry Pi voice channels

On Raspberry Pi OS, install FFmpeg and the Python dependencies. If you already
have a virtual environment for the bot, activate it and skip the environment
creation step.

```bash
sudo apt install ffmpeg python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U 'discord.py[voice]>=2.7' 'davey>=0.1.6,<0.2' python-dotenv
```

The `davey` pin avoids silent playback with discord.py 2.7.1.
See [the upstream compatibility fix](https://github.com/Rapptz/discord.py/pull/10548).

Set `DISCORD_TOKEN` in `.env` beside `2024-Discord.py`. Enable the **Presence**,
**Server Members**, and **Message Content** privileged intents in the Discord
Developer Portal because the script requests all intents. Run
`python 2024-Discord.py`. Use `.download` to upload the song currently
playing in voice to `#general`. The command uploads nothing while playback
is idle or paused.
To play it in voice, join a server voice channel and type `.play` or `.play <song name>` in a text
channel the bot can read and reply in. The bot joins your voice channel if it
is disconnected and plays in its current voice channel if it is already connected.
It needs **View Channel**, **Connect**, and **Speak** in the voice channel. Use
`.leave` to disconnect.

For YouTube fallback on `.play <song name>`, install `yt-dlp[default]` in the
same Python environment and have a supported Node.js or Deno on PATH. Local
MP3 matches take priority. Use YouTube playback for content you're authorized
to stream. `.download` attaches local files only.

Discord's documented bot interface does not support publishing a live webcam
feed into a voice channel. To share the Pi camera in the call, join using the
regular Discord client on a device that can access the camera and turn on
video there.

## Project 1 - Calculator
The objective for this bot is to calculate basic arithmetic inside the discord server. The bot can also convert Hex to Binary and give ascii value. This bot was build to practice python and I have no plans to update or add more features.

Example command
```
!cal 1 + 23 / 3 * 4
```


## Project 2
The main purpose of this bot is to randomly generate 2 teams and move players accordingly to their appropriate chat channel. This project idea came from playing custom team games where we would waste time picking team captains or spend time randomizing teams. 

The way the bot works is first you type ``` $custom ```. This will allow the bot to listen for anyone entering the command ```join```. When all the players in discord have entered the command join, the user then types ```done```. The bot will then randomly select half of the people joined and move them to a different chat.

There are few small codes that i wrote to help anyone new understand how things work. Play arround with it!

I do not plan to continue this project for the same reasons stated above in project 1.
