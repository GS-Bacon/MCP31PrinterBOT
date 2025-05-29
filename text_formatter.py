import re
import requests
from bs4 import BeautifulSoup
import textwrap # テキストの折り返しに便利なライブラリ

def format_text_with_url_summary(text: str, max_line_length: int = 80, max_display_length: int = 40, url_title_max_length: int = 20) -> tuple[str, list[tuple[str, str]]]:
    """
    文字列をフォーマットし、URLをページタイトルに変換して表示します。
    指定文字数以上の場合には省略表示を行い、1行が指定文字数を超えた場合は改行します。

    Args:
        text (str): フォーマットする元の文字列。
        max_line_length (int): 1行の最大文字数。これを超えると改行されます。
        max_display_length (int): 通常の文字列の最大表示文字数。これを超えると省略されます。
        url_title_max_length (int): URLから取得したページタイトルの最大表示文字数。これを超えると省略されます。

    Returns:
        tuple[str, list[tuple[str, str]]]:
            - フォーマットされ、改行が挿入された文字列。
            - (URL, 省略されたページタイトル) のタプルのリスト。
    """
    formatted_text_parts = []
    found_urls_with_titles = []

    url_pattern = re.compile(r'https?://[^\s]+')

    last_index = 0
    for match in url_pattern.finditer(text):
        # URLの前の部分を追加
        pre_url_text = text[last_index:match.start()]
        if pre_url_text:
            # ここでは_truncate_stringを使い、後でtextwrapで全体を折り返す
            formatted_text_parts.append(_truncate_string(pre_url_text, max_display_length))

        url = match.group(0)
        page_title = _get_page_title(url)
        truncated_title = _truncate_string(page_title, url_title_max_length, ellipsis_suffix="")

        formatted_text_parts.append(f"[{truncated_title}]")
        found_urls_with_titles.append((url, truncated_title))

        last_index = match.end()

    # 最後のURL以降の文字列を追加
    remaining_text = text[last_index:]
    if remaining_text:
        formatted_text_parts.append(_truncate_string(remaining_text, max_display_length))

    # 全体を結合してからtextwrapで折り返す
    combined_text = "".join(formatted_text_parts)
    wrapped_text = textwrap.fill(combined_text, width=max_line_length)

    return wrapped_text, found_urls_with_titles

def _truncate_string(s: str, max_len: int, ellipsis_suffix: str = "XXXXX[残り{}文字]") -> str:
    """
    文字列を指定された最大長に短縮します。
    最大長を超える場合は、省略記号と残りの文字数を追加します。

    Args:
        s (str): 短縮する文字列。
        max_len (int): 最大長。
        ellipsis_suffix (str): 省略されたときに使用するサフィックス。

    Returns:
        str: 短縮された文字列。
    """
    if len(s) > max_len:
        remaining_chars = len(s) - max_len
        return s[:max_len] + ellipsis_suffix.format(remaining_chars)
    return s

def _get_page_title(url: str) -> str:
    """
    指定されたURLからページのタイトルを取得します。
    取得できない場合はURLをそのまま返します。

    Args:
        url (str): タイトルを取得するURL。

    Returns:
        str: ページのタイトル、または取得できなかった場合はURL。
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        else:
            return url  # タイトルが見つからない場合はURLを返す
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return url  # エラーが発生した場合はURLを返す

if __name__ == '__main__':
    # 使用例

    # ---
    ## 通常の文字列の省略と改行の例
    test_string1 = "これは非常に長い文字列です。この文字列は指定された文字数よりもはるかに長いはずです。そして、これが省略される部分です。"
    formatted_text1, urls1 = format_text_with_url_summary(test_string1, max_line_length=40, max_display_length=20)
    print(f"オリジナル:\n{test_string1}")
    print(f"フォーマット後 (max_line_length=40, max_display_length=20):\n{formatted_text1}")
    print(f"URLリスト: {urls1}\n")

    # ---
    ## URLを含む文字列のフォーマットと改行の例
    test_string2 = "今日のニュースはこちらです: https://www.google.com/search?q=今日のニュース また、Pythonの公式ページも参照してください: https://www.python.org/documentation/ こちらも長いURLです: https://www.geeksforgeeks.org/python-string-length-check-and-truncate-example/"
    formatted_text2, urls2 = format_text_with_url_summary(test_string2, max_line_length=60, max_display_length=20, url_title_max_length=15)
    print(f"オリジナル:\n{test_string2}")
    print(f"フォーマット後 (max_line_length=60, max_display_length=20, url_title_max_length=15):\n{formatted_text2}")
    print(f"URLリスト: {urls2}\n")

    # ---
    ## 短い文字列で改行が不要な例
    test_string3 = "短い文字列です。URLなし。"
    formatted_text3, urls3 = format_text_with_url_summary(test_string3, max_line_length=40, max_display_length=20)
    print(f"オリジナル:\n{test_string3}")
    print(f"フォーマット後 (max_line_length=40, max_display_length=20):\n{formatted_text3}")
    print(f"URLリスト: {urls3}\n")

    # ---
    ## タイトルが短いURLと長いURLを含む例
    test_string4 = "タイトルが短いURL: https://www.example.com/ そして長いURL: https://www.geeksforgeeks.org/python-string-length-check-and-truncate-example/さらに別の短いURL: https://www.bing.com/"
    formatted_text4, urls4 = format_text_with_url_summary(test_string4, max_line_length=50, max_display_length=20, url_title_max_length=10)
    print(f"オリジナル:\n{test_string4}")
    print(f"フォーマット後 (max_line_length=50, max_display_length=20, url_title_max_length=10):\n{formatted_text4}")
    print(f"URLリスト: {urls4}\n")

    # ---
    ## 無効なURLを含む例
    test_string5 = "無効なURLが含まれる場合: http://invalid-url-example-12345.com/ そして有効なURL: https://www.google.com/search?q=example%20domain"
    formatted_text5, urls5 = format_text_with_url_summary(test_string5, max_line_length=50, max_display_length=20, url_title_max_length=15)
    print(f"オリジナル:\n{test_string5}")
    print(f"フォーマット後 (max_line_length=50, max_display_length=20, url_title_max_length=15):\n{formatted_text5}")
    print(f"URLリスト: {urls5}\n")