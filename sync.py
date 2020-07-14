import aioschedule as schedule
import inspect
import logging
from discord import Embed, Colour


logger = logging.getLogger("sync")


__functions = []


async def schedule_functions():
    for func in __functions:
        kwargs = {}
        if inspect.isfunction(func):
            clazz = getattr(inspect.getmodule(func), func.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
            if isinstance(clazz, type):
                kwargs["cls"] = clazz

        async def wrapper():
            from bot import bot, CJ_USER_ID
            user = bot.get_user(CJ_USER_ID)

            embed = Embed(title="Running Sync Function", description=f"Running sync function `{func.__name__}`", color=Colour.gold())
            embed.set_footer(text="Made by CJMinecraft")
            channel = await user.create_dm()
            await channel.send(embed=embed)

            await func(**kwargs)

            embed = Embed(title="Finished Sync Function", description=f"Finished sync function `{func.__name__}`",
                          color=Colour.gold())
            embed.set_footer(text="Made by CJMinecraft")
            channel = await user.create_dm()
            await channel.send(embed=embed)

        await wrapper()
        schedule.every(12).hours.do(wrapper)


def sync(func):
    __functions.append(func)
    logger.info("Scheduling bi-daily task %s" % func.__name__)
    return func
