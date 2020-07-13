from sched import scheduler
from time import time, sleep
from threading import Thread, Event
from types import FunctionType
from typing import Tuple, List
import inspect
from logging import getLogger


logger = getLogger("sync")


def sync(frequency: int):
    def decorator(func):
        if func.__module__ != "__main__":
            Scheduler.functions.append((func, frequency))
        return func
    return decorator


class Scheduler(Thread):
    functions: List[Tuple[FunctionType, int]] = []

    def __init__(self) -> None:
        super().__init__(name="Scheduler")
        self.__scheduler = scheduler(time, sleep)
        self.__stopped = Event()
        self.__classes = {}

    def __run_func(self, func: FunctionType, delay: int, priority: int):
        logger.info("Running func %s" % func.__name__)
        if func in self.__classes.keys():
            Thread(target=lambda: func(self.__classes[func])).start()
        else:
            Thread(target=func).start()
        if not self.__stopped.is_set():
            self.__scheduler.enter(delay, priority, self.__run_func, argument=(func, delay, priority))

    def run(self) -> None:
        for i in range(len(Scheduler.functions)):
            func, delay = Scheduler.functions[i]
            if inspect.isfunction(func):
                clazz = getattr(inspect.getmodule(func), func.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
                if isinstance(clazz, type):
                    self.__classes[func] = clazz
            logger.info("Running func %s" % func.__name__)
            if func in self.__classes.keys():
                Thread(target=lambda: func(self.__classes[func])).start()
            else:
                Thread(target=func).start()
            self.__scheduler.enter(delay, i, self.__run_func, argument=(func, delay, i,))

        self.__scheduler.run(True)

    def stop(self):
        self.__stopped.set()
