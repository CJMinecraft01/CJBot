from typing import Optional, List, Tuple
from utils import default_representation, time
import discord
from bs4 import BeautifulSoup
from requests import get
from json import loads
from collections import OrderedDict
from pkg_resources import parse_version
import xml.etree.ElementTree as ET
from io import BytesIO

from . import bot, InvalidVersion
from logging import getLogger


logger = getLogger("forge")


@default_representation
class ForgeVersion:

    @staticmethod
    def download_url(mc_version: str, forge_version: str, src: bool) -> str:
        return f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-{'src' if src else 'mdk'}.zip"

    def __init__(self, mc_version: str, forge_version: str, src: bool) -> None:
        self.__mc_version = mc_version
        self.__forge_version = forge_version
        self.__mdk = ForgeVersion.download_url(mc_version, forge_version, src)

    @property
    def mc_version(self):
        return self.__mc_version

    @property
    def forge_version(self):
        return self.__forge_version

    @property
    def mdk(self):
        return self.__mdk


class Versions:
    minecraft_versions = OrderedDict()
    forge_versions_slim = OrderedDict()
    forge_versions = OrderedDict()
    latest_minecraft_version = None
    latest_minecraft_version_group = None

    MC_VERSIONS_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    FORGE_MAVEN_METADATA = "http://files.minecraftforge.net/maven/net/minecraftforge/forge/maven-metadata.xml"
    FORGE_PROMOTIONS_URL = "http://files.minecraftforge.net/maven/net/minecraftforge/forge/promotions_slim.json"
    FORGE_URL = "https://files.minecraftforge.net/"

    @staticmethod
    def forge_version_url(mc_version: str) -> str:
        return f"http://files.minecraftforge.net/maven/net/minecraftforge/forge/index_{mc_version}.html"

    @classmethod
    def is_src(cls, files: List[List[str]]) -> bool:
        return len(list(filter(lambda file: file[1] == "src", files))) > 0

    @staticmethod
    def get_group(version: str):
        if version.count('.') >= 2:
            return '.'.join(version.split('.')[:-1])
        return version

    @staticmethod
    def parse_forge_version(version: str) -> Tuple[str, str]:
        versions = version.split("-")
        return versions[0], versions[1]

    @classmethod
    async def fetch_versions(cls):
        logger.info("Fetching forge versions")
        version_manifest = loads(get(cls.MC_VERSIONS_URL).content)
        minecraft_versions = map(str, sorted([parse_version(version["id"]) for version in version_manifest["versions"] if version["type"] == "release"], reverse=True))
        ordered_minecraft_versions = OrderedDict()

        first = True
        for version in minecraft_versions:
            group = cls.get_group(version)
            if first:
                cls.latest_minecraft_version_group = group
                cls.latest_minecraft_version = version
                first = False
            if group in ordered_minecraft_versions.keys():
                ordered_minecraft_versions[group].append(version)
            else:
                ordered_minecraft_versions[group] = [version]

        logger.info("Fetched minecraft versions")

        maven_manifest = ET.fromstring(get(cls.FORGE_MAVEN_METADATA).content)
        fg_versions = [cls.parse_forge_version(e.text) for e in maven_manifest.find("versioning").find("versions")]

        forge_versions_ = OrderedDict()
        forge_versions_slim = OrderedDict()

        forge_1_8 = parse_version("1.8")

        for mc_version, fg_version in fg_versions:
            group = cls.get_group(mc_version)
            version = ForgeVersion(mc_version, fg_version, parse_version(mc_version) < forge_1_8)
            if group in forge_versions_.keys():
                if mc_version in forge_versions_[group].keys():
                    forge_versions_[group][mc_version][fg_version] = version
                else:
                    forge_versions_[group][mc_version] = OrderedDict({fg_version: version})
            else:
                forge_versions_[group] = OrderedDict({mc_version: OrderedDict({fg_version: version})})

        new_mc_versions = OrderedDict()
        for group in ordered_minecraft_versions.keys():
            if group in forge_versions_.keys():
                new_mc_versions[group] = [version for version in ordered_minecraft_versions[group] if version in forge_versions_[group].keys()]

        promotions = loads(get(cls.FORGE_PROMOTIONS_URL).content)["promos"]
        for group in new_mc_versions.keys():
            versions = OrderedDict()
            for mc_version in new_mc_versions[group]:
                latest = list(forge_versions_[group][mc_version].values())[-1]
                recommended = None
                if f"{mc_version}-recommended" in promotions.keys():
                    recommended = ForgeVersion(mc_version, promotions[f"{mc_version}-recommended"], parse_version(mc_version) < forge_1_8)
                versions[mc_version] = {"latest": latest, "recommended": recommended}
            forge_versions_slim[group] = versions

        cls.minecraft_versions = new_mc_versions
        cls.forge_versions_slim = forge_versions_slim
        cls.forge_versions = forge_versions_

        logger.info("Fetched forge versions")


def resolve_version(version, group: bool = False):
    if version is None or len(version) == 0:
        return None
    if version == "latest":
        return Versions.latest_minecraft_version_group if group else Versions.latest_minecraft_version
    if version[0:2] != "1.":
        version = "1." + version
    val = -1
    for i in range(0, 2):
        val = version.find(".", val + 1)
    mc_version = version
    if val != -1:
        mc_version = version[:val]
    if mc_version not in Versions.minecraft_versions.keys():
        return None
    sub_versions = Versions.minecraft_versions[mc_version]
    if version not in sub_versions:
        return sub_versions[0]
    if group:
        return mc_version
    return version


@bot.command(name="mdk", short_doc="Gets the latest and recommended mdk for a version")
async def mdk(ctx, version: Optional[str] = None, forge: Optional[str] = None):
    """
    Gets the latest and recommended mdk for a version

    :param ctx: The context for the command
    :param version: Optional Minecraft version for the command (default -latest Minecraft version)
    :param forge: Optional Forge version to get the mdk for (default -latest and recommended mdks)
    :return:
    """
    resolved = resolve_version(version if version is not None else "latest")
    if resolved is None:
        raise InvalidVersion("", True)
        # await send_error(ctx, "Version Error",
        #                  "Please provide a valid Minecraft version. To see all available version type " +
        #                  bot.command_prefix + "mcversions")
        # return
    embed = discord.Embed(title="MDK Download for " + resolved, color=0x2E4460)
    if forge is not None:
        parent_version = resolve_version(resolved, True)
        if forge not in Versions.forge_versions[parent_version][resolved]:
            raise InvalidVersion(resolved, False)
        ver = Versions.forge_versions[parent_version][resolved][forge]
        embed.add_field(name=ver.forge_version, value=ver.mdk, inline=True)
    else:
        parent_version = resolve_version(resolved, True)
        forge_version = Versions.forge_versions_slim[parent_version][resolved]
        if forge_version["latest"] is not None:
            embed.add_field(name="Latest", value=forge_version["latest"].mdk, inline=True)
        if forge_version["recommended"] is not None:
            embed.add_field(name="Recommended", value=forge_version["recommended"].mdk, inline=True)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="forgeversions", short_doc="Lists all of the forge version for a particular version")
async def forge_versions(ctx, version: Optional[str] = None):
    """
    Lists all of the forge version for a particular version

    :param ctx: The context for the command
    :param version: Optional Minecraft version to get the forge versions for (default -latest Minecraft version)
    :return: None
    """
    resolved = resolve_version(version if version is not None else "latest")
    # if resolved is None:
    #     # Would print out every version if discord would let us
    #     embed = discord.Embed(title="Forge Versions", color=0x2E4460)
    #     for parent_version, child_versions in Versions.forge_versions.items():
    #         for parent, child_forge_versions in child_versions.items():
    #             value = ", ".join(child_forge_versions)
    #             if len(value) > 1024:
    #                 value = value[:1000] + "..."
    #             embed.add_field(name=parent, value=value, inline=False)
    #     embed.set_footer(text="Made by Dogatron03")
    #     await ctx.send(embed=embed)
    #     return
    if resolved is None:
        raise InvalidVersion("", True)
    embed = discord.Embed(title="Forge Versions", color=0x2E4460)
    version_group = resolve_version(resolved, True)
    child_versions = Versions.forge_versions[version_group][resolved]
    value = ", ".join(child_versions)
    if len(value) > 1024:
        value = value[:1000] + "..."
    embed.add_field(name=resolved, value=value, inline=False)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="mcversions", short_doc="Lists all of the Minecraft versions supported by Forge")
async def mcversions(ctx, version: Optional[str] = None):
    """
    Lists all of the Minecraft versions supported by Forge

    :param ctx: The context for the command
    :param version: Optional Minecraft group version to use (default -list all versions)
    :return: None
    """
    embed = discord.Embed(title="Supported Minecraft Versions by Forge", color=0x2E4460)
    handled = False
    if version is None:
        handled = True
        for parent_version, child_versions in Versions.minecraft_versions.items():
            versions = ", ".join(child_versions)
            embed.add_field(name=parent_version, value=versions, inline=False)
    version = resolve_version(version, True)
    if version in Versions.minecraft_versions.keys():
        versions = ", ".join(Versions.minecraft_versions[version])
        embed.add_field(name=version, value=versions, inline=False)
    elif not handled:
        raise InvalidVersion("", True)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="latestforge", short_doc="Gets the latest and recommended Forge version")
async def forge_latest(ctx, version: Optional[str] = None):
    """
    Gets the latest and recommended Forge version

    :param ctx: The context for the command
    :param version: Optional Minecraft version to use (default -latest Minecraft version)
    :return: None
    """
    if version is None:
        resolved = Versions.latest_minecraft_version
    else:
        resolved = resolve_version(version)
    if resolved is None:
        raise InvalidVersion("", True)

    embed = discord.Embed(title="Forge Versions for " + resolved, color=0x2E4460)

    parent_version = resolve_version(resolved, True)
    forge_version = Versions.forge_versions_slim[parent_version][resolved]
    if forge_version["latest"] is not None:
        embed.add_field(name="Latest", value=forge_version["latest"].forge_version, inline=True)
    if forge_version["recommended"] is not None:
        embed.add_field(name="Recommended", value=forge_version["recommended"].forge_version, inline=True)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)