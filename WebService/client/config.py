# client/config.py
from abc import ABC, abstractmethod

class BaseClientConfig(ABC):
    @property
    @abstractmethod
    def SERVER_IP(self):
        pass

    @property
    @abstractmethod
    def SERVER_PORT(self):
        pass

class ClientConfig(BaseClientConfig):
    # このファイルはGitHubにアップロードされます
    pass