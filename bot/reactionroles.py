from discord.ext.commands import TextChannelConverter, MessageConverter, RoleConverter, CheckFailure
from main import db
from . import bot, has_admin_role, is_dm, not_dm
from discord import Embed
from models import ReactionRole
from asyncio import TimeoutError
from enum import Enum, auto
import discord


class ReactionRoleType(Enum):
    ADD_ON_REACT_REMOVE_ON_DELETE = auto()
    REMOVE_ON_REACT_ADD_ON_DELETE = auto()
    ADD_ON_REACT = auto()
    REMOVE_ON_REACT = auto()


async def send_setup_message(ctx, message: str, part: int):
    embed = Embed(title=f"Reaction Roles - Setup part {part}", description=message, color=0x14c6e6)
    embed.set_footer(text="Made by CJMinecraft")
    return await ctx.send(embed=embed)


async def send_rr_error(ctx, message: str):
    embed = Embed(title=f"Reaction Roles - Error", description=message, color=0xe61414)
    embed.set_footer(text="Made by CJMinecraft")
    await ctx.send(embed=embed)


async def send_complete(channel, reaction_role: ReactionRole):
    embed = Embed(title="Reaction Roles - Setup Complete", color=0x14c6e6)
    embed.add_field(name="ReactionID", value=reaction_role.ReactionRoleId, inline=True)
    embed.add_field(name="Emoji", value=reaction_role.EmojiName, inline=True)
    embed.add_field(name="Type", value=ReactionRoleType(reaction_role.ReactionRoleType).name.replace("_", " ").lower(), inline=True)
    embed.add_field(name="MessageID", value=reaction_role.MessageId, inline=True)
    embed.add_field(name="Channel", value=f"<#{reaction_role.ChannelId}>", inline=True)
    embed.add_field(name="Role", value=f"<@&{reaction_role.RoleId}>", inline=True)
    embed.set_footer(text="Made by CJMinecraft")
    return await channel.send(embed=embed)


@bot.command(name="reactionrole", short_doc="Create a reaction to a message which can modify the roles of a user")
@has_admin_role()
@not_dm()
async def reaction_role(ctx):
    """
    Create a reaction to a message which can modify the roles of a user

    :param ctx: The context for the command
    :return: None
    """
    if is_dm(ctx):
        await send_rr_error(ctx, "Cannot use the reaction role command within a DM")
        return
    last_message = await send_setup_message(ctx, "First tag the channel that you would like the ReactionRole message to be sent", 1)
    stage = 0
    c = ctx.message.channel

    # Reaction role required elements
    channel = None
    message = None
    role = None
    emoji = None
    role_type = ReactionRoleType.ADD_ON_REACT_REMOVE_ON_DELETE

    while True:
        try:
            if stage < 4:
                m = await bot.wait_for("message", timeout=240, check=lambda x: x.channel == c and not x.author.bot)

                if stage == 0:
                    channel = await TextChannelConverter().convert(ctx, m.content)
                    await last_message.delete()
                    last_message = await send_setup_message(ctx, "Please enter the message id of the message you wish to add the reaction to", 2)
                    await m.delete()
                    stage += 1
                elif stage == 1:
                    message = await MessageConverter().convert(ctx, str(channel.id) + "-" + m.content)
                    await last_message.delete()
                    last_message = await send_setup_message(ctx, "Please enter the role you would like to assign", 3)
                    await m.delete()
                    stage += 1
                elif stage == 2:
                    role = await RoleConverter().convert(ctx, m.content)
                    await last_message.delete()
                    last_message = await send_setup_message(ctx,
                                                      "Please select which type of reaction role you would like (the number).\n"
                                                      "1: Add the role when the user reacts and remove if the user removes the reaction\n"
                                                      "2: Remove the role when the user reacts and add if the user removes the reaction\n"
                                                      "3: Add the role when the user reacts and keep until removed by an admin\n"
                                                      "4: Remove the role when the user reacts and keep removed until added by an admin", 4)
                    await m.delete()
                    stage += 1
                elif stage == 3:
                    valid = False
                    for rt in ReactionRoleType:
                        if m.content == str(rt.value):
                            role_type = rt
                            valid = True
                            break
                    if valid:
                        await last_message.delete()
                        last_message = await send_setup_message(ctx, "Please react with the reaction you wish to assign to the role", 5)
                        await m.delete()
                        stage += 1
                    else:
                        raise Exception("Invalid reaction role type")
            else:
                payload = await bot.wait_for("raw_reaction_add", timeout=240, check=lambda x: x.channel_id == c.id and not x.member.bot)
                emoji = payload.emoji
                await last_message.delete()
                await message.add_reaction(payload.emoji)
                break
        except TimeoutError:
            await last_message.delete()
            return
        except BaseException as e:
            await send_rr_error(ctx, str(e))

    rr = ReactionRole(GuildId=channel.guild.id, ChannelId=channel.id, MessageId=message.id, EmojiName=emoji.name, EmojiAnimated=emoji.animated, EmojiId=emoji.id, RoleId=role.id, ReactionRoleType=role_type.value)
    db.session.add(rr)
    db.session.commit()

    await send_complete(c, rr)


def reaction_role_from_payload(payload):
    from sqlalchemy import and_
    return ReactionRole.query.filter(and_(
        ReactionRole.GuildId == payload.guild_id, ReactionRole.ChannelId == payload.channel_id, ReactionRole.MessageId == payload.message_id, ReactionRole.EmojiName == payload.emoji.name, ReactionRole.EmojiAnimated == payload.emoji.animated, ReactionRole.EmojiId == payload.emoji.id)).first()


async def add_roles(user, guild_id, role_id):
    await user.add_roles(discord.utils.get(bot.get_guild(guild_id).roles, id=role_id))


async def remove_roles(user, guild_id, role_id):
    await user.remove_roles(discord.utils.get(bot.get_guild(guild_id).roles, id=role_id))


@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id is None:
        return
    if not payload.member.bot:
        rr = reaction_role_from_payload(payload)
        if rr is not None:
            if rr.ReactionRoleType == ReactionRoleType.ADD_ON_REACT.value or rr.ReactionRoleType == ReactionRoleType.ADD_ON_REACT_REMOVE_ON_DELETE.value:
                await add_roles(payload.member, payload.guild_id, rr.RoleId)
            elif rr.ReactionRoleType == ReactionRoleType.REMOVE_ON_REACT.value or rr.ReactionRoleType == ReactionRoleType.REMOVE_ON_REACT_ADD_ON_DELETE.value:
                await remove_roles(payload.member, payload.guild_id, rr.RoleId)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.guild_id is None:
        return
    user = bot.get_guild(payload.guild_id).get_member(payload.user_id)
    if not user.bot:
        rr = reaction_role_from_payload(payload)
        if rr is not None:
            if rr.ReactionRoleType == ReactionRoleType.ADD_ON_REACT_REMOVE_ON_DELETE.value:
                await remove_roles(user, payload.guild_id, rr.RoleId)
            elif rr.ReactionRoleType == ReactionRoleType.REMOVE_ON_REACT_ADD_ON_DELETE.value:
                await add_roles(user, payload.guild_id, rr.RoleId)
