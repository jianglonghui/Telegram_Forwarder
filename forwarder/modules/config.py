import json
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from forwarder import OWNER_ID, app, CONFIG, LOGGER

CONFIG_FILE = "chat_list.json"


def save_config():
    """保存配置到文件"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(CONFIG, f, indent=4, ensure_ascii=False)
    LOGGER.info("Configuration saved to chat_list.json")


def reload_forward_handler():
    """重新加载转发处理器的源聊天列表"""
    from forwarder.utils.chat import reload_config
    reload_config()


@app.on_message(filters.command("add") & filters.user(OWNER_ID))
async def add_forward(client, message: Message):
    """
    添加转发规则
    用法: /add <源ID> <目标ID> [过滤词1,过滤词2] [黑名单词1,黑名单词2]
    示例: /add -1001234567890 -1009876543210
    示例: /add -1001234567890 -1009876543210 BTC,ETH
    示例: /add -1001234567890 -1009876543210 BTC,ETH 广告,推广
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/add <源ID> <目标ID> [过滤词] [黑名单]`\n\n"
            "**示例:**\n"
            "`/add -1001234567890 -1009876543210`\n"
            "`/add -1001234567890 -1009876543210 BTC,ETH`\n"
            "`/add -1001234567890 -1009876543210 BTC,ETH 广告,推广`\n\n"
            "提示: 在群组发送 /id 获取群组ID",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        source = int(args[0])
        destination = int(args[1])
    except ValueError:
        return await message.reply("源ID和目标ID必须是数字")

    # 构建配置
    new_config = {
        "source": source,
        "destination": [destination]
    }

    # 解析过滤词
    if len(args) >= 3 and args[2]:
        new_config["filters"] = [f.strip() for f in args[2].split(",") if f.strip()]

    # 解析黑名单
    if len(args) >= 4 and args[3]:
        new_config["blacklist"] = [b.strip() for b in args[3].split(",") if b.strip()]

    # 添加到配置
    CONFIG.append(new_config)
    save_config()
    reload_forward_handler()

    result = f"**已添加转发规则 #{len(CONFIG)}**\n"
    result += f"源: `{source}`\n"
    result += f"目标: `{destination}`"
    if new_config.get("filters"):
        result += f"\n过滤词: {', '.join(new_config['filters'])}"
    if new_config.get("blacklist"):
        result += f"\n黑名单: {', '.join(new_config['blacklist'])}"

    await message.reply(result, parse_mode=ParseMode.MARKDOWN)


@app.on_message(filters.command("list") & filters.user(OWNER_ID))
async def list_forwards(client, message: Message):
    """列出所有转发规则"""
    if not CONFIG:
        return await message.reply("当前没有转发规则")

    result = "**当前转发规则:**\n\n"
    for i, config in enumerate(CONFIG, 1):
        result += f"**#{i}**\n"
        result += f"  源: `{config['source']}`\n"
        dest_str = ", ".join([f"`{d}`" for d in config['destination']])
        result += f"  目标: {dest_str}\n"
        if config.get("filters"):
            result += f"  过滤词: {', '.join(config['filters'])}\n"
        if config.get("blacklist"):
            result += f"  黑名单: {', '.join(config['blacklist'])}\n"
        result += "\n"

    await message.reply(result, parse_mode=ParseMode.MARKDOWN)


@app.on_message(filters.command("remove") & filters.user(OWNER_ID))
async def remove_forward(client, message: Message):
    """
    删除转发规则
    用法: /remove <规则编号>
    示例: /remove 1
    """
    args = message.text.split()[1:]

    if not args:
        return await message.reply(
            "**用法:** `/remove <规则编号>`\n"
            "使用 /list 查看规则编号",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        index = int(args[0]) - 1
    except ValueError:
        return await message.reply("规则编号必须是数字")

    if index < 0 or index >= len(CONFIG):
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    removed = CONFIG.pop(index)
    save_config()
    reload_forward_handler()

    await message.reply(
        f"**已删除规则 #{index + 1}**\n"
        f"源: `{removed['source']}`",
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command("adddest") & filters.user(OWNER_ID))
async def add_destination(client, message: Message):
    """
    为现有规则添加目标
    用法: /adddest <规则编号> <目标ID>
    示例: /adddest 1 -1009876543210
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/adddest <规则编号> <目标ID>`\n"
            "示例: `/adddest 1 -1009876543210`",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        index = int(args[0]) - 1
        dest = int(args[1])
    except ValueError:
        return await message.reply("规则编号和目标ID必须是数字")

    if index < 0 or index >= len(CONFIG):
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    if dest not in CONFIG[index]["destination"]:
        CONFIG[index]["destination"].append(dest)
        save_config()
        reload_forward_handler()
        await message.reply(f"已为规则 #{index + 1} 添加目标: `{dest}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("该目标已存在")


@app.on_message(filters.command("addfilter") & filters.user(OWNER_ID))
async def add_filter(client, message: Message):
    """
    为现有规则添加过滤词
    用法: /addfilter <规则编号> <过滤词1,过滤词2>
    示例: /addfilter 1 BTC,ETH
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/addfilter <规则编号> <过滤词>`\n"
            "示例: `/addfilter 1 BTC,ETH`",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        index = int(args[0]) - 1
    except ValueError:
        return await message.reply("规则编号必须是数字")

    if index < 0 or index >= len(CONFIG):
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    new_filters = [f.strip() for f in args[1].split(",") if f.strip()]
    if not new_filters:
        return await message.reply("请提供有效的过滤词")

    if "filters" not in CONFIG[index]:
        CONFIG[index]["filters"] = []

    added = []
    for f in new_filters:
        if f not in CONFIG[index]["filters"]:
            CONFIG[index]["filters"].append(f)
            added.append(f)

    if added:
        save_config()
        reload_forward_handler()
        await message.reply(f"已为规则 #{index + 1} 添加过滤词: {', '.join(added)}")
    else:
        await message.reply("所有过滤词已存在")


@app.on_message(filters.command("addblack") & filters.user(OWNER_ID))
async def add_blacklist(client, message: Message):
    """
    为现有规则添加黑名单词
    用法: /addblack <规则编号> <黑名单词1,黑名单词2>
    示例: /addblack 1 广告,推广
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/addblack <规则编号> <黑名单词>`\n"
            "示例: `/addblack 1 广告,推广`",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        index = int(args[0]) - 1
    except ValueError:
        return await message.reply("规则编号必须是数字")

    if index < 0 or index >= len(CONFIG):
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    new_blacklist = [b.strip() for b in args[1].split(",") if b.strip()]
    if not new_blacklist:
        return await message.reply("请提供有效的黑名单词")

    if "blacklist" not in CONFIG[index]:
        CONFIG[index]["blacklist"] = []

    added = []
    for b in new_blacklist:
        if b not in CONFIG[index]["blacklist"]:
            CONFIG[index]["blacklist"].append(b)
            added.append(b)

    if added:
        save_config()
        reload_forward_handler()
        await message.reply(f"已为规则 #{index + 1} 添加黑名单: {', '.join(added)}")
    else:
        await message.reply("所有黑名单词已存在")


@app.on_message(filters.command("clearfilter") & filters.user(OWNER_ID))
async def clear_filter(client, message: Message):
    """
    清除规则的过滤词
    用法: /clearfilter <规则编号>
    """
    args = message.text.split()[1:]

    if not args:
        return await message.reply("**用法:** `/clearfilter <规则编号>`", parse_mode=ParseMode.MARKDOWN)

    try:
        index = int(args[0]) - 1
    except ValueError:
        return await message.reply("规则编号必须是数字")

    if index < 0 or index >= len(CONFIG):
        return await message.reply(f"规则编号无效")

    if "filters" in CONFIG[index]:
        del CONFIG[index]["filters"]
        save_config()
        reload_forward_handler()
        await message.reply(f"已清除规则 #{index + 1} 的所有过滤词")
    else:
        await message.reply("该规则没有过滤词")


@app.on_message(filters.command("clearblack") & filters.user(OWNER_ID))
async def clear_blacklist(client, message: Message):
    """
    清除规则的黑名单
    用法: /clearblack <规则编号>
    """
    args = message.text.split()[1:]

    if not args:
        return await message.reply("**用法:** `/clearblack <规则编号>`", parse_mode=ParseMode.MARKDOWN)

    try:
        index = int(args[0]) - 1
    except ValueError:
        return await message.reply("规则编号必须是数字")

    if index < 0 or index >= len(CONFIG):
        return await message.reply(f"规则编号无效")

    if "blacklist" in CONFIG[index]:
        del CONFIG[index]["blacklist"]
        save_config()
        reload_forward_handler()
        await message.reply(f"已清除规则 #{index + 1} 的所有黑名单词")
    else:
        await message.reply("该规则没有黑名单")
