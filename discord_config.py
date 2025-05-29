# discord_config.py
import os

class DiscordConfig:
    """
    Discordボットの設定を定義するベースクラス。
    トークンやIDなどの機密情報は、このクラスを継承した別のファイルで定義します。
    """
    def __init__(self):
        # 環境変数から取得するなど、具体的な値はここに記述しない
        pass

    @property
    def bot_token(self) -> str:
        raise NotImplementedError("bot_tokenは継承クラスで実装してください。")

    @property
    def target_user_ids(self) -> list[int]: # 複数ユーザー対応のためリスト型に変更
        raise NotImplementedError("target_user_idsは継承クラスで実装してください。")