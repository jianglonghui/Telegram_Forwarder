import asyncio
import aiohttp
from typing import Union

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.enums import ParseMode

from forwarder import app, REMOVE_TAG, LOGGER, ENABLE_NARRATIVE, DEEPSEEK_API_KEY, GEMINI_API_KEY, ALPHA_CALL_URL, ENABLE_ALPHA_CALL
from forwarder.utils import get_destination, get_config, predicate_text
from forwarder.utils.message import find_matched_keyword, extract_contracts


async def send_message(
    message: Message, chat_id: int, thread_id: int = None
) -> Union[Message, None]:
    if REMOVE_TAG:
        return await message.copy(chat_id, reply_to_message_id=thread_id)
    return await message.forward(chat_id)


async def send_alpha_call(contract: dict, group_id: int, group_name: str):
    """发送合约信息到 Alpha Call 服务"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'contract_address': contract['address'],
                'chain': contract['chain'],
                'group_id': str(group_id),
                'group_name': group_name or str(group_id)
            }
            async with session.post(
                f"{ALPHA_CALL_URL}/call",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    LOGGER.info(f"[Alpha Call] {contract['address'][:10]}... from {group_name} (total: {data.get('total_calls', '?')})")
                else:
                    LOGGER.warning(f"[Alpha Call] HTTP {resp.status}")
    except Exception as e:
        LOGGER.debug(f"[Alpha Call] Failed: {e}")


# 动态过滤器：每次消息到来时检查当前配置的源群列表
def dynamic_source_filter():
    async def func(flt, client, message: Message):
        if message.chat is None:
            return False
        source_chats = [config.source.get_id() for config in get_config()]
        return message.chat.id in source_chats
    return filters.create(func)


@app.on_message(dynamic_source_filter() & ~filters.service & ~filters.bot)
async def forwarder(client, message: Message):
    if message is None or message.chat is None:
        return

    # 再次检查：排除机器人发送的消息
    if message.from_user and message.from_user.is_bot:
        return

    source = message.chat

    # 获取 topic_id (如果是论坛)
    topic_id = None
    is_forum = getattr(source, 'is_forum', False)
    if hasattr(message, 'topic') and message.topic:
        topic_id = message.topic.id
    elif hasattr(message, 'reply_to_top_message_id') and message.reply_to_top_message_id:
        topic_id = message.reply_to_top_message_id
    elif hasattr(message, 'reply_to_message_id') and message.reply_to_message_id and is_forum:
        topic_id = message.reply_to_message_id

    dest = get_destination(source.id, topic_id)
    message_text = message.text or message.caption or ""

    # Alpha Call: 提取合约地址并发送到服务
    if ENABLE_ALPHA_CALL and message_text:
        contracts = extract_contracts(message_text)
        if contracts:
            group_name = getattr(source, 'title', '') or getattr(source, 'username', '') or str(source.id)
            for contract in contracts:
                asyncio.create_task(send_alpha_call(contract, source.id, group_name))

    for config in dest:
        matched_keyword = None

        # 检查白名单过滤器
        if config.filters:
            matched_keyword = find_matched_keyword(config.filters, message_text)
            if not matched_keyword:
                continue

        # 检查黑名单
        if config.blacklist:
            if predicate_text(config.blacklist, message_text):
                continue

        for chat in config.destination:
            LOGGER.debug(f"Forwarding message from {source.id} to {chat}")
            try:
                # 转发原消息
                await send_message(message, chat.get_id(), chat.get_topic())

                # 如果启用了叙事功能且有匹配的关键词（任一 API key 可用即可）
                if ENABLE_NARRATIVE and (DEEPSEEK_API_KEY or GEMINI_API_KEY) and matched_keyword:
                    asyncio.create_task(
                        send_narrative(client, source.id, message, chat.get_id(), chat.get_topic(), matched_keyword)
                    )

            except FloodWait as err:
                LOGGER.warning(f"Rate limited, retrying in {err.value} seconds")
                await asyncio.sleep(err.value + 0.2)
                await send_message(message, chat.get_id(), chat.get_topic())
            except Exception as err:
                LOGGER.error(f"Failed to forward message from {source.id} to {chat} due to {err}")


async def send_narrative(client, source_chat_id: int, message: Message, dest_chat_id: int, thread_id: int, keyword: str):
    """异步生成并发送叙事总结（支持多个 AI）"""
    try:
        from forwarder.utils.narrative import generate_narrative

        LOGGER.info(f"Generating narrative for keyword: {keyword}")
        narratives = await generate_narrative(client, source_chat_id, message, keyword)

        # 发送所有 AI 生成的结果
        for narrative in narratives:
            try:
                await client.send_message(
                    dest_chat_id,
                    narrative,
                    reply_to_message_id=thread_id,
                    parse_mode=ParseMode.MARKDOWN
                )
                LOGGER.info(f"Narrative sent to {dest_chat_id}")
            except Exception as e:
                LOGGER.error(f"Failed to send narrative message: {e}")

    except Exception as e:
        LOGGER.error(f"Failed to generate narrative: {e}")
