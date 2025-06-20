# ServerConfig.py.template (このファイルをコピーして実際の値を記述する)
from server.config import BaseServerConfig

class MyActualServerConfig(BaseServerConfig):
    @property
    def SERVER_IP(self):
        return "0.0.0.0"

    @property
    def SERVER_PORT(self):
        return 6001 # 任意のポート番号