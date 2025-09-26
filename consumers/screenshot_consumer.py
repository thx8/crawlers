from crowbar_crawler.utils.kafka_client import create_consumer
from crowbar_crawler.utils.scrennshot import take_screenshot

def run_screen_consumer():
    consumer = create_consumer('screenshot')

    for msg in consumer:
        url = msg.value.get("url")
        print(f"收到 URL: {url}")

        take_screenshot(url)
