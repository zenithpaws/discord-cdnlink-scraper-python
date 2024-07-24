import nextcord
from nextcord.ext import commands
import os
import json
from datetime import datetime
import logging
import aiohttp
from urllib.parse import urlparse

# Load configuration
with open('config.json') as f:
    config = json.load(f)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create output folders if they don't exist
os.makedirs(config["outputFolder"], exist_ok=True)
os.makedirs("output_downloaded", exist_ok=True)  # Main download folder

# Bot setup
intents = nextcord.Intents.all()
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

def get_file_extension(url):
    """Extract file extension from a URL."""
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    return ext[1:].lower()  # Remove the dot and convert to lower case

# Helper function to get a unique file path
def get_unique_file_path(folder, file_name):
    base, ext = os.path.splitext(file_name)
    counter = 1
    new_file_name = file_name
    while os.path.exists(os.path.join(folder, new_file_name)):
        new_file_name = f"{base}_{counter}{ext}"
        counter += 1
    return new_file_name

@client.slash_command(description="Scrape attachments")
async def scrape(ctx, file_types: str = nextcord.SlashOption(default="all", choices=["images", "audio", "videos", "all"], description="The files types to scrape"), message_amount: str = nextcord.SlashOption(default="all", description="The amount of messages to scrape")):
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

    logger.info(f"File types selected: {file_types}")

    # Filter by file types based on the category
    if file_types == "images":
        valid_formats = config["imageFormats"]
    elif file_types == "audio":
        valid_formats = config["audioFormats"]
    elif file_types == "videos":
        valid_formats = config["videoFormats"]
    else:  # "all"
        valid_formats = []

    logger.info(f"Valid formats: {valid_formats}")

    # Extract file extension more reliably
    def get_file_extension(url):
        path = urlparse(url).path
        _, ext = os.path.splitext(path)
        return ext[1:].lower()  # Remove the dot and convert to lower case

    if valid_formats:
        links = [link for link in links if get_file_extension(link) in valid_formats]
    
    logger.info(f"Links after format filter: {links}")

    # Filter by exclude keywords
    links = [link for link in links if not any(keyword in link for keyword in config["excludeKeywords"])]

    logger.info(f"Links after exclude filter: {links}")

    # Create server and channel specific folders
    guild_name = ctx.guild.name.replace('/', '_').replace('\\', '_')  # Clean up special characters
    channel_name = ctx.channel.name.replace('/', '_').replace('\\', '_')  # Clean up special characters
    base_folder = f"{config['outputFolder']}/{guild_name}/{channel_name}"
    os.makedirs(base_folder, exist_ok=True)

    # Create log filename
    if file_types == "all":
        log_filename = f"{base_folder}/scrape_links_{datetime.now().strftime('%Y-%m-%d')}.txt"
    else:
        log_filename = f"{base_folder}/scrape_links_{datetime.now().strftime('%Y-%m-%d')}_{file_types}.txt"

    # Write the log file
    with open(log_filename, 'w') as f:
        if links:
            f.write('\n\n'.join(f'"{link}"' for link in links))
            logger.info(f"Scrape completed and links saved to {log_filename}\nTotal links found: {len(links)}")
            file = nextcord.File(log_filename)
            await ctx.send(f"Scrape completed and links saved to `{log_filename}`. Total links found: {len(links)}", file=file)
        else:
            logger.warning("Scrape completed but no links were found.")
            await ctx.send("Scrape completed but no links were found.")

@client.slash_command(description="Scrape attachments from all channels in the server")
async def serverwidescrape(ctx, file_types: str = nextcord.SlashOption(default="all", choices=["images", "audio", "videos", "all"], description="The file types to scrape"), message_amount: str = nextcord.SlashOption(default="all", description="The amount of messages to scrape")):
    await ctx.response.defer()

    # Create server folder
    guild_name = ctx.guild.name.replace('/', '_').replace('\\', '_')  # Clean up special characters
    base_folder = f"{config['outputFolder']}/{guild_name}"
    os.makedirs(base_folder, exist_ok=True)

    # Define log file for the entire server
    if file_types == "all":
        server_log_filename = f"{base_folder}/scrape_links_all_channels_{datetime.now().strftime('%Y-%m-%d')}.txt"
    else:
        server_log_filename = f"{base_folder}/scrape_links_all_channels_{datetime.now().strftime('%Y-%m-%d')}_{file_types}.txt"

    all_links = []

    for channel in ctx.guild.text_channels:
        logger.info(f"Scraping channel: {channel.name} ({channel.id})")

        try:
            # Fetch messages and links from the channel
            messages = await fetch_all_messages(channel, int(message_amount) if message_amount.lower() != "all" else None)
            links = []

            for msg in reversed(messages):
                found = [url for url in msg.content.split() if 'discordapp' in url]
                if found:
                    links.extend(found)
                    logger.info(f"Found link: {found} (total: {len(links)})")

                for attachment in msg.attachments:
                    links.append(attachment.url)
                    logger.info(f"Found attachment: {attachment.url} (total: {len(links)})")

            logger.info(f"File types selected: {file_types}")

            # Filter by file types based on the category
            if file_types == "images":
                valid_formats = config["imageFormats"]
            elif file_types == "audio":
                valid_formats = config["audioFormats"]
            elif file_types == "videos":
                valid_formats = config["videoFormats"]
            else:  # "all"
                valid_formats = []

            logger.info(f"Valid formats: {valid_formats}")

            def get_file_extension(url):
                path = urlparse(url).path
                _, ext = os.path.splitext(path)
                return ext[1:].lower()  # Remove the dot and convert to lower case

            if valid_formats:
                links = [link for link in links if get_file_extension(link) in valid_formats]

            logger.info(f"Links after format filter: {links}")

            # Filter by exclude keywords
            links = [link for link in links if not any(keyword in link for keyword in config["excludeKeywords"])]

            logger.info(f"Links after exclude filter: {links}")

            if links:
                all_links.extend(links)
                channel_log_filename = f"{base_folder}/{channel.name.replace('/', '_').replace('\\', '_')}/scrape_links_{datetime.now().strftime('%Y-%m-%d')}.txt"
                os.makedirs(os.path.dirname(channel_log_filename), exist_ok=True)
                with open(channel_log_filename, 'w') as f:
                    f.write('\n\n'.join(f'"{link}"' for link in links))
                logger.info(f"Channel scrape completed and links saved to {channel_log_filename}\nTotal links found: {len(links)}")

        except nextcord.Forbidden as e:
            logger.error(f"Missing access or forbidden to read messages in channel {channel.name} ({channel.id}). Error: {e}")

        except Exception as e:
            logger.error(f"An error occurred while scraping channel {channel.name} ({channel.id}): {e}")

    # Write the server-wide log file
    with open(server_log_filename, 'w') as f:
        if all_links:
            f.write('\n\n'.join(f'"{link}"' for link in all_links))
            logger.info(f"Server-wide scrape completed and links saved to {server_log_filename}\nTotal links found: {len(all_links)}")
            file = nextcord.File(server_log_filename)
            await ctx.send(f"Server-wide scrape completed and links saved to `{server_log_filename}`. Total links found: {len(all_links)}", file=file)
        else:
            logger.warning("Server-wide scrape completed but no links were found.")
            await ctx.send("Server-wide scrape completed but no links were found.")

@client.slash_command(description="Download attachments")
async def download(ctx, file_types: str = nextcord.SlashOption(default="all", choices=["images", "audio", "videos", "all"], description="The files types to download"), message_amount: str = nextcord.SlashOption(default="all", description="The amount of messages to scrape")):
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

    # Set valid formats and folder names
    formats_dict = {
        "images": config["imageFormats"],
        "audio": config["audioFormats"],
        "videos": config["videoFormats"]
    }

    if file_types == "all":
        valid_formats = [fmt for fmt_list in formats_dict.values() for fmt in fmt_list]
    else:
        valid_formats = formats_dict.get(file_types, [])

    # Extract file extension more reliably
    def get_file_extension(url):
        path = urlparse(url).path
        _, ext = os.path.splitext(path)
        return ext[1:].lower()  # Remove the dot and convert to lower case

    if valid_formats:
        links = [link for link in links if get_file_extension(link) in valid_formats]

    # Filter by exclude keywords
    links = [link for link in links if not any(keyword in link for keyword in config["excludeKeywords"])]

    # Create server and channel specific folders
    guild_name = ctx.guild.name.replace('/', '_').replace('\\', '_')  # Clean up special characters
    channel_name = ctx.channel.name.replace('/', '_').replace('\\', '_')  # Clean up special characters
    base_folder = f"output_downloaded/{guild_name}/{channel_name}"
    os.makedirs(base_folder, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        # Create a dictionary to track files by their extensions
        files_by_extension = {}

        for link in links:
            ext = get_file_extension(link)
            if ext not in valid_formats:
                continue  # Skip files that do not match valid formats

            # Initialize a list for each extension folder
            if ext not in files_by_extension:
                files_by_extension[ext] = []

            files_by_extension[ext].append(link)

        # Create folders and download files
        for ext, file_links in files_by_extension.items():
            download_folder = f"{base_folder}/{ext}"
            os.makedirs(download_folder, exist_ok=True)

            for link in file_links:
                file_name = os.path.basename(urlparse(link).path)
                unique_file_name = get_unique_file_path(download_folder, file_name)
                file_path = os.path.join(download_folder, unique_file_name)

                async with session.get(link) as resp:
                    if resp.status == 200:
                        with open(file_path, 'wb') as f:
                            f.write(await resp.read())
                        logger.info(f"Downloaded file: {unique_file_name} to {download_folder}")
                    else:
                        logger.error(f"Failed to download file: {file_name}")

    await ctx.send(f"Download completed. Files are saved in the `{base_folder}` folder with respective subfolders for each file type.")

@client.slash_command(description="Download attachments from all channels in the server")
async def serverwidedownload(ctx, file_types: str = nextcord.SlashOption(default="all", choices=["images", "audio", "videos", "all"], description="The file types to download"), message_amount: str = nextcord.SlashOption(default="all", description="The amount of messages to scrape")):
    await ctx.response.defer()

    # Create server folder
    guild_name = ctx.guild.name.replace('/', '_').replace('\\', '_')  # Clean up special characters
    base_folder = f"output_downloaded/{guild_name}"
    os.makedirs(base_folder, exist_ok=True)

    all_links = []

    for channel in ctx.guild.text_channels:
        logger.info(f"Downloading from channel: {channel.name} ({channel.id})")

        try:
            # Fetch messages and links from the channel
            messages = await fetch_all_messages(channel, int(message_amount) if message_amount.lower() != "all" else None)
            links = []

            for msg in reversed(messages):
                found = [url for url in msg.content.split() if 'discordapp' in url]
                if found:
                    links.extend(found)
                    logger.info(f"Found link: {found} (total: {len(links)})")

                for attachment in msg.attachments:
                    links.append(attachment.url)
                    logger.info(f"Found attachment: {attachment.url} (total: {len(links)})")

            # Set valid formats and folder names
            formats_dict = {
                "images": config["imageFormats"],
                "audio": config["audioFormats"],
                "videos": config["videoFormats"]
            }

            if file_types == "all":
                valid_formats = [fmt for fmt_list in formats_dict.values() for fmt in fmt_list]
            else:
                valid_formats = formats_dict.get(file_types, [])

            logger.info(f"Valid formats: {valid_formats}")

            if valid_formats:
                links = [link for link in links if get_file_extension(link) in valid_formats]

            links = [link for link in links if not any(keyword in link for keyword in config["excludeKeywords"])]

            if links:
                all_links.extend(links)
                channel_folder = f"{base_folder}/{channel.name.replace('/', '_').replace('\\', '_')}"
                os.makedirs(channel_folder, exist_ok=True)

                # Create a dictionary to track files by their extensions
                files_by_extension = {}

                for link in links:
                    ext = get_file_extension(link)
                    if ext not in valid_formats:
                        continue  # Skip files that do not match valid formats

                    # Initialize a list for each extension folder
                    if ext not in files_by_extension:
                        files_by_extension[ext] = []

                    files_by_extension[ext].append(link)

                # Create folders and download files
                for ext, file_links in files_by_extension.items():
                    download_folder = f"{channel_folder}/{ext}"
                    os.makedirs(download_folder, exist_ok=True)

                    for link in file_links:
                        file_name = os.path.basename(urlparse(link).path)
                        unique_file_name = get_unique_file_path(download_folder, file_name)
                        file_path = os.path.join(download_folder, unique_file_name)

                        async with aiohttp.ClientSession() as session:
                            async with session.get(link) as resp:
                                if resp.status == 200:
                                    with open(file_path, 'wb') as f:
                                        f.write(await resp.read())
                                    logger.info(f"Downloaded file: {unique_file_name} to {download_folder}")
                                else:
                                    logger.error(f"Failed to download file: {file_name}")

        except nextcord.Forbidden as e:
            logger.error(f"Missing access or forbidden to read messages in channel {channel.name} ({channel.id}). Error: {e}")

        except Exception as e:
            logger.error(f"An error occurred while downloading from channel {channel.name} ({channel.id}): {e}")

    # Write the server-wide log file
    server_log_filename = f"{base_folder}/download_all_channels_{datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(server_log_filename, 'w') as f:
        if all_links:
            f.write('\n\n'.join(f'"{link}"' for link in all_links))
            logger.info(f"Server-wide download completed and links saved to {server_log_filename}\nTotal links found: {len(all_links)}")
            file = nextcord.File(server_log_filename)
            await ctx.send(f"Server-wide download completed and links saved to `{server_log_filename}`. Total links found: {len(all_links)}", file=file)
        else:
            logger.warning("Server-wide download completed but no links were found.")
            await ctx.send("Server-wide download completed but no links were found.")

client.run(config["token"])