"""
API 接口模块 - 接收代币撮合推送
"""
import asyncio
import threading
from flask import Flask, request, jsonify

from forwarder import app as tg_app, LOGGER, RUNTIME_CONFIG

flask_app = Flask(__name__)


@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@flask_app.route('/news_token', methods=['POST'])
def news_token():
    """接收代币撮合结果并推送到 Telegram"""
    chat_id = RUNTIME_CONFIG.get('news_token_chat', '')
    if not chat_id:
        return jsonify({'success': False, 'error': 'NEWS_TOKEN_CHAT 未配置，使用 /setnews 设置'}), 400

    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '无数据'}), 400

    tweet = data.get('tweet', '')
    author = data.get('author', '')
    tokens = data.get('tokens', [])
    keywords = data.get('keywords', [])

    if not tokens:
        return jsonify({'success': False, 'error': '无匹配代币'}), 400

    # 构建消息
    keywords_str = ', '.join(keywords) if keywords else ''

    msg = f"🔔 **代币撮合**\n\n"
    msg += f"👤 @{author}\n"
    msg += f"📝 {tweet[:200]}{'...' if len(tweet) > 200 else ''}\n\n"
    if keywords_str:
        msg += f"🔑 关键词: {keywords_str}\n\n"

    # 显示代币和 CA
    msg += f"🪙 **匹配代币:**\n"
    for t in tokens[:5]:
        if isinstance(t, dict):
            symbol = t.get('symbol', '')
            ca = t.get('ca', '')
            msg += f"• **{symbol}**\n`{ca}`\n"
        else:
            msg += f"• {t}\n"

    # 异步发送到 Telegram
    try:
        target_chat = int(chat_id)
        asyncio.run_coroutine_threadsafe(
            send_telegram_message(target_chat, msg),
            tg_app.loop
        )
        tokens_str = ', '.join([t.get('symbol', str(t)) if isinstance(t, dict) else str(t) for t in tokens[:5]])
        LOGGER.info(f"[API] 推送代币撮合: {author} -> {tokens_str}")
        return jsonify({'success': True})
    except Exception as e:
        LOGGER.error(f"[API] 推送失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


async def send_telegram_message(chat_id: int, text: str):
    """发送消息到 Telegram"""
    from pyrogram.enums import ParseMode
    try:
        await tg_app.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        LOGGER.error(f"[Telegram] 发送失败: {e}")


def run_flask(port=5060):
    """运行 Flask 服务"""
    LOGGER.info(f"[API] 启动 Flask 服务: http://127.0.0.1:{port}")
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def start_api_server(port=5060):
    """在后台线程启动 API 服务（始终启动，可通过命令配置群组）"""
    thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    thread.start()
    chat_id = RUNTIME_CONFIG.get('news_token_chat', '')
    if chat_id:
        LOGGER.info(f"[API] 代币撮合推送已启用，目标群组: {chat_id}")
    else:
        LOGGER.info("[API] API 服务已启动，使用 /setnews <群组ID> 配置推送目标")
