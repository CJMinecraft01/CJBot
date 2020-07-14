import aioschedule as schedule
import inspect
import logging


logger = logging.getLogger("sync")


__functions = []


async def schedule_functions():
    for func in __functions:
        kwargs = {}
        if inspect.isfunction(func):
            clazz = getattr(inspect.getmodule(func), func.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
            if isinstance(clazz, type):
                kwargs["cls"] = clazz
        await func(**kwargs)
        schedule.every(12).hours.do(func, **kwargs)


def sync(func):
    __functions.append(func)
    logger.info("Scheduling bi-daily task %s" % func.__name__)
    return func
