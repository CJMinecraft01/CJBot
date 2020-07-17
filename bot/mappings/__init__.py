from typing import Optional
from bot import bot, get_user_options_from_context, InvalidVersion
from discord import Embed
from .downloader import MCPDownloader
from bot.page import Page


def resolve_version(version, group: bool = False):
    if version is None or len(version) == 0:
        return None
    if version == "latest":
        return MCPDownloader.latest_minecraft_version_group if group else MCPDownloader.latest_minecraft_version
    if version[0:2] != "1.":
        version = "1." + version
    val = -1
    for i in range(0, 2):
        val = version.find(".", val + 1)
    mc_version = version
    if val != -1:
        mc_version = version[:val]
    if mc_version not in MCPDownloader.minecraft_versions.keys():
        return None
    sub_versions = MCPDownloader.minecraft_versions[mc_version]
    if version not in sub_versions:
        return sub_versions[0]
    if group:
        return mc_version
    return version


@bot.command(name="latestmcp", short_doc="Gets the latest mcp version")
async def latest_mcp(ctx, version: Optional[str] = None):
    """
    Get the latest mcp version

    :param ctx: The context for the command
    :param version: Optional Minecraft version to specify which MCP version to use (default - user's latest mcp version setting)
    :return: None
    """
    if version is None:
        version = get_user_options_from_context(ctx).DefaultMCPMinecraftVersion
    version = resolve_version(version)
    if version is None:
        raise InvalidVersion("", True)
    else:
        embed = Embed(title="MCP Versions for " + version, color=0x2E4460)
        mcp_version = MCPDownloader.versions.get_version(version)
        if mcp_version is None:
            raise InvalidVersion("", True)

        if snapshot := mcp_version.latest_snapshot:
            embed.add_field(name="Snapshot", value=snapshot.version, inline=True)
        if stable := mcp_version.latest_stable:
            embed.add_field(name="Stable", value=stable, inline=True)

        embed.set_footer(text="Made by CJMinecraft")
        await ctx.send(embed=embed)


async def not_found(ctx):
    embed = Embed(title="List of MCP Mappings", description="No results found", color=0x2E4460)
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


def search_all(name: str, version: str):
    for result in MCPDownloader.database[version].search_field(name):
        yield result
    for result in MCPDownloader.database[version].search_method(name):
        yield result
    for result in MCPDownloader.database[version].search_parameters(name):
        yield result
    for result in MCPDownloader.database[version].search_classes(name):
        yield result


@bot.command(name="mcp", short_doc="Looks up a field, method or parameter within an MCP version")
async def mappings(ctx, name: str, version: Optional[str] = None):
    """
    Looks up a field, method or parameter within an MCP version

    :param ctx: The context for the command
    :param name: The name to search
    :param version: Optional version to specify which MCP version to use (default -user's latest mcp version setting)
    :return: None
    """
    if version is None:
        version = get_user_options_from_context(ctx).DefaultMCPMinecraftVersion

    if name.startswith("field"):
        await find_field(ctx, name, version)
    elif name.startswith("func"):
        await find_method(ctx, name, version)
    elif name.startswith("p"):
        await find_parameter(ctx, name, version)
    else:
        version = resolve_version(version if version is not None else "latest")
        if version is None:
            raise InvalidVersion("", True)

        page = Page(5, search_all(name, version))
        await page.show(ctx, title=f"List of MCP Mappings for {version}", colour=0x2E4460)

        # found_field = False
        #
        # embed = Embed(title="List of MCP Mappings", color=0x2E4460)
        # for field, clazz in MCPDownloader.database[version].search_field(name):
        #     found_field = True
        #     embed.add_field(name=f"{version}: {clazz.intermediate_name}", value=field.to_message(clazz), inline=False)
        #
        # embed.set_footer(text="Made by CJMinecraft")
        # if found_field:
        #     await ctx.send(embed=embed)
        #
        # found_method = False
        #
        # embed = Embed(title="List of MCP Mappings", color=0x2E4460)
        # for method, clazz in MCPDownloader.database[version].search_method(name):
        #     found_method = True
        #     embed.add_field(name=f"{version}: {clazz.intermediate_name}", value=method.to_message(clazz), inline=False)
        #
        # embed.set_footer(text="Made by CJMinecraft")
        # if found_method:
        #     await ctx.send(embed=embed)
        #
        # found_param = False
        #
        # embed = Embed(title="List of MCP Mappings", color=0x2E4460)
        # for parameter, method in MCPDownloader.database[version].search_parameters(name):
        #     found_param = True
        #     embed.add_field(name=f"{version}: {method.name if method.name is not None else method.intermediate_name}",
        #                     value=parameter.to_message(), inline=False)
        #
        # embed.set_footer(text="Made by CJMinecraft")
        # if found_param:
        #     await ctx.send(embed=embed)
        #
        # if not (found_field or found_method or found_param):
        #     await not_found(ctx)


@bot.command(name="mcpf", short_doc="Looks up a field within an MCP version")
async def find_field(ctx, name: str, version: Optional[str] = None):
    """
    Looks up a field within an MCP version

    :param ctx: The context for the command
    :param name: The name to search
    :param version: Optional version to specify which MCP version to use (default -user's latest mcp version setting)
    :return: None
    """
    if version is None:
        version = get_user_options_from_context(ctx).DefaultMCPMinecraftVersion
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        raise InvalidVersion("", True)

    page = Page(5, MCPDownloader.database[version].search_field(name))
    await page.show(ctx, title=f"List of MCP Mappings for {version}", colour=0x2E4460)

    # found = False
    #
    # embed = Embed(title="List of MCP Mappings", color=0x2E4460)
    # for field, clazz in MCPDownloader.database[version].search_field(name):
    #     found = True
    #     embed.add_field(name=f"{version}: {clazz.intermediate_name}", value=field.to_message(clazz), inline=False)
    #
    # if not found:
    #     await not_found(ctx)
    #     return
    #
    # embed.set_footer(text="Made by CJMinecraft")
    # await ctx.send(embed=embed)


@bot.command(name="mcpm", short_doc="Looks up a method within an MCP version")
async def find_method(ctx, name: str, version: Optional[str] = None):
    """
    Looks up a method within an MCP version

    :param ctx: The context for the command
    :param name: The name to search
    :param version: Optional version to specify which MCP version to use (default -user's latest mcp version setting)
    :return: None
    """
    if version is None:
        version = get_user_options_from_context(ctx).DefaultMCPMinecraftVersion
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        raise InvalidVersion("", True)

    page = Page(5, MCPDownloader.database[version].search_method(name))
    await page.show(ctx, title=f"List of MCP Mappings for {version}", colour=0x2E4460)

    # found = False
    # embed = Embed(title="List of MCP Mappings", color=0x2E4460)
    # for method, clazz in MCPDownloader.database[version].search_method(name):
    #     found = True
    #     embed.add_field(name=f"{version}: {clazz.intermediate_name}", value=method.to_message(clazz), inline=False)
    #
    # if not found:
    #     await not_found(ctx)
    #     return
    #
    # embed.set_footer(text="Made by CJMinecraft")
    # await ctx.send(embed=embed)


@bot.command(name="mcpp", short_doc="Looks up a parameter within an MCP version")
async def find_parameter(ctx, name: str, version: Optional[str] = None):
    """
    Looks up a parameter within an MCP version

    :param ctx: The context for the command
    :param name: The name to search
    :param version: Optional version to specify which MCP version to use (default -user's latest mcp version setting)
    :return: None
    """
    if version is None:
        version = get_user_options_from_context(ctx).DefaultMCPMinecraftVersion
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        raise InvalidVersion("", True)

    page = Page(5, MCPDownloader.database[version].search_parameters(name))
    await page.show(ctx, title=f"List of MCP Mappings for {version}", colour=0x2E4460)

    # embed = Embed(title="List of MCP Mappings", color=0x2E4460)
    # found = False
    # for parameter, method in MCPDownloader.database[version].search_parameters(name):
    #     found = True
    #     embed.add_field(name=f"{version}: {method.name if method.name is not None else method.intermediate_name}", value=parameter.to_message(), inline=False)
    # if not found:
    #     await not_found(ctx)
    #     return
    # embed.set_footer(text="Made by CJMinecraft")
    # await ctx.send(embed=embed)


@bot.command(name="mcpc", short_doc="Looks up a class within an MCP version")
async def find_class(ctx, name: str, version: Optional[str] = None):
    """
    Looks up a class within an MCP version

    :param ctx: The context for the command
    :param name: The name to search
    :param version: Optional version to specify which MCP version to use (default - user's latest mcp version setting)
    :return: None
    """
    if version is None:
        version = get_user_options_from_context(ctx).DefaultMCPMinecraftVersion
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        raise InvalidVersion("", True)

    page = Page(5, MCPDownloader.database[version].search_classes(name))
    await page.show(ctx, title=f"List of MCP Mappings for {version}", colour=0x2E4460)