import sys
sys.path.append('.')
from drive_downloader import download_drive_link
import traceback

try:
    print("Starting download...")
    res = download_drive_link("https://drive.google.com/drive/folders/1VbbmCsnyAdzB4DqoRfhsDpvhmU7NV0lU")
    print(res)
except Exception as e:
    traceback.print_exc()
