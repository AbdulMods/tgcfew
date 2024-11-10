"""Utility functions to smoothen your life."""

import logging
import os
import platform
import re
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from telethon.client import TelegramClient
from telethon.hints import EntityLike
from telethon.tl.custom.message import Message
from telethon.tl.types import ChatWriteForbiddenError, UserBannedInChannelError

from tgcf import __version__
from tgcf.config import CONFIG
from tgcf.plugin_models import STYLE_CODES

if TYPE_CHECKING:
    from tgcf.plugins import TgcfMessage


def platform_info():
    nl = "\n"
    return f"""Running tgcf {__version__}\
    \nPython {sys.version.replace(nl,"")}\
    \nOS {os.name}\
    \nPlatform {platform.system()} {platform.release()}\
    \n{platform.architecture()} {platform.processor()}"""


async def send_message(peer_id: int, tm: "TgcfMessage") -> Message:
    """Send message with restricted chat handling."""
    try:
        # First try normal forwarding
        if tm.file_type == "nofile":
            try:
                return await tm.client.send_message(
                    peer_id,
                    tm.text,
                    formatting_entities=tm.text_entities,
                    reply_to=tm.reply_to,
                )
            except Exception:
                # If forwarding fails, try sending as new message
                return await tm.client.send_message(
                    peer_id,
                    tm.text,
                    formatting_entities=tm.text_entities,
                    reply_to=tm.reply_to,
                    force_document=True  # Force send as new message
                )
        else:
            try:
                # Try sending file normally first
                return await tm.client.send_file(
                    peer_id,
                    tm.new_file,
                    caption=tm.text,
                    formatting_entities=tm.text_entities,
                    reply_to=tm.reply_to,
                )
            except Exception:
                # If fails, download and re-upload as new file
                file_data = await tm.client.download_media(tm.message, bytes)
                return await tm.client.send_file(
                    peer_id,
                    file_data,
                    caption=tm.text,
                    formatting_entities=tm.text_entities, 
                    reply_to=tm.reply_to,
                    force_document=True
                )
            
    except ChatWriteForbiddenError:
        logging.error(f"No permission to write in chat {peer_id}")
        raise
        
    except UserBannedInChannelError:
        logging.error(f"Banned from writing in chat {peer_id}")
        raise
        
    except Exception as e:
        logging.error(f"Failed to send message to {peer_id}: {str(e)}")
        raise


def cleanup(*files: str) -> None:
    """Delete the file names passed as args."""
    for file in files:
        try:
            os.remove(file)
        except FileNotFoundError:
            logging.info(f"File {file} does not exist, so cant delete it.")


def stamp(file: str, user: str) -> str:
    """Stamp the filename with the datetime, and user info."""
    now = str(datetime.now())
    outf = safe_name(f"{user} {now} {file}")
    try:
        os.rename(file, outf)
        return outf
    except Exception as err:
        logging.warning(f"Stamping file name failed for {file} to {outf}. \n {err}")


def safe_name(string: str) -> str:
    """Return safe file name.

    Certain characters in the file name can cause potential problems in rare scenarios.
    """
    return re.sub(pattern=r"[-!@#$%^&*()\s]", repl="_", string=string)


def match(pattern: str, string: str, regex: bool) -> bool:
    if regex:
        return bool(re.findall(pattern, string))
    return pattern in string


def replace(pattern: str, new: str, string: str, regex: bool) -> str:
    def fmt_repl(matched):
        style = new
        s = STYLE_CODES.get(style)
        return f"{s}{matched.group(0)}{s}"

    if regex:
        if new in STYLE_CODES:
            compliled_pattern = re.compile(pattern)
            return compliled_pattern.sub(repl=fmt_repl, string=string)
        return re.sub(pattern, new, string)
    else:
        return string.replace(pattern, new)


def clean_session_files():
    for item in os.listdir():
        if item.endswith(".session") or item.endswith(".session-journal"):
            os.remove(item)
