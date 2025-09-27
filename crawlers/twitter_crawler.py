# coding=utf-8
import requests
import os
import re
import json
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from utils.minio_client import upload_file


def create_crawler():
    # print('进入到create_driver_without_login')
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


def download_media(url, folder, item_id, index, media_type):
    """下载单个媒体文件并上传到 MinIO"""
    os.makedirs(folder, exist_ok=True)

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
    local_path = os.path.join(folder, filename)

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
        resp.raise_for_status()

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
        upload_file(filename, content, content_type)  # 先注释掉方法目前没有
        print(f"成功下载并上传: {filename}")
        return local_path, filename, content_type

    except requests.RequestException as e:
        print(f"下载 {url} 失败: {e}")
        return None, None, None
    except Exception as e:
        print(f"处理文件 {url} 时出错: {e}")
        return None, None, None


def extract_twitter_media(tweet_url, item_id, platform="twitter", folder="downloads"):
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
                        img_url, folder, item_id, index, "image"
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

        # 查找视频
        print("正在查找视频...")
        video_elements = driver.find_elements(By.CSS_SELECTOR,
                                              '[data-testid="videoPlayer"] video, [data-testid="videoPlayer"] source')

        for index, video_element in enumerate(video_elements, 1):
            try:
                video_url = None

                # 尝试获取视频URL
                if video_element.get_attribute("src"):
                    video_url = video_element.get_attribute("src")
                elif video_element.get_attribute("data-src"):
                    video_url = video_element.get_attribute("data-src")

                if video_url:
                    print(f"找到视频 {index}: {video_url}")
                    local_path, minio_filename, content_type = download_media(
                        video_url, folder, item_id, index, "video"
                    )
                    if local_path:
                        media_files.append({
                            "local_path": local_path,
                            "minio_filename": minio_filename,
                            "content_type": content_type,
                            "media_type": "video"
                        })

            except Exception as e:
                print(f"处理视频 {index} 时出错: {e}")
                continue

        # 如果没找到视频，尝试查找其他可能的视频元素
        if not any(media["media_type"] == "video" for media in media_files):
            print("尝试查找其他视频元素...")
            alternative_video_elements = driver.find_elements(By.CSS_SELECTOR,
                                                              'video, [data-testid="videoComponent"] video')

            for index, video_element in enumerate(alternative_video_elements, 1):
                try:
                    video_url = video_element.get_attribute("src")
                    if video_url and "video" in video_url:
                        print(f"找到替代视频 {index}: {video_url}")
                        local_path, minio_filename, content_type = download_media(
                            video_url, folder, item_id, f"alt_{index}", "video"
                        )
                        if local_path:
                            media_files.append({
                                "local_path": local_path,
                                "minio_filename": minio_filename,
                                "content_type": content_type,
                                "media_type": "video"
                            })

                except Exception as e:
                    print(f"处理替代视频 {index} 时出错: {e}")
                    continue

    except Exception as e:
        print(f"访问推文时出错: {e}")
    finally:
        if driver:
            driver.quit()

    print(f"总共找到 {len(media_files)} 个媒体文件")
    return media_files


def fetch(tweet_url, item_id, platform="twitter", folder="downloads"):
    """主函数：从Twitter推文下载媒体文件"""
    print(f"开始处理Twitter推文: {tweet_url}")

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
    test_url = "https://x.com/Cristiano/status/1971675969137303570"  # 替换为实际的推文URL
    test_item_id = "test_tweet_001"

    media_files = fetch(test_url, test_item_id)
    print(f"测试完成，下载了 {len(media_files)} 个文件")
