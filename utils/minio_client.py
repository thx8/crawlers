import io

from minio import Minio
from minio.error import S3Error
import crowbar_crawler.config as all_config

def create_minio_client():
    client = Minio(
        all_config.MINIO_SERVERS,
        access_key= all_config.MINIO_ACCESS_KEY,
        secret_key= all_config.MINIO_SECRET_KEY,
        secure= all_config.MINIO_SECURE
    )

    # 检查 bucket 是否存在，不存在则创建
    try:
        if not client.bucket_exists(all_config.MINIO_BUCKET_NAME):
            client.make_bucket(all_config.MINIO_BUCKET_NAME)
            print(f"Bucket {all_config.MINIO_BUCKET_NAME} created")
        else:
            print(f"Bucket {all_config.MINIO_BUCKET_NAME} already exists")
    except S3Error as e:
        print(f"MinIO error: {str(e)}")
        raise
    return client


def upload_file(filename, screenshot,content_type):
    screenshot_stream = io.BytesIO(screenshot)
    minio_client = create_minio_client()
    minio_client.put_object(
        all_config.MINIO_BUCKET_NAME,
        filename,
        screenshot_stream,
        length=len(screenshot),
        content_type=content_type
    )