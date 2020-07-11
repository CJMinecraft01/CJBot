from pathlib import Path
from typing import Optional, Type, List


def __get_master_path() -> Path:
    """
    :return: The master path to the base folder of the program. This is the folder in which the launch files are found
    """
    import sys
    import os
    # noinspection SpellCheckingInspection
    try:
        # PyInstaller creates a temp folder and stores path in "_MEIPASS"
        # noinspection PyUnresolvedReferences,PyProtectedMember
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    # print(base_path)
    return Path(base_path)


MASTER_PATH = __get_master_path()


def _create_repr(clazz, ignore_attributes: Optional[List[str]] = None, ignore_types: Optional[List[type]] = None) \
        -> None:
    """
    Create the __repr__ function for the given class with the given attributes to ignore

    :param clazz: The class containing the attributes
    :param ignore_attributes: The attributes which should be ignored
    :param ignore_types: The attribute types to ignore
    :return: None
    """
    # import inspect
    # Ensure that we are adding the functions to a class
    if not isinstance(clazz, type):
        raise AttributeError("Cannot mark non class type to have a default representation function")

    if ignore_attributes is None:
        ignore_attributes = []
    if ignore_types is None:
        ignore_types = []

    # Construct the __repr__ function
    def represent(self) -> str:
        """
        The represent function for a class which returns all of the attributes and values of the attributes in a
        function

        :param self: The object to get the attributes of
        :return: The object converted to a string
        """

        # Get all of the attributes which are public and have not got a name in ignore_attributes and aren't of a
        # type in ignore_types
        attributes = [f"{name}={repr(getattr(self, name))}" for name in list(filter(
            lambda name: name not in ignore_attributes and not (name.startswith('_'))
            and not callable(getattr(self, name)) and type(getattr(self, name)) not in ignore_types, dir(self)))]
        return f"{self.__class__.__name__}({', '.join(attributes)})"  # Return the formatted string

    # Override the functions
    clazz.__repr__ = represent


# noinspection PyUnresolvedReferences
def default_representation(clazz_: Optional[Type] = None, ignore_attributes: Optional[List[str]] = None,
                           ignore_types: Optional[List[type]] = None):
    """
    Automatically creates the __repr__ overrides by analysing the instance for the values of all the attributes.

    This is a decorator so can be used e.g.\n
    >>> class Person:
    ...     def __init__(self, name: str):
    ...         self.name = name
    ...
    >>> Person = default_representation(Person)
    or like:
    >>> @default_representation
    ... class Person:
    ...     def __init__(self, name: str):
    ...         self.name = name

    and when an instance is created and outputted we get the result:\n
    >>> print(Person('Bob'))
    Bob(name='bob')

    :param clazz_: The class to add the default representation to
    :param ignore_attributes: The attributes of this class to ignore
    :param ignore_types: The attribute types to ignore
    :return: The updated class
    """

    def decorator(clazz: Type) -> Type:
        """
        Decorate the provided class, adding a __repr__ function

        :param clazz: The class to decorate
        :return: The decorated class
        """
        _create_repr(clazz, ignore_attributes, ignore_types)
        return clazz

    return decorator(clazz_) if clazz_ is not None else decorator