"""
All of the JSON related functions which allow classes to be json serializable and deserializable
"""

__all__ = ['serializable', 'JsonSerializable', 'Json']

from json import JSONEncoder, loads, dumps, load, dump
from abc import ABCMeta, abstractmethod
from typing import Dict, List, Type, Any, Optional
from bidict import bidict


_serializers = bidict({})  # Stores a list of serializable object classes


def serializable(clazz_: Optional[Type] = None, class_names: Optional[List[str]] = None, short_name: Optional[str] = None) -> Type:
    """
    Mark a class as something which can be serialised
    Can be used like a decorator.

    Usage: \n
    >>> serializable(Class)
    or
    >>> @serializable
    ... class Class(JsonSerializable):
    ...     def serialize(self) -> dict:
    ...         pass
    ...     @staticmethod
    ...     def deserialize(o: dict):
    ...         pass

    :param clazz_: The class to register as something which can be serialised
    :param class_names: The names of sub classes which are also serialisable
    :param short_name: The shorthand name for the class (to reduce file sizes)
    :return: The provided class
    """
    def wrapper(clazz: Type) -> Type:
        """
        Wrap a class to say the class is serializable meaning when encountered when we deserialize, we can create the
        correct class

        :param clazz: The class which is Json Serializable
        :return: The class
        """
        if not isinstance(clazz, type):
            raise AttributeError("Cannot mark non class type as json serializable")
        if not issubclass(clazz, JsonSerializable):
            raise AttributeError("Cannot mark class as json serializable if it isn't a subclass of JsonSerializable")
        if class_names is None:
            _serializers[short_name if short_name is not None else clazz_.__name__] = clazz
        else:
            for name in class_names:
                _serializers[name] = clazz
        return clazz
    return wrapper if clazz_ is None else wrapper(clazz_)


class JsonSerializable(metaclass=ABCMeta):
    """
    Represents an object which can be serialised into a JSON format
    """

    @abstractmethod
    def serialize(self) -> Dict[str, Any]:
        """
        Convert this object into a dictionary

        :return: the converted object
        """
        pass

    @staticmethod
    @abstractmethod
    def deserialize(o: Dict[str, Any]):
        """
        Convert a previously serialised dictionary into an object

        :param o: The dictionary
        :return: the deserialized object
        """
        pass


class _JsonEncoder(JSONEncoder):
    """
    Represents a json encoder for use in json.dumps or json.dump
    """

    def default(self, o: Any):
        """
        Convert an object into a json formatted version

        :param o: The object to convert
        :return: The converted object
        """
        if issubclass(type(o), JsonSerializable):
            return {f"_{_serializers.inverse[o.__class__]}_": o.serialize()}
        return super(_JsonEncoder, self).default(o)


def _deserialize(o: Dict[str, Any]):
    """
    Deserialize the given json object

    :param o: The object to deserialize
    :return: The deserialized form of the object
    """
    for name, serializer in _serializers.items():
        if f"_{name}_" in o.keys():
            return serializer.deserialize(o[f"_{name}_"])
        if f"_{serializer.__name__}_" in o.keys():
            return serializer.deserialize(o[f"_{serializer.__name__}_"])
        if f"__{name}__" in o.keys():
            return serializer.deserialize(o[f"__{name}__"])
        if f"__{serializer.__name__}__" in o.keys():
            return serializer.deserialize(o[f"__{serializer.__name__}__"])
    return o


class Json:
    """
    Used to wrap the json functions
    """

    @staticmethod
    def loads(*args, **kwargs) -> Any:
        """
        Convert a JSON string into a python object using the builtin json library but giving functionality to serialise
        JSONSerializable objects

        :param args: The arguments for the loads function
        :param kwargs: The keyword arguments for the loads function
        :return: the python object represented using the provided JSON string
        """
        return loads(object_hook=_deserialize, *args, **kwargs)

    @staticmethod
    def dumps(*args, **kwargs) -> str:
        """
        Convert a python object into a JSON string using the builtin json library but giving functionality to
        deserialize JSONSerializable objects

        :param args: The arguments for the dumps function
        :param kwargs: The keyword arguments for the dumps function
        :return: the python object as a JSON string
        """
        return dumps(cls=_JsonEncoder, *args, **kwargs)

    @staticmethod
    def load(*args, **kwargs) -> Any:
        """
        Convert a JSON string into a python object using the builtin json library but giving functionality to serialise
        JSONSerializable objects

        :param args: The arguments for the load function
        :param kwargs: The keyword arguments for the load function
        :return: the python object represented using the provided JSON string
        """
        return load(object_hook=_deserialize, *args, **kwargs)

    @staticmethod
    def dump(*args, **kwargs) -> None:
        """
        Convert a python object into a JSON string using the builtin json library but giving functionality to
        deserialize JSONSerializable objects

        :param args: The arguments for the dump function
        :param kwargs: The keyword arguments for the dump function
        :return: None
        """
        return dump(cls=_JsonEncoder, *args, **kwargs)
