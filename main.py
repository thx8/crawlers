from consumers.item_consumer import run_item_consumer
from consumers.screenshot_consumer import run_screen_consumer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """主函数，启动 Kafka 消费者并持续监听消息"""
    try:
        screen_consumer = run_screen_consumer()
        # item_consumer = run_item_consumer()
    except KeyboardInterrupt:
        logger.info("消费者被中断，正在关闭...")
    except Exception as e:
        logger.error(f"消费者运行错误: {str(e)}")


if __name__ == "__main__":
    main()