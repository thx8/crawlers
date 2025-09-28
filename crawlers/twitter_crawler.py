# coding=utf-8
import requests
import os
import re
import undetected_chromedriver as UC
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from yt_dlp import YoutubeDL
# from utils.minio_client import upload_file


def create_crawler():
    # 配置 Chrome 选项
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")  # 无头模式，若要调试可以注释掉
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    # 启动浏览器
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_x_video(url: str, folder: str):
    """
    下载 X(原Twitter) 推文中的视频为 mp4，自动选择最佳画质和音频并合并。
    :param url: 推文链接，如 https://x.com/username/status/1234567890
    :param output_template: 输出文件名模板
    """

    def progress(d):
        if d.get('status') == 'downloading':
            # 显示简单进度
            speed = d.get('speed') or 0
            eta = d.get('eta')
            p = d.get('_percent_str', '').strip()
            s = f"进度: {p}  速度: {speed/1024/1024:.2f} MB/s"
            if eta is not None:
                s += f"  预计剩余: {eta}s"
            print(s, end='\r')
        elif d.get('status') == 'finished':
            print("\n下载完成，正在合并/转封装...")

    ydl_opts = {
        # 选最好的视频+音频；若不支持合并则退回最好的单路流
        "format": "b",  # bv*+ba/
        # 输出文件名
        "outtmpl": folder + "%(title).80s-%(id)s.%(ext)s",
        # 成品想要 mp4；若源是 m3u8，会自动用 ffmpeg 转封装
        "merge_output_format": "mp4",
        # 出错时继续（有时推文线程里有多媒体失败不影响主视频）
        "ignoreerrors": True,
        # 避免报错中断
        "retries": 5,
        "fragment_retries": 5,
        # 显示进度
        "progress_hooks": [progress],
        # 某些地区/网络需要该 UA 才能正常解析
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
        # 如果你需要下载需要登录可见的视频，可以解开下面这行，直接用浏览器 Cookie：
        # "cookiesfrombrowser": ("chrome",),  # 或 ("edge",) / ("firefox",)
        # 或者用 cookie 文件：
        # "cookiefile": "cookies.txt",
    }

    # 允许 x.com 或 twitter.com，两者都可以
    url = url.replace("twitter.com", "x.com")

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)  # 若是推文含多媒体，会按上面策略下载
        # 返回主条目的文件名（可能为列表）
        if info is None:
            print("没有可下载的媒体，可能需要登录或链接不包含视频。")
            return
        # 打印一下输出文件名（单条/多条都尽量给出）
        def _collect_entries(i):
            if i is None:
                return []
            if "entries" in i and i["entries"]:
                res = []
                for e in i["entries"]:
                    res += _collect_entries(e)
                return res
            return [i]

        entries = _collect_entries(info)
        print("\n保存的文件：")
        for e in entries:
            fn = ydl.prepare_filename(e)
            if e.get("ext") and not fn.endswith(f".{e['ext']}"):
                fn = fn.rsplit(".", 1)[0] + f".{e['ext']}"
            print(" -", fn)

def download_media(url, folder, platform, item_id, index, media_type):
    """下载单个媒体文件并上传到 MinIO"""
    os.makedirs(f'{folder}/{platform}', exist_ok=True)

    # 从URL获取文件扩展名
    extension = url.split(".")[-1].split("?")[0].split("#")[0].lower()

    # 根据媒体类型设置默认扩展名
    if media_type == "image":
        if extension not in ["jpg", "jpeg", "png", "gif", "webp"]:
            extension = "jpg"
    elif media_type == "video":
        if extension not in ["mp4", "webm", "mov"]:
            extension = "mp4"

    filename = f"{item_id}_{index}.{extension}"
    local_path = os.path.join(folder, platform, filename)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        resp = requests.get(url, stream=True, headers=headers, timeout=30)
        resp.raise_for_status() #

        content = b""
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    content += chunk

        # 确定内容类型
        if media_type == "image":
            content_type = f"image/{extension}" if extension in ["jpg", "jpeg", "png", "gif", "webp"] else "image/jpeg"
        else:  # video
            content_type = f"video/{extension}" if extension in ["mp4", "webm", "mov"] else "video/mp4"

        # 上传到MinIO
        # upload_file(filename, content, content_type)  # 先注释掉方法目前没有
        print(f"成功下载并上传: {filename}")
        return local_path, filename, content_type

    except requests.RequestException as e:
        print(f"下载 {url} 失败: {e}")
        return None, None, None
    except Exception as e:
        print(f"处理文件 {url} 时出错: {e}")
        return None, None, None


def extract_twitter_media(tweet_url, item_id, platform="twitter", folder="downloads/twitter"):
    """从Twitter推文URL提取并下载图片和视频"""
    os.makedirs(folder, exist_ok=True)
    media_files = []

    driver = None
    try:
        # 设置WebDriver
        driver = create_crawler()

        # 访问推文页面
        print(f"正在访问推文: {tweet_url}")
        driver.get(tweet_url)

        # 等待页面加载
        wait = WebDriverWait(driver, 20)

        # 等待推文内容加载
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]')))
        except TimeoutException:
            print("推文页面加载超时，可能推文不存在或需要登录")
            return media_files

        # 查找图片
        print("正在查找图片...")
        image_elements = driver.find_elements(By.CSS_SELECTOR,
                                              '[data-testid="tweetPhoto"] img, [data-testid="tweetPhoto"] source')

        for index, img_element in enumerate(image_elements, 1):
            try:
                # 尝试获取高分辨率图片URL
                img_url = None

                # 方法1: 从src属性获取
                if img_element.get_attribute("src"):
                    img_url = img_element.get_attribute("src")
                # 方法2: 从data-src属性获取
                elif img_element.get_attribute("data-src"):
                    img_url = img_element.get_attribute("data-src")

                if img_url:
                    # 尝试获取更高分辨率的图片
                    if "?format=" in img_url:
                        img_url = img_url.split("?format=")[0] + "?format=jpg&name=orig"
                    elif "&format=" in img_url:
                        img_url = img_url.split("&format=")[0] + "&format=jpg&name=orig"
                    elif "name=" not in img_url:
                        img_url += "?format=jpg&name=orig"

                    print(f"找到图片 {index}: {img_url}")
                    local_path, minio_filename, content_type = download_media(
                        img_url, folder, platform,item_id, index, "image"
                    )
                    if local_path:
                        media_files.append({
                            "local_path": local_path,
                            "minio_filename": minio_filename,
                            "content_type": content_type,
                            "media_type": "image"
                        })

            except Exception as e:
                print(f"处理图片 {index} 时出错: {e}")
                continue

        # 下载视频
        download_x_video(tweet_url, f'downloads/{platform}/{item_id}_')

    except Exception as e:
        print(f"访问推文时出错: {e}")
    finally:
        if driver:
            driver.quit()

    print(f"总共找到 {len(media_files)} 个媒体文件")
    return media_files


def fetch(tweet_url, platform="twitter", folder="downloads"):
    """主函数：从Twitter推文下载媒体文件"""
    print(f"开始处理    Twitter推文: {tweet_url}")

    item_id = f"{test_url.split('/')[5]}"
    # 验证URL格式
    if not tweet_url.startswith("https://twitter.com/") and not tweet_url.startswith("https://x.com/"):
        print("错误: 请提供有效的Twitter推文URL")
        return []

    # 确保URL格式正确
    if not tweet_url.endswith("/"):
        tweet_url += "/"

    # 提取媒体文件
    media_files = extract_twitter_media(tweet_url, item_id, platform, folder)

    # 打印结果摘要
    if media_files:
        print(f"\n下载完成! 共下载 {len(media_files)} 个文件:")
        for media in media_files:
            print(f"  - {media['media_type']}: {media['minio_filename']}")
    else:
        print("未找到任何媒体文件")

    return media_files


if __name__ == "__main__":
    # 测试用例
    test_url = "https://x.com/aespa_official/status/1971915321788576147"  # 替换为实际的推文URL


    media_files = fetch(test_url)
    print(f"测试完成，下载了 {len(media_files)} 个文件")
