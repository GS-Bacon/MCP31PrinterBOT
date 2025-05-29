# bot.py
import discord
from discord.ext import commands
from my_discord_secrets import MyDiscordSecrets
import re # 正規表現モジュールをインポート
from printer_driver import PrinterDriver
from image_converter import ImageConverter
from PIL import Image, ImageDraw
from qr_image_generator import QRImageGenerator
import requests
import aiohttp
from qr_image_generator import QRImageGenerator
from text_formatter import format_text_with_url_summary
# DiscordConfigから設定を読み込む
config = MyDiscordSecrets()
TOKEN = config.bot_token
TARGET_USER_IDS = config.target_user_ids
FONT_PATH='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
# インテントを設定
# メンションやメッセージ内容を取得するために必要なインテントを有効にする
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容の読み取りを許可

bot = commands.Bot(command_prefix='!', intents=intents)
def PrintImg(image_bytes: bytes):
    """
    ダウンロードした画像のバイトデータを受け取り、処理するダミー関数。
    ここに実際の画像処理ロジックを記述します。
    """
    print(f"--- PrintImg関数が画像を処理中 ---")
    print(f"画像データのサイズ: {len(image_bytes)}バイト")

    # 例: 画像バイトデータをファイルとして保存する
    # with open("downloaded_image_from_bytes.png", "wb") as f:
    #     f.write(image_bytes)
    # print("画像をバイトデータからファイルとして保存しました。")

    # 例: Pillow (PIL) ライブラリを使って画像を開く (要: pip install Pillow)
    # from PIL import Image
    # import io
    # try:
    #     image = Image.open(io.BytesIO(image_bytes))
    #     print(f"画像サイズ: {image.size}, フォーマット: {image.format}")
    #     # image.show() # 画像を表示する (開発時のみ推奨)
    # except Exception as e:
    #     print(f"Pillowで画像を開けませんでした: {e}")

    print(f"--- PrintImg関数による画像処理完了 (仮) ---")

async def download_image(url: str) -> bytes | None:
    """
    指定されたURLから画像をダウンロードし、バイトデータを返します。
    エラーが発生した場合はNoneを返します。
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status() # HTTPエラーがあれば例外を発生させる
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
    # ユーザーメンション: <@!ID> または <@ID>
    content = re.sub(r'<@!?\d+>', '', content)
    # チャンネルメンション: <#ID>
    content = re.sub(r'<#\d+>', '', content)
    # ロールメンション: <@&ID>
    content = re.sub(r'<@&\d+>', '', content)
    # URLのプレビューを抑制する記法: <URL>
    content = re.sub(r'<https?://[^\s]+>', '', content)

    return content.strip() # 前後の空白を削除して返す

@bot.event
async def on_ready():
    """ボットが起動したときに実行されるイベント"""
    print(f'Logged in as {bot.user}')
    print(f'Target User IDs: {TARGET_USER_IDS}')

@bot.event
async def on_message(message: discord.Message):
    """
    メッセージが送信されたときに実行されるイベント。
    特定のユーザーへのメンションや返信を検出します。
    """
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return

    # メッセージ内容からメンション部分を削除
    cleaned_content = clean_message_content(message.content)

    # 構造体として格納するデータ
    data_structure = {
        "type": None,  # "mention" or "reply"
        "sender_username": message.author.display_name,
        "message_url": None, # 後で設定
        "content": cleaned_content, # クリーンアップされた内容を使用
        "attachments": [],
        "channel_url": f"https://discord.com/channels/{message.guild.id}/{message.channel.id}" if message.guild else None
    }

    # メッセージURLを取得
    if message.guild:
        data_structure["message_url"] = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
    else: # DMの場合
        data_structure["message_url"] = f"https://discord.com/channels/@me/{message.channel.id}/{message.id}"

    # 添付ファイル (画像を含む) の取得
    for attachment in message.attachments:
        attachment_info = {
            "filename": attachment.filename,
            "url": attachment.url,
            "is_image": attachment.content_type.startswith("image/") if attachment.content_type else False
        }
        data_structure["attachments"].append(attachment_info)
    # メンションの検出
    is_target_mentioned = False
    if message.mentions:
        for user in message.mentions:
            if user.id in TARGET_USER_IDS:
                is_target_mentioned = True
                break
    
    if is_target_mentioned:
        data_structure["type"] = "mention"

    # 返信 (リプライ) の検出
    is_reply_to_target = False
    if message.reference and message.reference.resolved:
        referenced_message = message.reference.resolved
        if referenced_message.author.id in TARGET_USER_IDS:
            is_reply_to_target = True

    if is_reply_to_target:
        data_structure["type"] = "reply"
    if is_target_mentioned or is_reply_to_target:
        driver = PrinterDriver()
        converter = ImageConverter(
        font_path=FONT_PATH,
        font_size=20,
        default_width=driver.paper_width_dots # プリンターの紙幅に合わせる
        )
        if driver.check_connection():
            print("プリンターに接続できます。")
        else:
            print("プリンターに接続できません。IPアドレスやケーブル接続を確認してください。")
        image_output_path = "output_text_image.png"
        text_image_obj = converter.text_to_bitmap(f"================================================\nDiscord {data_structure['type']} !!!!\nto {data_structure['sender_username']}\n================================================\n", output_path=image_output_path)
        driver.print_image(text_image_obj)
        #本文
        formatted_text, urls=format_text_with_url_summary(data_structure['content'],max_line_length=30,max_display_length=300, url_title_max_length=15)
        text_to_print_image = formatted_text
        text_image_obj = converter.text_to_bitmap(text_to_print_image, output_path=image_output_path)
        if text_image_obj:
            driver.print_image(text_image_obj)
        #添付画像印刷
        for img in data_structure['attachments']:
            if img["is_image"]:
                image_bytes = await download_image(img["url"])
                if image_bytes:
                    driver.print_image_from_bytes(image_bytes)
        #含まれるURLをQRにして添付
        qr_generator = QRImageGenerator(font_path=FONT_PATH)
        for url in urls:
            qr_data_short = url[0]
            description_short = url[1]
            qr_small_image = qr_generator.generate_qr_with_text(
                qr_data_short, 
                description_short, 
                "output_qr_small.png", 
                qr_box_size=4,    # 小さめのQRコード
                qr_border=2       # 周囲の余白も小さく
            )
            if qr_small_image:
                driver.print_image(qr_small_image, alignment=1)
                driver.print_empty_lines(1)
        driver.print_empty_lines(5)

        print("\n--- 紙をカット ---")
        driver.cut_paper(mode='full')
    await bot.process_commands(message)

# ボットを実行
if __name__ == '__main__':
    bot.run(TOKEN)