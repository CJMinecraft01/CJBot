from main import db
from models import ServerOptions
from . import bot, is_dm, get_server_options_from_context, send_message, send_error, has_admin_role, \
    get_user_options_from_context
from discord import Embed
from discord.ext.commands import RoleConverter, Context, CheckFailure
from typing import Optional, List, Callable, Any


class Setting:
    settings: List['Setting'] = []

    def __init__(self, name: str, field_name: str, description: str, converter: Optional[Callable[[Context, str], Any]] = None, to_string: Optional[Callable[[Context, str], Any]] = None, user_setting: bool = False):
        self.name = name
        self.field_name = field_name
        self.description = description
        self.user_setting = user_setting
        if converter is None:
            self.converter = lambda ctx, val: val
        else:
            self.converter = converter
        if to_string is None:
            self.to_string = lambda ctx, val: val
        else:
            self.to_string = to_string
        Setting.settings.append(self)


async def admin_role_converter(ctx, val):
    result = None
    try:
        result = (await RoleConverter().convert(ctx, val)).id
    except Exception as e:
        if val.lower() != "null" or val.lower() != "none":
            raise e
    return result


async def default_mcp_minecraft_version_converter(ctx, val):
    if val == "none" or val == "null":
        return None
    return val


class Settings:
    ADMIN_ROLE = Setting("adminrole", "AdminRoleId", "The role required to perform commands", converter=admin_role_converter, to_string=lambda ctx, val: f"<@&{val}>")
    DEFAULT_MCP_MINECRAFT_VERSION = Setting("default_mcp_minecraft_version", "DefaultMCPMinecraftVersion", "The default minecraft version when looking up using MCP", converter=default_mcp_minecraft_version_converter, user_setting=True)


def get_setting_from_name(name: str):
    setting = None
    for s in Setting.settings:
        if name == s.name:
            setting = s
            break
    return setting


def user_has_admin_role(ctx):
    server_options = get_server_options_from_context(ctx)
    if server_options.AdminRoleId == None:
        return True
    for role in ctx.author.roles:
        if role.id == server_options.AdminRoleId:
            return True
    return False


@bot.command(name="settings", short_doc="Manages user settings")
async def settings(ctx, name: Optional[str], value: Optional[str]):
    """
    Manages user settings

    :param ctx: The contex for the command
    :param name: Optional name of the setting
    :param value: The value for the provided setting
    :return: None
    """
    # if is_dm(ctx):
    #     await send_error(ctx, "Invalid Command", "The settings command is not valid within a DM")
    #     return

    admin_role = user_has_admin_role(ctx)

    dm = is_dm(ctx)

    if name is None:
        # Print all of the settings

        if not dm:
            server_options = get_server_options_from_context(ctx)
        user_options = get_user_options_from_context(ctx)

        embed = Embed(title="Settings", color=0x14c6e6)

        for setting in Setting.settings:
            if dm and not setting.user_setting:
                continue
            if not setting.user_setting and not admin_role:
                continue
            embed.add_field(name="Name", value=setting.name, inline=True)
            embed.add_field(name="Description", value=setting.description, inline=True)
            if setting.user_setting:
                val = getattr(user_options, setting.field_name)
            else:
                val = getattr(server_options, setting.field_name)
            embed.add_field(name="Value", value=setting.to_string(ctx, val) if val is not None else "None", inline=True)

        embed.set_footer(text="Made by CJMinecraft")
        await ctx.send(embed=embed)
        return
    if value is None:
        setting = get_setting_from_name(name)
        if setting is None:
            raise Exception("Setting not found")
        if dm and not setting.user_setting:
            # can't do server setting in dm
            return
        if not setting.user_setting and not admin_role:
            # invalid perms
            return
        if not dm:
            server_options = get_server_options_from_context(ctx)
        user_options = get_user_options_from_context(ctx)
        embed = Embed(title=f"Setting - {setting.name}", color=0x14c6e6)
        embed.add_field(name="Name", value=setting.name, inline=True)
        embed.add_field(name="Description", value=setting.description, inline=True)
        if setting.user_setting:
            val = getattr(user_options, setting.field_name)
        else:
            val = getattr(server_options, setting.field_name)
        embed.add_field(name="Value", value=setting.to_string(ctx, val) if val is not None else "None",
                        inline=True)
        embed.set_footer(text="Made by CJMinecraft")
        await ctx.send(embed=embed)
        return
    setting = get_setting_from_name(name)

    if setting is None:
        raise Exception("Setting not found")

    if setting.user_setting:
        user_options = get_user_options_from_context(ctx)
        try:
            result = None
            try:
                result = await setting.converter(ctx, value)
            except Exception as e:
                if value.lower() != "null" and value.lower() != "none":
                    raise e

            setattr(user_options, setting.field_name, result)
            db.session.commit()
        except Exception as e:
            await send_error(ctx, "An error occurred", str(e))
            return
    elif not setting.user_setting and admin_role and not dm:
        server_options = get_server_options_from_context(ctx)
        try:
            result = None
            try:
                result = await setting.converter(ctx, value)
            except Exception as e:
                if value.lower() != "null" and value.lower() != "none":
                    raise e

            setattr(server_options, setting.field_name, result)
            db.session.commit()
        except Exception as e:
            await send_error(ctx, "An error occurred", str(e))
            return
    await send_message(ctx, "Setting changed", "Successfully updated setting")