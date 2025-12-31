import asyncio
from datetime import datetime

from forwarder import app, HEARTBEAT_CHAT, HEARTBEAT_INTERVAL, LOGGER


def get_chat_id():
    """获取心跳发送目标"""
    if not HEARTBEAT_CHAT:
        return None
    if HEARTBEAT_CHAT.lower() == "me":
        return "me"
    return int(HEARTBEAT_CHAT)


async def heartbeat_loop():
    """心跳循环"""
    chat_id = get_chat_id()
    if not chat_id:
        return

    # 发送启动消息
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await app.send_message(chat_id, f"🚀 Forwarder 已启动 | {now}")
        LOGGER.info(f"Startup message sent to {chat_id}")
    except Exception as e:
        LOGGER.error(f"Failed to send startup message: {e}")

    # 心跳循环
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL * 60)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"💓 心跳 | {now}"

            await app.send_message(chat_id, message)
            LOGGER.info(f"Heartbeat sent to {chat_id}")

        except Exception as e:
            LOGGER.error(f"Failed to send heartbeat: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟再试


# 在模块加载时设置启动钩子
if HEARTBEAT_CHAT:
    LOGGER.info(f"Heartbeat configured: every {HEARTBEAT_INTERVAL} minutes to {HEARTBEAT_CHAT}")

    # 使用 Pyrogram 的 start handler
    original_start = app.start

    async def start_with_heartbeat():
        await original_start()
        asyncio.create_task(heartbeat_loop())

    app.start = start_with_heartbeat
