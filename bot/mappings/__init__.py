from typing import Optional
from bot import bot
from discord import Embed
from .downloader import MCPDownloader


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


@bot.command(name="latestmcp")
async def latest_mcp(ctx, version: Optional[str] = None):
    version = resolve_version(version)
    if version is None:
        # error
        pass
    else:
        embed = Embed(title="MCP Versions for " + version, color=0x2E4460)
        mcp_version = MCPDownloader.versions.get_version(version)
        if mcp_version is None:
            # error
            return

        if snapshot := mcp_version.latest_snapshot:
            embed.add_field(name="Snapshot", value=snapshot.version, inline=True)
        if stable := mcp_version.latest_stable:
            embed.add_field(name="Stable", value=stable, inline=True)

        embed.set_footer(text="Made by CJMinecraft")
        await ctx.send(embed=embed)


@bot.command(name="mcp")
async def mappings(ctx, name: str, version: Optional[str] = None):
    if name.startswith("field"):
        await find_field(ctx, name, version)
    elif name.startswith("func"):
        await find_method(ctx, name, version)
    elif name.startswith("p"):
        await find_parameter(ctx, name, version)
    else:
        await find_field(ctx, name, version)
        await find_method(ctx, name, version)
        await find_parameter(ctx, name, version)


@bot.command(name="mcpf")
async def find_field(ctx, name: str, version: Optional[str] = None):
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        # error
        return

    found = False

    embed = Embed(title="List of MCP Mappings", color=0x2E4460)
    for field, clazz in MCPDownloader.database[version].search_field(name):
        found = True
        embed.add_field(name=f"{version}: {clazz.intermediate_name}", value=field.to_message(clazz), inline=False)

    if not found:
        return

    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


@bot.command(name="mcpm")
async def find_method(ctx, name: str, version: Optional[str] = None):
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        # error
        return
    found = False
    embed = Embed(title="List of MCP Mappings", color=0x2E4460)
    for method, clazz in MCPDownloader.database[version].search_method(name):
        found = True
        embed.add_field(name=f"{version}: {clazz.intermediate_name}", value=method.to_message(clazz), inline=False)

    if not found:
        return

    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


@bot.command(name="mcpp")
async def find_parameter(ctx, name: str, version: Optional[str] = None):
    version = resolve_version(version if version is not None else "latest")
    if version is None:
        # error
        return
    embed = Embed(title="List of MCP Mappings", color=0x2E4460)
    found = False
    for parameter, method in MCPDownloader.database[version].search_parameters(name):
        found = True
        embed.add_field(name=f"{version}: {method.name if method.name is not None else method.intermediate_name}", value=parameter.to_message(), inline=False)
    if not found:
        return
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)
