from crowbar_crawler.utils.kafka_client import create_consumer
from crowbar_crawler.crawlers import youtube_crawler

CRAWLER_MAP = {
    "youtube": youtube_crawler.fetch,
}

def run_item_consumer():
    consumer = create_consumer('item')

    for msg in consumer:
        url = msg.value.get("url")
        platform = msg.value.get("platform")
        print(f"收到任务: {platform} {url}")
        if platform in CRAWLER_MAP:
            data = CRAWLER_MAP[platform](url)


        else:
            print(f"未找到对应爬虫: {platform}")



