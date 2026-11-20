"""Open a Discord voice-channel link in Chromium."""

import argparse
import re
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel_url", help="The Discord voice channel's copied link")
    parser.add_argument("--browser", help="Path or command name for Chromium")
    args = parser.parse_args()

    if not re.fullmatch(r"https://discord\.com/channels/[0-9]+/[0-9]+/?", args.channel_url):
        parser.error("Use a Discord channel link: https://discord.com/channels/SERVER_ID/CHANNEL_ID")

    browser = args.browser or shutil.which("chromium") or shutil.which("chromium-browser")
    if not browser:
        parser.error("Chromium was not found. Install it or specify --browser.")

    try:
        subprocess.Popen([browser, args.channel_url])
    except OSError as error:
        parser.exit(1, f"Could not launch Chromium: {error}\n")


if __name__ == "__main__":
    main()
