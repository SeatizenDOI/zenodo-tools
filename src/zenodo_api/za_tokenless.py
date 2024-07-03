import shutil
import zipfile
import requests
from pathlib import Path

from ..utils.lib_tools import md5
from ..utils.constants import ZENODO_LINK_WITHOUT_TOKEN

from .za_base_function import file_downloader



def download_manager_without_token(files: list, output_folder: Path, session_name: str, doi: str) -> None:
    """ Manage to download files without token. """
    path_zip_session = Path(output_folder, session_name, "ZIP")
    path_zip_session.mkdir(exist_ok=True, parents=True)

    for file in files:

        path_tmp_file = Path(path_zip_session, file["key"])
        url = f"{ZENODO_LINK_WITHOUT_TOKEN}/{doi}/files/{file['key']}/content"
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


def get_version_from_doi(doi: str) -> dict:
    """ Retrieve all information about a session with a doi. """
    r = requests.get(f"{ZENODO_LINK_WITHOUT_TOKEN}/{doi}")

    version_json = {}
    if r.status_code == 404:
        print(f"Cannot access to {doi}. Error 404")
    else:
        version_json = r.json()
    
    return version_json


def get_version_from_session_name(session_name: str) -> dict:
    """ Retrieve last version about a session with a session_name. """

    query = f'q=metadata.identifiers.identifier:"urn:{session_name}"'
    r = requests.get(f"{ZENODO_LINK_WITHOUT_TOKEN}?{query}")

    version_json = {}
    if r.status_code == 404:
        print(f"Cannot access to {session_name}. Error 404")
        return version_json
    
    # Try to acces version. If all is good we have just one version, but if we have more or less than one version, we have an error.
    try:
        list_version = r.json()["hits"]["hits"]
        if len(list_version) > 1:
            print("Retrieve more than one version, abort.")
        elif len(list_version) == 0:
            print(f"No version found for {session_name}.")
        else:
            version_json = list_version[0]
    except:
        print(f"Cannot get version for {session_name}.")
    
    return version_json

def get_all_versions_from_session_name(session_name: str) -> list:
    """ Retrieve all versions about a session with a session_name. """

    query = f'q=metadata.identifiers.identifier:"urn:{session_name}"&allversions=true'
    r = requests.get(f"{ZENODO_LINK_WITHOUT_TOKEN}?{query}")

    version_json = []
    if r.status_code == 404:
        print(f"Cannot access to {session_name}. Error 404")
        return version_json
    
    # Try to access version. If all is good we have just one conceptrecid, else we have a problem.
    try:
        list_version = r.json()["hits"]["hits"]

        if len(list_version) == 0:
            print(f"No version found for {session_name}.")
            return version_json

        conceptrecids = set(map(lambda version: version['conceptrecid'], list_version))
        if len(conceptrecids) > 1:
            print("Retrieve more than one deposit, abort.")
        else:
            version_json = list_version

    except:
        print(f"Cannot get version for {session_name}.")
    
    return version_json