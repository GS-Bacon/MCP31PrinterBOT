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
        
        # Pillowの最新バージョンでは textbbox が正確な高さを返す
        # フォントの基準となる行の高さを取得
        # 'A'などの文字のbboxを取得して基準とするのが確実
        try:
            # getbbox はPillow 9.1.0以降でtextbboxの代わり
            # textbboxはPillow 8.0.0以降
            # getbboxはテキストの実際の描画範囲を返すため、特に ascender/descender を持つフォントでは重要
            # ダミー文字でベースライン高さを取得
            _, _, _, _, ascender, descender = draw.font.getfontinfo() # Pillow 10.0+
            base_line_height = ascender + abs(descender)
        except Exception:
            # 古いPillowやフォントでgetfontinfoが使えない場合
            try:
                ascender, descender = self.font.getmetrics()
                base_line_height = ascender + abs(descender)
            except AttributeError:
                base_line_height = self.font_size * 1.2 # fallback

        # 行間を調整するための追加スペース
        line_spacing_extra = int(self.font_size * 0.2) 
        effective_min_line_height = base_line_height + line_spacing_extra # 各行の最低限確保したい高さ

        calculated_line_dimensions = [] # 各行の(幅, 高さ)を保存するリスト

        for line_num, line in enumerate(lines):
            line_width = 0
            line_height = 0

            # 空行または空白のみの行の処理
            # 'textbbox'は空白文字や空文字列に対してゼロの高さや幅を返す場合があるため、特別に処理
            if not line.strip(): # 空行または空白文字のみの行の場合
                # 最小の行の高さを確保
                line_width = 0 # 空行なので幅は0
                line_height = effective_min_line_height
                print(f"DEBUG: Line {line_num} is empty/whitespace, setting height to {line_height}")
            else:
                # textbboxでテキストの描画サイズを取得
                # textbbox は (left, top, right, bottom) を返す
                # Pillow 9.2.0 以降では textbbox は (x0, y0, x1, y1) を返す
                # したがって、幅は x1-x0, 高さは y1-y0
                bbox = draw.textbbox((0, 0), line, font=self.font)
                line_width = bbox[2] - bbox[0]
                calculated_text_height = bbox[3] - bbox[1]
                
                # テキストの実際の描画高さと、最低限確保したい行の高さを比較し、大きい方を選ぶ
                line_height = max(calculated_text_height, effective_min_line_height)
                print(f"DEBUG: Line {line_num} ('{line}'): calculated_text_height={calculated_text_height}, chosen_line_height={line_height}, width={line_width}")
            
            max_line_width = max(max_line_width, line_width)
            calculated_line_dimensions.append((line_width, line_height))
        
        # 全体の高さを計算
        total_height = sum(dim[1] for dim in calculated_line_dimensions)

        # 画像の最終的な幅と高さ
        # 左右の余白を少し増やし、特に下部の余白を多めに取る
        image_width = max(self.default_width, max_line_width + 20) # 左右に余裕を持たせる (左10, 右10)
        image_height = total_height + 20 # 上下にも余裕を持たせる (上10, 下10)

        # 画像を作成 (白色背景、黒色テキスト) - 'RGB'モードで作成し、カラー画像として返す
        img = Image.new('RGB', (image_width, image_height), color = (255, 255, 255)) # 白背景 (RGB)
        draw = ImageDraw.Draw(img)

        y_offset = 10 # 上余白を少し増やす
        for i, line in enumerate(lines):
            # 空行でもテキストを描画（何も表示されないがオフセットは進む）
            # 空行の場合でも draw.text を呼ぶことで、y_offsetの計算が統一される
            draw.text((10, y_offset), line, font=self.font, fill=(0, 0, 0)) # 左余白を少し増やす
            y_offset += calculated_line_dimensions[i][1] # 計算された行の高さを加算

        if output_path:
            try:
                img.save(output_path)
                print(f"DEBUG: Generated text image saved to {output_path}")
            except Exception as e:
                print(f"ERROR: 画像保存中にエラーが発生しました: {e}")
        return img
    
    def image_from_bytes(self, image_bytes: bytes, auto_rotate_for_max_size: bool = False) -> Image.Image | None:
        """
        バイト列形式の画像データをPIL.Imageオブジェクトに変換する。
        必要に応じて、画像を90度回転させて、より大きな表示領域に収まるようにする。
        :param image_bytes: 画像のバイト列データ (PNG, JPEGなどのファイルデータ)
        :param auto_rotate_for_max_size: Trueの場合、画像の幅がデフォルト幅より小さいが、
                                         高さを幅として回転するとデフォルト幅に近づく場合、画像を90度回転させる。
                                         デフォルトはFalse（回転させない）。
        :return: 変換されたPIL.Imageオブジェクト、またはエラーの場合はNone
        """
        try:
            img_io = io.BytesIO(image_bytes)
            img = Image.open(img_io)
            print(f"DEBUG: Successfully converted bytes to PIL Image. Mode: {img.mode}, Original Size: {img.size}")

            if auto_rotate_for_max_size:
                # 画像の幅が default_width より小さく、
                # かつ高さを幅とすることで default_width に近づく場合に回転を検討
                # (例: 縦長の画像を横長にすることで、プリンターの紙幅に合わせる)
                
                # 現在の幅と高さ
                current_width, current_height = img.size
                
                # 回転した場合の幅と高さ
                rotated_width, rotated_height = current_height, current_width

                # ロジック:
                # 1. 現在の幅がdefault_widthよりも小さい
                # 2. かつ、回転後の幅(元の高さ)がdefault_widthに近い、またはより大きい
                # 3. かつ、現在の幅と高さの比率が大きく異なる（縦長である）
                # ここでは、単純に現在の幅より回転後の幅がdefault_widthに近づくか、default_widthを超える場合に回転を検討
                # ただし、default_widthを超える場合は縮小が必要になることに注意
                
                # 簡単な判断基準: 縦長の画像を横幅に合わせる方が良い場合
                # 現在の画像が、default_widthに対して「幅が狭く、高さがある」場合
                if current_width < self.default_width and current_height > self.default_width:
                     # 90度回転することで、幅が広がってdefault_widthに近づくか確認
                    if rotated_width <= self.default_width: # 回転後の幅がデフォルト幅以下に収まるなら回転
                        img = img.transpose(Image.ROTATE_90)
                        print(f"DEBUG: Image rotated 90 degrees for max size. New Size: {img.size}")
                    elif rotated_width > self.default_width and current_width < current_height:
                        # 回転後の幅がdefault_widthを超えるが、元の画像が非常に縦長で
                        # 回転した方がdefault_widthに近づく（かつ後で縮小できる）場合
                        # ここはより複雑な判断が必要になるため、シンプルな条件に留める
                        # 例: 縦横比が一定以上異なる場合
                        if current_height / current_width > 1.5: # 縦横比が1.5倍以上の場合
                            img = img.transpose(Image.ROTATE_90)
                            print(f"DEBUG: Image rotated 90 degrees for max size (aspect ratio). New Size: {img.size}")
                
                # もし画像が横長だが、default_widthより短く、回転するともっと小さくなる場合は回転しない
                # 例: (400, 200) -> default_width=576. 回転すると (200, 400) になって、幅が縮むので回転しない

            return img
        except Exception as e:
            print(f"ERROR: バイト列からの画像変換中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return None

    def combine_images_vertically(self, images: list[Image.Image], 
                                  padding: int = 1, 
                                  target_width: int = None) -> Image.Image | None:
        """
        複数のPIL.Imageオブジェクトを垂直方向に結合して1枚の画像にする。
        各画像は、指定されたターゲット幅に合わせて縮小（または拡大）される。
        結合された画像は、各画像を水平方向左に配置する。
        :param images: 結合するPIL.Imageオブジェクトのリスト
        :param padding: 各画像間のパディング（ピクセル数）
        :param target_width: 結合画像の最終的な幅。Noneの場合、ImageConverterのdefault_widthを使用。
                             各画像はこの幅に合わせてリサイズされる。
        :return: 結合されたPIL.Imageオブジェクト、またはエラーの場合はNone
        """
        if not images:
            print("WARNING: 結合する画像が指定されていません。")
            return None

        # ターゲット幅の決定
        if target_width is None:
            combined_target_width = self.default_width
        else:
            combined_target_width = target_width
        
        print(f"DEBUG: Combining images. Target width: {combined_target_width}")

        # RGBモードに変換し、ターゲット幅に合わせてリサイズ
        processed_images = []
        total_height = 0

        for i, img in enumerate(images):
            # RGBモードに変換
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # ターゲット幅に合わせてリサイズ (アスペクト比を維持)
            if img.width > combined_target_width: # 画像がターゲット幅より広い場合のみ縮小
                new_height = int(img.height * combined_target_width / img.width)
                img = img.resize((combined_target_width, new_height), Image.Resampling.LANCZOS)
                print(f"DEBUG: Image {i} resized from {images[i].size} to {img.size}")
            # もし画像がターゲット幅より狭い場合は、拡大しない
            # 必要であれば、後のパディングで対応する
            
            processed_images.append(img)
            total_height += img.height
            if i < len(images) - 1: # 最後の画像以外にパディングを追加
                total_height += padding

        # 結合された画像を作成 (白背景)
        combined_img = Image.new('RGB', (combined_target_width, total_height), color=(255, 255, 255))

        current_y_offset = 0
        for img in processed_images:
            x_offset = 0 # 左寄せのまま

            combined_img.paste(img, (x_offset, current_y_offset))
            current_y_offset += img.height + padding

        print(f"DEBUG: Combined images vertically. Final size: {combined_img.size}")
        return combined_img