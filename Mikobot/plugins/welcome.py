# <============================================== IMPORTS =========================================================>
import html
import os
import random
import re
import textwrap
import time
from contextlib import suppress
from datetime import datetime
from functools import partial

import unidecode
from PIL import Image, ImageChops, ImageDraw, ImageFont
from pyrogram import filters as ft
from pyrogram.types import ChatMemberUpdated, Message
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown, mention_html, mention_markdown

import Database.sql.welcome_sql as sql
from Database.mongodb.toggle_mongo import dwelcome_off, dwelcome_on, is_dwelcome_on
from Database.sql.global_bans_sql import is_user_gbanned
from Infamous.temp import temp
from Mikobot import DEV_USERS
from Mikobot import DEV_USERS as SUDO
from Mikobot import DRAGONS, EVENT_LOGS, LOGGER, OWNER_ID, app, dispatcher, function
from Mikobot.plugins.helper_funcs.chat_status import check_admin, is_user_ban_protected
from Mikobot.plugins.helper_funcs.misc import build_keyboard, revert_buttons
from Mikobot.plugins.helper_funcs.msg_types import get_welcome_type
from Mikobot.plugins.helper_funcs.string_handling import escape_invalid_curly_brackets
from Mikobot.plugins.log_channel import loggable
from Mikobot.utils.can_restrict import can_restrict

# <=======================================================================================================>

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}


# <================================================ TEMPLATE WELCOME FUNCTION =======================================================>
async def circle(pfp, size=(259, 259)):
    pfp = pfp.resize(size, Image.ANTIALIAS).convert("RGBA")
    bigsize = (pfp.size[0] * 3, pfp.size[1] * 3)
    mask = Image.new("L", bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(pfp.size, Image.ANTIALIAS)
    mask = ImageChops.darker(mask, pfp.split()[-1])
    pfp.putalpha(mask)
    return pfp


async def draw_multiple_line_text(image, text, font, text_start_height):
    draw = ImageDraw.Draw(image)
    image_width, image_height = image.size
    y_text = text_start_height
    lines = textwrap.wrap(text, width=50)
    for line in lines:
        line_width, line_height = font.getsize(line)
        draw.text(
            ((image_width - line_width) // 2, y_text), line, font=font, fill="black"
        )
        y_text += line_height


async def welcomepic(pic, user, chat, user_id):
    user = unidecode.unidecode(user)
    background = Image.open("Extra/bgg.jpg")
    background = background.resize(
        (background.size[0], background.size[1]), Image.ANTIALIAS
    )
    pfp = Image.open(pic).convert("RGBA")
    pfp = await circle(pfp, size=(259, 259))
    pfp_x = 55
    pfp_y = (background.size[1] - pfp.size[1]) // 2 + 38
    draw = ImageDraw.Draw(background)
    font = ImageFont.truetype("Extra/Calistoga-Regular.ttf", 42)
    text_width, text_height = draw.textsize(f"{user} [{user_id}]", font=font)
    text_x = 20
    text_y = background.height - text_height - 20 - 25
    draw.text((text_x, text_y), f"{user} [{user_id}]", font=font, fill="white")
    background.paste(pfp, (pfp_x, pfp_y), pfp)
    welcome_image_path = f"downloads/welcome_{user_id}.png"
    background.save(welcome_image_path)
    return welcome_image_path


@app.on_chat_member_updated(ft.group)
async def member_has_joined(client, member: ChatMemberUpdated):
    if (
        not member.new_chat_member
        or member.new_chat_member.status in {"banned", "left", "restricted"}
        or member.old_chat_member
    ):
        return
    user = member.new_chat_member.user if member.new_chat_member else member.from_user
    if user.id in SUDO:
        await client.send_message(member.chat.id, "**Global Admins Joined The Chat!**")
        return
    elif user.is_bot:
        return
    else:
        chat_id = member.chat.id
        welcome_enabled = await is_dwelcome_on(chat_id)
        if not welcome_enabled:
            return
        if f"welcome-{chat_id}" in temp.MELCOW:
            try:
                await temp.MELCOW[f"welcome-{chat_id}"].delete()
            except:
                pass
        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        joined_date = datetime.fromtimestamp(time.time()).strftime("%Y.%m. %d %H:%M:%S")
        first_name = (
            f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        )
        user_id = user.id
        dc = user.dc_id
        try:
            pic = await client.download_media(
                user.photo.big_file_id, file_name=f"pp{user_id}.png"
            )
        except AttributeError:
            pic = "Extra/profilepic.png"
        try:
            welcomeimg = await welcomepic(
                pic, user.first_name, member.chat.title, user_id
            )
            temp.MELCOW[f"welcome-{chat_id}"] = await client.send_photo(
                member.chat.id,
                photo=welcomeimg,
                caption=f"**𝗛𝗲𝘆❗️{mention}, 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗧𝗼 {member.chat.title} 𝗚𝗿𝗼𝘂𝗽.**\n\n**➖➖➖➖➖➖➖➖➖➖➖➖**\n**𝗡𝗔𝗠𝗘 : {first_name}**\n**𝗜𝗗 : {user_id}**\n**𝗗𝗔𝗧𝗘 𝗝𝗢𝗜𝗡𝗘𝗗 : {joined_date}**",
            )
        except Exception as e:
            print(e)
        try:
            os.remove(f"downloads/welcome_{user_id}.png")
            os.remove(f"downloads/pp{user_id}.png")
        except Exception:
            pass


@app.on_message(ft.command("dwelcome on"))
@can_restrict
async def enable_welcome(_, message: Message):
    chat_id = message.chat.id
    welcome_enabled = await is_dwelcome_on(chat_id)
    if welcome_enabled:
        await message.reply_text("Default welcome is already enabled")
        return
    await dwelcome_on(chat_id)
    await message.reply_text("New default welcome message enabled for this chat.")


@app.on_message(ft.command("dwelcome off"))
@can_restrict
async def disable_welcome(_, message: Message):
    chat_id = message.chat.id
    welcome_enabled = await is_dwelcome_on(chat_id)
    if not welcome_enabled:
        await message.reply_text("Default welcome is already disabled")
        return
    await dwelcome_off(chat_id)
    await message.reply_text("New default welcome disabled for this chat.")


# <=======================================================================================================>


# <================================================ NORMAL WELCOME FUNCTION =======================================================>
async def send(update: Update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.effective_message.message_id
    if cleanserv:
        try:
            await dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        try:
            msg = await dispatcher.bot.send_message(
                chat.id,
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        except:
            msg = await update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                reply_to_message_id=reply,
            )
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            msg = await update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
                quote=False,
            )
        elif excp.message == "Button_url_invalid":
            try:
                msg = await dispatcher.bot.send_message(
                    chat.id,
                    backup_message
                    + "\nNote: The current message has an invalid URL in one of its buttons. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except:
                msg = await update.effective_message.reply_text(
                    backup_message
                    + "\nNote: The current message has an invalid URL in one of its buttons. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )
        elif excp.message == "Unsupported URL protocol":
            try:
                msg = await dispatcher.bot.send_message(
                    chat.id,
                    backup_message
                    + "\nNote: The current message has buttons which use URL protocols that are unsupported by Telegram. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except:
                msg = await update.effective_message.reply_text(
                    backup_message
                    + "\nNote: The current message has buttons which use URL protocols that are unsupported by Telegram. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )
        elif excp.message == "Wrong URL host":
            try:
                msg = await dispatcher.bot.send_message(
                    chat.id,
                    backup_message
                    + "\nNote: The current message has some bad URLs. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except:
                msg = await update.effective_message.reply_text(
                    backup_message
                    + "\nNote: The current message has some bad URLs. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! Got invalid URL host errors")
        elif excp.message == "Have no rights to send a message":
            return
        else:
            try:
                msg = await dispatcher.bot.send_message(
                    chat.id,
                    backup_message
                    + "\nNote: An error occurred when sending the custom message. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except:
                msg = await update.effective_message.reply_text(
                    backup_message
                    + "\nNote: An error occurred when sending the custom message. Please update.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )
            LOGGER.exception()
    return msg


@loggable
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:
        if new_mem.id == bot.id and not Mikobot.ALLOW_CHATS:
            with suppress(BadRequest):
                await update.effective_message.reply_text(
                    "Groups are disabled for {}, I'm outta here.".format(bot.first_name)
                )
            await bot.leave_chat(update.effective_chat.id)
            return

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True
        media_wel = False

        if is_user_gbanned(new_mem.id):
            return

        if should_welc:
            reply = update.message.message_id
            cleanserv = sql.clean_service(chat.id)
            if cleanserv:
                try:
                    await dispatcher.bot.delete_message(
                        chat.id, update.message.message_id
                    )
                except BadRequest:
                    pass
                reply = False

            if new_mem.id == OWNER_ID:
                await update.effective_message.reply_text(
                    "Oh, darling, I have searched for you everywhere.",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    "{}\n"
                    "#USER_JOINED\n"
                    "Bot owner just joined the group".format(html.escape(chat.title))
                )
                continue

            elif new_mem.id in DEV_USERS:
                await update.effective_message.reply_text(
                    "Be cool! A member of the team just joined.",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    "{}\n"
                    "#USER_JOINED\n"
                    "Bot dev just joined the group".format(html.escape(chat.title))
                )
                continue

            elif new_mem.id in DRAGONS:
                await update.effective_message.reply_text(
                    "Whoa! A dragon disaster just joined! Stay alert!",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    "{}\n"
                    "#USER_JOINED\n"
                    "Bot sudo just joined the group".format(html.escape(chat.title))
                )
                continue

            elif new_mem.id == bot.id:
                creator = None
                for x in await bot.get_chat_administrators(update.effective_chat.id):
                    if x.status == "creator":
                        creator = x.user
                        break
                if creator:
                    reply = """#NEWGROUP \
                        \nID:   `{}` \
                    """.format(
                        chat.id
                    )

                    if chat.title:
                        reply += "\nGroup name:   **{}**".format(
                            escape_markdown(chat.title)
                        )

                    if chat.username:
                        reply += "\nUsername: @{}".format(
                            escape_markdown(chat.username)
                        )

                    reply += "\nCreator ID:   `{}`".format(creator.id)

                    if creator.username:
                        reply += "\nCreator Username: @{}".format(creator.username)

                    await bot.send_message(
                        EVENT_LOGS,
                        reply,
                        parse_mode="markdown",
                    )
                else:
                    await bot.send_message(
                        EVENT_LOGS,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>".format(
                            html.escape(chat.title),
                            chat.id,
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                await update.effective_message.reply_text(
                    "I feel like I'm gonna suffocate in here.",
                    reply_to_message_id=reply,
                )
                continue

            else:
                buttons = sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    media_wel = True

                first_name = new_mem.first_name or "PersonWithNoName"

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES,
                        ).format(first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(
                            "{} {}".format(first_name, new_mem.last_name)
                        )
                    else:
                        fullname = escape_markdown(first_name)
                    count = await chat.get_member_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@{}".format(escape_markdown(new_mem.username))
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome,
                        VALID_WELCOME_FORMATTERS,
                    )
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_mem.id,
                    )

                else:
                    res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name),
                    )
                    keyb = []

                backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name),
                )
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None
            reply = None

        if (
            await is_user_ban_protected(
                chat, new_mem.id, await chat.get_member(new_mem.id)
            )
            or human_checks
        ):
            should_mute = False
        if new_mem.is_bot:
            should_mute = False

        if user.id == new_mem.id:
            if should_mute:
                if welc_mutes == "soft":
                    await bot.restrict_chat_member(
                        chat.id,
                        new_mem.id,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_add_web_page_previews=False,
                            can_manage_topics=False,
                        ),
                        until_date=(int(time.time() + 24 * 60 * 60)),
                    )
                if welc_mutes == "strong":
                
