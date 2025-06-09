# このファイルはSlack APIトークンや秘密鍵など、機密情報を直接記述するために使用します。
# 実際のアプリケーションでは、環境変数から読み込むことを強く推奨します。
# config.pyで定義されたBaseConfigを参考に、環境変数に設定してください。

# 例: 環境変数を設定していない場合のフォールバック値として利用できますが、
# 本番環境では環境変数を使用してください。

# import os
# os.environ["SLACK_API_TOKEN"] = "xoxb-YOUR_ACTUAL_SLACK_BOT_TOKEN_HERE"
# os.environ["SLACK_APP_TOKEN"] = "xapp-YOUR_ACTUAL_SLACK_APP_TOKEN_HERE"
# os.environ["SLACK_SIGNING_SECRET"] = "YOUR_ACTUAL_SLACK_SIGNING_SECRET_HERE"

# config.py から設定をインポートし、必要に応じて上書きします。
from .config import config

# 例: 開発環境でのみ特定のチャンネルを監視する場合
# config.TARGET_CHANNEL_IDS = ["C1234567890_DEV_CHANNEL"]

# 注意: このファイルは直接編集せずに、環境変数を使用することがセキュリティ上最も推奨されます。
# これはあくまでデバッグやローカルテストのための便宜的なものです。