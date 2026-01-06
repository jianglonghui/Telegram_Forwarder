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
GEMINI_API_KEY = getenv("GEMINI_API_KEY", "")
ENABLE_NARRATIVE = getenv("ENABLE_NARRATIVE", "False") in {"true", "True", "1"}
NARRATIVE_CONTEXT = int(getenv("NARRATIVE_CONTEXT", "10"))  # 上下文消息数

# 心跳配置
HEARTBEAT_CHAT = getenv("HEARTBEAT_CHAT", "")  # "me" 或群组ID
HEARTBEAT_INTERVAL = int(getenv("HEARTBEAT_INTERVAL", "30"))  # 分钟

# 代币撮合推送群组
NEWS_TOKEN_CHAT = getenv("NEWS_TOKEN_CHAT", "")

# Alpha Call 服务配置
def get_alpha_call_port():
    """从运行中的进程获取端口"""
    try:
        import subprocess
        # 1. 先找 alpha_call_service 的进程 ID
        ps_result = subprocess.run(
            ['pgrep', '-f', 'alpha_call_service'],
            capture_output=True, text=True, timeout=5
        )
        pids = ps_result.stdout.strip().split('\n')
        if not pids or not pids[0]:
            raise Exception("未找到 alpha_call_service 进程")

        # 2. 用 lsof 查找该进程监听的端口
        for pid in pids:
            if not pid.strip():
                continue
            lsof_result = subprocess.run(
                ['lsof', '-P', '-n', '-p', pid.strip()],
                capture_output=True, text=True, timeout=5
            )
            for line in lsof_result.stdout.split('\n'):
                if 'TCP' in line and 'LISTEN' in line:
                    # 格式: python 12345 user 5u IPv4 ... TCP *:5054 (LISTEN)
                    parts = line.split()
                    for part in parts:
                        if ':' in part:
                            port = part.split(':')[-1].replace('(LISTEN)', '')
                            if port.isdigit():
                                LOGGER.info(f"从进程 {pid} 发现 Alpha Call 端口: {port}")
                                return port
    except Exception as e:
        LOGGER.debug(f"无法从进程获取端口: {e}")
    # 回退到环境变量
    
    env_port = getenv("MEME_ALPHA_CALL_PORT") or getenv("ALPHA_CALL_PORT")
    if env_port:
        return env_port
    return "5054"

ALPHA_CALL_PORT = get_alpha_call_port()
ALPHA_CALL_URL = getenv("ALPHA_CALL_URL", f"http://127.0.0.1:{ALPHA_CALL_PORT}")
ENABLE_ALPHA_CALL = getenv("ENABLE_ALPHA_CALL", "True") in {"true", "True", "1"}

# 运行时配置（从 runtime_config.json 加载，支持持久化）
RUNTIME_CONFIG_FILE = "runtime_config.json"

def load_runtime_config():
    """加载运行时配置"""
    config = {}
    try:
        if path.isfile(RUNTIME_CONFIG_FILE):
            with open(RUNTIME_CONFIG_FILE, "r") as f:
                config = json.load(f)
    except Exception as e:
        LOGGER.error(f"加载运行时配置失败: {e}")
    # 环境变量作为默认值
    if not config.get('news_token_chat') and NEWS_TOKEN_CHAT:
        config['news_token_chat'] = NEWS_TOKEN_CHAT
    return config

RUNTIME_CONFIG = load_runtime_config()

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
