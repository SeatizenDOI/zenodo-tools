import os
import time
import requests
import traceback

from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

from ..utils.constants import MAX_RETRY_TO_UPLOAD_DOWNLOAD_FILE

def file_downloader(url, output_file, params = {}):
    """ Download file at output_file path. """
    isDownload, max_try = False, 0
    while not isDownload:
        try:
            r = requests.get(f"{url}", stream=True, params=params)
            total = int(r.headers.get('content-length', 0))

            with open(output_file, 'wb') as file, tqdm(total=total, unit='B', unit_scale=True) as bar:
                for data in r.iter_content(chunk_size=1000):
                    size = file.write(data)
                    bar.update(size)
            
            isDownload = True
        except KeyboardInterrupt:
            raise NameError("Stop iteration")
        except:
            print(traceback.format_exc(), end="\n\n")
            max_try += 1
            if max_try >= MAX_RETRY_TO_UPLOAD_DOWNLOAD_FILE: raise NameError("Abort due to max try")
            time.sleep(0.5)


def file_uploader(url, file, params):
    """ Upload file to url"""
    isSend, max_try = False, 0
    while not isSend:
        try:
            print(f"Try number {max_try} on {MAX_RETRY_TO_UPLOAD_DOWNLOAD_FILE}")
            file_size = os.stat(file).st_size
            with open(file, "rb") as f:
                with tqdm(total=file_size, unit="B", unit_scale=True) as t:
                    wrapped_file = CallbackIOWrapper(t.update, f, "read")
                    requests.put(f"{url}/{file.name}", data=wrapped_file, params=params)
            isSend = True
        except KeyboardInterrupt:
            raise NameError("Stop upload")
        except:
            print(traceback.format_exc(), end="\n\n")
            max_try += 1
            if max_try >= MAX_RETRY_TO_UPLOAD_DOWNLOAD_FILE: raise NameError("Abort due to max try")
            time.sleep(0.5)