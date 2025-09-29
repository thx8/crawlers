from datetime import datetime
from utils.minio_client import upload_file
from utils.webdriver import setup_driver
import time

# 截屏函数
def take_screenshot(item):
    driver = setup_driver()
    try:
        driver.get(item['itemURL'])
        time.sleep(5)
        # 设置窗口大小以确保完整截图
        driver.set_window_size(1920, 1080)
        # 生成文件名，包含时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{item['itemId']}_{timestamp}.png"
        # 截屏到内存
        screenshot = driver.get_screenshot_as_png()
        upload_file(filename,screenshot,'image/png')
        print(f"Screenshot uploaded to MinIO: {filename}")
    except Exception as e:
        print(f"Error processing screenshot for {item['itemURL']}: {str(e)}")
    finally:
        driver.quit()