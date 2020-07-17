from . import bot, send_error, check_command, send_error_for_failed_check
from typing import Optional
from discord import Embed, Colour
from string import whitespace
from re import compile
from .page import PageEntry, Page


COMMAND_FROM_DESCRIPTION = compile(r":param (.+): (.+)")


def get_command_signature(command):
    """Retrieves the signature portion of the help page.

    Parameters
    ------------
    command: :class:`Command`
        The command to get the signature of.

    Returns
    --------
    :class:`str`
        The signature for the command.
    """

    parent = command.full_parent_name
    if len(command.aliases) > 0:
        aliases = '|'.join(command.aliases)
        fmt = '[%s|%s]' % (command.name, aliases)
        if parent:
            fmt = parent + ' ' + fmt
        alias = fmt
    else:
        alias = command.name if not parent else parent + ' ' + command.name

    return '%s %s' % (alias, command.signature)


class Cmd(PageEntry):

    def __init__(self, name: str, usage: str, description: str) -> None:
        self.__name = name
        self.__usage = usage
        self.__description = description

    def title(self) -> str:
        return f"{bot.command_prefix}{self.__name}"

    def to_message(self) -> str:
        return f"__Usage__: `{bot.command_prefix}{self.__usage}`\n__Description__: {self.__description if len(self.__description) > 0 else 'None'}"


def command_generator(commands):
    for command in commands:
        yield command


@bot.command(name="help", short_doc="Shows this message")
async def help_command(ctx, command: Optional[str] = None):
    """
    Shows this command

    :param ctx: The context for the command
    :param command: Optional command to get help for
    :return: None
    """
    if command is None:
        # embed = Embed(title="Help", colour=Colour.red())
        commands = []
        for cmd in bot.walk_commands():
            if await check_command(ctx, cmd):
                continue
            commands.append(Cmd(cmd.name, get_command_signature(cmd), cmd.short_doc))
            # text = f"__Usage__: `{bot.command_prefix}{get_command_signature(cmd)}`\n"
            #
            # text += "__Description__: " + cmd.short_doc if len(cmd.short_doc) > 0 else "None" + "\n"
            #
            # embed.add_field(name=f"{bot.command_prefix}{cmd.name}", value=text, inline=False)
            # embed.add_field(name="Description", value=help_text, inline=True)
        # embed.set_footer(text="Made by CJMinecraft")
        # await ctx.send(embed=embed)
        page = Page(5, command_generator(commands))
        await page.show(ctx, title="Help", colour=Colour.red())
    else:
        cmd = bot.get_command(command)
        if cmd is None:
            await send_error(ctx, "Command Not Found", f"Cannot find help for command `{bot.command_prefix}{command}` as command does not exist")
            return
        if name := await check_command(ctx, cmd):
            await send_error_for_failed_check(ctx, name)
            return
        embed = Embed(title=f"{bot.command_prefix}{cmd.name} help", colour=Colour.red())
        text = f"__Usage__: `{bot.command_prefix}{get_command_signature(cmd)}`\n"
        help_text = ""
        params = ""
        if cmd.help:
            for line in cmd.help.splitlines():
                if line in whitespace:
                    continue
                if line.startswith(":"):
                    if match := COMMAND_FROM_DESCRIPTION.match(line):
                        parameter = match.group(1)
                        description = match.group(2)
                        if parameter in cmd.clean_params.keys():
                            p = cmd.clean_params[parameter]
                            params += f"_{p.name}_: {description}\n"
                else:
                    help_text += line
        else:
            help_text = cmd.description if len(cmd.description) > 0 else "None"
        text += "__Description__:\n" + help_text + "\n"
        if len(params) > 0:
            text += "__Arguments__:\n" + params

        embed.add_field(name=f"{bot.command_prefix}{cmd.name}", value=text, inline=False)
        embed.set_footer(text="Made by CJMinecraft")
        await ctx.send(embed=embed)
