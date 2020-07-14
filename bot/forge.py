from typing import Optional, List
from utils import default_representation, time
import discord
from bs4 import BeautifulSoup
from requests import get
from json import loads
from collections import OrderedDict

from . import bot, send_error, InvalidVersion


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
    SYNCING = False

    minecraft_versions = OrderedDict()
    forge_versions_slim = OrderedDict()
    forge_versions = OrderedDict()
    latest_minecraft_version = None
    latest_minecraft_version_group = None

    MC_VERSIONS_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    FORGE_PROMOTIONS_URL = "http://files.minecraftforge.net/maven/net/minecraftforge/forge/promotions.json"
    FORGE_URL = "https://files.minecraftforge.net/"

    @staticmethod
    def forge_version_url(mc_version: str) -> str:
        return f"http://files.minecraftforge.net/maven/net/minecraftforge/forge/index_{mc_version}.html"

    @classmethod
    def is_src(cls, files: List[List[str]]) -> bool:
        return len(list(filter(lambda file: file[1] == "src", files))) > 0

    @classmethod
    async def fetch_versions(cls):
        page = get(cls.FORGE_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        first = True
        minecraft_versions = OrderedDict()
        for version in soup.find_all("li", attrs={"class": "li-version-list"}):
            parent_version = version.find("a").text.strip()
            child_versions = []
            if first:
                cls.latest_minecraft_version_group = parent_version
            for ver in version.find_all("li"):
                a = ver.find("a")
                if a is not None:
                    child_versions.append(a.text.strip())
                else:
                    child_versions.append(ver.text.strip())
                if first:
                    cls.latest_minecraft_version = child_versions[-1]
                    first = False
            minecraft_versions[parent_version] = child_versions
        print("Fetched supported MC versions")
        promotions = loads(get(cls.FORGE_PROMOTIONS_URL).content)

        forge_versions_slim = OrderedDict()
        forge_versions_ = OrderedDict()

        for parent_version in minecraft_versions.keys():
            versions_slim = OrderedDict()
            versions = OrderedDict()
            for version in minecraft_versions[parent_version]:
                found_slim = False
                src = False
                if f"{version}-latest" in promotions["promos"]:
                    found_slim = True
                    latest = promotions["promos"][f"{version}-latest"]
                    if cls.is_src(latest["files"]):
                        src = True
                    latest = ForgeVersion(latest["mcversion"], latest["version"], src)
                    recommended = promotions["promos"][f"{version}-recommended"] if f"{version}-recommended" in promotions["promos"] else None
                    recommended = ForgeVersion(recommended["mcversion"], recommended["version"], src) if recommended is not None else None
                    versions_slim[version] = {"latest": latest, "recommended": recommended}
                else:
                    print("Having to webscrape to find latest and recommended versions for MC", version)

                page = get(cls.forge_version_url(version))
                soup = BeautifulSoup(page.text, "html.parser")
                if not found_slim:
                    downloads = soup.find_all("div", attrs={"class": "download"})
                    latest = None
                    recommended = None
                    for download in downloads:
                        i = download.find("i")
                        forge_ver = download.find("small").text.strip()
                        if version in forge_ver:
                            forge_ver = forge_ver[len(version) + 3:]
                        src = download.find("a", {"title": "Src"}) is not None

                        ver = ForgeVersion(version, forge_ver, src)

                        if "promo-latest" in i["class"]:
                            latest = ver
                        else:
                            recommended = ver
                    versions_slim[version] = {"latest": latest, "recommended": recommended}

                # get all forge versions for this mc version
                forge_vers = OrderedDict({ver.contents[0].strip(): ForgeVersion(version, ver.contents[0].strip(), src) for ver in soup.find_all("td", attrs={"class": "download-version"})})
                versions[version] = forge_vers
            forge_versions_slim[parent_version] = versions_slim
            forge_versions_[parent_version] = versions
        print("Fetched forge versions")

        cls.minecraft_versions = minecraft_versions
        cls.forge_versions_slim = forge_versions_slim
        cls.forge_versions = forge_versions_


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


@bot.command(name="mdk")
async def mdk(ctx, version: str, forge: Optional[str] = None):
    resolved = resolve_version(version)
    embed = discord.Embed(title="MDK Download for " + resolved, color=0x2E4460)
    if resolved is None:
        raise InvalidVersion("", True)
        # await send_error(ctx, "Version Error",
        #                  "Please provide a valid Minecraft version. To see all available version type " +
        #                  bot.command_prefix + "mcversions")
        # return
    if forge is not None:
        parent_version = resolve_version(resolved, True)
        if forge not in Versions.forge_versions[parent_version][resolved]:
            raise InvalidVersion(resolved, False)
            # await send_error(ctx, "Version Error",
            #                  "Please provide a valid Forge version. To see all available version type " +
            #                  bot.command_prefix + "forgeversions " + resolved)
        ver = Versions.forge_versions[parent_version][resolved][forge]
        embed.add_field(name=ver.forge_version, value=ver.mdk, inline=True)
        # versions = await fetch_versions(resolved)
        # if forge not in versions:
        #     await send_error(ctx, "Version Error",
        #                      "Invalid Forge version " + forge + " for Minecraft version " + resolved +
        #                      ". To see all available forge version type " +
        #                      bot.command_prefix + "forgeversions " + resolved)
        #     return
        # link = await fetch_mdk_forge(resolved, forge)
        # if link is None:
        #     await send_error(ctx, "Version Error",
        #                      "Forge version " + forge + " for Minecraft version " + resolved +
        #                      " does not seem to have a valid MDK or SRC download.")
        #     return
        #
        # embed.add_field(name=forge, value=link)
    else:
        parent_version = resolve_version(resolved, True)
        forge_version = Versions.forge_versions_slim[parent_version][resolved]
        if forge_version["latest"] is not None:
            embed.add_field(name="Latest", value=forge_version["latest"].mdk, inline=True)
        if forge_version["recommended"] is not None:
            embed.add_field(name="Recommended", value=forge_version["recommended"].mdk, inline=True)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="forgeversions")
async def forge_versions(ctx, version: str):
    resolved = resolve_version(version)
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
        # await send_error(ctx, "Version Error",
        #                  "Please provide a valid Minecraft version. To see all available version type " +
        #                  bot.command_prefix + "mcversions")
        return
    embed = discord.Embed(title="Forge Versions", color=0x2E4460)
    version_group = resolve_version(resolved, True)
    child_versions = Versions.forge_versions[version_group][resolved]
    value = ", ".join(child_versions)
    if len(value) > 1024:
        value = value[:1000] + "..."
    embed.add_field(name=resolved, value=value, inline=False)
    embed.set_footer(text="Made by Dogatron03")
    await ctx.send(embed=embed)


@bot.command(name="mcversions")
async def mcversions(ctx, version: Optional[str] = None):
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


@bot.command(name="latestforge")
async def forge_latest(ctx, version: Optional[str] = None):
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