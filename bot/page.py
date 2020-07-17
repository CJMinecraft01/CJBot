from abc import ABCMeta, abstractmethod
from typing import Generator, List

from . import bot
from discord import Embed, Message
from enum import Enum, auto


class PageEntry(metaclass=ABCMeta):
    @abstractmethod
    def title(self) -> str:
        pass

    @abstractmethod
    def to_message(self) -> str:
        pass


class PageActionResult(Enum):
    PREVIOUS_PAGE = auto()
    NEXT_PAGE = auto()
    CANCEL = auto()

    @staticmethod
    def get_result(emoji):
        if emoji.name == Page.PREVIOUS_PAGE_EMOJI:
            return PageActionResult.PREVIOUS_PAGE
        if emoji.name == Page.NEXT_PAGE_EMOJI:
            return PageActionResult.NEXT_PAGE
        return PageActionResult.CANCEL


class Page:
    PREVIOUS_PAGE_EMOJI = "\U00002B05"
    NEXT_PAGE_EMOJI = "\U000027A1"
    CANCEL_EMOJI = "\U0000274E"

    def __init__(self, size: int, generator: Generator) -> None:
        self.__size = size
        self.__page = 1
        self.__max_page_reached = False
        self.__max_page_size = 0
        self.__generator = generator
        self.__entries: List[PageEntry] = []

    async def __add_reaction(self, message, emoji):
        try:
            await message.add_reaction(emoji)
        except: pass

    async def __remove_reaction(self, message, emoji, user=None):
        try:
            await message.remove_reaction(emoji, user if user is not None else bot.user)
        except: pass

    async def __cancel(self, message: Message):
        try:
            await message.clear_reactions()
        except:
            await self.__remove_reaction(message, self.PREVIOUS_PAGE_EMOJI)
            await self.__remove_reaction(message, self.CANCEL_EMOJI)
            await self.__remove_reaction(message, self.NEXT_PAGE_EMOJI)

    async def __handle_pages(self, message, channel, embed, user) -> PageActionResult:
        edit = True
        while True:
            if edit:
                for entry in self.__entries[(self.__page - 1) * self.__size:min(self.__page * self.__size,len(self.__entries))]:
                    embed.add_field(name=entry.title(), value=entry.to_message(), inline=False)
                await message.edit(embed=embed)
            # await self.__cancel(message)
            # if self.show_previous_page:
            #     await self.__add_reaction(message, self.PREVIOUS_PAGE_EMOJI)
            # await self.__add_reaction(message, self.CANCEL_EMOJI)
            # if self.show_next_page:
            #     await self.__add_reaction(message, self.NEXT_PAGE_EMOJI)
            payload = await bot.wait_for("raw_reaction_add", check=lambda x: (x.guild_id is None and x.user_id == user.id) or (x.guild_id is not None and x.channel_id == channel.id and not x.member.bot and x.member == user))
            action = PageActionResult.get_result(payload.emoji)
            if action == PageActionResult.CANCEL:
                await self.__cancel(message)
                return action
            if action == PageActionResult.NEXT_PAGE:
                await self.__remove_reaction(message, self.NEXT_PAGE_EMOJI, user)
                if self.show_next_page:
                    self.__page += 1
                    embed.clear_fields()
                    edit = True
                else:
                    edit = False
            elif action == PageActionResult.PREVIOUS_PAGE:
                await self.__remove_reaction(message, self.PREVIOUS_PAGE_EMOJI, user)
                if self.show_previous_page:
                    self.__page -= 1
                    embed.clear_fields()
                    edit = True
                else:
                    edit = False
            if self.__page * self.__size > len(self.__entries) and edit:
                return PageActionResult.NEXT_PAGE

    async def show(self, ctx, title: str, colour):
        channel = ctx.message.channel
        message: Message = None
        embed = Embed(title=title, colour=colour)
        embed.set_footer(text="Made by CJMinecraft")
        # While generating the results
        for result in self.__generator:
            self.__entries.append(result)
            embed.add_field(name=result.title(), value=result.to_message(), inline=False)
            if len(self.__entries) % (self.__size * self.__page) == 0:
                if message is None:
                    # Will only happen once when the data is being generated
                    message = await ctx.send(embed=embed)
                    await self.__add_reaction(message, self.PREVIOUS_PAGE_EMOJI)
                    await self.__add_reaction(message, self.CANCEL_EMOJI)
                    await self.__add_reaction(message, self.NEXT_PAGE_EMOJI)
                else:
                    await message.edit(embed=embed)
                    # await self.__cancel(message)
                    # if self.show_previous_page:
                    #     await self.__add_reaction(message, self.PREVIOUS_PAGE_EMOJI)
                    # await self.__add_reaction(message, self.CANCEL_EMOJI)
                    # if self.show_next_page:
                    #     await self.__add_reaction(message, self.NEXT_PAGE_EMOJI)
                while True:
                    payload = await bot.wait_for("raw_reaction_add", check=lambda x: (x.guild_id is None and x.user_id == ctx.message.author.id) or (x.guild_id is not None and x.channel_id == channel.id and not x.member.bot and x.member == ctx.message.author))
                    action = PageActionResult.get_result(payload.emoji)
                    if action == PageActionResult.CANCEL:
                        await self.__cancel(message)
                        return
                    if action == PageActionResult.NEXT_PAGE:
                        await self.__remove_reaction(message, self.NEXT_PAGE_EMOJI, ctx.message.author)
                        if self.show_next_page:
                            self.__page += 1
                            embed.clear_fields()
                            break
                    elif action == PageActionResult.PREVIOUS_PAGE:
                        await self.__remove_reaction(message, self.PREVIOUS_PAGE_EMOJI, ctx.message.author)
                        if self.show_previous_page:
                            self.__page -= 1
                            embed.clear_fields()
                            if await self.__handle_pages(message, channel, embed, ctx.message.author) == PageActionResult.CANCEL:
                                return
                            break

        if message is None:
            if len(embed.fields) == 0:
                embed.description = "No results found"
            # Must not be enough results to fill one page
            await ctx.send(embed=embed)
        else:
            # await message.edit(embed=embed)
            # await self.__cancel(message)
            self.__max_page_reached = True
            self.__max_page_size = self.__page
            embed.clear_fields()
            await self.__add_reaction(message, self.PREVIOUS_PAGE_EMOJI)
            await self.__add_reaction(message, self.CANCEL_EMOJI)
            await self.__handle_pages(message, channel, embed, ctx.message.author)

    @property
    def show_previous_page(self):
        return self.__page > 1

    @property
    def show_next_page(self):
        return not self.__max_page_reached or self.__page < self.__max_page_size

    @property
    def size(self):
        return self.__size
