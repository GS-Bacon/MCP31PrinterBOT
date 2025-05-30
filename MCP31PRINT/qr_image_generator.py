# qr_image_generator.py

import qrcode
from PIL import Image, ImageDraw, ImageFont
import io

class QRImageGenerator:
    def __init__(self, font_path: str = None, font_size: int = 20, default_width: int = 576):
        """
        QRコードと説明文を組み合わせた画像を生成するクラス。
        :param font_path: 説明文に使用するフォントファイルのパス
        :param font_size: 説明文のフォントサイズ
        :param default_width: 生成する画像のデフォルト幅 (プリンターの紙幅に合わせる)
        """
        self.font_path = font_path
        self.font_size = font_size
        self.default_width = default_width
        self.font = self._load_font()

    def _load_font(self):
        """フォントを読み込む。指定がなければPillowのデフォルトフォントを使用。"""
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, self.font_size)
            else:
                print("警告: フォントパスが指定されていません。Pillowのデフォルトフォントを使用します。")
                print("日本語表示には適切なTrueTypeフォントを指定してください。")
                return ImageFont.load_default()
        except IOError:
            print(f"エラー: フォントファイル '{self.font_path}' が見つからないか、読み込めません。")
            print("Pillowのデフォルトフォントを使用します。")
            return ImageFont.load_default()
        except Exception as e:
            print(f"フォントの読み込み中に予期せぬエラーが発生しました: {e}")
            return ImageFont.load_default()

    def generate_qr_with_text(self, qr_data: str, description_text: str = "", 
                              output_path: str = None, 
                              qr_box_size: int = 10, qr_border: int = 4, 
                              qr_image_width: int = None, # QRコード画像の希望幅
                              text_max_width: int = None) -> Image.Image: # 説明文の最大幅
        """
        QRコードを生成し、その下に説明文を追加した画像を返す。
        :param qr_data: QRコードにエンコードするデータ (URL, テキストなど)
        :param description_text: QRコードの下に表示する説明文
        :param output_path: 生成された画像を保存するパス (Noneの場合、PIL.Imageオブジェクトを返す)
        :param qr_box_size: QRコードの各セルのピクセル数 (大きいほどQRコード画像が大きくなる)
        :param qr_border: QRコードの周囲の余白 (セル数)
        :param qr_image_width: QRコード画像の希望幅。Noneの場合、box_sizeとborderから自動計算。
        :param text_max_width: 説明文の最大幅。Noneの場合、qr_image_widthかdefault_widthを基準。
        :return: QRコードと説明文が結合されたPIL.Imageオブジェクト
        """
        print(f"DEBUG: Generating QR code for data: '{qr_data}'")
        print(f"DEBUG: Description text: '{description_text}'")

        # 1. QRコードの生成
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H, # 高いエラー訂正レベル
            box_size=qr_box_size, 
            border=qr_border,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # QRコードの希望幅が指定されていればリサイズ
        if qr_image_width is not None and qr_img.width != qr_image_width:
            print(f"DEBUG: Resizing QR code image from {qr_img.size} to width {qr_image_width}.")
            qr_img = qr_img.resize((qr_image_width, int(qr_img.height * qr_image_width / qr_img.width)), Image.Resampling.LANCZOS)
        
        print(f"DEBUG: QR code image generated. Size: {qr_img.size}")


        # 2. 説明文の画像生成 (image_converter.py のロジックを参考に)
        # 説明文の画像幅は、QRコード画像の幅かdefault_widthの大きい方に合わせる
        # あるいはtext_max_widthが指定されていればそれを優先
        if text_max_width is None:
            text_img_effective_width = max(qr_img.width, self.default_width)
        else:
            text_img_effective_width = text_max_width

        # 説明文の描画サイズを計算するためのダミー画像
        dummy_img = Image.new('RGB', (1, 1), color = (255, 255, 255))
        draw_dummy = ImageDraw.Draw(dummy_img)

        # フォントのメトリクスから基準の行の高さを取得
        try:
            ascender, descender = self.font.getmetrics()
            base_line_height = ascender + abs(descender)
        except AttributeError:
            base_line_height = self.font_size * 1.2

        line_spacing_extra = int(self.font_size * 0.2) # 行間

        processed_lines = []
        total_text_height = 0
        line_heights = []

        for line in description_text.splitlines():
            if line.strip() == "": # 空行の場合
                processed_lines.append("")
                current_line_height = base_line_height + line_spacing_extra
                line_heights.append(current_line_height)
                total_text_height += current_line_height
                continue
            
            # テキストの自動改行処理
            current_line_text = ""
            for char in line:
                test_line = current_line_text + char
                # 文字列の幅をチェック
                char_bbox = draw_dummy.textbbox((0,0), test_line, font=self.font)
                char_width = char_bbox[2] - char_bbox[0]

                if char_width > text_img_effective_width - 20: # 左右の余白を考慮
                    processed_lines.append(current_line_text)
                    line_bbox = draw_dummy.textbbox((0, 0), current_line_text, font=self.font)
                    current_line_height = max(line_bbox[3] - line_bbox[1], base_line_height) + line_spacing_extra
                    line_heights.append(current_line_height)
                    total_text_height += current_line_height
                    current_line_text = char # 次の行の開始
                else:
                    current_line_text += char
            
            if current_line_text: # 残りの文字があれば追加
                processed_lines.append(current_line_text)
                line_bbox = draw_dummy.textbbox((0, 0), current_line_text, font=self.font)
                current_line_height = max(line_bbox[3] - line_bbox[1], base_line_height) + line_spacing_extra
                line_heights.append(current_line_height)
                total_text_height += current_line_height
        
        # 説明文画像の高さ
        text_image_height = total_text_height + 20 # 上下余白

        # 説明文の画像を作成
        text_img = Image.new('RGB', (text_img_effective_width, text_image_height), color = (255, 255, 255))
        draw_text = ImageDraw.Draw(text_img)

        y_offset_text = 10 # 上余白
        for i, line in enumerate(processed_lines):
            # テキストを中央寄せにする
            if line.strip() == "": # 空行の場合は中央寄せをしない
                x_offset_text = 10 # 左端に寄せる
            else:
                line_bbox = draw_dummy.textbbox((0, 0), line, font=self.font)
                line_actual_width = line_bbox[2] - line_bbox[0]
                x_offset_text = (text_img_effective_width - line_actual_width) // 2
                x_offset_text = max(x_offset_text, 10) # 最低限の左余白

            draw_text.text((x_offset_text, y_offset_text), line, font=self.font, fill=(0, 0, 0))
            y_offset_text += line_heights[i]
        
        print(f"DEBUG: Description text image generated. Size: {text_img.size}")

        # 3. QRコードと説明文画像を結合
        # 最終的な画像の幅は、QRコード画像と説明文画像の大きい方に合わせる
        final_width = max(qr_img.width, text_img.width) 
        # QRコードとテキストの間に少しスペースを設ける
        padding_between = 20 
        
        final_height = qr_img.height + text_img.height + padding_between + 10 # 下部にさらに少し余白

        # 最終画像を作成 (白背景)
        combined_img = Image.new('RGB', (final_width, final_height), color=(255, 255, 255))

        # QRコードを中央に配置
        qr_x = (final_width - qr_img.width) // 2
        combined_img.paste(qr_img, (qr_x, 0))
        print(f"DEBUG: QR code pasted at ({qr_x}, 0)")

        # 説明文をQRコードの下に中央に配置
        text_x = (final_width - text_img.width) // 2
        combined_img.paste(text_img, (text_x, qr_img.height + padding_between))
        print(f"DEBUG: Description text pasted at ({text_x}, {qr_img.height + padding_between})")

        print(f"DEBUG: Combined image size: {combined_img.size}")

        if output_path:
            try:
                combined_img.save(output_path)
                print(f"DEBUG: Generated QR code with text image saved to {output_path}")
            except Exception as e:
                print(f"ERROR: 結合画像の保存中にエラーが発生しました: {e}")
        
        return combined_img

# --- 使用例 (main.py から呼び出すイメージ) ---
if __name__ == "__main__":
    # 例: fontsフォルダに日本語フォントがある場合
    # font_path = "fonts/YOUR_JAPANESE_FONT.ttf" # 環境に合わせてパスを調整
    font_path = None # デフォルトフォントで試す場合はNone

    qr_generator = QRImageGenerator(font_path=font_path, font_size=24)

    print("--- デフォルトサイズ (qr_box_size=10) ---")
    qr_data_1 = "https://www.google.com"
    description_1 = "Google検索はこちら"
    qr_img_1 = qr_generator.generate_qr_with_text(qr_data_1, description_1, "qr_with_text_google_default.png")
    print(f"Generated qr_with_text_google_default.png (PIL Image object: {qr_img_1 is not None})")

    print("\n--- QRコードサイズを小さく (qr_box_size=5) ---")
    qr_data_2 = "https://www.example.com/small_qr"
    description_2 = "小さなQRコードの例"
    qr_img_2 = qr_generator.generate_qr_with_text(qr_data_2, description_2, "qr_with_text_small_qr.png", qr_box_size=5)
    print(f"Generated qr_with_text_small_qr.png (PIL Image object: {qr_img_2 is not None})")

    print("\n--- QRコードサイズを大きく (qr_box_size=15) ---")
    qr_data_3 = "https://www.example.com/large_qr_data"
    description_3 = "大きなQRコードの例"
    qr_img_3 = qr_generator.generate_qr_with_text(qr_data_3, description_3, "qr_with_text_large_qr.png", qr_box_size=15)
    print(f"Generated qr_with_text_large_qr.png (PIL Image object: {qr_img_3 is not None})")

    print("\n--- 説明文の自動改行とQRコードの希望幅指定 ---")
    qr_data_4 = "https://www.very_long_url_that_needs_qr_code_to_be_of_certain_width.com/path/to/resource"
    description_4 = "これは非常に長い説明文です。指定した幅に収まるように自動的に改行されることを期待しています。プリンターの用紙幅に合わせて、テキストが適切に整形されるかを確認しましょう。"
    # QRコード画像を特定幅に設定し、テキストはその幅に合わせて自動改行
    qr_img_4 = qr_generator.generate_qr_with_text(
        qr_data_4, 
        description_4, 
        "qr_with_text_autowrap_custom_width.png", 
        qr_box_size=8, 
        qr_image_width=300, # QRコード画像の希望幅
        text_max_width=300 # 説明文の最大幅もQRコードに合わせる
    )
    print(f"Generated qr_with_text_autowrap_custom_width.png (PIL Image object: {qr_img_4 is not None})")


    # この `qr_img` などのPIL.Imageオブジェクトを `printer_driver.py` の `print_image` 関数に渡す
    # 例:
    # from printer_driver import PrinterDriver
    # driver = PrinterDriver()
    # driver.print_image(qr_img_1, alignment=1) # 中央寄せで印刷