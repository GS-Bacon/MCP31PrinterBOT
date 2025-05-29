import socketserver
import cv2
import sys

HOST = "192.168.0.199"  # ここはRaspberryPiのIPアドレスを入力
PORT = 5569


class TCPHandler(socketserver.BaseRequestHandler):
    videoCap = ''

    def handle(self):
        ret, frame = videoCap.read()

        # まず画像を上下反転させる (flipCode=0)
        frame_flipped_vertical = cv2.flip(frame, 0)
        # 次に、上下反転した画像を左右反転させる (flipCode=1)
        frame_flipped_both = cv2.flip(frame_flipped_vertical, 1)

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 100]  # この値100は映像の質の値
        # 上下左右反転したフレームをエンコードする
        jpegs_byte = cv2.imencode('.jpeg', frame_flipped_both, encode_param)[1]
        self.request.send(jpegs_byte)


videoCap = cv2.VideoCapture(0)

if not videoCap.isOpened():
    print("Error: Could not open video stream.")
    sys.exit()

socketserver.TCPServer.allow_reuse_address = True
server = socketserver.TCPServer((HOST, PORT), TCPHandler)

try:
    print(f"Server listening on {HOST}:{PORT}")
    server.serve_forever()
except KeyboardInterrupt:
    print("Server shutting down.")
    server.shutdown()
    videoCap.release()
    sys.exit()