import logging
import json
from os import getenv, path

from dotenv import load_dotenv
from pyrogram import Client

load_dotenv(".env")


logging.basicConfig(
    format="[ %(asctime)s: %(levelname)-8s ] %(name)-20s - %(message)s",
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)

# 降低 pyrogram 和 asyncio 日志级别
pyrogram_logger = logging.getLogger('pyrogram')
pyrogram_logger.setLevel(logging.WARNING)

asyncio_logger = logging.getLogger('asyncio')
asyncio_logger.setLevel(logging.CRITICAL)

# load json file
config_name = "chat_list.json"
if not path.isfile(config_name):
    LOGGER.error("No chat_list.json config file found! Exiting...")
    exit(1)
with open(config_name, "r") as data:
    CONFIG = json.load(data)


API_ID = getenv("API_ID")
API_HASH = getenv("API_HASH")
SESSION_NAME = getenv("SESSION_NAME", "forwarder")

if not API_ID or not API_HASH:
    LOGGER.error("No API_ID or API_HASH provided! Get them from https://my.telegram.org")
    exit(1)

OWNER_ID = int(getenv("OWNER_ID", "0"))
REMOVE_TAG = getenv("REMOVE_TAG", "False") in {"true", "True", "1"}

# AI 叙事总结配置
DEEPSEEK_API_KEY = getenv("DEEPSEEK_API_KEY", "")
ENABLE_NARRATIVE = getenv("ENABLE_NARRATIVE", "False") in {"true", "True", "1"}
NARRATIVE_CONTEXT = int(getenv("NARRATIVE_CONTEXT", "10"))  # 上下文消息数

# 心跳配置
HEARTBEAT_CHAT = getenv("HEARTBEAT_CHAT", "")  # "me" 或群组ID
HEARTBEAT_INTERVAL = int(getenv("HEARTBEAT_INTERVAL", "30"))  # 分钟

# 代理配置
PROXY_TYPE = getenv("PROXY_TYPE", "").lower()
PROXY_HOST = getenv("PROXY_HOST", "")
PROXY_PORT = getenv("PROXY_PORT", "")

proxy = None
if PROXY_TYPE and PROXY_HOST and PROXY_PORT:
    proxy = {
        "scheme": PROXY_TYPE,  # socks5, socks4, http
        "hostname": PROXY_HOST,
        "port": int(PROXY_PORT),
    }
    # 如果有用户名密码
    proxy_user = getenv("PROXY_USER", "")
    proxy_pass = getenv("PROXY_PASS", "")
    if proxy_user:
        proxy["username"] = proxy_user
    if proxy_pass:
        proxy["password"] = proxy_pass
    LOGGER.info(f"Using proxy: {PROXY_TYPE}://{PROXY_HOST}:{PROXY_PORT}")

# 创建 Pyrogram 客户端 (UserBot)
app = Client(
    SESSION_NAME,
    api_id=int(API_ID),
    api_hash=API_HASH,
    proxy=proxy,
)
