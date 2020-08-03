from flask import Blueprint
from flask_restful import Api, Resource, reqparse, fields, marshal_with

from bot import InvalidVersion
from bot.mappings import resolve_version, search_all
from bot.mappings.downloader import MCPDownloader, MappingType


api_blueprint = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_blueprint)


search_parser = reqparse.RequestParser()
search_parser.add_argument("mc", required=False, default="latest", help="The Minecraft version to use")
search_parser.add_argument("s", dest="search", required=False, help="The search term")
search_parser.add_argument("page", default=0, type=int, required=False, help="Which page of results to fetch")


class EnumField(fields.Raw):
    def format(self, value):
        return value.name


parameter_fields = {
    "type": EnumField(attribute="mapping_type"),
    "intermediate_name": fields.String,
    "name": fields.String
}


method_fields = {
    "type": EnumField(attribute="mapping_type"),
    "original_name": fields.String,
    "intermediate_name": fields.String,
    "name": fields.String,
    "signature": fields.String,
    "description": fields.String,
    "physical_side": EnumField(attribute="side"),
    "parameters": fields.List(fields.Nested(parameter_fields))
}


field_fields = {
    "type": EnumField(attribute="mapping_type"),
    "original_name": fields.String,
    "intermediate_name": fields.String,
    "name": fields.String,
    "description": fields.String,
    "physical_side": EnumField(attribute="side")
}


class_fields = {
    "type": EnumField(attribute="mapping_type"),
    "original_name": fields.String,
    "intermediate_name": fields.String,
    "name": fields.String,
    "description": fields.String,
    "fields": fields.List(fields.Nested(field_fields)),
    "methods": fields.List(fields.Nested(method_fields)),
    "constructors": fields.List(fields.Nested(method_fields))
}


search_fields = {
    "fields": fields.List(fields.Nested(field_fields)),
    "methods": fields.List(fields.Nested(method_fields)),
    "parameters": fields.List(fields.Nested(parameter_fields)),
    "classes": fields.List(fields.Nested(class_fields))
}


PAGE_SIZE = 5


@api.resource("/mcp")
class SearchMCPResource(Resource):
    @marshal_with(search_fields)
    def get(self):
        search_args = search_parser.parse_args()
        version = resolve_version(search_args["mc"])
        page = search_args["page"]
        if version is not None:
            if search_args["search"] is None:
                return {}

            results = []
            count = 0
            for result in search_all(search_args["search"], version):
                if count > PAGE_SIZE * (page + 1):
                    break
                if count > PAGE_SIZE * page:
                    results.append(result)
                count += 1
            return {
                "fields": list(filter(lambda r: r.mapping_type == MappingType.FIELD, results)),
                "methods": list(filter(lambda r: r.mapping_type == MappingType.METHOD, results)),
                "parameters": list(filter(lambda r: r.mapping_type == MappingType.PARAMETER, results)),
                "classes": list(filter(lambda r: r.mapping_type == MappingType.CLASS, results)),
            }

        raise InvalidVersion("", search_args["mc"])


@api.resource("/mcp/class")
class SearchMCPClassResource(Resource):
    @marshal_with(class_fields)
    def get(self):
        search_args = search_parser.parse_args()
        version = resolve_version(search_args["mc"])
        page = search_args["page"]
        if version is not None:
            if search_args["search"] is None:
                return {}

            results = []
            count = 0
            for result in MCPDownloader.database[version].search_classes(search_args["search"]):
                if count > PAGE_SIZE * (page + 1):
                    break
                if count > PAGE_SIZE * page:
                    results.append(result)
                count += 1
            return results

        raise InvalidVersion("", search_args["mc"])


@api.resource("/mcp/field")
class SearchMCPFieldResource(Resource):
    @marshal_with(field_fields)
    def get(self):
        search_args = search_parser.parse_args()
        version = resolve_version(search_args["mc"])
        page = search_args["page"]
        if version is not None:
            if search_args["search"] is None:
                return {}

            results = []
            count = 0
            for result in MCPDownloader.database[version].search_field(search_args["search"]):
                if count > PAGE_SIZE * (page + 1):
                    break
                if count > PAGE_SIZE * page:
                    results.append(result)
                count += 1
            return results

        raise InvalidVersion("", search_args["mc"])


@api.resource("/mcp/method")
class SearchMCPMethodResource(Resource):
    @marshal_with(method_fields)
    def get(self):
        search_args = search_parser.parse_args()
        version = resolve_version(search_args["mc"])
        page = search_args["page"]
        if version is not None:
            if search_args["search"] is None:
                return {}

            results = []
            count = 0
            for result in MCPDownloader.database[version].search_method(search_args["search"]):
                if count > PAGE_SIZE * (page + 1):
                    break
                if count > PAGE_SIZE * page:
                    results.append(result)
                count += 1
            return results

        raise InvalidVersion("", search_args["mc"])


@api.resource("/mcp/parameter")
class SearchMCPParameterResource(Resource):
    @marshal_with(parameter_fields)
    def get(self):
        search_args = search_parser.parse_args()
        version = resolve_version(search_args["mc"])
        page = search_args["page"]
        if version is not None:
            if search_args["search"] is None:
                return {}

            results = []
            count = 0
            for result in MCPDownloader.database[version].search_parameters(search_args["search"]):
                if count > PAGE_SIZE * (page + 1):
                    break
                if count > PAGE_SIZE * page:
                    results.append(result)
                count += 1
            return results

        raise InvalidVersion("", search_args["mc"])
