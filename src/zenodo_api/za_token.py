import json
import shutil
import zipfile
import requests
from pathlib import Path
from datetime import datetime

from .za_error import ZenodoErrorHandler, ParsingReturnType
from .za_base_function import file_downloader, file_uploader
from ..utils.lib_tools import md5
from ..utils.constants import NB_VERSION_TO_FETCH

class ZenodoAPI:
    
    def __init__(self, session_name: str, config_json: dict) -> None:
        self.session_name = session_name
        self.deposit_id = None
        self.ACCESS_TOKEN = config_json["ACCESS_TOKEN_DEV_SEATIZEN"]
        self.ZENODO_LINK = config_json["ZENODO_DEV_LINK"]
        
        self.params = {'access_token': self.ACCESS_TOKEN}
        self.headers = {"Content-Type": "application/json"}

        if session_name != "":
            self.set_deposit_id() # Try to get current id of the session.
        

    # -- Complexe operations on deposit
    def create_deposit_on_zenodo(self, session_tmp_folder: Path, metadata: dict) -> None:
        """
            session_tmp_folder: Upload all file in tmp folder
        """
        print("-- Upload raw data... ")
 
        # Try to add record (file) to this deposit.
        bucket_url = self.__zenodo_new_deposit()

        # Upload files.
        self.__zenodo_upload_files(session_tmp_folder, bucket_url)

        # Add metadata.
        self.__zenodo_send_metadata(metadata)

        # Publish version.
        self.__zenodo_actions_publish()


    def add_new_version_to_deposit(self, temp_folder: Path, metadata: dict, 
                                   restricted_files: list = [], dontUploadWhenLastVersionIsProcessedData: bool = False) -> None:
        """ Create a new version of a deposit"""
        print("-- Upload new data for existing version... ")
        # Get actual state of the deposit.
        deposit = self.__get_single_deposit()

        # If a version is currently edited, we discard change to create a new one.
        if deposit["state"] == "unsubmitted" and deposit["submitted"] == False or deposit["state"] == "inprogress" and deposit["submitted"] == True:
            self.__zenodo_actions_discard()
            self.set_deposit_id()
        
        if dontUploadWhenLastVersionIsProcessedData: #!FIXME To delete when finishing to upload all data
            deposit = self.__get_single_deposit()
            if "PROCESSED_DATA" in deposit["metadata"]["version"]:
                raise NameError(f"We already have a processed data version: https://zenodo.org/records/{self.deposit_id}")
        
        # Create a new version.
        bucket_url = self.__zenodo_actions_newversion()
        
        # Remove restricted file.
        self.__remove_restricted_files(restricted_files)

        # Upload new files.
        self.__zenodo_upload_files(temp_folder, bucket_url)

        # Update metadata.
        self.__zenodo_send_metadata(metadata)
        
        # Publish.
        self.__zenodo_actions_publish()


    def edit_metadata(self, metadata: dict) -> None:
        """ Update metadata of deposit_id """
        # Get actual state of the deposit.
        deposit = self.__get_single_deposit()

        # If a version is currently edited, we discard change to edit a new one.
        if deposit["state"] == "unsubmitted" and deposit["submitted"] == False or deposit["state"] == "inprogress" and deposit["submitted"] == True:
            self.__zenodo_actions_discard()
            self.set_deposit_id()
        
        # Switch to edit mode.
        self.__zenodo_actions_edit()

        # Update metadata.
        self.__zenodo_send_metadata(metadata)

        # Publish metadata.
        self.__zenodo_actions_publish()


    def clean_draft_no_version(self) -> None:
        """ Delete all draft version. """
        
        deposits = self.get_all_zenodo_deposit() # !FIXME Cannot get only draft version.
        for deposit in deposits:
            try:
                if deposit["state"] == "unsubmitted" and deposit["submitted"] == False and deposit["title"] == "":
                    print(f"\nDelete draft version {deposit['id']}")
                    r2 = requests.post(deposit["links"]["discard"], params=self.params, json={}, headers=self.headers)
                    ZenodoErrorHandler.parse(r2, ParsingReturnType.ALL)

            except:
                continue

    # Update current session without deleting object
    def update_current_session(self, session_name: str) -> None:
        self.deposit_id = None
        self.session_name = session_name
        
        if session_name != "":
            self.set_deposit_id() # Try to get current id of the session.

    # Simple operation on deposit.
    def __get_single_deposit(self) -> dict:
        """ Get data from a deposit. """
        r = requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}?access_token={self.ACCESS_TOKEN}")
        self.deposit_id = r.json()["id"]
        return r.json()


    def list_files(self) -> dict:
        """ List all files for a session. """
        return requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}/files?access_token={self.ACCESS_TOKEN}").json()


    def zenodo_download_files(self, output_folder: Path) -> None:
        """ Download all file """
        self.__set_session_name()

        path_zip_session = Path(output_folder, self.session_name, "ZIP")
        path_zip_session.mkdir(exist_ok=True, parents=True)

        for file in self.list_files():

            path_tmp_file = Path(path_zip_session, file["filename"])
            print(f"\nWorking with: {path_tmp_file}")
            file_downloader(file["links"]["download"], path_tmp_file, self.params)

            # Retry while checksum is different.
            while md5(path_tmp_file) != file["checksum"]:
                print(f"[WARNING] Checksum error when downloading {path_tmp_file}. We retry.")
                path_tmp_file.unlink()
                file_downloader(file["links"]["download"], path_tmp_file, self.params)

            # Extract file in directory.
            path_to_unzip_or_move = Path(output_folder, self.session_name)
            if ".zip" not in file["filename"]:
                print(f"Move {path_tmp_file} to {path_to_unzip_or_move}.")
                shutil.move(path_tmp_file, Path(path_to_unzip_or_move, file["filename"]))
            else:
                if "DCIM" in file["filename"]:
                    path_to_unzip_or_move = Path(output_folder, self.session_name, "DCIM")
                elif "PROCESSED_DATA" in file["filename"]:
                    folder_name = file["filename"].replace(".zip", "").replace("PROCESSED_DATA_", "")
                    path_to_unzip_or_move = Path(output_folder, self.session_name, "PROCESSED_DATA", folder_name)
                else:
                    path_to_unzip_or_move = Path(output_folder, self.session_name, file["filename"].replace(".zip", ""))
                
                print(f"Unzip {path_tmp_file} to {path_to_unzip_or_move}.")
                with zipfile.ZipFile(path_tmp_file, 'r') as zip_ref:
                    zip_ref.extractall(path_to_unzip_or_move)
            

        # Delete zip file and folder
        print(f"\nRemove {path_zip_session} folder.")
        for file in path_zip_session.iterdir():
            file.unlink()
        path_zip_session.rmdir()


    def __set_session_name(self) -> None:
        """ Set session name from deposit_id """

        deposit = self.__get_single_deposit()
        try:
            for identifier in deposit["metadata"]["related_identifiers"]:
                if identifier["relation"] == "isAlternateIdentifier" and identifier["scheme"] == "urn":
                    self.session_name = identifier["identifier"].replace("urn:", "")
                    break
        except KeyError:
            raise NameError("Session name not find")


    def __remove_restricted_files(self, restricted_files: list) -> None:
        """ Remove restricted file before publish new version. """
        
        if len(restricted_files) == 0: return # No file to filter

        print("Removing restricted files")
        files = self.list_files()

        for file in files:
            file_name = file["filename"].replace(".zip", "").replace("PROCESSED_DATA_", "") # Remove .zip and middle folder name.
            for f in restricted_files: 
                if f in file_name: # Exemple: DCIM in DCIM_2
                    requests.delete(f'{self.ZENODO_LINK}/{self.deposit_id}/files/{file["id"]}', params={'access_token': self.ACCESS_TOKEN})
                    continue # Get out of for because no need to check extra match if we have already delete file
        

    def __zenodo_new_deposit(self) -> str:
        """ Create a new deposit. """
        print("Create new deposit")
        r = requests.post(self.ZENODO_LINK, params=self.params, json={}, headers=self.headers)
        self.deposit_id = ZenodoErrorHandler.parse(r)
        return r.json()["links"]["bucket"]


    def __zenodo_actions_discard(self) -> None:
        """ Discard change of current version. """
        print("Discard change of current version")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/discard", params=self.params, json={}, headers=self.headers)
        ZenodoErrorHandler.parse(r)


    def __zenodo_actions_newversion(self) -> str:
        """ Create new version. Return the bucket_url to upload new files. """
        print("Create new version.")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/newversion", params=self.params, json={}, headers=self.headers)
        self.deposit_id = ZenodoErrorHandler.parse(r)
        return r.json()["links"]["bucket"]


    def __zenodo_actions_edit(self) -> None:
        """ Edit current version. """
        print("Edit current version.")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/edit", params=self.params, json={}, headers=self.headers)
        ZenodoErrorHandler.parse(r)
    

    def __zenodo_actions_publish(self) -> None:
        """ Publish current version. Warning cannot remove file after publish. """
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/publish", params={'access_token': self.ACCESS_TOKEN})
        self.deposit_id = ZenodoErrorHandler.parse(r)
        print("Version publish.")


    def __zenodo_send_metadata(self, metadata: dict) -> None:
        """ Upload metadata for a zenodo version. """
        r = requests.put(f'{self.ZENODO_LINK}/{self.deposit_id}',
                        params=self.params,
                        data=json.dumps(metadata),
                        headers=self.headers
                    )
        ZenodoErrorHandler.parse(r)


    def __zenodo_upload_files(self, tmp_folder: Path, bucket_url: str) -> None:
        """ Upload a folder of file to specific version. Warning, don't check if the total size is < 50 Go (Zenodo limit)"""
        print("Uploading new file")
       
        if not Path.exists(tmp_folder) or not tmp_folder.is_dir():
            print("\t[WARNING] TMP folder not found")
            return
        
        for file in tmp_folder.iterdir():
            print(f"Send file {file.name}")
            file_uploader(bucket_url, file, self.params)


    def get_conceptrecid_specific_deposit(self) -> int:
        """ Extract conceptrecid from a deposit"""
        r = requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}?access_token={self.ACCESS_TOKEN}")
        return r.json()["conceptrecid"]


    # -- Operation to associate deposit to a doi or a name
    def set_deposit_id(self) -> None:
        """ Find deposit id with identifiers equal to session_name. If more than one deposit have the same session_name return None """

        query = f'metadata.identifiers.identifier:"urn:{self.session_name}" metadata.related_identifiers.identifier:"urn:{self.session_name}"'
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN, 'size': NB_VERSION_TO_FETCH, 'q': query})

        if r.status_code == 404:
            raise NameError(f"Cannot access to {self.session_name}.")
        
        deposits = r.json()
        if len(deposits) > 1:
            raise NameError("Retrieve more than one deposit, abort.")
        elif len(deposits) == 0:
            print(f"[WARNING] No id found for session {self.session_name}") # Only warning print
            return None
        else:
            self.deposit_id = deposits[0]["id"]


    def get_all_version_ids_for_deposit(self, conceptrecid: int) -> tuple[list, list]:
        """ Return a list of ids for raw data version and a list of id for processed data version for a specific session"""
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN, 'size': NB_VERSION_TO_FETCH, "all_versions": True, 'q': f"conceptrecid:{conceptrecid}"})
        if len(r.json()) == 0:
            raise NameError("No concept id found")

        raw_data_ids, processed_data_ids = [], []
        for deposit in r.json():
            version = deposit["metadata"]["version"].replace(" ", "_")
            if "RAW_DATA" in version:
                raw_data_ids.append(deposit["id"])
            elif "PROCESSED_DATA" in version:
                processed_data_ids.append(deposit["id"])
            else:
                print(f"No match for version {version}")
        return raw_data_ids, processed_data_ids


    def get_conceptrecid_from_idOrConceptrecid(self, idOrConceptrecid: int) -> int | None:
        """ Return conceptrecid from doi who can be an id or a conceptrecid """
        # Try to check if it's an id
        r = requests.get(f"{self.ZENODO_LINK}/{idOrConceptrecid}?access_token={self.ACCESS_TOKEN}")
        if r.status_code == 200:
            return r.json()["conceptrecid"]
        
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN, "all_versions": True, 'q': f"conceptrecid:{idOrConceptrecid}"})
        if len(r.json()) > 0:
            return idOrConceptrecid
        
        return None
    
    def get_all_zenodo_deposit(self, all_versions: bool = True) -> list[dict]:
        """ Grab all deposit in user zenodo account. Can also get all versions."""
        print(f"Retrieve all versions in user zenodo account in packs of {NB_VERSION_TO_FETCH}.")
        
        need_to_fetch_more, page = True, 1
        versions = []
        while need_to_fetch_more:

            start_t = datetime.now()
            request = requests.get(self.ZENODO_LINK, params={"access_token": self.ACCESS_TOKEN, 'size': NB_VERSION_TO_FETCH, "all_versions": all_versions, "page": page})
            
            print(f"Query time for page {page}: {datetime.now() - start_t} sec")
            if request.status_code == 200:
                versions = versions + request.json()
                if len(versions) % NB_VERSION_TO_FETCH == 0:
                    page += 1
                else:
                    need_to_fetch_more = False
            else:
                print(f"[WARNING] Request failed, try again for page {page}")

        return versions