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
📖 **Telegram Forwarder 帮助**

**基础命令:**
• `/start` - 启动机器人
• `/help` - 显示此帮助信息
• `/id` - 获取当前聊天/用户ID

**配置管理:**
• `/list` - 查看所有转发规则
• `/add <源> <目标> [过滤词] [黑名单]` - 添加规则
• `/remove <编号>` - 删除规则 (支持多编号: 1,2,3)
• `/adddest <编号> <目标ID>` - 添加目标 (支持多编号)
• `/removedest <编号> <目标ID>` - 删除目标 (支持多编号)
• `/addfilter <编号> <词>` - 添加过滤词 (支持多编号)
• `/addblack <编号> <词>` - 添加黑名单词 (支持多编号)
• `/clearfilter <编号>` - 清除过滤词 (支持多编号)
• `/clearblack <编号>` - 清除黑名单 (支持多编号)

**使用示例:**
```
/id
/add -1001234567890 -1009876543210
/add -1001234567890 -1009876543210 BTC,ETH
/addfilter 1,2,3 SOL,DOGE
/remove 1,2
```

**说明:**
• 过滤词(白名单): 只转发包含这些词的消息
• 黑名单: 不转发包含这些词的消息
• 多个词/编号用逗号分隔
• 特殊过滤词: `0x` 匹配EVM合约, `ca` 匹配Solana合约
• 多个词用逗号分隔
• 使用 /id 在群组中获取群组ID

**AI 叙事功能:**
启用后，匹配关键词时会自动生成上下文总结
配置 DEEPSEEK_API_KEY 和 ENABLE_NARRATIVE=True
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
    await message.reply(PM_HELP_TEXT)
