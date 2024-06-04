import shutil
import zipfile
import requests
from pathlib import Path

from ..utils.lib_tools import md5
from .base_function import file_downloader


def download_manager_without_token(files, output_folder, session_name, doi):
    """ Manage to download files without token. """
    path_zip_session = Path(output_folder, session_name, "ZIP")
    path_zip_session.mkdir(exist_ok=True, parents=True)

    for file in files:

        path_tmp_file = Path(path_zip_session, file["key"])
        url = f"https://zenodo.org/api/records/{doi}/files/{file['key']}/content"
        print(f"\nWorking with: {path_tmp_file}")
        file_downloader(url, path_tmp_file)

        # Retry while checksum is different.
        while md5(path_tmp_file) != file["checksum"].replace("md5:", ""):
            print(f"[WARNING] Checksum error when downloading {path_tmp_file}. We retry.")
            path_tmp_file.unlink()
            file_downloader(url, path_tmp_file)

        # Extract file in directory.
        path_to_unzip_or_move = Path(output_folder, session_name)
        if ".zip" not in file["key"]:
            print(f"Move {path_tmp_file} to {path_to_unzip_or_move}.")
            shutil.move(path_tmp_file, Path(path_to_unzip_or_move, file["key"]))
        else:
            if "DCIM" in file["key"]:
                path_to_unzip_or_move = Path(output_folder, session_name, "DCIM")
            elif "PROCESSED_DATA" in file["key"]:
                folder_name = file["key"].replace(".zip", "").replace("PROCESSED_DATA_", "")
                path_to_unzip_or_move = Path(output_folder, session_name, "PROCESSED_DATA", folder_name)
            else:
                path_to_unzip_or_move = Path(output_folder, session_name, file["key"].replace(".zip", ""))
            
            print(f"Unzip {path_tmp_file} to {path_to_unzip_or_move}.")
            with zipfile.ZipFile(path_tmp_file, 'r') as zip_ref:
                zip_ref.extractall(path_to_unzip_or_move)
            

    # Delete zip file and folder
    print(f"\nRemove {path_zip_session} folder.")
    for file in path_zip_session.iterdir():
        file.unlink()
    path_zip_session.rmdir()


def get_version_from_doi(doi):
    """ Retrieve all information about a session with a doi. """
    r = requests.get(f"https://zenodo.org/api/records/{doi}")

    version_json = {}
    if r.status_code == 404:
        print(f"Cannot access to {doi}. Error 404")
    else:
        version_json = r.json()
    
    return version_json