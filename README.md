# A Discord bot that can scrape attachment links from a channel
Do I really need to explain???\
The code is probably a bit messy, but it works so :)

## Prerequisites
- [Python 3.9 or higher](https://python.org/)
- [git](https://git-scm.com/downloads)

## How to use
1. Clone the repo
```bash
git clone https://github.com/zenithpaws/discord-cdnlink-scraper-python.git
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Create a Discord bot here: https://discord.com/developers/applications
    1. Enable the option shown in the image below
  ![Option to Enable: Message Content Intent](https://cdn.spin.rip/r/firefox_3037402965.png)
    2. Copy the token and invite the bot to your server using this link (Replace `CLIENT_ID` with your bot's client ID): `https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=274878008320&scope=bot`
  
4. Open [config.json](config.json) and fill in the values
5. Run the bot
```bash
py bot.py
```
6. Run the command
```
/scrape [videos only true/false] [amount of messages to scrape].
```
Both are optional, and are not needed\
Default is videos and images, all messages

## Want to see features added?
Open an issue and I'll take a look and see if I can add it.

## License
[MIT](LICENSE)\
Made by [spinfal](https://out.spin.rip/home)\
Converted to Python by [zenithpaws](https://linktr.ee/zenithpaws)