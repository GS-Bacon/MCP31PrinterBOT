# main.py

from printer_driver import PrinterDriver
from image_converter import ImageConverter
import os
from PIL import Image, ImageDraw
from qr_image_generator import QRImageGenerator # 新しく追加
FONT_PATH='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def main():
    driver = PrinterDriver()
    converter = ImageConverter(
        #font_path='C:/Windows/Fonts/msgothic.ttc', # Windowsの場合の日本語フォント例
        # font_path='/System/Library/Fonts/Osaka.ttf', # macOSの場合の日本語フォント例
        font_path=FONT_PATH,
        font_size=32,
        default_width=driver.paper_width_dots # プリンターの紙幅に合わせる
    )

    print("--- プリンター接続チェック ---")
    if driver.check_connection():
        print("プリンターに接続できます。")
    else:
        print("プリンターに接続できません。IPアドレスやケーブル接続を確認してください。")
        return # 接続できない場合は処理を中断

    print("\n--- テキストをビットマップイメージに変換して印刷 ---")
    text_to_print_image = "こちらは画像として印刷されます。\nフォント指定が可能です。\n"
    image_output_path = "output_text_image.png"
    
    # テキストを画像に変換
    text_image_obj = converter.text_to_bitmap(text_to_print_image, output_path=image_output_path)
    
    if text_image_obj:
        # 変換した画像を印刷 (PIL.Imageオブジェクトを直接渡す)
        driver.print_image(text_image_obj) 
    else:
        print("ERROR: テキスト画像の生成に失敗しました。")
    text_converter = ImageConverter(font_path=FONT_PATH) # テキスト画像変換
    qr_generator = QRImageGenerator(font_path=FONT_PATH) # QRコード＋テキスト画像変換

    text_converter = ImageConverter(font_path=FONT_PATH) 
    qr_generator = QRImageGenerator(font_path=FONT_PATH) 

    # 例1: デフォルトのQRサイズで印刷
    print("\n--- QRコードと説明文の印刷 (デフォルトサイズ) ---")
    qr_data_url = "https://www.google.com/maps/@35.7505295,139.7997973,15z"
    description_map = "お店の地図はこちらから\nご来店お待ちしております！"
    qr_map_image = qr_generator.generate_qr_with_text(qr_data_url, description_map, "output_qr_map.png")
    if qr_map_image:
        driver.print_image(qr_map_image, alignment=1)
        driver.print_empty_lines(3)

    # 例2: QRコードを小さめに、説明文も短く
    print("\n--- QRコードを小さめに印刷 ---")
    qr_data_short = "https://example.com/short"
    description_short = "簡単なQRコード"
    qr_small_image = qr_generator.generate_qr_with_text(
        qr_data_short, 
        description_short, 
        "output_qr_small.png", 
        qr_box_size=5,    # 小さめのQRコード
        qr_border=2       # 周囲の余白も小さく
    )
    if qr_small_image:
        driver.print_image(qr_small_image, alignment=1)
        driver.print_empty_lines(3)

    # 例3: QRコードを特定幅に、説明文は自動改行で長文対応
    print("\n--- 特定幅のQRと長文説明文 ---")
    qr_data_long_text = "https://ja.wikipedia.org/wiki/QR%E3%82%B3%E3%83%BC%E3%83%89_%E4%BB%A5%E4%B8%8B%E3%81%AF%E3%83%86%E3%82%B9%E3%83%88%E7%94%A8%E3%81%AE%E9%95%B7%E3%81%84URL%E3%81%A7%E3%81%99%E3%80%82%E3%81%93%E3%82%8C%E3%81%8C%E3%81%A9%E3%81%AE%E3%81%8F%E3%82%89%E3%81%84%E3%81%AE%E9%95%B7%E3%81%95%E3%81%AB%E3%81%AA%E3%82%8B%E3%81%8B%E7%A2%BA%E8%AA%8D%E3%81%97%E3%81%BE%E3%81%97%E3%82%87%E3%81%86"
    description_long = "このQRコードは、非常に長いURLを含んでいます。そのため、プリンターの用紙幅に合わせて適切にサイズが調整され、見やすいように表示されることを期待しています。説明文も長文ですが、自動改行されるはずです。"
    qr_custom_width_image = qr_generator.generate_qr_with_text(
        qr_data_long_text, 
        description_long, 
        "output_qr_custom_width.png", 
        qr_box_size=8,           # QRコードのセルサイズ
        qr_image_width=400,      # QRコード画像全体の希望幅 (例: プリンター幅-左右余白)
        text_max_width=400       # 説明文の最大幅もQRコード幅に合わせる
    )
    if qr_custom_width_image:
        driver.print_image(qr_custom_width_image, alignment=1)
        driver.print_empty_lines(3)
    print("\n--- 紙をフィード ---")
    driver.print_empty_lines(5)

    print("\n--- 紙をカット ---")
    driver.cut_paper(mode='full')

    print("\n--- 処理完了 ---")

if __name__ == "__main__":
    main()