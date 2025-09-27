import requests
import os
import yt_dlp
import re
from crowbar_crawler.utils.minio_client import upload_file



def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def download_url(url, folder, item_id, index, platform):
    """下载单个图片/GIF/视频并上传到 MinIO"""
    os.makedirs(folder, exist_ok=True)
    extension = url.split(".")[-1].split("?")[0].lower()
    if extension not in ["jpg", "jpeg", "png", "gif", "mp4"]:
        extension = "jpg"  # 默认扩展名
    filename = f"{item_id}_{index}.{extension}"
    local_path = os.path.join(folder, filename)

    try:
        resp = requests.get(url, stream=True, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        content = b""
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 8):
                if chunk:
                    f.write(chunk)
                    content += chunk
        content_type = f"image/{extension}" if extension in ["jpg", "jpeg", "png", "gif"] else "video/mp4"
        upload_file(filename, content, content_type)
        return local_path, filename, content_type
    except requests.RequestException as e:
        print(f"下载 {url} 失败: {e}")
        return None, None, None


def fetch(post_url, item_id, platform, folder="downloads"):
    """从 Reddit 帖子下载媒体（视频、图片或图集）并上传到 MinIO"""
    os.makedirs(folder, exist_ok=True)
    media_files = []

    # 1. 获取 JSON 元数据
    if not post_url.endswith(".json"):
        json_url = post_url.rstrip("/") + "/.json"
    else:
        json_url = post_url

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(json_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data or not isinstance(data, list) or not data[0].get("data", {}).get("children"):
            print("无法解析 JSON 数据：帖子可能不存在或被限制")
            return media_files

        post_data = data[0]["data"]["children"][0]["data"]

        # 2. 处理图集帖子
        if post_data.get("is_gallery"):
            items = post_data["gallery_data"]["items"]
            for index, item in enumerate(items, 1):
                media_id = item["media_id"]
                meta = post_data["media_metadata"].get(media_id)
                if meta and meta.get("s", {}).get("u"):
                    url = meta["s"]["u"].replace("&amp;", "&")
                    local_path, minio_filename, content_type = download_url(url, folder, item_id, index, platform)
                    if local_path:
                        media_files.append(
                            {"local_path": local_path, "minio_filename": minio_filename, "content_type": content_type})
            return media_files

        # 3. 处理 Reddit 托管的视频
        if post_data.get("media", {}).get("reddit_video"):
            video_url = post_data["media"]["reddit_video"]["fallback_url"]
            local_path, minio_filename, content_type = download_url(video_url, folder, item_id, 1, platform)
            if local_path:
                media_files.append(
                    {"local_path": local_path, "minio_filename": minio_filename, "content_type": content_type})
            return media_files

        # 4. 处理单张图片或 GIF
        if post_data.get("post_hint") in ["image", "link"] and post_data.get("url"):
            local_path, minio_filename, content_type = download_url(post_data["url"], folder, item_id, 1, platform)
            if local_path:
                media_files.append(
                    {"local_path": local_path, "minio_filename": minio_filename, "content_type": content_type})
            return media_files

    except requests.RequestException as e:
        print(f"获取 Reddit JSON 失败: {e}")
    except Exception as e:
        print(f"解析 JSON 失败: {e}")

    # 5. 仅对可能的外部视频使用 yt-dlp
    ydl_opts = {
        'outtmpl': os.path.join(folder, f'{item_id}_%(index)s.%(ext)s'),
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': False,
        'verbose': True,
        'socket_timeout': 10,
        'retries': 3,
        'fragment_retries': 3,
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post_url, download=False)
            print("yt-dlp info:", info)
            if info.get('entries') is None and info.get('ext') == 'mp4' and 'reddit.com/gallery' not in post_url:
                ydl.download([post_url])
                local_path = os.path.join(folder, f"{item_id}_1.mp4")
                with open(local_path, "rb") as f:
                    content = f.read()
                content_type = "video/mp4"
                minio_filename = f"{item_id}_1.mp4"
                upload_file(minio_filename, content, content_type)
                media_files.append(
                    {"local_path": local_path, "minio_filename": minio_filename, "content_type": content_type})
    except Exception as e:
        print(f"yt-dlp 失败，可能不是视频帖子: {e}")

    return media_files
