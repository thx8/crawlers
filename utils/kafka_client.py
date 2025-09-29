from confluent_kafka import Consumer
import json
import config as all_config

def create_consumer(group_id):
    consumer = Consumer({
        'bootstrap.servers': all_config.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': group_id,
        'auto.offset.reset': 'earliest',
    })
    return consumer
