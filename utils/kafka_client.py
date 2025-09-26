from kafka import KafkaConsumer
import json
import crowbar_crawler.config as all_config

def create_consumer(group_id):
    consumer = KafkaConsumer(
        bootstrap_servers=all_config.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )
    return consumer
