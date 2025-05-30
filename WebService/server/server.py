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
        self.output_dir = "received_files" # output_dir を定義
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

            # 修正: image_bytes がリストとして返されることを想定
            header_data, body_text, body_image_bytes_list, footer_data = deserialize_data(data_buffer)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            sender_ip = addr[0].replace('.', '_')

            driver = PrinterDriver()
            converter = ImageConverter(
            font_path=FONT_PATH,
            font_size=30,
            default_width=driver.paper_width_dots # プリンターの紙幅に合わせる
            )

            imglist=[]
            #ヘッダープリント
            if header_data:
                if header_data["type"] == "text" and header_data["content"]:
                    imglist.append(converter.text_to_bitmap(text=header_data["content"]))
                elif header_data["type"] == "image" and header_data["content"]:
                    imglist.append(converter.image_from_bytes(header_data["content"]))
            #本文プリント
            if body_text:
                imglist.append(converter.text_to_bitmap(text=format_text_with_url_summary(body_text,max_line_length=30,max_display_length=900, url_title_max_length=15)[0]))
                print(body_text)
            if body_image_bytes_list:
                for i,image_bytes in enumerate(body_image_bytes_list):
                    imglist.append(converter.image_from_bytes(image_bytes=image_bytes))

            if footer_data:
                if footer_data["type"] == "text" and footer_data["content"]:
                    imglist.append(converter.text_to_bitmap(text=footer_data["content"]))
                elif footer_data["type"] == "image" and footer_data["content"]:
                    imglist.append(converter.image_from_bytes(footer_data["content"]))
            printimg=converter.combine_images_vertically(images=imglist)
            if printimg:
                driver.print_image(printimg)
                driver.print_empty_lines(5)
                print("\n--- 紙をカット ---")
                driver.cut_paper(mode='full')
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
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