from utils.kafka_client import create_consumer
from utils.scrennshot import take_screenshot
import json

def run_screen_consumer():
    consumer = create_consumer('screenshot')
    consumer.subscribe(['screenshots-data-test'])
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
                take_screenshot(value)
                print(f"Received message: {value}")
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
    except KeyboardInterrupt:
        print("Stopping consumer...")
    finally:
        consumer.close()
