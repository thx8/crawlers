from utils.kafka_client import create_consumer
from crawlers import youtube_crawler
from crawlers import reddit_crawler
from crawlers import twitter_crawler
from utils.sql import update
import json
CRAWLER_MAP = {
    "Youtube": youtube_crawler.fetch,
    'Reddit':reddit_crawler.fetch,
    # 'twitter':twitter_crawler.fetch,
}
def run_item_consumer():
    consumer = create_consumer('item')
    consumer.subscribe(['item'])
    try:
        while True:
            msg = consumer.poll(timeout=1.0)  # Poll for messages
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            try:
                value = json.loads(msg.value().decode('utf-8'))
                platform = value["itemSource"]
                data = CRAWLER_MAP[platform](value)
                print(data)
                # update(data)
                print(f"Received message: {value}")
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
    except KeyboardInterrupt:
        print("Stopping consumer...")
    finally:
        consumer.close()




