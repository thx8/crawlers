# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = '115.236.28.68:51117'  # 替换为你的Kafka地址
# KAFKA_GROUP_ID = 'screenshot_group'  # 替换为你的Kafka地址

# MySQL 配置
MYSQL_USER = 'your_username'  # 替换为你的MySQL用户名
MYSQL_PASSWORD = 'your_password'  # 替换为你的MySQL密码
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_DATABASE = 'crawl_db'
DATABASE_URL = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'

# minio 配置
MINIO_SERVERS = '115.236.28.68:51118'
MINIO_ACCESS_KEY = 'EC1ibQVWWJvq3hsT'
MINIO_SECRET_KEY = 'dEszkoevTt4fA3i5LGq1gi3cSsciXJrE'
MINIO_BUCKET_NAME = 'screenshots-test'
MINIO_SECURE = False


# 支持的平台爬取
CRAWL_PLATFORM = ['youtube','twitter','tiktok','reddit']