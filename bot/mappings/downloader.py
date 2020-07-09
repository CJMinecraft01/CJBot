from json import loads
from typing import List
from urllib.request import urlopen
from abc import ABCMeta, abstractmethod
from pkg_resources import parse_version
from pprint import pprint
from datetime import date


class MappingDownloader(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def update_versions(cls):
        pass


class MCPVersions:

    class MCPVersion:

        class MCPSnapshotVersion:

            def __init__(self, version: int) -> None:
                self.__version = str(version)
                self.__date = date(year=int(self.__version[:4]), month=int(self.__version[4:6]), day=int(self.__version[6:]))

            @property
            def version(self):
                return self.__version

            @property
            def date(self):
                return self.__date

            def __repr__(self):
                return f"MCPSnapshotVersion(version={self.__version})"

        def __init__(self, mc_version: str, snapshots: List[int], stables: List[int]) -> None:
            self.__mc_version = parse_version(mc_version)
            self.__snapshots = sorted(list(map(MCPVersions.MCPVersion.MCPSnapshotVersion, snapshots)), key=lambda snapshot: snapshot.date, reverse=True)
            self.__stables = sorted(stables, reverse=True)

        @property
        def mc_version(self):
            return self.__mc_version

        def __repr__(self):
            return f"MCPVersion(mc_version={self.__mc_version})"

    def __init__(self, versions: dict) -> None:
        self.__versions = []
        for key, value in versions.items():
            self.__versions.append(MCPVersions.MCPVersion(key, value["snapshot"], value["stable"]))

        self.__versions = sorted(self.__versions, key=lambda ver: ver.mc_version, reverse=True)
        print("Loaded MCP versions")
        pprint(self.__versions)


class MCPDownloader(MappingDownloader):
    VERSION_JSON = "http://export.mcpbot.bspk.rs/versions.json"
    SRGS_URL = "http://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp/%1$s/mcp-%1$s-srg.zip"
    TSRGS_URL = "http://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config/%1$s/mcp_config-%1$s.zip"
    MAPPINGS_URL_SNAPSHOT = "http://export.mcpbot.bspk.rs/mcp_snapshot/%1$d-%2$s/mcp_snapshot-%1$d-%2$s.zip"
    MAPPINGS_URL_STABLE = "http://export.mcpbot.bspk.rs/mcp_stable/%1$d-%2$s/mcp_stable-%1$d-%2$s.zip"

    __versions = None

    @classmethod
    def update_versions(cls):
        response = urlopen(cls.VERSION_JSON)
        if response.code == 200:
            cls.__versions = MCPVersions(loads(response.read()))


if __name__ == '__main__':
    MCPDownloader.update_versions()
