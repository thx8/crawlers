import asyncio
import os
import re
import time


from utils.dowload import fetch_data_stream
from utils.hybrid.hybrid_crawler import HybridCrawler


HybridCrawler = HybridCrawler()  # 先创建实例




def find_url(string: str) -> list:
    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return url



async def parse_video():
    # 控制台输入
    input_data = input("请输入抖音或TikTok的分享口令或网址（可多个，用空格分隔）：\n")

    # 解析URL列表
    url_lists = find_url(input_data)

    # 解析开始时间
    start = time.time()

    # 成功/失败统计
    success_count = 0
    failed_count = 0
    success_list = []
    failed_list = []

    print("\n正在解析 TikTok 链接，请稍等...\n")

    # 遍历链接列表（并发执行）
    tasks = [handle_url(url, idx + 1, len(url_lists), success_list, failed_list) for idx, url in enumerate(url_lists)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 统计
    for r in results:
        if isinstance(r, bool) and r:
            success_count += 1
        else:
            failed_count += 1

    # 全部解析完成
    end = time.time()
    time_consuming = round(end - start, 2)
    print("\n解析完成！")
    print(f"成功: {success_count}，失败: {failed_count}，总数: {success_count + failed_count}")
    if success_list:
        print("\n成功列表:")
        print("\n".join(success_list))
    if failed_list:
        print("\n失败列表:")
        print("\n".join(failed_list))
    print(f"\n耗时: {time_consuming}s")


async def handle_url(url, url_index, total, success_list, failed_list):
    try:
        data = await HybridCrawler.hybrid_parsing_single_video(url, minimal=True)
    except Exception as e:
        print(f"[错误] 解析失败，第 {url_index} 个链接: {url}")
        print(f"原因: {str(e)}\n")
        failed_list.append(url)
        return False

    url_type = 'Video' if data.get('type') == 'video' else 'Image'
    platform = data.get('platform')

    # 输出解析结果
    print(f"解析第 {url_index}/{total} 个链接: {url}")
    print(f"类型: {url_type}")
    print(f"平台: {platform}")
    print(f"ID: {data.get('aweme_id')}")
    print(f"描述: {data.get('desc')}")
    print(f"作者昵称: {data.get('author').get('nickname')}")
    print(f"作者ID: {data.get('author').get('unique_id')}")

    base_dir = os.getcwd()
    download_dir = os.path.join(base_dir, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    if url_type == 'Video':
        wm_video_url_HQ = data.get('video_data').get('wm_video_url_HQ')
        nwm_video_url_HQ = data.get('video_data').get('nwm_video_url_HQ')

        print(f"视频链接-水印: {wm_video_url_HQ}")
        print(f"视频链接-无水印: {nwm_video_url_HQ}")
        print(f"视频下载-水印: /api/download?url={url}&prefix=true&with_watermark=true")
        print(f"视频下载-无水印: /api/download?url={url}&prefix=true&with_watermark=false\n")

        if nwm_video_url_HQ:
            nwm_file_path = os.path.join(download_dir, f"{platform}_{data.get('aweme_id')}.mp4")
            await fetch_data_stream(nwm_video_url_HQ, nwm_file_path)
            print(f"视频已下载-无水印: {nwm_file_path}")

    elif url_type == 'Image':
        no_watermark_image_list = data.get('image_data').get('no_watermark_image_list')
        for image in no_watermark_image_list:
            print(f"图片直链: {image}")
            print(f"图片下载-水印: /api/download?url={url}&prefix=true&with_watermark=true")
            print(f"图片下载-无水印: /api/download?url={url}&prefix=true&with_watermark=false\n")

    success_list.append(url)
    return True


if __name__ == "__main__":
    asyncio.run(parse_video())
