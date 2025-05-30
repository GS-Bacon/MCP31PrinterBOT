# receiver.py

import socket
import threading
import os
import json
import base64
from datetime import datetime

# 受信設定
RECEIVER_IP = '0.0.0.0'  # すべてのインターフェースからの接続を許可
RECEIVER_PORT = 12345    # 使用するポート番号
SAVE_DIR = 'received_data' # 受信データを保存するディレクトリ

def handle_client(client_socket, addr):
    """
    クライアントからの接続を処理する関数
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Connection from {addr}")

    try:
        # データ長を受け取る (4バイトの固定長)
        data_length_bytes = client_socket.recv(4)
        if not data_length_bytes:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Client {addr} disconnected unexpectedly (no data length).")
            return
        data_length = int.from_bytes(data_length_bytes, 'big')

        # データを受信する
        received_bytes = b''
        while len(received_bytes) < data_length:
            packet = client_socket.recv(4096)  # 適切なバッファサイズ
            if not packet:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Client {addr} disconnected unexpectedly (incomplete data).")
                break
            received_bytes += packet
        else:
            # JSONデータをデコード
            decoded_data = received_bytes.decode('utf-8')
            data = json.loads(decoded_data)

            message = data.get('message', '')
            image_base64 = data.get('image', None)
            timestamp = data.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
            sender_ip = data.get('sender_ip', addr[0]) # 送信元IPアドレスを保持

            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received from {sender_ip}:")
            print(f"  Message: {message}")

            # 保存ディレクトリの作成
            os.makedirs(SAVE_DIR, exist_ok=True)

            # メッセージをテキストファイルに保存
            message_filename = os.path.join(SAVE_DIR, f"message_{sender_ip}_{timestamp}.txt")
            with open(message_filename, 'w', encoding='utf-8') as f:
                f.write(f"Sender IP: {sender_ip}\n")
                f.write(f"Timestamp: {datetime.fromtimestamp(float(timestamp.replace('_', '')) / 1000000 if '_' in timestamp else float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')}\n\n") # タイムスタンプのフォーマットを調整
                f.write(message)
            print(f"  Message saved to: {message_filename}")

            # 画像データがあればデコードして保存
            if image_base64:
                try:
                    image_data = base64.b64decode(image_base64)
                    image_filename = os.path.join(SAVE_DIR, f"image_{sender_ip}_{timestamp}.png") # 例としてpngで保存
                    with open(image_filename, 'wb') as f:
                        f.write(image_data)
                    print(f"  Image saved to: {image_filename}")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error decoding or saving image from {sender_ip}: {e}")
            else:
                print("  No image received.")

    except json.JSONDecodeError:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Invalid JSON received from {addr}.")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error handling client {addr}: {e}")
    finally:
        client_socket.close()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Connection with {addr} closed.")

def start_receiver():
    """
    受信サービスを開始する関数
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # ソケットを再利用可能にする
    server_socket.bind((RECEIVER_IP, RECEIVER_PORT))
    server_socket.listen(5) # 5つの保留中の接続を許可
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Receiver listening on {RECEIVER_IP}:{RECEIVER_PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_handler.start()

if __name__ == "__main__":
    start_receiver()