from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from forwarder import app, OWNER_ID

PM_START_TEXT = """
Hey {}, I'm {}!
I'm a userbot used to forward messages from one chat to another.

To obtain a list of commands, use /help.
"""

PM_HELP_TEXT = """
Here is a list of usable commands:
 - /start : Starts the bot.
 - /help : Sends you this help message.

Just send /id in private chat/group/channel and I will reply its id.
"""


@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message: Message):
    chat = message.chat
    user = message.from_user

    if chat.type.value == "private":
        me = await client.get_me()
        await message.reply(
            PM_START_TEXT.format(user.first_name, me.first_name),
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply("I'm up and running!")


@app.on_message(filters.command("help") & filters.user(OWNER_ID))
async def help_command(client, message: Message):
    chat = message.chat

    if chat.type.value != "private":
        await message.reply("Contact me via PM to get a list of usable commands.")
    else:
        await message.reply(PM_HELP_TEXT)
