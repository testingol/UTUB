import asyncio
import io
import os
import re
import subprocess
import sys
import traceback
from asyncio import sleep
from contextlib import suppress
from io import BytesIO, StringIO
from random import randint
from typing import Optional
from pprint import pprint
from urllib.parse import quote, unquote
from json.decoder import JSONDecodeError
import wget
from pyrogram import filters as Filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
)
from pyrogram import Client, filters
from pyrogram.raw import functions, types
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.messages import GetFullChat
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall
from pyrogram.raw.types import InputGroupCall, InputPeerChannel, InputPeerChat
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from ..config import Config
from ..translations import Messages as tr
from ..utubebot import UtubeBot

class u:
    _ = ""

def _stringify(text=None, *args, **kwargs):
    if text:
        u._ = text
        text = _parse_eval(text)
    return print(text, *args, **kwargs)

def _unquote_text(text):
    return text.replace("'", unquote("%5C%27")).replace('"', unquote("%5C%22"))

def json_parser(data, indent=None, ascii=False):
    parsed = {}
    try:
        if isinstance(data, str):
            parsed = json.loads(str(data))
            if indent:
                parsed = json.dumps(
                    json.loads(str(data)), indent=indent, ensure_ascii=ascii
                )
        elif isinstance(data, dict):
            parsed = data
            if indent:
                parsed = json.dumps(data, indent=indent, ensure_ascii=ascii)
    except JSONDecodeError:
        parsed = eval(data)
    return parsed

def _parse_eval(value=None):
    if not value:
        return value
    if hasattr(value, "stringify"):
        try:
            return value.stringify()
        except TypeError:
            pass
    elif isinstance(value, dict):
        try:
            return json_parser(value, indent=1)
        except BaseException:
            pass
    elif isinstance(value, list):
        newlist = "["
        for index, child in enumerate(value):
            newlist += "\n  " + str(_parse_eval(child))
            if index < len(value) - 1:
                newlist += ","
        newlist += "\n]"
        return newlist
    return str(value)
    
    
@UtubeBot.on_message(
    Filters.private
    & Filters.incoming
    & Filters.command("eval")
    & Filters.user(Config.AUTH_USERS)
)

async def evaluation_cmd_t(client: UtubeBot, message: Message):
    await message.reply_chat_action(ChatAction.TYPING)
    user_id = message.from_user.id
    status_message = await message.reply("__Processing eval pyrogram...__")
    try:
        cmd = message.text.split(" ", maxsplit=1)[1]
    except IndexError:
        return await status_message.edit("__No evaluate message!__")
    exc = None
    with io.StringIO() as redirected_output, io.StringIO() as redirected_error:
        old_stderr, old_stdout = sys.stderr, sys.stdout
        try:
            sys.stdout, sys.stderr = redirected_output, redirected_error
            await aexec(cmd, client, message)
        except Exception:
            exc = traceback.format_exc()
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        stdout = redirected_output.getvalue()
        stderr = redirected_error.getvalue()

    evaluation = exc if exc else (stderr if stderr else (stdout if stdout else "Success"))
    final_output = f"**OUTPUT**:\n<pre language=''>{evaluation.strip()}</pre>"

    if len(final_output) > 4096:
        with open("eval.txt", "w+", encoding="utf8") as out_file:
            out_file.write(final_output)
        await status_message.reply_document(
            document="eval.txt",
            caption=cmd[: 4096 // 4 - 1],
            disable_notification=True,
        )
        os.remove("eval.txt")
        await status_message.delete()
    else:
        await status_message.edit_text(final_output)


async def aexec(code, client, message):
    exec(
        (
            "async def __aexec(client, message):\n"
            + " import os\n"
            + " import wget\n"
            + " event = e = message\n"
            + " r = reply = message.reply_to_message\n"
            + " chat = message.chat.id\n"
            + " c = client\n"
            + " to_photo = message.reply_photo\n"
            + " to_video = message.reply_video\n"
            + " print = p = _stringify\n"
        )
        + "".join(f"\n {l}" for l in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)

async def shell_exec(code, treat=True):
    process = await asyncio.create_subprocess_shell(
        code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    stdout = (await process.communicate())[0]
    if treat:
        stdout = stdout.decode().strip()
    return stdout, process