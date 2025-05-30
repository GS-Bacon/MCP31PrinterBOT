import discord
from discord.ext import commands
from .my_discord_secrets import MyDiscordSecrets
import re
from MCP31PRINT.printer_driver import PrinterDriver
from MCP31PRINT.image_converter import ImageConverter
from WebService.client.client import FileSenderClient
from MCP31PRINT.qr_image_generator import QRImageGenerator
import requests
import aiohttp
from MCP31PRINT.text_formatter import format_text_with_url_summary
from PIL import Image, ImageDraw # ImageDraw も追加

import json # JSONファイルの読み書き用
import os   # ファイルパス操作用

# DiscordConfigから設定を読み込む
config = MyDiscordSecrets()
TOKEN = config.bot_token
TARGET_USER_IDS = config.target_user_ids
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc' # 必要に応じてパスを調整

# DM送信済みユーザーIDを記録するファイル
DM_SENT_USERS_FILE = 'dm_sent_users.json'

# インテントを設定
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guild_messages = True # ギルドメッセージも引き続き処理するため有効

bot = commands.Bot(command_prefix='!', intents=intents)

# DM送信済みユーザーIDをメモリにロードする関数
def load_dm_sent_users() -> list[int]:
    if os.path.exists(DM_SENT_USERS_FILE):
        with open(DM_SENT_USERS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {DM_SENT_USERS_FILE} is empty or invalid JSON. Initializing as empty list.")
                return []
    return []

# DM送信済みユーザーIDをファイルに保存する関数
def save_dm_sent_users(user_ids: list[int]):
    with open(DM_SENT_USERS_FILE, 'w') as f:
        json.dump(user_ids, f)

# グローバル変数としてDM送信済みユーザーIDのリストを初期化
dm_sent_user_ids = load_dm_sent_users()


def PrintImg(image_bytes: bytes):
    """
    ダウンロードした画像のバイトデータを受け取り、処理するダミー関数。
    ここに実際の画像処理ロジックを記述します。
    """
    print(f"--- PrintImg関数が画像を処理中 ---")
    print(f"画像データのサイズ: {len(image_bytes)}バイト")
    print(f"--- PrintImg関数による画像処理完了 (仮) ---")

async def download_image(url: str) -> bytes | None:
    """
    指定されたURLから画像をダウンロードし、バイトデータを返します。
    エラーが発生した場合はNoneを返します。
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                image_bytes = await response.read()
                print(f"画像をダウンロードしました: {url}")
                return image_bytes
        except aiohttp.ClientError as e:
            print(f"画像のダウンロード中にエラーが発生しました ({url}): {e}")
            return None

def clean_message_content(content: str) -> str:
    """
    メッセージ内容からメンション（<@ID>）やチャンネルメンション（<#ID>）、
    ロールメンション（<@&ID>）などのDiscord固有の記法を削除します。
    """
    content = re.sub(r'<@!?\d+>', '', content)
    content = re.sub(r'<#\d+>', '', content)
    content = re.sub(r'<@&\d+>', '', content)
    content = re.sub(r'<https?://[^\s]+>', '', content)
    return content.strip()

@bot.event
async def on_ready():
    """ボットが起動したときに実行されるイベント"""
    print(f'Logged in as {bot.user}')
    print(f'Target User IDs: {TARGET_USER_IDS}')
    print(f'Loaded DM sent user IDs: {dm_sent_user_ids}')

@bot.event
async def on_message(message: discord.Message):
    """
    メッセージが送信されたときに実行されるイベント。
    特定のユーザーへのメンションや返信を検出します。
    DMからのメッセージも処理します。
    """
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return

    is_dm = (message.guild is None)

    # 送信者名の設定 (DMの場合は匿名化)
    sender_display_name = "匿名ユーザー" if is_dm else message.author.display_name

    # メッセージ内容からメンション部分を削除
    cleaned_content = clean_message_content(message.content)

    # 構造体として格納するデータ
    data_structure = {
        "type": None,  # "mention", "reply", "dm"
        "sender_username": sender_display_name, # 匿名化された名前を使用
        "message_url": None,
        "content": cleaned_content,
        "attachments": [],
        "server_name": None,  # 新しく追加
        "channel_name": None, # 新しく追加
        "channel_url": None
    }

    # サーバー名、チャンネル名、URLの取得
    if is_dm:
        data_structure["type"] = "dm"
        data_structure["message_url"] = f"https://discord.com/channels/@me/{message.channel.id}/{message.id}"
        # DMの場合、サーバー名とチャンネル名は空（None）のまま
    else: # ギルド（サーバー）メッセージの場合
        data_structure["server_name"] = message.guild.name
        data_structure["channel_name"] = message.channel.name
        data_structure["message_url"] = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        data_structure["channel_url"] = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}"

    # 添付ファイル (画像を含む) の取得
    for attachment in message.attachments:
        attachment_info = {
            "filename": attachment.filename,
            "url": attachment.url,
            "is_image": attachment.content_type.startswith("image/") if attachment.content_type else False
        }
        data_structure["attachments"].append(attachment_info)
    # DMメッセージの処理と自動返信
    if is_dm:
        print(f"--- DMメッセージ検出 ---")
        print(f"送信者: {data_structure['sender_username']}") # 匿名化された名前が表示される
        print(f"内容: {data_structure['content']}")
        print(f"メッセージURL: {data_structure['message_url']}")
        if data_structure['attachments']:
            print(f"添付ファイル: {[att['filename'] for att in data_structure['attachments']]}")
        print(f"--------------------")

        # DM送信済みユーザーリストのチェックと更新
        user_id = message.author.id
        if user_id not in dm_sent_user_ids:
            # 初めてDMを受け取ったユーザーの場合、DMを送信
            welcome_message = (
                "この度は、連携アプリとしてご利用いただきありがとうございます。\n"
                "私は自動応答ボットです。送信されたメッセージを処理し、プリンターに出力します。\n"
                "ご不明な点があれば、このDMでお気軽にお尋ねください。"
            )
            try:
                await message.author.send(welcome_message)
                dm_sent_user_ids.append(user_id)
                save_dm_sent_users(dm_sent_user_ids)
                print(f"DMを初めて送信したユーザーID: {user_id} を記録しました。")
            except discord.Forbidden:
                print(f"ユーザー {user_id} ({message.author.name}) へのDM送信に失敗しました。ユーザーがDMをブロックしている可能性があります。")
        else:
            print(f"ユーザー {user_id} には以前DMを送信済みです。")

    else: # ギルド（サーバー）メッセージの処理
        is_target_mentioned = False
        if message.mentions:
            for user in message.mentions:
                if user.id in TARGET_USER_IDS:
                    is_target_mentioned = True
                    break
        
        is_reply_to_target = False
        if message.reference and message.reference.resolved:
            referenced_message = message.reference.resolved
            if referenced_message.author.id in TARGET_USER_IDS:
                is_reply_to_target = True

        if is_target_mentioned:
            data_structure["type"] = "mention"
        elif is_reply_to_target:
            data_structure["type"] = "reply"
        
        if is_target_mentioned or is_reply_to_target:
            print(f"--- ギルドメッセージ検出 ({data_structure['type']}) ---")
            print(f"データ: {data_structure}")
            print(f"--------------------")
    
    # ここからプリンター出力の共通処理
    # DM, メンション, リプライのいずれかの条件が満たされた場合に実行
    if data_structure["type"] is not None: # DM, mention, reply のいずれかであれば
        driver = PrinterDriver()
        converter = ImageConverter(
            font_path=FONT_PATH,
            font_size=20,
            default_width=driver.paper_width_dots
        )
        if driver.check_connection():
            print("プリンターに接続できます。")
        else:
            print("プリンターに接続できません。IPアドレスやケーブル接続を確認してください。")
        client = FileSenderClient() 

        # ヘッダー情報の生成
        header_text = ""
        if data_structure["type"] == "dm":
            header_text = "================================================\n" \
                          "DM Message\n" \
                          "from Anonymous\n" \
                          "================================================\n"
        else: # ギルドメッセージの場合
            header_text = f"================================================\n" \
                          f"Discord {data_structure['type']} !!!!\n" \
                          f"from {data_structure['sender_username']}\n" \
                          f"Server: {data_structure['server_name'] if data_structure['server_name'] else 'N/A'}\n" \
                          f"Channel: #{data_structure['channel_name'] if data_structure['channel_name'] else 'N/A'}\n" \
                          f"================================================\n"

        # 本文の印刷
        body_text=""
        body_result=format_text_with_url_summary(data_structure['content'],max_line_length=30,max_display_length=900, url_title_max_length=15)
        if data_structure['content']:
            body_text=body_result[0]

        # 添付画像印刷 (PrintImg関数が既にダウンロードと処理を行っているため、ここではdriver.print_image_from_bytesを呼び出す)
        body_image_bytes_list = []
        for img in data_structure['attachments']:
            if img["is_image"]:
                image_bytes = await download_image(img["url"]) # ここでダウンロードし直す
                if image_bytes:
                    body_image_bytes_list.append(image_bytes)
        #フッター
        
        # 含まれるURLをQRにして添付
        # urls変数がformat_text_with_url_summaryから返されることを想定
        QRS=[]
        QRImages=None
        if 'urls' in locals() and body_result: # urlsが存在し、空でないことを確認
            qr_generator = QRImageGenerator(font_path=FONT_PATH)
            for url in body_result[1]:
                qr_data_short = url[0]
                description_short = url[1]
                qr_small_image = qr_generator.generate_qr_with_text(
                    qr_data_short, 
                    description_short, 
                    "output_qr_small.png", 
                    qr_box_size=4,
                    qr_border=2
                )
                if qr_small_image:
                    QRS.append(qr_small_image)
        if len(QRS)>0:
            QRImages=converter.combine_images_vertically(QRS)
        print(f"ヘッダー！！！！！！！！！！！！！！！！{header_text}")
        client.send_data(
            header_data={"type": "text", "content": header_text}, # FileSenderClientが期待する形式に合わせる
            body_text_message=body_text,
            body_image_bytes_list=body_image_bytes_list if body_image_bytes_list else None,
            footer_data={"type": "image", "content": QRImages} if QRImages else None
        )
    
    await bot.process_commands(message)

# ボットを実行
if __name__ == '__main__':
    bot.run(TOKEN)