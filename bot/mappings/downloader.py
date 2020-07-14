from collections import OrderedDict
from json import loads, dumps
from typing import List, Optional, Dict, Any, Tuple
from abc import ABCMeta, abstractmethod
from pkg_resources import parse_version
from datetime import date
from pathlib import Path
from csv import DictReader
from zipfile import ZipFile
from sync import sync
from utils import MASTER_PATH, default_representation, time
from utils.json import Json, JsonSerializable, serializable
from requests import get
from io import BytesIO
from os import scandir
from re import compile
from enum import Enum, auto
from shutil import rmtree
from logging import getLogger


logger = getLogger("mcp")


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

    def __new__(cls, key: str, searge_key: Optional[str], csv_file_name: Optional[str],
                parent: Optional['MappingType']):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        obj.key = key
        obj.searge_key = searge_key
        obj.csv_file_name = csv_file_name
        obj.parent = parent
        return obj


@default_representation
@serializable
class Mapping(JsonSerializable):

    def serialize(self) -> Dict[str, Any]:
        return {"mapping_type": self.__mapping_type.value, "original_name": self.__original_name,
                "intermediate_name": self.__intermediate_name, "name": self.__name, "description": self.__description}

    @staticmethod
    def deserialize(o: Dict[str, Any]):
        return Mapping(MappingType(o["mapping_type"]), o["original_name"], o["intermediate_name"], o["name"],
                       o["description"])

    def __init__(self, mapping_type: MappingType, original_name: Optional[str], intermediate_name: str,
                 name: Optional[str] = None, description: Optional[str] = None) -> None:
        self.__mapping_type = mapping_type
        self.__original_name = original_name
        self.__intermediate_name = intermediate_name
        self.__name = name
        self.__description = description if description is None or len(description) > 0 else None

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
@serializable
class Parameter(Mapping):

    def serialize(self) -> Dict[str, Any]:
        return {"original_name": self.original_name,
                "intermediate_name": self.intermediate_name, "name": self.name, "description": self.description,
                "side": self.__side.value}

    @staticmethod
    def deserialize(o: Dict[str, Any]):
        return Parameter(o["original_name"], o["intermediate_name"], o["name"], o["description"], Side(o["side"]))

    def __init__(self, original_name: Optional[str], intermediate_name: str,
                 name: Optional[str], description: Optional[str], side: Side) -> None:
        super().__init__(MappingType.PARAMETER, original_name, intermediate_name, name, description)
        self.__side = side

    @property
    def side(self):
        return self.__side

    def to_message(self):
        return f"`{self.intermediate_name}` -> `{self.name}`"


@default_representation
@serializable
class Method(Mapping):

    def serialize(self) -> Dict[str, Any]:
        return {"original_name": self.original_name,
                "intermediate_name": self.intermediate_name, "name": self.name, "description": self.description,
                "side": self.__side.value, "static": self.__static, "signature": self.__signature,
                "parameters": self.__parameters}

    @staticmethod
    def deserialize(o: Dict[str, Any]):
        m = Method(o["original_name"], o["intermediate_name"], o["signature"], o["name"], o["description"],
                   Side(o["side"]), o["static"])
        for param in o["parameters"]:
            m.add_parameter(param)
        return m

    def __init__(self, original_name: Optional[str], intermediate_name: Optional[str], signature: str,
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

    def search_parameter(self, search: str):
        results = []
        for param in self.__parameters:
            if param.name == search:
                results.append(param)
            elif param.intermediate_name == search:
                results.append(param)
        return results

    def to_message(self, clazz: 'Class') -> str:
        params = ', '.join(map(lambda param: param.to_message(), self.parameters)) if len(self.parameters) > 0 else "None"
        return f"__Name__: `{self.original_name}` -> `{self.intermediate_name}` -> `{self.name}`\n" \
               f"__Description__: `{self.description if self.description is not None else 'None'}`\n" \
               f"__Side__: `{self.side.name}`\n" \
               f"__AT__: `public {clazz.intermediate_name.replace('/', '.')} {self.intermediate_name}{self.signature} # {self.name}`\n" \
               f"__Parameters__: {params}"


@default_representation
@serializable
class Field(Mapping):

    def serialize(self) -> Dict[str, Any]:
        return {"original_name": self.original_name,
                "intermediate_name": self.intermediate_name, "name": self.name, "description": self.description,
                "side": self.__side.value}

    @staticmethod
    def deserialize(o: Dict[str, Any]):
        return Field(o["original_name"], o["intermediate_name"], o["name"], o["description"], Side(o["side"]))

    def __init__(self, original_name: str, intermediate_name: str,
                 name: Optional[str], description: Optional[str], side: Side) -> None:
        super().__init__(MappingType.FIELD, original_name, intermediate_name, name, description)
        self.__side = side

    @property
    def side(self):
        return self.__side

    def to_message(self, clazz: 'Class') -> str:
        return f"__Name__: `{self.original_name}` -> `{self.intermediate_name}` -> `{self.name}`\n" \
               f"__Description__: `{self.description if self.description is not None else 'None'}`\n" \
               f"__Side__: `{self.side.name}`\n" \
               f"__AT__: `public {clazz.intermediate_name.replace('/', '.')} {self.intermediate_name} # {self.name}`"


@default_representation
@serializable
class Class(Mapping):

    def serialize(self) -> Dict[str, Any]:
        return {"original_name": self.original_name, "intermediate_name": self.intermediate_name, "name": self.name,
                "description": self.description, "child_classes": self.__child_classes, "fields": self.__fields,
                "methods": self.__methods, "constructors": self.__constructors}

    @staticmethod
    def deserialize(o: Dict[str, Any]):
        c = Class(o["original_name"], o["intermediate_name"], o["name"], o["description"])
        for child_class in o["child_classes"]:
            c.add_child_class(child_class)
        for field in o["fields"]:
            c.add_field(field)
        for method in o["methods"]:
            c.add_method(method)
        for constructor in o["constructors"]:
            c.add_constructor(constructor)
        return c

    def __init__(self, original_name: str, intermediate_name: str, name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        super().__init__(MappingType.CLASS, original_name, intermediate_name, name, description)
        self.__child_classes = []
        self.__fields = []
        self.__methods = []
        self.__constructors = []

    def add_field(self, field: Mapping):
        self.__fields.append(field)

    def add_method(self, method: Method):
        self.__methods.append(method)

    def add_child_class(self, clazz: 'Class'):
        self.__child_classes.append(clazz)

    def add_constructor(self, constructor: Method):
        self.__constructors.append(constructor)

    def search_field(self, search: str) -> List[Tuple[Field, 'Class']]:
        results = []
        for field in self.__fields:
            if field.name == search:
                results.append((field, self))
            elif field.intermediate_name == search:
                results.append((field, self))
        return results

    def search_method(self, search: str) -> List[Tuple[Method, 'Class']]:
        results = []
        for method in self.__methods:
            if method.name == search:
                results.append((method, self))
            elif method.intermediate_name == search:
                results.append((method, self))
        return results

    def search_parameters(self, search: str) -> List[Tuple[Parameter, Method]]:
        results = []
        for method in self.__methods:
            results.extend([(param, method) for param in method.search_parameter(search)])
        return results

    @property
    def child_classes(self):
        return self.__child_classes

    @property
    def fields(self):
        return self.__fields

    @property
    def methods(self):
        return self.__methods

    @property
    def constructors(self):
        return self.__constructors


class MappingDatabase:

    def __init__(self, path: Path, mc_version: Optional[str] = None, snapshot: Optional[str] = None) -> None:
        self.__classes = []
        self.__mc_version = mc_version
        self.__snapshot = snapshot
        self.__path = path

    def add_class(self, clazz: Class):
        self.__classes.append(clazz)

    def save(self):
        self.__path.write_text(
            Json.dumps({"mc_version": self.__mc_version, "snapshot": self.__snapshot, "classes": self.__classes}))

    def load(self):
        data = Json.loads(self.__path.read_text())
        self.__mc_version = data["mc_version"]
        self.__snapshot = data["snapshot"]
        self.__classes = data["classes"]

    @property
    def mc_version(self):
        return self.__mc_version

    @property
    def snapshot(self):
        return self.__snapshot

    @property
    def classes(self):
        return self.__classes

    def search_field(self, search: str) -> Tuple[Field, Class]:
        for clazz in self.__classes:
            result = clazz.search_field(search)
            if len(result) > 0:
                for r in result:
                    yield r

    def search_method(self, search: str) -> Tuple[Method, Class]:
        for clazz in self.__classes:
            result = clazz.search_method(search)
            if len(result) > 0:
                for r in result:
                    yield r

    def search_parameters(self, search: str) -> Tuple[Parameter, Method]:
        for clazz in self.__classes:
            result = clazz.search_parameters(search)
            if len(result) > 0:
                for r in result:
                    yield r


class MCPVersions:
    class MCPVersion:
        class MCPSnapshotVersion:

            def __init__(self, version: int) -> None:
                self.__version = str(version)
                self.__date = date(year=int(self.__version[:4]), month=int(self.__version[4:6]),
                                   day=int(self.__version[6:]))

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
            self.__snapshots = sorted(list(map(MCPVersions.MCPVersion.MCPSnapshotVersion, snapshots)),
                                      key=lambda snapshot: snapshot.date, reverse=True)
            self.__stables = sorted(stables, reverse=True)

        @property
        def mc_version(self):
            return self.__mc_version

        @property
        def latest_snapshot(self):
            if len(self.__snapshots) > 0:
                return self.__snapshots[0]
            return None

        @property
        def latest_stable(self):
            if len(self.__stables) > 0:
                return self.__stables[0]
            return None

        def __repr__(self):
            return f"MCPVersion(mc_version={self.__mc_version})"

    def __init__(self, versions: dict) -> None:
        vs = []
        for key, value in versions.items():
            vs.append(MCPVersions.MCPVersion(key, value["snapshot"], value["stable"]))

        vs.append(MCPVersions.MCPVersion("1.16.1", [20200707], []))
        vs = sorted(vs, key=lambda ver: ver.mc_version, reverse=True)
        self.__latest = vs[0]
        self.__versions = {str(version.mc_version): version for version in vs}

    @property
    def latest(self):
        return self.__latest

    def keys(self):
        return self.__versions.keys()

    def get_version(self, version: str):
        if version in self.__versions.keys():
            return self.__versions[version]
        return None

    def __iter__(self):
        return self.__versions.values().__iter__()


class MCPDownloader(MappingDownloader):
    VERSION_JSON = "http://export.mcpbot.bspk.rs/versions.json"
    SRGS_URL = lambda version: f"http://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp/{version}/mcp-{version}-srg.zip"
    TSRGS_URL = lambda version: f"http://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config/{version}/mcp_config-{version}.zip"
    MAPPINGS_URL_SNAPSHOT = lambda mc_version, snapshot: f"http://export.mcpbot.bspk.rs/mcp_snapshot/{snapshot}-{mc_version}/mcp_snapshot-{snapshot}-{mc_version}.zip"
    MAPPINGS_URL_STABLE = lambda mc_version, snapshot: f"http://export.mcpbot.bspk.rs/mcp_stable/{snapshot}-{mc_version}/mcp_stable-{snapshot}-{mc_version}.zip"

    SRG_PARAM = compile(r"(?:p_)?(\d+)_(\d+)_?")
    SRG_CONSTRUCTOR_PARAM = compile(r"(?:p_i)?(\d+)_(\d+)_?")
    SRG_METHOD_ID = compile(r"(?:func_)?(\d+)_(\w+)_?")

    versions: MCPVersions = None
    minecraft_versions = OrderedDict()
    latest_minecraft_version_group = None
    latest_minecraft_version = None

    database = {}

    MCP_FILES = MAPPINGS / "mcp"

    @classmethod
    @sync
    async def update(cls):
        from bot.forge import Versions
        cls.update_versions()
        cls.get_latest()
        cls.load_versions()
        logger.info("Waiting for minecraft versions")
        await Versions.fetch_versions()
        logger.info("Finished waiting")
        mc_versions = OrderedDict()
        first = True
        for mc_group, child_versions in Versions.minecraft_versions.items():
            versions = []
            for version in child_versions:
                if version in cls.versions.keys():
                    if first:
                        cls.latest_minecraft_version = version
                        cls.latest_minecraft_version_group = mc_group
                        first = False
                    versions.append(version)
            mc_versions[mc_group] = versions
        cls.minecraft_versions = mc_versions
        logger.info("Detected latest MCP minecraft versions")

    @classmethod
    def update_versions(cls):
        response = get(cls.VERSION_JSON)
        if response.status_code == 200:
            result = loads(response.content)
            cls.versions = MCPVersions(result)
            logger.info("Loaded MCP versions")

    @classmethod
    def get_latest(cls):
        if not cls.MCP_FILES.exists():
            cls.MCP_FILES.mkdir(parents=True)

        new_forge = parse_version("1.13")

        for version in cls.versions:
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
                try:
                    zip_file = ZipFile(BytesIO(
                        get(cls.MAPPINGS_URL_SNAPSHOT(version.mc_version, latest_snapshot.version), stream=True).content))
                    zip_file.extractall(path=path / "mcp")

                    url = cls.TSRGS_URL if version.mc_version >= new_forge else cls.SRGS_URL

                    zip_file = ZipFile(BytesIO(
                        get(url(version.mc_version), stream=True).content))
                    zip_file.extractall(path=path / "srg")

                    meta_file.write_text(data=dumps({
                        "mc_version": str(version.mc_version),
                        "snapshot": latest_snapshot.version,
                        "tsrg": version.mc_version >= new_forge
                    }))

                    logger.info("Updated mappings for", version.mc_version)
                except Exception as e:
                    logger.error(f"An error occurred when trying to download mappings for {version.mc_version}")
                    logger.exception(e)
            else:
                logger.info(f"Skipped {version.mc_version} as already on latest snapshot {latest_snapshot.version}")

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
                logger.info(f"Skipping directory {directory} as no meta file exists")
                continue

            db_file = path / "db.json"

            db: MappingDatabase

            if db_file.exists():
                db = MappingDatabase(db_file)
                db.load()
                if db.mc_version == meta["mc_version"] and db.snapshot == meta["snapshot"]:
                    cls.database[meta["mc_version"]] = db
                    logger.info("Found up to date database for MC", db.mc_version, "snapshot", db.snapshot)
                    continue
                else:
                    db = MappingDatabase(db_file, meta["mc_version"], meta["snapshot"])
                    logger.info("Detected out of date database for MC", db.mc_version, "snapshot", db.snapshot)
            else:
                db = MappingDatabase(db_file, meta["mc_version"], meta["snapshot"])
                logger.info("Couldn't find database for MC", db.mc_version, "snapshot", db.snapshot)

            mcp_folder = path / "mcp"

            fields_file = mcp_folder / "fields.csv"
            fields = DictReader(fields_file.open(mode="r"))
            fields = {field["searge"]: field for field in fields}

            methods_file = mcp_folder / "methods.csv"
            methods = DictReader(methods_file.open(mode="r"))
            methods = {method["searge"]: method for method in methods}

            params_file = mcp_folder / "params.csv"
            params = DictReader(params_file.open(mode="r"))
            temp = {}
            constructor_params = {}
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
                    match = cls.SRG_CONSTRUCTOR_PARAM.match(param["param"])
                    if match:
                        method_id = match.group(1)
                        param_index = match.group(2)
                        if method_id in constructor_params.keys():
                            constructor_params[method_id][param_index] = param
                        else:
                            constructor_params[method_id] = {param_index: param}

            params = temp

            srg_folder = path / "srg"

            if parse_version(meta["mc_version"]) >= new_forge:
                # TSRG parser
                tsrg_file = srg_folder / "config" / "joined.tsrg"

                static_methods_file = srg_folder / "config" / "static_methods.txt"
                static_methods = static_methods_file.read_text().splitlines()

                constructors_file = srg_folder / "config" / "constructors.txt"
                constructors = {}
                for line in constructors_file.read_text().splitlines():
                    data = line.split(" ")
                    if data[1] in constructors.keys():
                        constructors[data[1]].append({"method_id": data[0], "class": data[1], "signature": data[2]})
                    else:
                        constructors[data[1]] = [{"method_id": data[0], "class": data[1], "signature": data[2]}]

                clazz = None

                for line in tsrg_file.read_text().splitlines():
                    if not line.startswith("\t"):
                        if clazz is not None:
                            db.add_class(clazz)
                        names = line.split(" ")
                        clazz = Class(names[0], names[1])

                        if clazz.intermediate_name in constructors.keys():
                            for constructor in constructors[clazz.intermediate_name]:
                                c = Method(None, None, constructor["signature"], constructor["class"], None, Side.BOTH, False)
                                if constructor["method_id"] in constructor_params.keys():
                                    for param in constructor_params[constructor["method_id"]].values():
                                        c.add_parameter(Parameter(None, param["param"], param["name"], None,
                                                                  Side(int(param["side"]) + 1)))
                                clazz.add_constructor(c)
                    else:
                        data = line[1:].split(" ")
                        if len(data) == 2:
                            # Field
                            if data[1] in fields.keys():
                                field = fields[data[1]]
                                clazz.add_field(
                                    Field(data[0], data[1], field["name"], field["desc"], Side(int(field["side"]) + 1)))
                            else:
                                # Mapping not found for this field so use default values
                                clazz.add_field(Field(data[0], data[1], None, None, Side.BOTH))
                        else:
                            if data[2] in methods.keys():
                                method = methods[data[2]]
                                match = cls.SRG_METHOD_ID.match(method["searge"])
                                m = Method(data[0], data[2], data[1], method["name"], method["desc"],
                                           Side(int(method["side"]) + 1), data[2] in static_methods)
                                if match is not None:
                                    method_id = match.group(1)
                                    if method_id in params.keys():
                                        for param in params[method_id].values():
                                            m.add_parameter(Parameter(None, param["param"], param["name"], None,
                                                                      Side(int(param["side"]) + 1)))
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
                srg_file = srg_folder / "joined.srg"

                static_methods_file = srg_folder / "static_methods.txt"
                static_methods = static_methods_file.read_text().splitlines()

                classes = {}

                for line in srg_file.read_text().splitlines():
                    if line.startswith("CL: "):
                        line = line[4:]
                        # Classes
                        names = line.split(" ")
                        clazz = Class(names[0], names[1])

                        classes[names[1]] = clazz
                    elif line.startswith("FD: "):
                        line = line[4:]
                        # Fields
                        data = line.split(" ")
                        field_data = data[1].split("/")
                        field_name = field_data[-1]
                        class_name = '/'.join(field_data[:-1])
                        if field_name in fields.keys():
                            field = fields[field_name]
                            classes[class_name].add_field(
                                Field(data[0].split("/")[-1], field_name, field["name"], field["desc"], Side(int(field["side"]) + 1)))
                        else:
                            # Mapping not found for this field so use default values
                            classes[class_name].add_field(Field(data[0].split("/")[-1], field_name, None, None, Side.BOTH))
                    elif line.startswith("MD: "):
                        line = line[4:]
                        # Methods
                        data = line.split(" ")

                        method_data = data[2].split("/")
                        method_name = method_data[-1]
                        class_name = '/'.join(method_data[:-1])

                        if method_name in methods.keys():
                            method = methods[method_name]
                            match = cls.SRG_METHOD_ID.match(method["searge"])
                            m = Method(data[0].split("/")[-1], method_name, data[3], method["name"], method["desc"],
                                       Side(int(method["side"]) + 1), method_name in static_methods)
                            if match is not None:
                                method_id = match.group(1)
                                if method_id in params.keys():
                                    for param in params[method_id].values():
                                        m.add_parameter(Parameter(None, param["param"], param["name"], None,
                                                                  Side(int(param["side"]) + 1)))
                            classes[class_name].add_method(m)
                        else:
                            match = cls.SRG_METHOD_ID.match(data[2])
                            m = Method(data[0].split("/")[-1], method_name, data[3], None, None, Side.BOTH, method_name in static_methods)
                            if match is not None:
                                method_id = match.group(1)
                                if method_id in params.keys():
                                    for param in params[method_id].values():
                                        m.add_parameter(Parameter(None, param["param"], param["name"], None,
                                                                  Side(int(param["side"]) + 1)))
                            classes[class_name].add_method(m)

                constructors_file = srg_folder / "joined.exc"
                for line in constructors_file.read_text().splitlines():
                    if "V=|" in line:
                        ps = line.split("V=")[1][1:].split(",")
                        class_name = line.split(".")[0]

                        if class_name in classes.keys():
                            c = Method(None, None, line[line.index("("):line.index("V=")], line[line.index('.'):line.index('(')], None, Side.BOTH, False)

                            for param in ps:
                                match = cls.SRG_CONSTRUCTOR_PARAM.match(param)
                                if match:
                                    method_id = match.group(1)
                                    param_index = match.group(2)
                                    if method_id in constructor_params.keys() and param_index in constructor_params[method_id].keys():
                                        p = constructor_params[method_id][param_index]
                                        c.add_parameter(Parameter(None, p["param"], p["name"], None, Side(int(p["side"]) + 1)))
                                    else:
                                        c.add_parameter(Parameter(None, param, param, None, Side.BOTH))

                            classes[class_name].add_constructor(c)

                for clazz in classes.values():
                    db.add_class(clazz)

            cls.database[meta["mc_version"]] = db
            db.save()
            rmtree(srg_folder.as_posix())
            rmtree(mcp_folder.as_posix())
            logger.info("Updated database for MC", db.mc_version, "snapshot", db.snapshot)

        logger.info("Loaded MCP data")


if __name__ == '__main__':
    MCPDownloader.update_versions()
    MCPDownloader.get_latest()
    MCPDownloader.load_versions()
