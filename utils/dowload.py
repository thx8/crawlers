import os
import zipfile
import asyncio
from utils.hybrid.hybrid_crawler import HybridCrawler
import httpx
import aiofiles

HybridCrawler = HybridCrawler()

async def fetch_data_stream(url: str, file_path: str, headers: dict = None):
    headers = headers or {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            async with aiofiles.open(file_path, 'wb') as out_file:
                async for chunk in response.aiter_bytes():
                    await out_file.write(chunk)
    return file_path

async def parse_and_download(url: str, download_dir: str = "downloads"):
    data = await HybridCrawler.hybrid_parsing_single_video(url, minimal=True)
    url_type = 'Video' if data.get('type') == 'video' else 'Image'
    platform = data.get('platform')
    aweme_id = data.get('aweme_id')

    os.makedirs(download_dir, exist_ok=True)

    if url_type == 'Video':
        wm_video_url_HQ = data.get('video_data').get('wm_video_url_HQ')
        nwm_video_url_HQ = data.get('video_data').get('nwm_video_url_HQ')

        # 下载视频
        wm_file = os.path.join(download_dir, f"{platform}_{aweme_id}_watermark.mp4")
        nwm_file = os.path.join(download_dir, f"{platform}_{aweme_id}.mp4")
        if wm_video_url_HQ:
            await fetch_data_stream(wm_video_url_HQ, wm_file)
            print(f"视频下载完成-水印: {wm_file}")
        if nwm_video_url_HQ:
            await fetch_data_stream(nwm_video_url_HQ, nwm_file)
            print(f"视频下载完成-无水印: {nwm_file}")

    elif url_type == 'Image':
        no_watermark_image_list = data.get('image_data').get('no_watermark_image_list')
        watermark_image_list = data.get('image_data').get('watermark_image_list')
        zip_nwm = os.path.join(download_dir, f"{platform}_{aweme_id}_images.zip")
        zip_wm = os.path.join(download_dir, f"{platform}_{aweme_id}_images_watermark.zip")

        # 下载无水印图片
        image_files_nwm = []
        for idx, img_url in enumerate(no_watermark_image_list):
            img_path = os.path.join(download_dir, f"{platform}_{aweme_id}_{idx+1}.jpg")
            await fetch_data_stream(img_url, img_path)
            image_files_nwm.append(img_path)
        # 压缩无水印图片
        with zipfile.ZipFile(zip_nwm, 'w') as zipf:
            for img in image_files_nwm:
                zipf.write(img, os.path.basename(img))
        print(f"图片下载完成-无水印: {zip_nwm}")

        # 下载水印图片
        image_files_wm = []
        for idx, img_url in enumerate(watermark_image_list):
            img_path = os.path.join(download_dir, f"{platform}_{aweme_id}_{idx+1}_watermark.jpg")
            await fetch_data_stream(img_url, img_path)
            image_files_wm.append(img_path)
        # 压缩水印图片
        with zipfile.ZipFile(zip_wm, 'w') as zipf:
            for img in image_files_wm:
                zipf.write(img, os.path.basename(img))
        print(f"图片下载完成-水印: {zip_wm}")

# 示例调用
# if __name__ == "__main__":
#     test_url = "https://www.tiktok.com/@example/video/1234567890"
#     asyncio.run(parse_and_download(test_url))
