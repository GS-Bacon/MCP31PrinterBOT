# server/config.py
from abc import ABC, abstractmethod

class BaseServerConfig(ABC):
    @property
    @abstractmethod
    def SERVER_IP(self):
        pass

    @property
    @abstractmethod
    def SERVER_PORT(self):
        pass

class ServerConfig(BaseServerConfig):
    # このファイルはGitHubにアップロードされます
    # 実際の値はここで直接記述せず、継承したファイルで指定します。
    # 例: from actual_server_config import MyActualServerConfig
    # そして MyActualServerConfig を使用します。
    pass