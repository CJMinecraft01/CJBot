from pathlib import Path
from types import FunctionType, MethodType, MemberDescriptorType
from typing import Optional, Type, List, Any, Union


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


def get_container_class(method: Union[MethodType, FunctionType, MemberDescriptorType]) -> Optional[type]:
    """
    Get the class which the provided method is a part of

    :param method: The method to get the class that it is a part of
    :return: The class which the provided method is a part of
    """

    # Source: https://stackoverflow.com/questions/3589311/get-defining-class-of-unbound-method-object-in-python-3
    # /25959545#25959545

    import inspect
    if inspect.ismethod(method):  # If the method variable is a method type
        for clazz in inspect.getmro(method.__self__.__class__):  # Get the all of the parent classes
            if clazz.__dict__.get(method.__name__) is method:  # If the object with this method's name is this method
                return clazz  # It must be that class
        method = method.__func__  # Otherwise get the function from the method
    if inspect.isfunction(method):  # If the method variable is a function type
        # Get the class from the module the method is a part of using it's qualifying name
        clazz = getattr(inspect.getmodule(method), method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(clazz, type):
            return clazz
    if inspect.ismethoddescriptor(method):  # If the method variable is a method descriptor
        # noinspection SpellCheckingInspection
        return getattr(method, '__objclass__', None)
    return None


def time(f: FunctionType) -> FunctionType:
    """
    Time how long it takes for the provided function to execute and output to the console.

    This is a decorator so can be used e.g.\n
    >>> def example_function():
    ...     pass
    >>> example_function = time(example_function)
    or like:
    >>> @time
    ... def example_function():
    ...     pass

    :param f: The function to time
    :return: The wrapper of the function
    """

    from time import time
    import inspect

    mod = inspect.getmodule(f)

    def wrapper(*args, **kwargs) -> Any:
        """
        A wrapper function to decorate a function, which means when the function is executed, it is timed

        :param args: The arguments of the function
        :param kwargs: The key word arguments of the function
        :return: The return arguments of the function
        """
        start = time()  # Get the start time
        ret = f(*args, **kwargs)  # Call the function

        clazz = get_container_class(f)  # Get the container class of the function
        # Get the name of the function
        if mod is None:
            if clazz is None:
                name = f"__main__.{f.__name__}"
            else:
                name = f"__main__.{clazz.__name__}.{f.__name__}"
        else:
            if clazz is None:
                name = f"{mod.__name__}.{f.__name__}"
            else:
                name = f"{mod.__name__}.{clazz.__name__}.{f.__name__}"

        print("Took %s seconds to execute %s" % ("{:.2f}".format(time() - start), name))
        return ret

    return wrapper
