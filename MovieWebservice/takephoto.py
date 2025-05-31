import cv2
from flask import Flask, Response, render_template

app = Flask(__name__)

# カメラオブジェクトはグローバルに保持
camera = None

def generate_frames():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("Error: Could not open video stream.")
            return

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # 画像を上下反転させる (flipCode=0)
            frame_flipped_vertical = cv2.flip(frame, 0)
            # 上下反転した画像を左右反転させる (flipCode=1)
            frame_flipped_both = cv2.flip(frame_flipped_vertical, 1)

            # JPEGにエンコード
            ret, buffer = cv2.imencode('.jpg', frame_flipped_both, [int(cv2.IMWRITE_JPEG_QUALITY), 90]) # 品質を調整可能 (0-100)
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    # 動画を表示するシンプルなHTMLページ
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    # MJPEGストリームを返す
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        # すべてのIPアドレスでリッスン (LANとTailscaleの両方からアクセス可能にする)
        app.run(host='0.0.0.0', port=5569, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("Server shutting down.")
        if camera:
            camera.release()