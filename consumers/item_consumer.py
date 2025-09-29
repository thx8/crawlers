from utils.kafka_client import create_consumer
from crawlers import youtube_crawler
from crawlers import reddit_crawler

CRAWLER_MAP = {
    "Youtube": youtube_crawler.fetch,
    'Reddit':reddit_crawler.fetch,
}
def run_item_consumer():
    consumer = create_consumer('item')

    for crowItem in consumer:
        platform = crowItem.value.get("itemSource")
        itemURL = crowItem.value.get("itemURL")
        print(f"收到任务: {platform} {itemURL}")
        if platform in CRAWLER_MAP:
            data = CRAWLER_MAP[platform](crowItem)


        else:
            print(f"未找到对应爬虫: {platform}")



