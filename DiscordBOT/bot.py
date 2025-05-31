import discord
from discord.ext import commands
from .my_discord_secrets import MyDiscordSecrets
import re
# from MCP31PRINT.printer_driver import PrinterDriver # ★★★ 完全に削除またはコメントアウト
from MCP31PRINT.image_converter import ImageConverter
from WebService.client.client import FileSenderClient
from MCP31PRINT.qr_image_generator import QRImageGenerator
import requests
import aiohttp
from MCP31PRINT.text_formatter import format_text_with_url_summary
from PIL import Image, ImageDraw

import json
import os

# DiscordConfigから設定を読み込む
config = MyDiscordSecrets()
TOKEN = config.bot_token
TARGET_USER_IDS = config.target_user_ids
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

# DM送信済みユーザーIDを記録するファイル
DM_SENT_USERS_FILE = '/home/bacon/MCP31PrinterBOT/DiscordBOT/dm_sent_users.json'

# インテントを設定
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guild_messages = True

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
        "server_name": None,
        "channel_name": None,
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
        print(f"送信者: {data_structure['sender_username']}")
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
    
    # ここからFileSenderClientへのデータ送信処理
    # DM, メンション, リプライのいずれかの条件が満たされた場合に実行
    if data_structure["type"] is not None:
        # PrinterDriver を bot.py で直接使う必要はないため、インスタンス化しない
        # driver = PrinterDriver() # ★★★ 削除

        # ImageConverter は QRコード結合のために必要なので残す
        # default_width は PrinterDriver.paper_width_dots の値（通常384）に合わせる
        converter = ImageConverter(
            font_path=FONT_PATH,
            font_size=20,
            default_width=384 # MCP31PRINT/printer_driver.py の paper_width_dots と同じ値にすること
        )
        
        # FileSenderClient のインスタンス化
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
        
        # 本文の印刷 (準備)
        # format_text_with_url_summary の結果をそのまま送る
        formatted_text, urls_from_content = format_text_with_url_summary(
            data_structure['content'],
            max_line_length=30, # あなたの希望に合わせて調整
            max_display_length=900,
            url_title_max_length=15
        )
        body_text_to_send = formatted_text # 整形済みテキストをクライアントに送る

        # 添付画像データの準備
        body_image_bytes_list = []
        for img_attachment in data_structure['attachments']:
            if img_attachment["is_image"]:
                image_bytes = await download_image(img_attachment["url"])
                if image_bytes:
                    body_image_bytes_list.append(image_bytes)

        # フッター (QRコード画像) の準備と結合
        footer_qr_images_pil = [] # PIL Imageオブジェクトのリスト
        qr_generator = QRImageGenerator(font_path=FONT_PATH)
        if urls_from_content: # urls_from_content を使用
            for url_data in urls_from_content:
                qr_data_short = url_data[0]
                description_short = url_data[1]
                qr_small_image_pil = qr_generator.generate_qr_with_text(
                    qr_data_short, 
                    description_short, 
                    "output_qr_small.png", 
                    qr_box_size=4,
                    qr_border=2
                )
                if qr_small_image_pil:
                    footer_qr_images_pil.append(qr_small_image_pil)
        
        combined_qr_image_bytes = None
        if footer_qr_images_pil:
            combined_pil_image = converter.combine_images_vertically(footer_qr_images_pil)
            if combined_pil_image:
                import io
                with io.BytesIO() as buffer:
                    combined_pil_image.save(buffer, format='PNG') # または 'BMP', 'JPEG' などプリンターがサポートする形式
                    combined_qr_image_bytes = buffer.getvalue()

        # client.send_data の呼び出し
        print(f"ヘッダーデータをFileSenderClientに送信（最終形式）:\n{header_text.strip()}")
        print(f"本文テキストをFileSenderClientに送信（整形済み）:\n{body_text_to_send.strip()}")
        print(f"添付画像数: {len(body_image_bytes_list)}")
        print(f"QRコード画像データあり: {combined_qr_image_bytes is not None}")

        try:
            client.send_data(
                header_data={"type": "text", "content": header_text},
                body_text_message=body_text_to_send, # 整形済みテキスト
                body_image_bytes_list=body_image_bytes_list if body_image_bytes_list else None,
                footer_data={"type": "image", "content": combined_qr_image_bytes} if combined_qr_image_bytes else None # QRコードはバイトデータ
            )
            print("データをFileSenderClientに正常に送信しました。")
        except Exception as e:
            print(f"FileSenderClientへのデータ送信中にエラーが発生しました: {e}")

    await bot.process_commands(message)

# ボットを実行
if __name__ == '__main__':
    bot.run(TOKEN)