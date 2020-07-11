from json import loads, dumps
from typing import List, Optional
from abc import ABCMeta, abstractmethod
from pkg_resources import parse_version
from pprint import pprint
from datetime import date
from pathlib import Path
from csv import DictReader
from zipfile import ZipFile
from utils import MASTER_PATH, default_representation, time
from requests import get
from io import BytesIO
from os import scandir
from re import compile
from enum import Enum, auto


MAPPINGS = MASTER_PATH / "mappings"


class MappingDownloader(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def update_versions(cls):
        pass

    @classmethod
    @abstractmethod
    def get_latest(cls):
        pass

    @classmethod
    @abstractmethod
    def load_versions(cls):
        pass


class MappingType(Enum):
    CLASS = ("c", "CL", None, None,)
    FIELD = ("f", "FD", "fields", CLASS,)
    METHOD = ("m", "MD", "methods", CLASS,)
    PARAMETER = ("p", None, "params", METHOD,)

    def __new__(cls, key: str, searge_key: Optional[str], csv_file_name: Optional[str], parent: Optional['MappingType']):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        obj.key = key
        obj.searge_key = searge_key
        obj.csv_file_name = csv_file_name
        obj.parent = parent
        return obj


@default_representation
class Mapping:

    def __init__(self, mapping_type: MappingType, original_name: Optional[str], intermediate_name: str, name: Optional[str] = None, description: Optional[str] = None) -> None:
        self.__mapping_type = mapping_type
        self.__original_name = original_name
        self.__intermediate_name = intermediate_name
        self.__name = name
        self.__description = description

    @property
    def mapping_type(self):
        return self.__mapping_type

    @property
    def original_name(self):
        return self.__original_name

    @property
    def intermediate_name(self):
        return self.__intermediate_name

    @property
    def name(self):
        return self.__name

    @property
    def description(self):
        return self.__description


class Side(Enum):
    CLIENT = auto()
    SERVER = auto()
    BOTH = auto()


@default_representation
class Parameter(Mapping):

    def __init__(self, original_name: Optional[str], intermediate_name: str,
                 name: Optional[str], description: Optional[str], side: Side) -> None:
        super().__init__(MappingType.PARAMETER, original_name, intermediate_name, name, description)
        self.__side = side

    @property
    def side(self):
        return self.__side


@default_representation
class Method(Mapping):

    def __init__(self, original_name: str, intermediate_name: str, signature: str,
                 name: Optional[str], description: Optional[str], side: Side, static: bool) -> None:
        super().__init__(MappingType.METHOD, original_name, intermediate_name, name, description)
        self.__signature = signature
        self.__side = side
        self.__static = static
        self.__parameters = []

    def add_parameter(self, parameter: Parameter):
        self.__parameters.append(parameter)

    @property
    def static(self):
        return self.__static

    @property
    def side(self):
        return self.__side

    @property
    def signature(self):
        return self.__signature

    @property
    def parameters(self):
        return self.__parameters


@default_representation
class Field(Mapping):

    def __init__(self, original_name: str, intermediate_name: str,
                 name: Optional[str], description: Optional[str], side: Side) -> None:
        super().__init__(MappingType.FIELD, original_name, intermediate_name, name, description)
        self.__side = side

    @property
    def side(self):
        return self.__side


@default_representation
class Class(Mapping):

    def __init__(self, original_name: str, intermediate_name: str, name: Optional[str] = None, description: Optional[str] = None) -> None:
        super().__init__(MappingType.CLASS, original_name, intermediate_name, name, description)
        self.__child_classes = []
        self.__fields = []
        self.__methods = []

    def add_field(self, field: Mapping):
        self.__fields.append(field)

    def add_method(self, method: Method):
        self.__methods.append(method)

    @property
    def child_classes(self):
        return self.__child_classes

    @property
    def fields(self):
        return self.__fields

    @property
    def methods(self):
        return self.__methods


class MappingDatabase:

    def __init__(self) -> None:
        self.__fields = {}
        self.__classes = []
        self.__methods = {}
        self.__parameters = {}

    def add_class(self, clazz: Class):
        self.__classes.append(clazz)


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

        @property
        def latest_snapshot(self):
            return self.__snapshots[-1]

        @property
        def latest_stable(self):
            return self.__stables[-1]

        def __repr__(self):
            return f"MCPVersion(mc_version={self.__mc_version})"

    def __init__(self, versions: dict) -> None:
        self.__versions = []
        for key, value in versions.items():
            self.__versions.append(MCPVersions.MCPVersion(key, value["snapshot"], value["stable"]))

        self.__versions = sorted(self.__versions, key=lambda ver: ver.mc_version, reverse=True)

    def __iter__(self):
        return self.__versions.__iter__()


class MCPDownloader(MappingDownloader):
    VERSION_JSON = "http://export.mcpbot.bspk.rs/versions.json"
    SRGS_URL = lambda version: f"http://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp/{version}/mcp-{version}-srg.zip"
    TSRGS_URL = lambda version: f"http://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config/{version}/mcp_config-{version}.zip"
    MAPPINGS_URL_SNAPSHOT = lambda mc_version, snapshot: f"http://export.mcpbot.bspk.rs/mcp_snapshot/{snapshot}-{mc_version}/mcp_snapshot-{snapshot}-{mc_version}.zip"
    MAPPINGS_URL_STABLE = lambda mc_version, snapshot: f"http://export.mcpbot.bspk.rs/mcp_stable/{snapshot}-{mc_version}/mcp_stable-{snapshot}-{mc_version}.zip"

    SRG_PARAM = compile(r"(?:p_)?(\d+)_(\d+)_?")
    SRG_METHOD_ID = compile(r"(?:func_)?(\d+)_(\w+)_?")

    __versions = None

    __database = {}

    MCP_FILES = MAPPINGS / "mcp"

    @classmethod
    def update_versions(cls):
        response = get(cls.VERSION_JSON)
        if response.status_code == 200:
            cls.__versions = MCPVersions(loads(response.content))
            print("Loaded MCP versions")

    @classmethod
    def get_latest(cls):
        if not cls.MCP_FILES.exists():
            cls.MCP_FILES.mkdir(parents=True)

        new_forge = parse_version("1.13")

        for version in cls.__versions:
            latest_snapshot: MCPVersions.MCPVersion.MCPSnapshotVersion = version.latest_snapshot

            path = cls.MCP_FILES / str(version.mc_version)

            latest = True

            if not path.exists():
                path.mkdir()
                latest = False

            meta_file = path / "meta.json"
            if not meta_file.exists():
                latest = False
            else:
                latest = loads(meta_file.read_text())["snapshot"] == latest_snapshot.version

            if not latest:
                zip_file = ZipFile(BytesIO(get(cls.MAPPINGS_URL_SNAPSHOT(version.mc_version, latest_snapshot.version), stream=True).content))
                zip_file.extractall(path=path)

                url = cls.TSRGS_URL if version.mc_version >= new_forge else cls.SRGS_URL

                zip_file = ZipFile(BytesIO(
                    get(url(version.mc_version), stream=True).content))
                zip_file.extractall(path=path)

                meta_file.write_text(data=dumps({
                    "mc_version": str(version.mc_version),
                    "snapshot": latest_snapshot.version,
                    "tsrg": version.mc_version >= new_forge
                }))

                print("Updated mappings for", version.mc_version)
            else:
                print(f"Skipped {version.mc_version} as already on latest snapshot {latest_snapshot.version}")

    @classmethod
    @time
    def load_versions(cls):
        new_forge = parse_version("1.13")

        for directory in scandir(cls.MCP_FILES):
            path = Path(directory.path)

            meta_file = path / "meta.json"
            meta = None

            if meta_file.exists():
                meta = loads(meta_file.read_text())
            else:
                print(f"Skipping directory {directory} as no meta file exists")
                continue

            db = MappingDatabase()

            fields_file = path / "fields.csv"
            fields = DictReader(fields_file.open(mode="r"))
            fields = {field["searge"]: field for field in fields}

            methods_file = path / "methods.csv"
            methods = DictReader(methods_file.open(mode="r"))
            methods = {method["searge"]: method for method in methods}

            params_file = path / "params.csv"
            params = DictReader(params_file.open(mode="r"))
            temp = {}
            for param in params:
                match = cls.SRG_PARAM.match(param["param"])
                if match:
                    method_id = match.group(1)
                    param_index = match.group(2)
                    if method_id in temp.keys():
                        temp[method_id][param_index] = param
                    else:
                        temp[method_id] = {param_index: param}
                else:
                    # Typically these will be constructor parameters
                    pass

            params = temp

            # TODO constructors
            # in constructors.txt for TSRGs
            # id class signature
            # in params.csv, params are p_i id ...

            if parse_version(meta["mc_version"]) >= new_forge:
                # TSRG parser
                tsrg_file = path / "config" / "joined.tsrg"

                static_methods_file = path / "config" / "static_methods.txt"
                static_methods = static_methods_file.read_text().splitlines()

                clazz = None

                for line in tsrg_file.read_text().splitlines():
                    if not line.startswith("\t"):
                        if clazz is not None:
                            db.add_class(clazz)
                        names = line.split(" ")
                        clazz = Class(names[0], names[1])
                    else:
                        data = line[1:].split(" ")
                        if len(data) == 2:
                            # Field
                            if data[1] in fields.keys():
                                field = fields[data[1]]
                                clazz.add_field(Field(data[0], data[1], field["name"], field["desc"], Side(int(field["side"]) + 1)))
                            else:
                                # Mapping not found for this field so use default values
                                clazz.add_field(Field(data[0], data[1], None, None, Side.BOTH))
                        else:
                            if data[2] in methods.keys():
                                method = methods[data[2]]
                                match = cls.SRG_METHOD_ID.match(method["searge"])
                                m = Method(data[0], data[2], data[1], method["name"], method["desc"], Side(int(method["side"]) + 1), data[2] in static_methods)
                                if match is not None:
                                    method_id = match.group(1)
                                    if method_id in params.keys():
                                        for param in params[method_id].values():
                                            m.add_parameter(Parameter(None, param["param"], param["name"], None, Side(int(param["side"]) + 1)))
                                clazz.add_method(m)
                            else:
                                match = cls.SRG_METHOD_ID.match(data[2])
                                m = Method(data[0], data[2], data[1], None, None, Side.BOTH, data[2] in static_methods)
                                if match is not None:
                                    method_id = match.group(1)
                                    if method_id in params.keys():
                                        for param in params[method_id].values():
                                            m.add_parameter(Parameter(None, param["param"], param["name"], None,
                                                                      Side(int(param["side"]) + 1)))
                                clazz.add_method(m)
            else:
                # SRG parser
                pass

            cls.__database[meta["mc_version"]] = db


if __name__ == '__main__':
    MCPDownloader.update_versions()
    MCPDownloader.get_latest()
    MCPDownloader.load_versions()
