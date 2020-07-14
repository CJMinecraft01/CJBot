from . import bot
from pbwrap import Pastebin
from os import getenv
from mimetypes import guess_type
from requests import get


PASTEBIN_DEV_KEY = getenv("PASTEBIN_DEV_KEY")


def get_file_type_from_name(name: str) -> str:
    return name.split(".")[-1].lower()


def is_valid(file_type: str):
    return file_type == "txt" or file_type == "java" or fi


api = Pastebin(PASTEBIN_DEV_KEY)


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    ctx = await bot.get_context(message)
    if len(message.attachments) > 0:
        urls = ""
        for attachment in message.attachments:
            if guess_type(attachment.filename)[0] == "text/plain":
                url = api.create_paste(api_paste_code=get(attachment.url).content, api_paste_name=attachment.filename, api_paste_private=1, api_paste_expire_date="1M")
                urls += url + " "
        if len(urls) > 0:
            await message.delete()
            await ctx.send(f"{message.content} {urls}")
