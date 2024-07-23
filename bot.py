import nextcord
from nextcord.ext import commands
import os
import json
from datetime import datetime
import logging

# Load configuration
with open('config.json') as f:
    config = json.load(f)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create output folder if it doesn't exist
os.makedirs(config["outputFolder"], exist_ok=True)

# Bot setup
intents = nextcord.Intents.default()
intents.messages = True
client = commands.Bot(command_prefix=config["prefix"], intents=intents)

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')

async def fetch_all_messages(channel, limit=None):
    messages = []
    async for message in channel.history(limit=None):
        messages.append(message)
        if limit and len(messages) >= limit:
            break
    return messages

@client.event
async def on_message(message):
    if not message.content.startswith(config["prefix"]) or message.author.bot:
        return

    await client.process_commands(message)

@client.slash_command(description="Scrape attachments")
async def scrape(ctx, videos_only: bool = False, message_amount: str = "all"):
    await ctx.response.defer()

    if message_amount.lower() == "all":
        message_amount = None
        logger.info("Fetching all messages...")
    else:
        message_amount = int(message_amount)
        logger.info(f"Fetching {message_amount} messages...")

    messages = await fetch_all_messages(ctx.channel, message_amount)
    links = []

    for msg in reversed(messages):
        found = [url for url in msg.content.split() if 'discordapp' in url]
        if found:
            links.extend(found)
            logger.info(f"Found link: {found} (total: {len(links)})")

        for attachment in msg.attachments:
            links.append(attachment.url)
            logger.info(f"Found attachment: {attachment.url} (total: {len(links)})")

    if videos_only:
        links = [link for link in links if link.split('.')[-1].lower() in config["videoFormats"]]
    
    links = [link for link in links if not any(keyword in link for keyword in config["excludeKeywords"])]

    filename = f"{config['outputFolder']}/discord_cdn_links-{datetime.now().strftime('%Y-%m-%d')}_{ctx.channel.id}.txt"
    if links:
        with open(filename, 'w') as f:
            f.write('\n \n'.join(links))
        logger.info(f"Scrape completed and links saved to {filename}\nTotal links found: {len(links)}")
        file = nextcord.File(filename)
        await ctx.send(f"Scrape completed and links saved to `{filename}`. Total links found: {len(links)}", file=file)
    else:
        logger.warning("Scrape completed but no links were found.")
        await ctx.send("Scrape completed but no links were found.")

client.run(config["token"])