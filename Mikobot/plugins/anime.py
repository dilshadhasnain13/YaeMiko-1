# <============================================== IMPORTS =========================================================>
import asyncio
import json
import logging
import os
import random
import re
import shlex
import time
from datetime import datetime
from os.path import basename
from time import time
from traceback import format_exc as err
from typing import Optional, Tuple
from urllib.parse import quote
from uuid import uuid4

import requests
import urllib3
from bs4 import BeautifulSoup
from motor.core import AgnosticClient, AgnosticCollection, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import (
    FloodWait,
    MessageNotModified,
    UserNotParticipant,
    WebpageCurlFailed,
    WebpageMediaEmpty,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from Mikobot import BOT_USERNAME, MESSAGE_DUMP, MONGO_DB_URI, app
from Mikobot.utils.custom_filters import PREFIX_HANDLER

# <=======================================================================================================>

FILLERS = {}

BOT_OWNER = list({int(x) for x in ("5907205317").split()})

_MGCLIENT: AgnosticClient = AsyncIOMotorClient(MONGO_DB_URI)

_DATABASE: AgnosticDatabase = _MGCLIENT["MikobotAnime"]


def get_collection(name: str) -> AgnosticCollection:
    """Create or Get Collection from your database"""
    return _DATABASE[name]


def _close_db() -> None:
    _MGCLIENT.close()


GROUPS = get_collection("GROUPS")
SFW_GRPS = get_collection("SFW_GROUPS")
DC = get_collection("DISABLED_CMDS")
AG = get_collection("AIRING_GROUPS")
CG = get_collection("CRUNCHY_GROUPS")
SG = get_collection("SUBSPLEASE_GROUPS")
HD = get_collection("HEADLINES_GROUPS")
MHD = get_collection("MAL_HEADLINES_GROUPS")
CHAT_OWNER = ChatMemberStatus.OWNER
MEMBER = ChatMemberStatus.MEMBER
ADMINISTRATOR = ChatMemberStatus.ADMINISTRATOR

failed_pic = "https://telegra.ph/file/09733b49f3a9d5b147d21.png"
no_pic = [
    "https://telegra.ph/file/0d2097f442e816ba3f946.jpg",
    "https://telegra.ph/file/5a152016056308ef63226.jpg",
    "https://telegra.ph/file/d2bf913b18688c59828e9.jpg",
    "https://telegra.ph/file/d53083ea69e84e3b54735.jpg",
    "https://telegra.ph/file/b5eb1e3606b7d2f1b491f.jpg",
]


DOWN_PATH = "Mikobot/downloads/"

AUTH_USERS = get_collection("AUTH_USERS")
IGNORE = get_collection("IGNORED_USERS")
PIC_DB = get_collection("PIC_DB")
GROUPS = get_collection("GROUPS")
CC = get_collection("CONNECTED_CHANNELS")
USER_JSON = {}
USER_WC = {}

LANGUAGES = {
    "af": "afrikaans",
    "sq": "albanian",
    "am": "amharic",
    "ar": "arabic",
    "hy": "armenian",
    "az": "azerbaijani",
    "eu": "basque",
    "be": "belarusian",
    "bn": "bengali",
    "bs": "bosnian",
    "bg": "bulgarian",
    "ca": "catalan",
    "ceb": "cebuano",
    "ny": "chichewa",
    "zh-cn": "chinese (simplified)",
    "zh-tw": "chinese (traditional)",
    "co": "corsican",
    "hr": "croatian",
    "cs": "czech",
    "da": "danish",
    "nl": "dutch",
    "en": "english",
    "eo": "esperanto",
    "et": "estonian",
    "tl": "filipino",
    "fi": "finnish",
    "fr": "french",
    "fy": "frisian",
    "gl": "galician",
    "ka": "georgian",
    "de": "german",
    "el": "greek",
    "gu": "gujarati",
    "ht": "haitian creole",
    "ha": "hausa",
    "haw": "hawaiian",
    "iw": "hebrew",
    "he": "hebrew",
    "hi": "hindi",
    "hmn": "hmong",
    "hu": "hungarian",
    "is": "icelandic",
    "ig": "igbo",
    "id": "indonesian",
    "ga": "irish",
    "it": "italian",
    "ja": "japanese",
    "jw": "javanese",
    "kn": "kannada",
    "kk": "kazakh",
    "km": "khmer",
    "ko": "korean",
    "ku": "kurdish (kurmanji)",
    "ky": "kyrgyz",
    "lo": "lao",
    "la": "latin",
    "lv": "latvian",
    "lt": "lithuanian",
    "lb": "luxembourgish",
    "mk": "macedonian",
    "mg": "malagasy",
    "ms": "malay",
    "ml": "malayalam",
    "mt": "maltese",
    "mi": "maori",
    "mr": "marathi",
    "mn": "mongolian",
    "my": "myanmar (burmese)",
    "ne": "nepali",
    "no": "norwegian",
    "or": "odia",
    "ps": "pashto",
    "fa": "persian",
    "pl": "polish",
    "pt": "portuguese",
    "pa": "punjabi",
    "ro": "romanian",
    "ru": "russian",
    "sm": "samoan",
    "gd": "scots gaelic",
    "sr": "serbian",
    "st": "sesotho",
    "sn": "shona",
    "sd": "sindhi",
    "si": "sinhala",
    "sk": "slovak",
    "sl": "slovenian",
    "so": "somali",
    "es": "spanish",
    "su": "sundanese",
    "sw": "swahili",
    "sv": "swedish",
    "tg": "tajik",
    "ta": "tamil",
    "tt": "tatar",
    "te": "telugu",
    "th": "thai",
    "tr": "turkish",
    "tk": "turkmen",
    "uk": "ukrainian",
    "ur": "urdu",
    "ug": "uyghur",
    "uz": "uzbek",
    "vi": "vietnamese",
    "cy": "welsh",
    "xh": "xhosa",
    "yi": "yiddish",
    "yo": "yoruba",
    "zu": "zulu",
}

DEFAULT_SERVICE_URLS = (
    "translate.google.ac",
    "translate.google.ad",
    "translate.google.ae",
    "translate.google.al",
    "translate.google.am",
    "translate.google.as",
    "translate.google.at",
    "translate.google.az",
    "translate.google.ba",
    "translate.google.be",
    "translate.google.bf",
    "translate.google.bg",
    "translate.google.bi",
    "translate.google.bj",
    "translate.google.bs",
    "translate.google.bt",
    "translate.google.by",
    "translate.google.ca",
    "translate.google.cat",
    "translate.google.cc",
    "translate.google.cd",
    "translate.google.cf",
    "translate.google.cg",
    "translate.google.ch",
    "translate.google.ci",
    "translate.google.cl",
    "translate.google.cm",
    "translate.google.cn",
    "translate.google.co.ao",
    "translate.google.co.bw",
    "translate.google.co.ck",
    "translate.google.co.cr",
    "translate.google.co.id",
    "translate.google.co.il",
    "translate.google.co.in",
    "translate.google.co.jp",
    "translate.google.co.ke",
    "translate.google.co.kr",
    "translate.google.co.ls",
    "translate.google.co.ma",
    "translate.google.co.mz",
    "translate.google.co.nz",
    "translate.google.co.th",
    "translate.google.co.tz",
    "translate.google.co.ug",
    "translate.google.co.uk",
    "translate.google.co.uz",
    "translate.google.co.ve",
    "translate.google.co.vi",
    "translate.google.co.za",
    "translate.google.co.zm",
    "translate.google.co.zw",
    "translate.google.co",
    "translate.google.com.af",
    "translate.google.com.ag",
    "translate.google.com.ai",
    "translate.google.com.ar",
    "translate.google.com.au",
    "translate.google.com.bd",
    "translate.google.com.bh",
    "translate.google.com.bn",
    "translate.google.com.bo",
    "translate.google.com.br",
    "translate.google.com.bz",
    "translate.google.com.co",
    "translate.google.com.cu",
    "translate.google.com.cy",
    "translate.google.com.do",
    "translate.google.com.ec",
    "translate.google.com.eg",
    "translate.google.com.et",
    "translate.google.com.fj",
    "translate.google.com.gh",
    "translate.google.com.gi",
    "translate.google.com.gt",
    "translate.google.com.hk",
    "translate.google.com.jm",
    "translate.google.com.kh",
    "translate.google.com.kw",
    "translate.google.com.lb",
    "translate.google.com.lc",
    "translate.google.com.ly",
    "translate.google.com.mm",
    "translate.google.com.mt",
    "translate.google.com.mx",
    "translate.google.com.my",
    "translate.google.com.na",
    "translate.google.com.ng",
    "translate.google.com.ni",
    "translate.google.com.np",
    "translate.google.com.om",
    "translate.google.com.pa",
    "translate.google.com.pe",
    "translate.google.com.pg",
    "translate.google.com.ph",
    "translate.google.com.pk",
    "translate.google.com.pr",
    "translate.google.com.py",
    "translate.google.com.qa",
    "translate.google.com.sa",
    "translate.google.com.sb",
    "translate.google.com.sg",
    "translate.google.com.sl",
    "translate.google.com.sv",
    "translate.google.com.tj",
    "translate.google.com.tr",
    "translate.google.com.tw",
    "translate.google.com.ua",
    "translate.google.com.uy",
    "translate.google.com.vc",
    "translate.google.com.vn",
    "translate.google.com",
    "translate.google.cv",
    "translate.google.cx",
    "translate.google.cz",
    "translate.google.de",
    "translate.google.dj",
    "translate.google.dk",
    "translate.google.dm",
    "translate.google.dz",
    "translate.google.ee",
    "translate.google.es",
    "translate.google.eu",
    "translate.google.fi",
    "translate.google.fm",
    "translate.google.fr",
    "translate.google.ga",
    "translate.google.ge",
    "translate.google.gf",
    "translate.google.gg",
    "translate.google.gl",
    "translate.google.gm",
    "translate.google.gp",
    "translate.google.gr",
    "translate.google.gy",
    "translate.google.hn",
    "translate.google.hr",
    "translate.google.ht",
    "translate.google.hu",
    "translate.google.ie",
    "translate.google.im",
    "translate.google.io",
    "translate.google.iq",
    "translate.google.is",
    "translate.google.it",
    "translate.google.je",
    "translate.google.jo",
    "translate.google.kg",
    "translate.google.ki",
    "translate.google.kz",
    "translate.google.la",
    "translate.google.li",
    "translate.google.lk",
    "translate.google.lt",
    "translate.google.lu",
    "translate.google.lv",
    "translate.google.md",
    "translate.google.me",
    "translate.google.mg",
    "translate.google.mk",
    "translate.google.ml",
    "translate.google.mn",
    "translate.google.ms",
    "translate.google.mu",
    "translate.google.mv",
    "translate.google.mw",
    "translate.google.ne",
    "translate.google.nf",
    "translate.google.nl",
    "translate.google.no",
    "translate.google.nr",
    "translate.google.nu",
    "translate.google.pl",
    "translate.google.pn",
    "translate.google.ps",
    "translate.google.pt",
    "translate.google.ro",
    "translate.google.rs",
    "translate.google.ru",
    "translate.google.rw",
    "translate.google.sc",
    "translate.google.se",
    "translate.google.sh",
    "translate.google.si",
    "translate.google.sk",
    "translate.google.sm",
    "translate.google.sn",
    "translate.google.so",
    "translate.google.sr",
    "translate.google.st",
    "translate.google.td",
    "translate.google.tg",
    "translate.google.tk",
    "translate.google.tl",
    "translate.google.tm",
    "translate.google.tn",
    "translate.google.to",
    "translate.google.tt",
    "translate.google.us",
    "translate.google.vg",
    "translate.google.vu",
    "translate.google.ws",
)
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URLS_SUFFIX = [
    re.search("translate.google.(.*)", url.strip()).group(1)
    for url in DEFAULT_SERVICE_URLS
]
URL_SUFFIX_DEFAULT = "cn"


def rand_key():
    return str(uuid4())[:8]


def control_user(func):
    async def wrapper(_, message: Message):
        msg = json.loads(str(message))
        gid = msg["chat"]["id"]
        gidtype = msg["chat"]["type"]
        if gidtype in [ChatType.SUPERGROUP, ChatType.GROUP] and not (
            await GROUPS.find_one({"_id": gid})
        ):
            try:
                gidtitle = msg["chat"]["username"]
            except KeyError:
                gidtitle = msg["chat"]["title"]
            await GROUPS.insert_one({"_id": gid, "grp": gidtitle})
            await clog(
                "Mikobot",
                f"Bot added to a new group\n\n{gidtitle}\nID: `{gid}`",
                "NEW_GROUP",
            )
        try:
            user = msg["from_user"]["id"]
        except KeyError:
            user = msg["chat"]["id"]
        if await IGNORE.find_one({"_id": user}):
            return
        nut = time()
        if user not in BOT_OWNER:
            try:
                out = USER_JSON[user]
                if nut - out < 1.2:
                    USER_WC[user] += 1
                    if USER_WC[user] == 3:
                        await message.reply_text(
                            ("Stop spamming bot!!!" + "\nElse you will be blacklisted"),
                        )
                        await clog("Mikobot", f"UserID: {user}", "SPAM")
                    if USER_WC[user] == 5:
                        await IGNORE.insert_one({"_id": user})
                        await message.reply_text(
                            (
                                "You have been exempted from using this bot "
                                + "now due to spamming 5 times consecutively!!!"
                                + "\nTo remove restriction plead to "
                                + "@ProjectCodeXSupport"
                            )
                        )
                        await clog("Mikobot", f"UserID: {user}", "BAN")
                        return
                    await asyncio.sleep(USER_WC[user])
                else:
                    USER_WC[user] = 0
            except KeyError:
                pass
            USER_JSON[user] = nut
        try:
            await func(_, message, msg)
        except FloodWait as e:
            await asyncio.sleep(e.x + 5)
        except MessageNotModified:
            pass
        except Exception:
            e = err()
            reply_msg = None
            if func.__name__ == "trace_bek":
                reply_msg = message.reply_to_message
            try:
                await clog(
                    "Mikobot",
                    "Message:\n" + msg["text"] + "\n\n" + "```" + e + "```",
                    "COMMAND",
                    msg=message,
                    replied=reply_msg,
                )
            except Exception:
                await clog("Mikobot", e, "FAILURE", msg=message)

    return wrapper


def check_user(func):
    async def wrapper(_, c_q: CallbackQuery):
        cq = json.loads(str(c_q))
        user = cq["from_user"]["id"]
        if await IGNORE.find_one({"_id": user}):
            return
        cqowner_is_ch = False
        cqowner = cq["data"].split("_").pop()
        if "-100" in cqowner:
            cqowner_is_ch = True
            ccdata = await CC.find_one({"_id": cqowner})
            if ccdata and ccdata["usr"] == user:
                user_valid = True
            else:
                user_valid = False
        if user in BOT_OWNER or user == int(cqowner):
            if user not in BOT_OWNER:
                nt = time()
                try:
                    ot = USER_JSON[user]
                    if nt - ot < 1.4:
                        await c_q.answer(
                            ("Stop spamming bot!!!\n" + "Else you will be blacklisted"),
                            show_alert=True,
                        )
                        await clog("Mikobot", f"UserID: {user}", "SPAM")
                except KeyError:
                    pass
                USER_JSON[user] = nt
            try:
                await func(_, c_q, cq)
            except FloodWait as e:
                await asyncio.sleep(e.x + 5)
            except MessageNotModified:
                pass
            except Exception:
                e = err()
                reply_msg = None
                if func.__name__ == "tracemoe_btn":
                    reply_msg = c_q.message.reply_to_message
                try:
                    await clog(
                        "Mikobot",
                        "Callback:\n" + cq["data"] + "\n\n" + "```" + e + "```",
                        "CALLBACK",
                        cq=c_q,
                        replied=reply_msg,
                    )
                except Exception:
                    await clog("Mikobot", e, "FAILURE", cq=c_q)
        else:
            if cqowner_is_ch:
                if user_valid:
                    try:
                        await func(_, c_q, cq)
                    except FloodWait as e:
                        await asyncio.sleep(e.x + 5)
                    except MessageNotModified:
                        pass
                    except Exception:
                        e = err()
                        reply_msg = None
                        if func.__name__ == "tracemoe_btn":
                            reply_msg = c_q.message.reply_to_message
                        try:
                            await clog(
                                "Mikobot",
                                "Callback:\n" + cq["data"] + "\n\n" + "```" + e + "```",
                                "CALLBACK_ANON",
                                cq=c_q,
                                replied=reply_msg,
                            )
                        except Exception:
                            await clog("Mikobot", e, "FAILURE", cq=c_q)
                else:
                    await c_q.answer(
                        (
                            "No one can click buttons on queries made by "
                            + "channels unless connected with /aniconnect!!!"
                        ),
                        show_alert=True,
                    )
            else:
                await c_q.answer(
                    "Not your query!!!",
                    show_alert=True,
                )

    return wrapper


async def media_to_image(client: app, message: Message, x: Message, replied: Message):
    if not (replied.photo or replied.sticker or replied.animation or replied.video):
        await x.edit_text("Media Type Is Invalid !")
        await asyncio.sleep(5)
        await x.delete()
        return
    media = replied.photo or replied.sticker or replied.animation or replied.video
    if not os.path.isdir(DOWN_PATH):
        os.makedirs(DOWN_PATH)
    dls = await client.download_media(
        media,
        file_name=DOWN_PATH + rand_key(),
    )
    dls_loc = os.path.join(DOWN_PATH, os.path.basename(dls))
    if replied.sticker and replied.sticker.file_name.endswith(".tgs"):
        png_file = os.path.join(DOWN_PATH, f"{rand_key()}.png")
        cmd = (
            f"lottie_convert.py --frame 0 -if lottie " + f"-of png {dls_loc} {png_file}"
        )
        stdout, stderr = (await runcmd(cmd))[:2]
        os.remove(dls_loc)
        if not os.path.lexists(png_file):
            await x.edit_text("This sticker is Gey, Task Failed Successfully ≧ω≦")
            await asyncio.sleep(5)
            await x.delete()
            raise Exception(stdout + stderr)
        dls_loc = png_file
    elif replied.sticker and replied.sticker.file_name.endswith(".webp"):
        stkr_file = os.path.join(DOWN_PATH, f"{rand_key()}.png")
        os.rename(dls_loc, stkr_file)
        if not os.path.lexists(stkr_file):
            await x.edit_text("```Sticker not found...```")
            await asyncio.sleep(5)
            await x.delete()
            return
        dls_loc = stkr_file
    elif replied.animation or replied.video:
        await x.edit_text("`Converting Media To Image ...`")
        jpg_file = os.path.join(DOWN_PATH, f"{rand_key()}.jpg")
        await take_screen_shot(dls_loc, 0, jpg_file)
        os.remove(dls_loc)
        if not os.path.lexists(jpg_file):
            await x.edit_text("This Gif is Gey (｡ì _ í｡), Task Failed Successfully !")
            await asyncio.sleep(5)
            await x.delete()
            return
        dls_loc = jpg_file
    return dls_loc


async def runcmd(cmd: str) -> Tuple[str, str, int, int]:
    """run command in terminal"""
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode("utf-8", "replace").strip(),
        stderr.decode("u
