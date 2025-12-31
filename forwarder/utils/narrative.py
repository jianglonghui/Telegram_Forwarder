import asyncio
import httpx
from typing import List, Optional
from pyrogram.types import Message

from forwarder import DEEPSEEK_API_KEY, NARRATIVE_CONTEXT, LOGGER

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

NARRATIVE_PROMPT = """你是一个专业的群聊分析师。请根据以下聊天记录，以【{keyword}】关键词提及者为中心，生成一段简洁的叙事总结。

要求：
1. 重点关注提到关键词的用户说了什么
2. 分析其他人对此的反应和回复
3. 总结讨论的核心观点和情绪
4. 使用简洁的中文，控制在200字以内
5. 格式：先说谁提到了什么，然后说群友的反应

聊天记录：
{context}

请生成叙事总结："""


async def get_context_messages(client, chat_id: int, message_id: int, count: int = NARRATIVE_CONTEXT) -> List[dict]:
    """获取消息的上下文（前后各 count 条消息）"""
    messages = []

    try:
        # 获取当前消息之前的消息
        async for msg in client.get_chat_history(chat_id, limit=count + 1, offset_id=message_id + 1):
            if msg.text or msg.caption:
                user_name = "未知用户"
                if msg.from_user:
                    user_name = msg.from_user.first_name or msg.from_user.username or str(msg.from_user.id)
                messages.append({
                    "id": msg.id,
                    "user": user_name,
                    "text": msg.text or msg.caption or "",
                    "is_target": msg.id == message_id
                })

        messages.reverse()  # 按时间顺序排列

        # 等待15秒，让群友有时间回复
        await asyncio.sleep(15)

        # 获取当前消息之后的消息（群友的反应）
        after_messages = []
        async for msg in client.get_chat_history(chat_id, limit=count, offset_id=message_id - count):
            if msg.id > message_id and (msg.text or msg.caption):
                user_name = "未知用户"
                if msg.from_user:
                    user_name = msg.from_user.first_name or msg.from_user.username or str(msg.from_user.id)
                after_messages.append({
                    "id": msg.id,
                    "user": user_name,
                    "text": msg.text or msg.caption or "",
                    "is_target": False
                })

        after_messages.reverse()
        messages.extend(after_messages)

    except Exception as e:
        LOGGER.error(f"Failed to get context messages: {e}")

    return messages


def format_context(messages: List[dict]) -> str:
    """格式化上下文消息为文本"""
    lines = []
    for msg in messages:
        marker = ">>> " if msg.get("is_target") else ""
        lines.append(f"{marker}[{msg['user']}]: {msg['text']}")
    return "\n".join(lines)


async def call_deepseek_api(prompt: str) -> Optional[str]:
    """调用 DeepSeek API 生成总结"""
    if not DEEPSEEK_API_KEY:
        LOGGER.error("DeepSeek API key not configured")
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(DEEPSEEK_API_URL, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        LOGGER.error(f"DeepSeek API call failed: {e}")
        return None


async def generate_narrative(client, chat_id: int, message: Message, keyword: str) -> Optional[str]:
    """生成叙事总结"""
    # 获取上下文消息
    context_messages = await get_context_messages(client, chat_id, message.id)

    if not context_messages:
        LOGGER.warning("No context messages found")
        return None

    # 格式化上下文
    context_text = format_context(context_messages)

    # 构建 prompt
    prompt = NARRATIVE_PROMPT.format(keyword=keyword, context=context_text)

    # 调用 API
    summary = await call_deepseek_api(prompt)

    if summary:
        # 格式化输出
        user_name = "未知用户"
        if message.from_user:
            user_name = message.from_user.first_name or message.from_user.username or str(message.from_user.id)

        result = f"📝 **AI 叙事总结**\n"
        result += f"🔑 关键词: `{keyword}`\n"
        result += f"👤 提及者: {user_name}\n"
        result += f"━━━━━━━━━━━━━━━\n"
        result += summary

        return result

    return None
