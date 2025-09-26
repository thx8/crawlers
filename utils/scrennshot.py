from datetime import datetime
from minio_client import upload_file
from webdriver import setup_driver

# 截屏函数
def take_screenshot(url):
    driver = setup_driver()
    try:
        driver.get(url)
        # 设置窗口大小以确保完整截图
        driver.set_window_size(1920, 1080)
        # 生成文件名，包含时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        # 截屏到内存
        screenshot = driver.get_screenshot_as_png()
        upload_file(filename,screenshot,'image/png')
        print(f"Screenshot uploaded to MinIO: {filename}")
    except Exception as e:
        print(f"Error processing screenshot for {url}: {str(e)}")
    finally:
        driver.quit()