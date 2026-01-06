import json
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from forwarder import OWNER_ID, app, CONFIG, LOGGER, RUNTIME_CONFIG, RUNTIME_CONFIG_FILE

CONFIG_FILE = "chat_list.json"


def save_config():
    """保存转发配置到文件"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(CONFIG, f, indent=4, ensure_ascii=False)
    LOGGER.info("Configuration saved to chat_list.json")


def save_runtime_config():
    """保存运行时配置到文件"""
    with open(RUNTIME_CONFIG_FILE, "w") as f:
        json.dump(RUNTIME_CONFIG, f, indent=4, ensure_ascii=False)
    LOGGER.info(f"Runtime config saved to {RUNTIME_CONFIG_FILE}")


def reload_forward_handler():
    """重新加载转发处理器的源聊天列表"""
    from forwarder.utils.chat import reload_config
    reload_config()


def parse_indices(arg: str, max_len: int) -> list:
    """解析逗号分隔的编号，返回有效的索引列表（从0开始）"""
    indices = []
    for part in arg.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part) - 1
            if 0 <= idx < max_len and idx not in indices:
                indices.append(idx)
        except ValueError:
            continue
    return indices


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
    用法: /remove <规则编号> 或 /remove <编号1,编号2,编号3>
    示例: /remove 1 或 /remove 1,2,3
    """
    args = message.text.split()[1:]

    if not args:
        return await message.reply(
            "**用法:** `/remove <规则编号>`\n"
            "支持多个编号: `/remove 1,2,3`\n"
            "使用 /list 查看规则编号",
            parse_mode=ParseMode.MARKDOWN
        )

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    # 从大到小排序，避免删除时索引变化
    indices.sort(reverse=True)
    removed_list = []
    for idx in indices:
        removed = CONFIG.pop(idx)
        removed_list.append(f"#{idx + 1} (源: `{removed['source']}`)")

    save_config()
    reload_forward_handler()

    await message.reply(
        f"**已删除 {len(removed_list)} 条规则:**\n" + "\n".join(removed_list),
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command("adddest") & filters.user(OWNER_ID))
async def add_destination(client, message: Message):
    """
    为现有规则添加目标
    用法: /adddest <规则编号> <目标ID>
    示例: /adddest 1 -1009876543210 或 /adddest 1,2,3 -1009876543210
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/adddest <规则编号> <目标ID>`\n"
            "支持多个编号: `/adddest 1,2,3 -1009876543210`",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        dest = int(args[1])
    except ValueError:
        return await message.reply("目标ID必须是数字")

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    results = []
    for idx in indices:
        if dest not in CONFIG[idx]["destination"]:
            CONFIG[idx]["destination"].append(dest)
            results.append(f"#{idx + 1}")

    if results:
        save_config()
        reload_forward_handler()
        await message.reply(f"已为规则 {', '.join(results)} 添加目标: `{dest}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("该目标在所有规则中已存在")


@app.on_message(filters.command("removedest") & filters.user(OWNER_ID))
async def remove_destination(client, message: Message):
    """
    从现有规则删除目标
    用法: /removedest <规则编号> <目标ID>
    示例: /removedest 1 -1009876543210 或 /removedest 1,2,3 -1009876543210
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/removedest <规则编号> <目标ID>`\n"
            "支持多个编号: `/removedest 1,2,3 -1009876543210`",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        dest = int(args[1])
    except ValueError:
        return await message.reply("目标ID必须是数字")

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    results = []
    for idx in indices:
        if dest in CONFIG[idx]["destination"]:
            CONFIG[idx]["destination"].remove(dest)
            results.append(f"#{idx + 1}")

    if results:
        save_config()
        reload_forward_handler()
        await message.reply(f"已从规则 {', '.join(results)} 删除目标: `{dest}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("该目标不存在")


@app.on_message(filters.command("addfilter") & filters.user(OWNER_ID))
async def add_filter(client, message: Message):
    """
    为现有规则添加过滤词
    用法: /addfilter <规则编号> <过滤词1,过滤词2>
    示例: /addfilter 1 BTC,ETH 或 /addfilter 1,2,3 BTC,ETH
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/addfilter <规则编号> <过滤词>`\n"
            "支持多个编号: `/addfilter 1,2,3 BTC,ETH`",
            parse_mode=ParseMode.MARKDOWN
        )

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    new_filters = [f.strip() for f in args[1].split(",") if f.strip()]
    if not new_filters:
        return await message.reply("请提供有效的过滤词")

    results = []
    for idx in indices:
        if "filters" not in CONFIG[idx]:
            CONFIG[idx]["filters"] = []
        added = []
        for f in new_filters:
            if f not in CONFIG[idx]["filters"]:
                CONFIG[idx]["filters"].append(f)
                added.append(f)
        if added:
            results.append(f"规则 #{idx + 1}: {', '.join(added)}")

    if results:
        save_config()
        reload_forward_handler()
        await message.reply("**已添加过滤词:**\n" + "\n".join(results), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("所有过滤词已存在")


@app.on_message(filters.command("addblack") & filters.user(OWNER_ID))
async def add_blacklist(client, message: Message):
    """
    为现有规则添加黑名单词
    用法: /addblack <规则编号> <黑名单词1,黑名单词2>
    示例: /addblack 1 广告,推广 或 /addblack 1,2,3 广告,推广
    """
    args = message.text.split()[1:]

    if len(args) < 2:
        return await message.reply(
            "**用法:** `/addblack <规则编号> <黑名单词>`\n"
            "支持多个编号: `/addblack 1,2,3 广告,推广`",
            parse_mode=ParseMode.MARKDOWN
        )

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    new_blacklist = [b.strip() for b in args[1].split(",") if b.strip()]
    if not new_blacklist:
        return await message.reply("请提供有效的黑名单词")

    results = []
    for idx in indices:
        if "blacklist" not in CONFIG[idx]:
            CONFIG[idx]["blacklist"] = []
        added = []
        for b in new_blacklist:
            if b not in CONFIG[idx]["blacklist"]:
                CONFIG[idx]["blacklist"].append(b)
                added.append(b)
        if added:
            results.append(f"规则 #{idx + 1}: {', '.join(added)}")

    if results:
        save_config()
        reload_forward_handler()
        await message.reply("**已添加黑名单:**\n" + "\n".join(results), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("所有黑名单词已存在")


@app.on_message(filters.command("clearfilter") & filters.user(OWNER_ID))
async def clear_filter(client, message: Message):
    """
    清除规则的过滤词
    用法: /clearfilter <规则编号> 或 /clearfilter <编号1,编号2>
    """
    args = message.text.split()[1:]

    if not args:
        return await message.reply(
            "**用法:** `/clearfilter <规则编号>`\n"
            "支持多个编号: `/clearfilter 1,2,3`",
            parse_mode=ParseMode.MARKDOWN
        )

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    cleared = []
    for idx in indices:
        if "filters" in CONFIG[idx]:
            del CONFIG[idx]["filters"]
            cleared.append(f"#{idx + 1}")

    if cleared:
        save_config()
        reload_forward_handler()
        await message.reply(f"已清除规则 {', '.join(cleared)} 的所有过滤词")
    else:
        await message.reply("这些规则没有过滤词")


@app.on_message(filters.command("clearblack") & filters.user(OWNER_ID))
async def clear_blacklist(client, message: Message):
    """
    清除规则的黑名单
    用法: /clearblack <规则编号> 或 /clearblack <编号1,编号2>
    """
    args = message.text.split()[1:]

    if not args:
        return await message.reply(
            "**用法:** `/clearblack <规则编号>`\n"
            "支持多个编号: `/clearblack 1,2,3`",
            parse_mode=ParseMode.MARKDOWN
        )

    indices = parse_indices(args[0], len(CONFIG))
    if not indices:
        return await message.reply(f"规则编号无效，当前共有 {len(CONFIG)} 条规则")

    cleared = []
    for idx in indices:
        if "blacklist" in CONFIG[idx]:
            del CONFIG[idx]["blacklist"]
            cleared.append(f"#{idx + 1}")

    if cleared:
        save_config()
        reload_forward_handler()
        await message.reply(f"已清除规则 {', '.join(cleared)} 的所有黑名单词")
    else:
        await message.reply("这些规则没有黑名单")


@app.on_message(filters.command("setnews") & filters.user(OWNER_ID))
async def set_news_token_chat(client, message: Message):
    """
    设置代币撮合推送的目标群组
    用法: /setnews <群组ID> 或在目标群组发送 /setnews
    """
    args = message.text.split()[1:]

    if args:
        # 使用参数指定的群组ID
        try:
            chat_id = int(args[0])
        except ValueError:
            return await message.reply("群组ID必须是数字")
    else:
        # 使用当前群组
        chat_id = message.chat.id

    RUNTIME_CONFIG['news_token_chat'] = str(chat_id)
    save_runtime_config()

    await message.reply(
        f"**代币撮合推送已设置**\n"
        f"目标群组: `{chat_id}`",
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command("getnews") & filters.user(OWNER_ID))
async def get_news_token_chat(client, message: Message):
    """查看当前代币撮合推送配置"""
    chat_id = RUNTIME_CONFIG.get('news_token_chat', '')
    if chat_id:
        await message.reply(
            f"**代币撮合推送配置**\n"
            f"目标群组: `{chat_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply(
            "代币撮合推送未配置\n"
            "使用 `/setnews <群组ID>` 或在目标群组发送 `/setnews` 设置",
            parse_mode=ParseMode.MARKDOWN
        )


@app.on_message(filters.command("setalpha") & filters.user(OWNER_ID))
async def set_alpha_chat(client, message: Message):
    """
    设置 Alpha Call 翻倍推送的目标群组
    用法: /setalpha <群组ID> 或在目标群组发送 /setalpha
    """
    args = message.text.split()[1:]

    if args:
        # 使用参数指定的群组ID
        try:
            chat_id = int(args[0])
        except ValueError:
            return await message.reply("群组ID必须是数字")
    else:
        # 使用当前群组
        chat_id = message.chat.id

    RUNTIME_CONFIG['alpha_chat'] = str(chat_id)
    save_runtime_config()

    await message.reply(
        f"**Alpha Call 翻倍推送已设置**\n"
        f"目标群组: `{chat_id}`",
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command("getalpha") & filters.user(OWNER_ID))
async def get_alpha_chat(client, message: Message):
    """查看当前 Alpha Call 翻倍推送配置"""
    chat_id = RUNTIME_CONFIG.get('alpha_chat', '')
    if chat_id:
        await message.reply(
            f"**Alpha Call 翻倍推送配置**\n"
            f"目标群组: `{chat_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply(
            "Alpha Call 翻倍推送未配置\n"
            "使用 `/setalpha <群组ID>` 或在目标群组发送 `/setalpha` 设置",
            parse_mode=ParseMode.MARKDOWN
        )
