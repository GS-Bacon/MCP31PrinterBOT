import socket
import threading
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
sys.path.append(project_root)

from datetime import datetime
from common.network_utils import deserialize_data
from .config import BaseServerConfig

from MCP31PRINT.printer_driver import PrinterDriver
from MCP31PRINT.image_converter import ImageConverter
from MCP31PRINT.text_formatter import format_text_with_url_summary
FONT_PATH='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
# 実際のServerConfigクラスをインポートします
# ユーザーは ServerConfig.py.template をコピーして MyActualServerConfig.py などを作成し、
# そのファイルをインポートするように設定します。
try:
    from .MyActualServerConfig import MyActualServerConfig as ActualServerConfig
except ImportError:
    print("Error: MyActualServerConfig.py not found or incorrectly configured.")
    print("Please copy ServerConfig.py.template to MyActualServerConfig.py and set actual values.")
    exit(1)

class FileReceiverServer:
    def __init__(self):
        self.host = ActualServerConfig().SERVER_IP
        self.port = ActualServerConfig().SERVER_PORT
        self.output_dir = os.path.join(current_dir, "/home/bacon/MCP31PrinterBOT/WebService/server/received_files") # output_dir をより安全なパスに
        os.makedirs(self.output_dir, exist_ok=True)

    def _handle_client(self, conn, addr):
        print(f"Connected by {addr}")
        try:
            data_buffer = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data_buffer += chunk
                if b"<END_OF_TRANSMISSION>" in data_buffer:
                    data_buffer = data_buffer.replace(b"<END_OF_TRANSMISSION>", b"")
                    break

            header_data, body_text, body_image_bytes_list, footer_data = deserialize_data(data_buffer)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            sender_ip = addr[0].replace('.', '_')

            driver = PrinterDriver()
            converter = ImageConverter(
                font_path=FONT_PATH,
                font_size=30, # 必要に応じて調整
                default_width=driver.paper_width_dots # プリンターの紙幅に合わせる
            )

            imglist=[]
            
            # ヘッダープリント
            if header_data:
                # header_data は既に整形済みの文字列として bot.py から送られてくることを想定
                # bot.py で {"type": "text", "content": header_text} の形式で送っている場合、
                # ここで {"type": "text", "content": "..."} の形式で受け取れる
                if isinstance(header_data, dict) and header_data.get("type") == "text" and header_data.get("content"):
                    imglist.append(converter.text_to_bitmap(text=header_data["content"]))
                # 画像ヘッダーの可能性も考慮（もし将来的に画像ヘッダーを送るなら）
                elif isinstance(header_data, dict) and header_data.get("type") == "image" and header_data.get("content"):
                    imglist.append(converter.image_from_bytes(header_data["content"]))
                elif isinstance(header_data, str): # bot.py が文字列を直接送る場合
                    imglist.append(converter.text_to_bitmap(text=header_data))
                else:
                    print(f"Warning: Unexpected header_data format: {type(header_data)} - {header_data}")


            # 本文プリント (bot.py で整形済みなので、ここでは再整形しない)
            if body_text:
                # bot.py から送られてくる body_text は既に format_text_with_url_summary の結果であると仮定
                imglist.append(converter.text_to_bitmap(text=body_text))
                print(f"Received body text and converting to image: {body_text}")

            # 添付画像プリント
            if body_image_bytes_list:
                for i, image_bytes in enumerate(body_image_bytes_list):
                    imglist.append(converter.image_from_bytes(image_bytes=image_bytes))
                    print(f"Received body image {i+1} and converting to image.")

            # フッタープリント (QRコード画像)
            if footer_data:
                # footer_data は {"type": "image", "content": combined_qr_image_bytes} の形式を想定
                if isinstance(footer_data, dict) and footer_data.get("type") == "image" and footer_data.get("content"):
                    # content はバイトデータなので、直接 image_from_bytes に渡す
                    imglist.append(converter.image_from_bytes(footer_data["content"]))
                    print("Received footer QR image and converting to image.")
                elif isinstance(footer_data, dict) and footer_data.get("type") == "text" and footer_data.get("content"):
                    imglist.append(converter.text_to_bitmap(text=footer_data["content"]))
                    print("Received footer text and converting to image.")
                elif isinstance(footer_data, bytes): # bot.py がバイトデータを直接送る場合
                     imglist.append(converter.image_from_bytes(footer_data))
                     print("Received raw footer image bytes and converting to image.")
                else:
                    print(f"Warning: Unexpected footer_data format: {type(footer_data)} - {footer_data}")

            # すべての画像を結合して印刷
            if imglist:
                printimg = converter.combine_images_vertically(images=imglist)
                if printimg:
                    driver.print_image(printimg)
                    driver.print_empty_lines(5)
                    print("\n--- 紙をカット ---")
                    driver.cut_paper(mode='full')
                else:
                    print("No combined image to print (imglist was not empty but combine_images_vertically returned None).")
            else:
                print("No content to print (imglist was empty).")

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            import traceback
            traceback.print_exc() # エラーのスタックトレースも表示
        finally:
            conn.close()
            print(f"Connection with {addr} closed.")

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"Server listening on {self.host}:{self.port}")
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=self._handle_client, args=(conn, addr))
                thread.start()

if __name__ == "__main__":
    server = FileReceiverServer()
    server.start()