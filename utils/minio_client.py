import io

from minio import Minio
from minio.error import S3Error
import config as all_config

def create_minio_client(bucket_name):
    client = Minio(
        all_config.MINIO_SERVERS,
        access_key= all_config.MINIO_ACCESS_KEY,
        secret_key= all_config.MINIO_SECRET_KEY,
        secure= all_config.MINIO_SECURE
    )

    # 检查 bucket 是否存在，不存在则创建
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Bucket {bucket_name} created")
        else:
            print(f"Bucket {bucket_name} already exists")
    except S3Error as e:
        print(f"MinIO error: {str(e)}")
        raise
    return client


def upload_file(filename, file, content_type,bucket_name):
    # 校验参数
    try:
        content_type = validate_content_type(content_type)
    except ValueError as e:
        print(f"上传失败，参数校验错误: {e}")
        return False

    screenshot_stream = io.BytesIO(file)
    minio_client = create_minio_client(bucket_name)
    minio_client.put_object(
        bucket_name,
        filename,
        screenshot_stream,
        length=len(file),
        content_type=content_type
    )

def validate_content_type(content_type):
    """校验内容类型"""
    valid_types = [
        "image/jpeg", "image/png", "image/gif",
        "video/mp4", "video/mpeg", "video/webm"
    ]
    if not content_type or not isinstance(content_type, str):
        raise ValueError("内容类型不能为空且必须是字符串")
    if content_type not in valid_types:
        raise ValueError(f"无效的内容类型: {content_type}，支持的类型: {', '.join(valid_types)}")
    return content_type