import requests
import os
import yt_dlp

from selenium.webdriver.common.by import By

from utils.webdriver import setup_driver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

from utils.minio_client import upload_file



def download_video(video_url,itemId,folder):
    downloaded_file = os.path.join(folder, f'{itemId}.%(ext)s')
    ydl_opts = {
        'outtmpl': downloaded_file,  # 保存文件名
        'format': 'best',  # 选择最佳质量
    }

    # 下载视频
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)  # 下载并获取信息
            downloaded_file = ydl.prepare_filename(info_dict)  # 获取实际文件名
        print("视频下载完成！")

    except Exception as e:
        print(f"下载失败：{e}")

    try:
        with open(downloaded_file, 'rb') as f:
            video_data = f.read()
    except Exception as e:
        print(f"读取视频文件失败: {e}")
        return None

        # 上传到 MinIO
    content_type = "video/mp4"  # 根据实际文件类型设置
    extension = os.path.splitext(downloaded_file)[1][1:].lower()  # 提取扩展名（如 mp4）

    # 上传到 MinIO，移除前缀，仅使用 itemId.extension

    minio_filename = f'reddit_{itemId}.{extension}'
    upload_file(minio_filename, video_data, content_type,'item')
    return minio_filename

def download_imgs(img_urls,itemId,folder):
    save_img_url = []
    for index, img_url in enumerate(list(img_urls)):
        extension = img_url.split(".")[-1].split("?")[0].lower()
        if extension not in ["jpg", "jpeg", "png", "gif"]:
            extension = "jpg"  # 默认扩展名
        filename = f"{itemId}_{index}.{extension}"
        local_path = os.path.join(folder, filename)
        try:
            # 下载媒体文件
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(img_url, stream=True, headers=headers, timeout=10)
            resp.raise_for_status()

            content = b""
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        content += chunk

            # 设置内容类型
            content_type = "image/gif"

            # 上传到 MinIO，使用 item_id_index.extension 作为文件名
            minio_filename = f'reddit_{itemId}_{index}.{extension}'
            upload_file(minio_filename, content, content_type,'item')
            save_img_url.append(minio_filename)
            print(f"媒体下载并上传成功：{minio_filename}")

        except requests.RequestException as e:
            print(f"下载 {img_url} 失败: {e}")

    return save_img_url

def fetch(item, folder= os.path.join('downloads', 'reddit')):
    post_url = item['itemURL']
    item_id = item['itemId']
    # platform = item['itemSource']

    video_urls = []
    save_video_url = []

    img_urls = set()
    save_img_url = []

    driver = setup_driver()

    try:
        driver.get(post_url)

        # 提取视频内容
        try:
            video_list = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'shreddit-post div[slot="post-media-container"] shreddit-player-2')
                )
            )
            for video in video_list:
                media_json = json.loads(video.get_attribute('packaged-media-json'))
                permutation =  media_json['playbackMp4s']['permutations'][0]
                print(permutation['source']['url'])
                video_urls.append(permutation['source']['url'])
                # for permutation in media_json['playbackMp4s']['permutations']:
                #     print(permutation['source']['url'])
                #     video_urls.append(permutation['source']['url'])
        except:
            print("无视频内容")

        #  提取图片
        try:
            img_list = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'shreddit-post div[slot="post-media-container"] img')
                )
            )
            for img in img_list:
                img_urls.add(img.get_attribute('src'))
        except:
            print("无图片")

    finally:
        driver.quit()
    for video_url in video_urls:
        save_video_url.append(download_video(video_url,item_id,folder))


    save_img_url = download_imgs(img_urls, item_id, folder)

    item['saveVideoURL'] = save_video_url
    item['savePicURL'] = save_img_url
    print(item)
    return item


if __name__ == '__main__':
    item = {}
    item['itemURL'] = 'https://www.reddit.com/r/me_irl/comments/1nu6rrx/me_irl/'
    item['itemId'] = 'test4'
    fetch(item)