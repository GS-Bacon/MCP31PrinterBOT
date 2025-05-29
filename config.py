# config.py

class PrinterConfig:
    """
    プリンター設定の抽象クラス
    具体的な値は継承したクラスで定義する
    """
    PRINTER_IP: str = "192.168.1.XXX"  # 仮のIPアドレス。実際は継承先で上書き
    PRINTER_PORT: int = 9100         # 一般的なプリンターポート
    PAPER_WIDTH_DOTS: int = 576      # 一般的な80mm幅プリンターのドット数 (例えば、203dpiで80mm幅なら576ドット)
    # その他の設定項目があればここに追加