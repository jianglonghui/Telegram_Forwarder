from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode, ChatType

from forwarder import OWNER_ID, app


@app.on_message(filters.command("id") & (filters.user(OWNER_ID) | filters.channel))
async def get_id(client, message: Message):
    chat = message.chat

    if chat.type == ChatType.PRIVATE:
        return await message.reply(f"Your ID is `{chat.id}`", parse_mode=ParseMode.MARKDOWN)

    result = f"Chat ID: `{chat.id}`"

    # 检查是否是论坛/话题
    is_forum = getattr(chat, 'is_forum', False)
    if is_forum:
        topic_id = None
        if hasattr(message, 'topic') and message.topic:
            topic_id = message.topic.id
        elif hasattr(message, 'reply_to_top_message_id') and message.reply_to_top_message_id:
            topic_id = message.reply_to_top_message_id
        if topic_id:
            result += f"\nForum/Topic ID: `{topic_id}`"

    if message.reply_to_message:
        replied = message.reply_to_message

        # 转发的用户消息
        if replied.forward_from:
            sender = replied.forward_from
            forwarder_user = replied.from_user
            result += f"\nThe original sender ({sender.first_name}), ID is: `{sender.id}`"
            if forwarder_user:
                result += f"\nThe forwarder ({forwarder_user.first_name}) ID: `{forwarder_user.id}`"

        # 转发的频道消息
        if replied.forward_from_chat:
            channel = replied.forward_from_chat
            forwarder_user = replied.from_user
            result += f"\nThe channel {channel.title} ID: `{channel.id}`"
            if forwarder_user:
                result += f"\nThe forwarder ({forwarder_user.first_name}) ID: `{forwarder_user.id}`"

        # 来源设置了隐私保护，无法获取 ID
        if replied.forward_sender_name and not replied.forward_from and not replied.forward_from_chat:
            result += f"\n\n⚠️ 原消息来源 **{replied.forward_sender_name}** 设置了隐私保护，无法获取其 ID"

    return await message.reply(result, parse_mode=ParseMode.MARKDOWN)
