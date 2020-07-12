from typing import Optional

import discord
import requests
from bs4 import BeautifulSoup

from . import bot, send_error

forge_website = "http://files.minecraftforge.net/maven/net/minecraftforge/forge/index_"
forge_adfoc_prefix_length = 48
# forge_adfoc_prefix_length = 0
minecraft_versions = ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11", "1.12", "1.13",
                      "1.14", "1.15", "1.16"]
supported_forge_minecraft_versions = [["1.1"],
                                      ["1.2.3", "1.2.4", "1.2.5"],
                                      ["1.3.2"],
                                      ["1.4.0", "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5", "1.4.6", "1.4.7"],
                                      ["1.5", "1.5.1", "1.5.2"],
                                      ["1.6.1", "1.6.2", "1.6.3", "1.6.4"],
                                      ["1.7.2", "1.7.10_pre4", "1.7.10"],
                                      ["1.8", "1.8.8", "1.8.9"],
                                      ["1.9", "1.9.4"],
                                      ["1.10", "1.10.2"],
                                      ["1.11", "1.11.2"],
                                      ["1.12", "1.12.1", "1.12.2"],
                                      ["1.13.2"],
                                      ["1.14.2", "1.14.3", "1.14.4"],
                                      ["1.15", "1.15.1", "1.15.2"],
                                      ["1.16.1"]]


def resolve_version(version):
    if version is None or len(version) == 0:
        return -1
    if version == "latest":
        return supported_forge_minecraft_versions[-1][-1]
    if version[0:2] != "1.":
        version = "1." + version
    val = -1
    for i in range(0, 2):
        val = version.find(".", val + 1)
    mcversion = version
    if val != -1:
        mcversion = version[:val]
    if mcversion not in minecraft_versions:
        return -1
    subversions = supported_forge_minecraft_versions[minecraft_versions.index(mcversion)]
    if version not in subversions:
        return subversions[-1]
    return version


@bot.command(name="mdk")
async def mdk(ctx, version: Optional[str], forge: Optional[str]):
    resolved = resolve_version(version)
    embed = discord.Embed(title="MDK Download for " + resolved, color=0x2E4460)
    if resolved == -1:
        await send_error(ctx, "Version Error",
                         "Please provide a valid Minecraft version. To see all available version type " +
                         bot.command_prefix + "mcversions")
        return
    if forge is not None:
        versions = await fetch_versions(resolved)
        if forge not in versions:
            await send_error(ctx, "Version Error",
                             "Invalid Forge version " + forge + " for Minecraft version " + resolved +
                             ". To see all available forge version type " +
                             bot.command_prefix + "forgeversions " + resolved)
            return
        link = await fetch_mdk_forge(resolved, forge)
        if link is None:
            await send_error(ctx, "Version Error",
                             "Forge version " + forge + " for Minecraft version " + resolved +
                             " does not seem to have a valid MDK or SRC download.")
            return

        embed.add_field(name=forge, value=link)
    else:
        links = await fetch_mdk(resolved)
        if len(links) > 0:
            embed.add_field(name="Latest", value=links[0])
        if len(links) > 1:
            embed.add_field(name="Recommended", value=links[1])
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="forgeversions")
async def forge_versions(ctx, version: Optional[str]):
    resolved = resolve_version(version)
    if resolved == -1:
        await send_error(ctx, "Version Error",
                         "Please provide a valid Minecraft version. To see all available version type " +
                         bot.command_prefix + "mcversions")
        return
    vers = await fetch_versions(resolved)
    verx = [""]
    verxi = 0
    for ver in vers:
        if len(ver) + len(verx[verxi]) >= 1024:
            verxi += 1
            verx.append("")
        verx[verxi] = verx[verxi] + ver + ", "
    embed = discord.Embed(title="Forge Versions for " + resolved, color=0x2E4460)
    for i in range(0, verxi + 1):
        embed.add_field(name="#" + str(i), value=verx[i][:-2], inline=False)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="mcversions")
async def mcversions(ctx, version: Optional[str]):
    embed = discord.Embed(title="Supported Minecraft Versions by Forge", color=0x2E4460)
    if version is None or version not in minecraft_versions:
        verx = minecraft_versions.copy()
        verx.reverse()
        for mcverx in verx:
            vers = ""
            for v in supported_forge_minecraft_versions[minecraft_versions.index(mcverx)]:
                if vers != "":
                    vers += ", " + v
                else:
                    vers += v
            embed.add_field(name=mcverx, value=vers, inline=False)
    else:
        vers = ""
        for v in supported_forge_minecraft_versions[minecraft_versions.index(version)]:
            if vers != "":
                vers += ", " + v
            else:
                vers += v
        embed.add_field(name=version, value=vers, inline=False)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="forgelatest")
async def forge_latest(ctx, version: Optional[str]):
    resolved = resolve_version(version)
    if resolved == -1:
        await send_error(ctx, "Version Error",
                         "Please provide a valid Minecraft version. To see all available version type " +
                         bot.command_prefix + "mcversions")
        return
    versions = await fetch_latest(resolved)
    embed = discord.Embed(title="Forge Versions for " + resolved, color=0x2E4460)
    if len(versions) > 0:
        embed.add_field(name="Latest", value=versions[0])
    if len(versions) > 1:
        embed.add_field(name="Recommended", value=versions[1])
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


async def fetch_mdk(version):
    page = requests.get(forge_website + version + ".html")
    soup = BeautifulSoup(page.text, "html.parser")
    downloads = soup.find(class_="downloads")
    download = downloads.find_all(class_="download")
    hrefs = []
    title = "Mdk"
    if int(version[2]) != 1 and int(version[2]) < 8:
        title = "Src"
    for dl in download:
        hrefs.append(dl.find(title=title).get("href")[forge_adfoc_prefix_length:])
    return hrefs


async def fetch_latest(version):
    page = requests.get(forge_website + version + ".html")
    soup = BeautifulSoup(page.text, "html.parser")
    downloads = soup.find(class_="downloads")
    download = downloads.find_all(class_="download")
    vers = []
    for dl in download:
        x = str(dl.find("small").prettify()).split("\n")[1]
        vers.append(x[x.find("-") + 1:])
    return vers


async def fetch_mdk_forge(version, forge):
    page = requests.get(forge_website + version + ".html")
    soup = BeautifulSoup(page.text, "html.parser")
    downloads = soup.find(class_="download-list")
    download = downloads.find_all(class_="download-version")
    title = "mdk"
    if int(version[2]) != 1 and int(version[2]) < 8:
        title = "src"
    for dl in download:
        if str(dl).split("\n")[1].replace(" ", "").replace("\t", "") != forge:
            continue
        aa = dl.parent.find_all("a")
        for a in aa:
            if title in str(a.get("href")):
                return a.get("href")[forge_adfoc_prefix_length:]


async def fetch_versions(version):
    page = requests.get(forge_website + version + ".html")
    soup = BeautifulSoup(page.text, "html.parser")
    downloads = soup.find(class_="download-list")
    vers = downloads.find_all(class_="download-version")
    versx = []
    for ver in vers:
        versx.append(str(ver).split("\n")[1].replace(" ", "").replace("\t", ""))
    return versx
