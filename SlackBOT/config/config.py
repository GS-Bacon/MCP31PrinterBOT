import os

class BaseConfig:
    """
    Slackボットの基本的な設定クラス。
    開発環境と本番環境で共通の設定を定義します。
    """
    SLACK_API_TOKEN = os.getenv("SLACK_API_TOKEN", "xoxb-YOUR_SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "xapp-YOUR_SLACK_APP_TOKEN") # Socket Modeを使用する場合
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "YOUR_SLACK_SIGNING_SECRET")

    # ターゲットチャンネルID (オプション)
    TARGET_CHANNEL_IDS = [] # 例: ["C1234567890", "C9876543210"]

    # ログ設定
    LOG_LEVEL = "INFO"

class DevelopmentConfig(BaseConfig):
    """
    開発環境用の設定クラス。
    本番環境と異なる設定があればここで上書きします。
    """
    SLACK_API_TOKEN = os.getenv("SLACK_API_TOKEN_DEV", "xoxb-YOUR_DEV_SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN_DEV", "xapp-YOUR_DEV_SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET_DEV", "YOUR_DEV_SLACK_SIGNING_SECRET")
    LOG_LEVEL = "DEBUG"

class ProductionConfig(BaseConfig):
    """
    本番環境用の設定クラス。
    """
    pass # 現状はBaseConfigと同じ

def get_config():
    """
    環境変数 'FLASK_ENV' または 'PYTHON_ENV' に基づいて適切な設定クラスを返します。
    デフォルトは本番環境設定です。
    """
    env = os.getenv("FLASK_ENV") or os.getenv("PYTHON_ENV")
    if env == "development":
        print("Loading DevelopmentConfig")
        return DevelopmentConfig()
    else:
        print("Loading ProductionConfig")
        return ProductionConfig()

# ボットの起動時に設定をロード
config = get_config()