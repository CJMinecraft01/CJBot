from discord.ext import commands
from discord import DMChannel, Game, Embed, Status
from discord.ext.commands import CommandNotFound, CheckFailure, CommandInvokeError, MissingRequiredArgument

from models import ServerOptions, UserOptions
from main import db
from sync import schedule_functions
import os
import aioschedule as schedule

bot = commands.Bot(command_prefix="!")
bot.remove_command("help")


CJ_USER_ID = 232575009200013313


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


def not_dm():
    async def predicate(ctx):
        return not is_dm(ctx)

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


class InvalidVersion(Exception):

    def __init__(self, version: str, mc: bool) -> None:
        super().__init__("Invalid version!")
        self.__version = version
        self.__mc = mc

    @property
    def version(self):
        return self.__version

    @property
    def mc(self):
        return self.__mc


async def check_command(ctx, cmd):
    if len(cmd.checks) > 0:
        for check in cmd.checks:
            if not await check(ctx):
                name = check.__qualname__.split('.<locals>', 1)[0]
                return name
    return None


async def send_error_for_failed_check(ctx, name: str):
    if 'not_dm' == name:
        await send_error(ctx, "Invalid Channel",
                         f"Cannot perform command `{ctx.message.content}` inside of a DM")
    elif 'has_admin_role' == name:
        await send_error(ctx, "Invalid Permissions",
                         f"Cannot perform command `{ctx.message.content}` without admin privileges")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        name = await check_command(ctx, ctx.command)
        await send_error_for_failed_check(ctx, name)
    elif isinstance(error, CommandNotFound):
        return  # dont want to send message for every bad command
    elif isinstance(error, MissingRequiredArgument):
        await send_error(ctx, "Invalid arguments", f"`{error.param.name}` is a required argument for the command `{ctx.command.qualified_name}`\nFor help with this command type `!help {ctx.command.qualified_name}`")
    elif isinstance(error, CommandInvokeError):
        if isinstance(error.original, InvalidVersion):
            await send_error(ctx, "Version Error", f"Please provide a vaild {'Minecraft' if error.original.mc else 'Forge'} version. To see all available versions type `{bot.command_prefix}{'mc' if error.original.mc else 'forge'}versions {error.original.version}`")
        else:
            print(error)
    else:
        print(error)
        await send_error(ctx, "Error", "An error occurred")


async def background_task():
    from asyncio import sleep
    await bot.wait_until_ready()
    await bot.change_presence(status=Status.dnd)
    await schedule_functions()
    await bot.change_presence(activity=Game(name="play.diversionmc.net"))
    while True:
        await schedule.run_pending()
        await sleep(1)


bot.loop.create_task(background_task())


from . import reactionroles
from . import settings
from . import mappings
from . import forge
from . import help
from . import autobin


def run():
    token = os.environ.get("DISCORD_BOT_SECRET")
    bot.run(token)
