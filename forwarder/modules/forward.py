import asyncio
from typing import Union

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from forwarder import app, REMOVE_TAG, LOGGER
from forwarder.utils import get_destination, get_config, predicate_text


async def send_message(
    message: Message, chat_id: int, thread_id: int = None
) -> Union[Message, None]:
    if REMOVE_TAG:
        return await message.copy(chat_id, reply_to_message_id=thread_id)
    return await message.forward(chat_id)


# 获取所有需要监听的源聊天 ID
source_chats = [config.source.get_id() for config in get_config()]


@app.on_message(filters.chat(source_chats) & ~filters.service)
async def forwarder(client, message: Message):
    if message is None or message.chat is None:
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

    for config in dest:
        # 检查白名单过滤器
        if config.filters:
            if not predicate_text(config.filters, message.text or message.caption or ""):
                continue
        # 检查黑名单
        if config.blacklist:
            if predicate_text(config.blacklist, message.text or message.caption or ""):
                continue

        for chat in config.destination:
            LOGGER.debug(f"Forwarding message from {source.id} to {chat}")
            try:
                await send_message(message, chat.get_id(), chat.get_topic())
            except FloodWait as err:
                LOGGER.warning(f"Rate limited, retrying in {err.value} seconds")
                await asyncio.sleep(err.value + 0.2)
                await send_message(message, chat.get_id(), chat.get_topic())
            except Exception as err:
                LOGGER.error(f"Failed to forward message from {source.id} to {chat} due to {err}")
