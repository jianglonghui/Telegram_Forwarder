"""
API 接口模块 - 接收代币撮合推送
"""
import asyncio
import threading
import time as time_module
from flask import Flask, request, jsonify
from pyrogram import filters

from forwarder import app as tg_app, LOGGER, RUNTIME_CONFIG

flask_app = Flask(__name__)

# 全局等待队列：{chat_id: (Future, sent_time)}
_pending_replies = {}


@tg_app.on_message(filters.bot & filters.private)
async def _on_bot_reply(client, message):
    """监听 bot 回复"""
    chat_id = message.chat.id
    if chat_id in _pending_replies:
        future, sent_time = _pending_replies.pop(chat_id)
        if not future.done():
            future.set_result({
                'reply': message.text or '',
                'reply_latency_ms': round((time_module.time() - sent_time) * 1000)
            })


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
    author_name = data.get('authorName', '')
    tweet_type = data.get('type', '')
    tokens = data.get('tokens', [])
    keywords = data.get('keywords', [])
    # 引用/转推信息
    ref_author = data.get('refAuthor', '')
    ref_author_name = data.get('refAuthorName', '')
    ref_content = data.get('refContent', '')

    if not tokens:
        return jsonify({'success': False, 'error': '无匹配代币'}), 400

    # 构建消息
    keywords_str = ', '.join(keywords) if keywords else ''

    msg = f"🔔 **代币撮合**\n\n"
    # 作者信息
    if author_name:
        msg += f"👤 **{author_name}** (@{author})\n"
    else:
        msg += f"👤 @{author}\n"

    # 推文类型
    if tweet_type:
        type_labels = {
            'retweet': '🔄 转推',
            'quote': '💬 引用',
            'reply': '↩️ 回复'
        }
        msg += f"{type_labels.get(tweet_type, tweet_type)}\n"

    # 推文内容
    msg += f"📝 {tweet[:500]}{'...' if len(tweet) > 500 else ''}\n\n"

    # 引用/转推原文
    if ref_content:
        if ref_author_name:
            msg += f"📎 原推 **{ref_author_name}** (@{ref_author}):\n"
        elif ref_author:
            msg += f"📎 原推 @{ref_author}:\n"
        msg += f"{ref_content[:300]}{'...' if len(ref_content) > 300 else ''}\n\n"

    if keywords_str:
        msg += f"🔑 关键词: {keywords_str}\n\n"

    # 显示代币和 CA
    msg += f"🪙 **匹配代币:**\n"
    for t in tokens[:5]:
        if isinstance(t, dict):
            symbol = t.get('symbol', '')
            ca = t.get('ca', '')
            source = t.get('source', '')  # new/old
            method = t.get('method', '')  # ai/hardcoded
            # 来源标签
            source_label = '🆕新币' if source == 'new' else '📦老币' if source == 'old' else ''
            # 匹配方式标签
            method_label = '🤖AI' if method == 'ai' else '⚙️硬编码' if method == 'hardcoded' else ''
            # 组合标签
            tags = ' '.join(filter(None, [source_label, method_label]))
            if tags:
                msg += f"• **{symbol}** ({tags})\n`{ca}`\n"
            else:
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


@flask_app.route('/trade', methods=['POST'])
def trade():
    """接收交易指令并发送给交易机器人"""
    chat_id = RUNTIME_CONFIG.get('trade_bot_chat', '')
    if not chat_id:
        return jsonify({'success': False, 'error': 'TRADE_BOT_CHAT 未配置，使用 /settrade 设置'}), 400

    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '无数据'}), 400

    action = data.get('action', '').lower()  # buy/sell
    address = data.get('address', '')
    amount = data.get('amount', 0)

    if action not in ['buy', 'sell']:
        return jsonify({'success': False, 'error': 'action 必须是 buy 或 sell'}), 400

    if not address:
        return jsonify({'success': False, 'error': '缺少合约地址'}), 400

    if not amount or amount <= 0:
        return jsonify({'success': False, 'error': '金额必须大于0'}), 400

    # 构建交易指令
    cmd = f"/{action} {address} {amount}"
    wait_reply = data.get('wait_reply', False)  # 是否等待机器人回复

    try:
        target_chat = int(chat_id)

        if wait_reply:
            # 等待机器人回复
            future = asyncio.run_coroutine_threadsafe(
                send_and_wait_reply(target_chat, cmd, timeout=10.0),
                tg_app.loop
            )
            result = future.result(timeout=15)
            LOGGER.info(f"[API] 交易指令: {cmd} (发送:{result.get('send_latency_ms')}ms, 回复:{result.get('reply_latency_ms')}ms)")
            return jsonify({
                'success': True,
                'command': cmd,
                'send_latency_ms': result.get('send_latency_ms'),
                'reply_latency_ms': result.get('reply_latency_ms'),
                'reply': result.get('reply'),
                'timeout': result.get('timeout', False)
            })
        else:
            # 只发送不等待
            start_time = time_module.time()
            future = asyncio.run_coroutine_threadsafe(
                send_telegram_message(target_chat, cmd),
                tg_app.loop
            )
            future.result(timeout=10)
            elapsed_ms = (time_module.time() - start_time) * 1000
            LOGGER.info(f"[API] 交易指令: {cmd} ({elapsed_ms:.0f}ms)")
            return jsonify({'success': True, 'command': cmd, 'send_latency_ms': round(elapsed_ms)})
    except Exception as e:
        LOGGER.error(f"[API] 交易指令发送失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@flask_app.route('/alpha_double', methods=['POST'])
def alpha_double():
    """接收 Alpha Call 翻倍通知并推送到 Telegram"""
    chat_id = RUNTIME_CONFIG.get('alpha_chat', '')
    if not chat_id:
        return jsonify({'success': False, 'error': 'ALPHA_CHAT 未配置，使用 /setalpha 设置'}), 400

    data = request.json
    if not data:
        return jsonify({'success': False, 'error': '无数据'}), 400

    symbol = data.get('symbol', '')
    address = data.get('address', '')
    chain = data.get('chain', '')
    start_mcap = data.get('start_mcap', 0)
    current_mcap = data.get('current_mcap', 0)
    gain_ratio = data.get('gain_ratio', 0)
    group_name = data.get('group_name', '')
    sender = data.get('sender', '')
    elapsed_seconds = data.get('elapsed_seconds', 0)
    history = data.get('history', [])

    # 格式化市值
    def fmt_mcap(mcap):
        if mcap >= 1000000:
            return f"${mcap/1000000:.1f}M"
        elif mcap >= 1000:
            return f"${mcap/1000:.0f}k"
        return f"${mcap:.0f}"

    # 构建消息
    chain_emoji = "🟣" if chain == "SOL" else "🟡"
    msg = f"🚀 **Alpha Call 翻倍!**\n\n"
    msg += f"{chain_emoji} **{symbol or 'Unknown'}** ({chain})\n"
    msg += f"📈 涨幅: **{gain_ratio:.1f}x**\n"
    msg += f"💰 市值: {fmt_mcap(start_mcap)} → {fmt_mcap(current_mcap)}\n"
    msg += f"⏱️ 用时: {elapsed_seconds}秒\n\n"

    if sender:
        msg += f"👤 发送人: {sender}\n"
    if group_name:
        msg += f"💬 来源群: {group_name}\n"
    msg += f"\n📋 CA:\n`{address}`"

    # 添加市值历史
    if history and len(history) > 1:
        msg += f"\n\n📊 市值变化:"
        for h in history[-5:]:  # 最近5条
            msg += f"\n  {h.get('time', 0)}s: {fmt_mcap(h.get('mcap', 0))}"

    # 异步发送到 Telegram
    try:
        target_chat = int(chat_id)
        asyncio.run_coroutine_threadsafe(
            send_telegram_message(target_chat, msg),
            tg_app.loop
        )
        LOGGER.info(f"[API] Alpha 翻倍推送: {symbol} {gain_ratio:.1f}x")
        return jsonify({'success': True})
    except Exception as e:
        LOGGER.error(f"[API] Alpha 翻倍推送失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


async def send_telegram_message(chat_id: int, text: str):
    """发送消息到 Telegram"""
    from pyrogram.enums import ParseMode
    try:
        # 先获取 chat 信息填充 peer 缓存
        await tg_app.get_chat(chat_id)
        await tg_app.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        LOGGER.error(f"[Telegram] 发送失败: {e}")


async def send_and_wait_reply(chat_id: int, text: str, timeout: float = 10.0):
    """发送消息并等待机器人回复，返回回复内容和时延"""
    future = asyncio.Future()
    sent_time = time_module.time()
    _pending_replies[chat_id] = (future, sent_time)

    try:
        await tg_app.get_chat(chat_id)
        await tg_app.send_message(chat_id, text)
        send_latency_ms = round((time_module.time() - sent_time) * 1000)

        # 等待回复
        result = await asyncio.wait_for(future, timeout=timeout)
        result['send_latency_ms'] = send_latency_ms
        return result
    except asyncio.TimeoutError:
        _pending_replies.pop(chat_id, None)
        return {
            'reply': None,
            'timeout': True,
            'send_latency_ms': round((time_module.time() - sent_time) * 1000)
        }
    except Exception as e:
        _pending_replies.pop(chat_id, None)
        LOGGER.error(f"[Telegram] 发送/等待回复失败: {e}")
        return {'error': str(e)}


def run_flask(port=5060):
    """运行 Flask 服务"""
    LOGGER.info(f"[API] 启动 Flask 服务: http://127.0.0.1:{port}")
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def _send_startup_notification(port):
    """后台发送启动通知"""
    import time
    # 等待 Telegram 客户端启动完成
    for _ in range(30):
        if tg_app.is_connected:
            break
        time.sleep(1)

    if not tg_app.is_connected:
        LOGGER.warning("[API] Telegram 客户端未就绪，跳过启动通知")
        return

    news_chat = RUNTIME_CONFIG.get('news_token_chat', '')
    alpha_chat = RUNTIME_CONFIG.get('alpha_chat', '')

    startup_msg = "🟢 **Telegram Forwarder 已启动**\n\n"
    startup_msg += f"📡 API 服务: http://127.0.0.1:{port}\n"
    startup_msg += f"⏰ 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"

    if news_chat:
        try:
            asyncio.run_coroutine_threadsafe(
                send_telegram_message(int(news_chat), startup_msg),
                tg_app.loop
            )
            LOGGER.info(f"[API] 启动通知已发送到 news 群: {news_chat}")
        except Exception as e:
            LOGGER.error(f"[API] 发送启动通知到 news 群失败: {e}")

    if alpha_chat and alpha_chat != news_chat:
        try:
            asyncio.run_coroutine_threadsafe(
                send_telegram_message(int(alpha_chat), startup_msg),
                tg_app.loop
            )
            LOGGER.info(f"[API] 启动通知已发送到 alpha 群: {alpha_chat}")
        except Exception as e:
            LOGGER.error(f"[API] 发送启动通知到 alpha 群失败: {e}")

    if news_chat:
        LOGGER.info(f"[API] 代币撮合推送已启用，目标群组: {news_chat}")
    else:
        LOGGER.info("[API] API 服务已启动，使用 /setnews <群组ID> 配置推送目标")


def start_api_server(port=5060):
    """在后台线程启动 API 服务（始终启动，可通过命令配置群组）"""
    thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    thread.start()

    # 后台发送启动通知（不阻塞）
    notify_thread = threading.Thread(target=_send_startup_notification, args=(port,), daemon=True)
    notify_thread.start()
