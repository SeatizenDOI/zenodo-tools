import os
import json
import requests
from pathlib import Path

from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

from .ZenodoErrorHandler import ZenodoErrorHandler, ParsingReturnType

RESTRICTED_FILES = ["DCIM"]

class ZenodoUploader:
    

    def __init__(self, session_name, config_json):
        self.session_name = session_name
        self.deposit_id = None
        self.ACCESS_TOKEN = config_json["ACCESS_TOKEN_DEV_SEATIZEN"]
        self.ZENODO_LINK = config_json["ZENODO_LINK"]
        
        self.params = {'access_token': self.ACCESS_TOKEN}
        self.headers = {"Content-Type": "application/json"}

        self.set_deposit_id()
       
    def create_deposit_on_zenodo(self, session_tmp_folder, metadata):
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
    
    def add_new_version_to_deposit(self, temp_folder, metadata):
        print("-- Upload new data for existing version... ")
        # Get actual state of the deposit.
        deposit = self.__get_single_deposit()

        # If a version is currently edited, we discard change to create a new one.
        if deposit["state"] == "unsubmitted" and deposit["submitted"] == False or deposit["state"] == "inprogress" and deposit["submitted"] == True:
            self.__zenodo_actions_discard()
            self.set_deposit_id()
        
        # Create a new version.
        bucket_url = self.__zenodo_actions_newversion()
        
        # Remove restricted file.
        self.__remove_restricted_files()

        # Upload new files.
        self.__zenodo_upload_files(temp_folder, bucket_url)

        # Update metadata.
        self.__zenodo_send_metadata(metadata)
    
    def edit_metadata(self, metadata):
        """ Update metadata of deposit_id """
        # Get actual state of the deposit.
        deposit = self.__get_single_deposit()

        # If a version is currently edited, we discard change to edit a new one.
        if deposit["state"] == "unsubmitted" and deposit["submitted"] == False or deposit["state"] == "inprogress" and deposit["submitted"] == True:
            self.__zenodo_actions_discard()
            self.set_deposit_id()
        
        self.__zenodo_actions_edit()

        # Update metadata.
        self.__zenodo_send_metadata(metadata)

        # Publish metadata.
        self.__zenodo_actions_publish()

    def __get_single_deposit(self):
        r = requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}?access_token={self.ACCESS_TOKEN}")
        self.deposit_id = r.json()["id"]
        return r.json()

    def __remove_restricted_files(self):
        print("Removing restricted files")
        files = requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}/files?access_token={self.ACCESS_TOKEN}").json()

        for file in files:
            if file["filename"].replace(".zip", "").replace("PROCESSED_DATA_", "") in RESTRICTED_FILES:
                requests.delete(f'{self.ZENODO_LINK}/{self.deposit_id}/files/{file["id"]}', params={'access_token': self.ACCESS_TOKEN})
        

    def __zenodo_new_deposit(self):
        print("Create new deposit")
        r = requests.post(self.ZENODO_LINK, params=self.params, json={}, headers=self.headers)
        self.deposit_id = ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)
        return r.json()["links"]["bucket"]

    def __zenodo_actions_discard(self):
        print("Discard change of current version")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/discard", params=self.params, json={}, headers=self.headers)
        ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)

    def __zenodo_actions_newversion(self):
        print("Create new version")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/newversion", params=self.params, json={}, headers=self.headers)
        self.deposit_id = ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)
        return r.json()["links"]["bucket"]
    
    def __zenodo_actions_edit(self):
        print("Edit current version")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/edit", params=self.params, json={}, headers=self.headers)
        ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)
    
    def __zenodo_actions_publish(self):
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/publish", params={'access_token': self.ACCESS_TOKEN})
        self.deposit_id = ZenodoErrorHandler.parse(r)
        print("Version published")
    
    def __zenodo_send_metadata(self, metadata):
        r = requests.put(f'{self.ZENODO_LINK}/{self.deposit_id}',
                        params=self.params,
                        data=json.dumps(metadata),
                        headers=self.params
                    )
        ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)

    def __zenodo_upload_files(self, tmp_folder, bucket_url):
        print("Uploading new file")
        path_tmp = Path(tmp_folder)
        if not Path.exists(path_tmp) or not path_tmp.is_dir():
            print("\t[WARNING] TMP folder not found")
            return
        
        for file in path_tmp.iterdir():
            print(f"Send file {file.name}")
            file_size = os.stat(file).st_size
            with open(file, "rb") as f:
                with tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                    wrapped_file = CallbackIOWrapper(t.update, f, "read")
                    requests.put(f"{bucket_url}/{file.name}", data=wrapped_file, params=self.params)
    

    def set_deposit_id(self):
        """ Find deposit id with identifiers equal to session_name. If more than one deposit have the same session_name return None """
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN})
        ids = []
        for deposit in r.json():
            try:
                for identifiers in deposit["metadata"]["related_identifiers"]:
                    if identifiers["identifier"].replace("urn:", "") == self.session_name:
                        ids.append(deposit["id"])
                        break
            except:
                continue
        
        # Handle multiple case
        if len(ids) == 0:
            print(f"[WARNING] No id found for session {self.session_name}") # Only warning print
            return None
        elif len(ids) > 1:
            raise NameError(f"[WARNING] Multiple ids found for session {self.session_name}")
        else:
            self.deposit_id = ids[0]


    def get_session_info_by_id(self, deposit_id):
        """ Get deposit information with its id """
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN})
        for deposit in r.json():
            try:
                if deposit["id"] == deposit_id:
                    print(deposit)
            except:
                continue