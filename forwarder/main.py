import importlib

from forwarder import LOGGER, app
from forwarder.modules import ALL_MODULES

for module in ALL_MODULES:
    importlib.import_module("forwarder.modules." + module)


def run():
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))

    # 启动 API 服务
    from forwarder.modules.api import start_api_server
    start_api_server(port=5060)

    LOGGER.info("Starting userbot...")
    app.run()
