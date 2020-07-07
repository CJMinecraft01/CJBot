from discord.ext import commands
from models import ServerOptions
import os


bot = commands.Bot(command_prefix="$")


def get_server_options(guild_id):
    server_options = ServerOptions.query.filter(ServerOptions.GuildId == guild_id).first()
    if server_options is None:
        server_options = ServerOptions(GuildId=guild_id)
        db.session.add(server_options)
        db.session.commit()
    return server_options


def get_server_options_from_context(ctx):
    if ctx.message.server is None:
        return ServerOptions(GuildId=None)
    return get_server_options(ctx.message.channel.guild.id)


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


from .reactionroles import *


async def send_message(ctx, title: str, message: str):
    embed = discord.Embed(title=title, description=message, color=0x14c6e6)
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


async def send_error(ctx, title: str, message: str):
    embed = Embed(title=title, description=message, color=0xe61414)
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print("Bot is ready")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await send_error(ctx, "Error", "Invalid permissions")
    else:
        await send_error(ctx, "Error", "An error occurred")


# from . import reactionroles_old


# @bot.event
# async def on_message(message):
    # await reactionroles_old.on_message(message)
    # await bot.process_commands(message)


# @bot.event
# async def on_raw_reaction_add(payload):
    # await reactionroles_old.on_raw_reaction_add(payload)


def run():
    from . import reactionroles
    from . import settings
    from . import mappings

    token = os.environ.get("DISCORD_BOT_SECRET")
    bot.run(token)
