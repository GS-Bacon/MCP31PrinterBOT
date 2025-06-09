#!/home/bacon/MCP31PrinterBOT/.venv/bin/python
# -*- coding: utf-8 -*-

import os
import time
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# =================================================================
# パス設定の修正
# =================================================================

# 1. google_forms_printer ディレクトリのパスをシステムパスに追加
#    local_config.py をインポートできるようにするため
sys.path.append(os.path.dirname(__file__))
from local_config import AppConfig

# 2. MCP31PrinterBOT のルートパスをシステムパスに追加
#    'WebService' パッケージを認識させるため
#    app.pyは /home/bacon/MCP31PrinterBOT/google_forms_printer/app.py
#    MCP31PrinterBOTのルートは /home/bacon/MCP31PrinterBOT/
#    つまり、app.pyから見て一つ上のディレクトリがMCP31PrinterBOTのルート
mcp31_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(mcp31_root_path) # <-- ここでMCP31PrinterBOTのルートを追加

# 3. WebService.client.client を直接インポート (上記パス追加により可能になる)
#    from WebService.client.client import FileSenderClient
#    から以下に変更します。これで直接アクセスできるようになります。
from WebService.client.client import FileSenderClient

# =================================================================
# 設定 (AppConfigから読み込む) ---
# =================================================================
config = AppConfig()

SPREADSHEET_ID = config.SPREADSHEET_ID
RANGE_NAME = config.RANGE_NAME
CREDENTIALS_FILE = config.CREDENTIALS_FILE
POLLING_INTERVAL_SECONDS = config.POLLING_INTERVAL_SECONDS
PRINTED_ROWS_FILE = config.PRINTED_ROWS_FILE

# --- グローバル変数 ---
last_processed_row_count = 0
printer_client = None

# --- 印刷済み行の管理 ---
def load_printed_row_indices():
    """印刷済み行のインデックスをファイルから読み込む"""
    if os.path.exists(PRINTED_ROWS_FILE):
        with open(PRINTED_ROWS_FILE, 'r') as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    return set()

def save_printed_row_index(row_index):
    """印刷済み行のインデックスをファイルに保存する"""
    with open(PRINTED_ROWS_FILE, 'a') as f:
        f.write(f"{row_index}\n")

# --- Google Sheets API クライアントの初期化 ---
def get_sheets_service():
    """Google Sheets API サービスオブジェクトを返す"""
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service

# --- スプレッドシートからのデータ取得 ---
def get_spreadsheet_data(service, spreadsheet_id, range_name):
    """スプレッドシートから指定範囲のデータを取得する"""
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    return values

# --- 印刷処理 ---
def print_answer(row_data_list, row_index, printed_row_indices_set):
    """
    B列に新規で追加されたメッセージ内容を印刷モジュールを使って印刷サーバーに送信する。
    row_data_list: スプレッドシートの1行分のデータ（リスト）。RANGE_NAMEがB列のみの場合、このリストは要素を1つ含む。
    row_index: スプレッドシートの行番号 (1から始まる)
    printed_row_indices_set: 印刷済み行のセット
    """
    global printer_client
    if printer_client is None:
        printer_client = FileSenderClient()

    # B列のメッセージ内容を取得 (row_data_listは ['メッセージ内容'] の形式で来るはず)
    message_content = row_data_list[0] if row_data_list else "メッセージがありません"

    print(f"--- 新規メッセージ印刷ジョブを送信中 (行番号: {row_index}) ---")

    # ヘッダー: タイムスタンプは取得できないので、シンプルに「新規メッセージ」とする
    header_data = {"type": "text", "content": "--- 新規メッセージ ---"}

    # ボディテキスト: B列のメッセージ内容を直接設定
    body_text_message = message_content

    body_image_bytes_list = [] # 今回の要件では画像添付がないため、空リスト

    # フッター: 行番号と受付日時（これはスプレッドシートのA列にある想定なので、取得できない場合は省略）
    # もしA列のタイムスタンプも必要なら、RANGE_NAMEを 'シート1!A:B' などと変更し、
    # row_data_list[0]をタイムスタンプ、row_data_list[1]をメッセージとして利用する
    footer_data = {"type": "text", "content": f"受付: 行 {row_index}"}

    try:
        printer_client.send_data(
            header_data=header_data,
            body_text_message=body_text_message,
            body_image_bytes_list=body_image_bytes_list,
            footer_data=footer_data
        )
        print(f"新規メッセージを印刷ジョブ送信しました (行番号: {row_index})")
        save_printed_row_index(row_index)
        printed_row_indices_set.add(row_index)
    except Exception as e:
        print(f"印刷ジョブの送信に失敗しました (行番号: {row_index}): {e}")

# --- メイン処理 ---
def main():
    global last_processed_row_count

    if SPREADSHEET_ID == 'YOUR_SPREADSHEET_ID_HERE':
        print("エラー: local_config.py の SPREADSHEET_ID を GoogleスプレッドシートのIDに置き換えてください。")
        return

    print("Googleフォーム新規メッセージ印刷アプリケーションを開始します。")
    print(f"ポーリング間隔: {POLLING_INTERVAL_SECONDS}秒")
    print(f"スプレッドシートID: {SPREADSHEET_ID}")
    print(f"監視レンジ: {RANGE_NAME}")

    try:
        sheets_service = get_sheets_service()
        print("Google Sheets API 認証に成功しました。")
    except Exception as e:
        print(f"Google Sheets API の認証に失敗しました。認証情報ファイルを確認してください: {e}")
        return

    printed_row_indices = load_printed_row_indices()
    print(f"これまでに印刷済みの行: {sorted(list(printed_row_indices))}")

    print("初回データ取得と未印刷メッセージの確認を開始します...")
    all_rows = get_spreadsheet_data(sheets_service, SPREADSHEET_ID, RANGE_NAME)
    if all_rows:
        for i, row_data_list in enumerate(all_rows):
            current_row_index = i + 1
            if current_row_index not in printed_row_indices:
                if row_data_list and row_data_list[0]: # データが存在し、かつ空でないことを確認
                    print(f"未印刷の新規メッセージを検知しました (行番号: {current_row_index})")
                    print_answer(row_data_list, current_row_index, printed_row_indices)
                else:
                    print(f"行 {current_row_index} は空またはメッセージがありません。スキップします。")
            else:
                print(f"行 {current_row_index} は既に印刷済みです。")
        last_processed_row_count = len(all_rows)
    else:
        print("スプレッドシートにデータがありません。")

    print("--- 定期ポーリングを開始します ---")
    while True:
        try:
            current_rows = get_spreadsheet_data(sheets_service, SPREADSHEET_ID, RANGE_NAME)
            current_row_count = len(current_rows)

            if current_row_count > last_processed_row_count:
                print(f"新しいメッセージを検知しました: {current_row_count - last_processed_row_count}件")
                for i in range(last_processed_row_count, current_row_count):
                    row_data_list = current_rows[i]
                    current_row_index = i + 1
                    if current_row_index not in printed_row_indices:
                        if row_data_list and row_data_list[0]: # データが存在し、かつ空でないことを確認
                            print_answer(row_data_list, current_row_index, printed_row_indices)
                        else:
                            print(f"行 {current_row_index} は空またはメッセージがありません。スキップします。")
                    else:
                        print(f"重複検知: 行 {current_row_index} は既に印刷済みとして記録されています。")
                last_processed_row_count = current_row_count
            else:
                print(f"新しいメッセージはありません。現在の回答数: {current_row_count}")

        except Exception as e:
            print(f"エラー発生: {e}")
            print("次のポーリングで再試行します。")

        time.sleep(POLLING_INTERVAL_SECONDS)

if __name__ == '__main__':
    main()