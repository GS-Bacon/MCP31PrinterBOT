# client/client.py

import socket
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
if project_root not in sys.path:
    sys.path.append(project_root)

from common.network_utils import serialize_data 
from client.config import ClientConfig # 必要であれば

try:
    from .MyActualServerConfig import MyActualServerConfig as ActualClientConfig
except ImportError:
    print("Error: MyActualServerConfig.py not found or incorrectly configured.")
    print("Please copy ServerConfig.py.template to MyActualServerConfig.py and set actual values.")
    exit(1)


class FileSenderClient:
    def __init__(self):
        self.server_ip = ActualClientConfig().SERVER_IP
        self.server_port = ActualClientConfig().SERVER_PORT

    # send_data 関数の引数を変更: body_image_paths -> body_image_bytes_list
    def send_data(self, header_data=None, body_text_message=None, body_image_bytes_list=None, footer_data=None):
        
        # serialize_data 関数に、新しい引数を渡す
        data_to_send = serialize_data(
            header=header_data,
            body_text=body_text_message,
            body_image_bytes_list=body_image_bytes_list, # ここにバイト列のリストを渡す
            footer=footer_data
        )
        
        data_to_send += b"<END_OF_TRANSMISSION>"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.server_ip, self.server_port))
                s.sendall(data_to_send)
                print(f"Data sent successfully to {self.server_ip}:{self.server_port}")
            except ConnectionRefusedError:
                print(f"Connection refused. Make sure the server is running on {self.server_ip}:{self.server_port}")
            except Exception as e:
                print(f"An error occurred: {e}")

if __name__ == "__main__":
    client = FileSenderClient()

    while True:
        print("\n--- Send Data ---")
        
        # ヘッダーの入力
        header_choice = input("Header (t:text, i:image, s:skip, q:quit): ").lower()
        if header_choice == 'q':
            break # ここで終了判定
        header_data = None
        if header_choice == 't':
            header_content = input("Enter header text: ")
            header_data = {"type": "text", "content": header_content}
        elif header_choice == 'i':
            header_image_path = input("Enter header image path: ")
            # ヘッダー画像はパスからバイト列に変換
            if os.path.exists(header_image_path):
                try:
                    with open(header_image_path, "rb") as f:
                        header_image_bytes = f.read()
                        header_data = {"type": "image", "content": header_image_bytes}
                except IOError as e:
                    print(f"Error reading header image file '{header_image_path}': {e}. Skipping header image.")
            else:
                print(f"Warning: Header image file '{header_image_path}' not found. Skipping header image.")
        
        # 本文テキストの入力
        body_text_input = input("Enter body message (or 's' to skip, 'q' to quit): ")
        if body_text_input.lower() == 's':
            body_text_input = None
        elif body_text_input.lower() == 'q':
            break

        # 本文画像の入力 (複数対応)
        body_image_input = input("Enter paths to body image files (optional, comma-separated, leave blank to skip): ")
        body_image_bytes_list = [] # ここをバイト列のリストにする
        if body_image_input:
            body_image_paths = [p.strip() for p in body_image_input.split(',') if p.strip()]
            for img_path in body_image_paths:
                if os.path.exists(img_path):
                    try:
                        with open(img_path, "rb") as f:
                            body_image_bytes_list.append(f.read())
                    except IOError as e:
                        print(f"Error reading body image file '{img_path}': {e}. Skipping this image.")
                else:
                    print(f"Warning: Body image file '{img_path}' not found. Skipping this image.")
        
        # フッターの入力
        footer_choice = input("Footer (t:text, i:image, s:skip, q:quit): ").lower()
        if footer_choice == 'q':
            break # ここで終了判定
        footer_data = None
        if footer_choice == 't':
            footer_content = input("Enter footer text: ")
            footer_data = {"type": "text", "content": footer_content}
        elif footer_choice == 'i':
            footer_image_path = input("Enter footer image path: ")
            # フッター画像はパスからバイト列に変換
            if os.path.exists(footer_image_path):
                try:
                    with open(footer_image_path, "rb") as f:
                        footer_image_bytes = f.read()
                        footer_data = {"type": "image", "content": footer_image_bytes}
                except IOError as e:
                    print(f"Error reading footer image file '{footer_image_path}': {e}. Skipping footer image.")
            else:
                print(f"Warning: Footer image file '{footer_image_path}' not found. Skipping footer image.")
            
        client.send_data(
            header_data=header_data,
            body_text_message=body_text_input,
            body_image_bytes_list=body_image_bytes_list if body_image_bytes_list else None, # 空リストの場合はNoneを渡す
            footer_data=footer_data
        )
        print("-" * 30)