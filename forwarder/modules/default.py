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
**基础命令:**
/start - 启动机器人
/help - 帮助信息
/id - 获取聊天ID

**配置管理:**
/list - 查看所有转发规则
/add <源ID> <目标ID> [过滤词] [黑名单] - 添加规则
/remove <编号> - 删除规则
/adddest <编号> <目标ID> - 添加目标
/addfilter <编号> <词1,词2> - 添加过滤词
/addblack <编号> <词1,词2> - 添加黑名单
/clearfilter <编号> - 清除过滤词
/clearblack <编号> - 清除黑名单
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
