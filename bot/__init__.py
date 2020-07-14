from discord.ext import commands
from discord import DMChannel, Game, Embed
from discord.ext.commands import CommandNotFound, CheckFailure

from models import ServerOptions, UserOptions
from main import db
from sync import schedule_functions
import os
import aioschedule as schedule

bot = commands.Bot(command_prefix="!")


def is_dm(ctx):
    return isinstance(ctx.message.channel, DMChannel)


def get_server_options(guild_id):
    server_options = ServerOptions.query.filter(ServerOptions.GuildId == guild_id).first()
    if server_options is None:
        server_options = ServerOptions(GuildId=guild_id)
        db.session.add(server_options)
        db.session.commit()
    return server_options


def get_server_options_from_context(ctx):
    if is_dm(ctx):
        return ServerOptions(GuildId=None)
    return get_server_options(ctx.message.channel.guild.id)


def get_user_options(user_id):
    user_options = UserOptions.query.filter(UserOptions.UserId == user_id).first()
    if user_options is None:
        user_options = UserOptions(UserId=user_id)
        db.session.add(user_options)
        db.session.commit()
    return user_options


def get_user_options_from_context(ctx):
    return get_user_options(ctx.message.author.id)


def has_admin_role():
    async def predicate(ctx):
        server_options = get_server_options_from_context(ctx)
        if server_options.AdminRoleId is not None:
            for role in ctx.author.roles:
                if role.id == server_options.AdminRoleId:
                    return True
            return False
        return True

    return commands.check(predicate)


async def send_message(ctx, title: str, message: str):
    embed = Embed(title=title, description=message, color=0x14c6e6)
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


async def send_error(ctx, title: str, message: str):
    embed = Embed(title=title, description=message, color=0xe61414)
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print("Bot is ready")
    await bot.change_presence(activity=Game(name="play.diversionmc.net"))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await send_error(ctx, "Error", "Invalid permissions")
    if isinstance(error, CommandNotFound):
        return  # dont want to send message for every bad command
    else:
        print(error)
        await send_error(ctx, "Error", "An error occurred")


async def background_task():
    from asyncio import sleep
    await bot.wait_until_ready()
    await schedule_functions()
    while True:
        await schedule.run_pending()
        await sleep(1)


bot.loop.create_task(background_task())


from . import reactionroles
from . import settings
from . import mappings
from . import forge


def run():
    token = os.environ.get("DISCORD_BOT_SECRET")
    bot.run(token)
