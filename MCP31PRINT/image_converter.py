# image_converter.py

from PIL import Image, ImageDraw, ImageFont
import io

class ImageConverter:
    def __init__(self, font_path: str = None, font_size: int = 24, default_width: int = 576):
        """
        :param font_path: 使用するフォントファイルのパス (例: 'arial.ttf', 'Osaka.ttf' など)
        :param font_size: フォントサイズ
        :param default_width: 生成する画像のデフォルト幅 (プリンターの紙幅に合わせる)
        """
        self.font_path = font_path
        self.font_size = font_size
        self.default_width = default_width
        self.font = self._load_font()

    def _load_font(self):
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

    def text_to_bitmap(self, text: str, output_path: str = None) -> Image.Image:
        """
        入力された文字列をビットマップイメージに変換する (生成された画像はRGB)。
        :param text: 変換する文字列
        :param output_path: 画像を保存するパス (Noneの場合、PIL.Imageオブジェクトを返す)
        :return: PIL.Imageオブジェクト
        """
        dummy_img = Image.new('L', (1, 1), color = 255) # Lモード (グレースケール) で白背景
        draw = ImageDraw.Draw(dummy_img)
            
        lines = text.splitlines()
        max_line_width = 0
        total_height = 0
        line_heights = []

        # フォントの行の高さを事前に取得 (ascender + descender)
        # これにより、textbboxだけでは捉えきれない文字の下部のはみ出しを考慮する
        try:
            # font.getmetrics() は (ascender, descender) を返す
            # descender は負の値になることがあるので絶対値を取るか、加算する
            ascender, descender = self.font.getmetrics()
            # 一般的な行の高さは ascender + abs(descender)
            # ただし、textbboxの高さと組み合わせるため、ここでは参考値
            base_line_height = ascender + abs(descender)
        except AttributeError:
            # getmetricsが利用できない古いPillowバージョンやフォントの場合
            base_line_height = self.font_size * 1.2 # fallback

        line_spacing_extra = int(self.font_size * 0.2) # 行間にフォントサイズの20%を追加

        for line in lines:
            if line.strip() == "": # 空行の場合
                # 空行もフォントの標準的な高さ＋行間を確保
                current_line_height = base_line_height + line_spacing_extra
                line_heights.append(current_line_height)
                total_height += current_line_height
                continue

            # textbboxでテキストの描画サイズを取得
            line_bbox = draw.textbbox((0, 0), line, font=self.font)
            line_width = line_bbox[2] - line_bbox[0]
            
            # 描画されたテキストの高さと、フォントのベースライン高さを比較し、大きい方を選ぶ
            # さらに、下部にはみ出す文字のために少し余裕を持たせる
            current_line_height = max(line_bbox[3] - line_bbox[1], base_line_height) + line_spacing_extra
            
            max_line_width = max(max_line_width, line_width)
            total_height += current_line_height
            line_heights.append(current_line_height)
        
        # 画像の最終的な幅と高さ
        # 左右の余白を少し増やし、特に下部の余白を多めに取る
        image_width = max(self.default_width, max_line_width + 20) # 左右に余裕を持たせる
        image_height = total_height + 20 # 上下にも余裕を持たせる (特に下部)

        # 画像を作成 (白色背景、黒色テキスト) - 'RGB'モードで作成し、カラー画像として返す
        img = Image.new('RGB', (image_width, image_height), color = (255, 255, 255)) # 白背景 (RGB)
        draw = ImageDraw.Draw(img)

        y_offset = 10 # 上余白を少し増やす
        for i, line in enumerate(lines):
            draw.text((10, y_offset), line, font=self.font, fill=(0, 0, 0)) # 左余白を少し増やす
            y_offset += line_heights[i]

        if output_path:
            try:
                img.save(output_path)
                print(f"DEBUG: Generated text image saved to {output_path}")
            except Exception as e:
                print(f"ERROR: 画像保存中にエラーが発生しました: {e}")
        return img
    
    def image_from_bytes(self, image_bytes: bytes) -> Image.Image | None:
        """
        バイト列形式の画像データをPIL.Imageオブジェクトに変換する。
        :param image_bytes: 画像のバイト列データ (PNG, JPEGなどのファイルデータ)
        :return: 変換されたPIL.Imageオブジェクト、またはエラーの場合はNone
        """
        try:
            img_io = io.BytesIO(image_bytes)
            img = Image.open(img_io)
            print(f"DEBUG: Successfully converted bytes to PIL Image. Mode: {img.mode}, Size: {img.size}")
            return img
        except Exception as e:
            print(f"ERROR: バイト列からの画像変換中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return None

    def combine_images_vertically(self, images: list[Image.Image], padding: int = 1) -> Image.Image | None:
        """
        複数のPIL.Imageオブジェクトを垂直方向に結合して1枚の画像にする。
        結合された画像の幅は、リスト内で最も幅の広い画像の幅に合わせられる。
        結合された画像は、各画像を水平方向中央に配置する。
        :param images: 結合するPIL.Imageオブジェクトのリスト
        :param padding: 各画像間のパディング（ピクセル数）
        :return: 結合されたPIL.Imageオブジェクト、またはエラーの場合はNone
        """
        if not images:
            print("WARNING: 結合する画像が指定されていません。")
            return None

        # RGBモードに変換しておく
        processed_images = []
        for img in images:
            if img.mode != 'RGB':
                processed_images.append(img.convert('RGB'))
            else:
                processed_images.append(img)
        images = processed_images

        max_width = 0
        total_height = 0

        for i, img in enumerate(images):
            max_width = max(max_width, img.width)
            total_height += img.height
            if i < len(images) - 1: # 最後の画像以外にパディングを追加
                total_height += padding

        # 結合された画像を作成 (白背景)
        combined_img = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))

        current_y_offset = 0
        for img in images:
            # 画像を中央に配置するためのX座標
            x_offset = (max_width - img.width) // 2
            combined_img.paste(img, (x_offset, current_y_offset))
            current_y_offset += img.height + padding

        print(f"DEBUG: Combined images vertically. Final size: {combined_img.size}")
        return combined_img