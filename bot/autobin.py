from . import bot
from pbwrap import Pastebin
from os import getenv
from mimetypes import guess_type
from requests import get
from discord import Embed


PASTEBIN_DEV_KEY = getenv("PASTEBIN_DEV_KEY")


def get_file_type_from_name(name: str) -> str:
    return name.split(".")[-1].lower()


VALID_FILE_TYPES = ["java", "log", "toml", "cfg"]


def is_valid_file(name: str) -> bool:
    return name.lower() in VALID_FILE_TYPES


api = Pastebin(PASTEBIN_DEV_KEY)


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    ctx = await bot.get_context(message)
    if len(message.attachments) > 0:
        urls = ""
        for attachment in message.attachments:
            if "text" in guess_type(attachment.filename)[0] or is_valid_file(get_file_type_from_name(attachment.filename)):
                url = api.create_paste(api_paste_code=get(attachment.url).content, api_paste_name=attachment.filename, api_paste_private=1, api_paste_expire_date="1M")
                urls += url + " "
        if len(urls) > 0:
            await message.delete()
            embed = Embed(description=f"{message.content} {urls}")
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            embed.set_footer(text="Made by CJMinecraft")
            await ctx.send(embed=embed)
