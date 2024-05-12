import os
import json
import requests
import traceback
import time
from pathlib import Path

from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

from .constants import MAX_RETRY_TO_UPLOAD_FILE, NB_VERSION_TO_FETCH
from .ZenodoErrorHandler import ZenodoErrorHandler, ParsingReturnType

RESTRICTED_FILES = ["DCIM"]

class ZenodoUploader:
    

    def __init__(self, session_name, config_json):
        self.session_name = session_name
        self.deposit_id = None
        self.ACCESS_TOKEN = config_json["ACCESS_TOKEN_ZENODO_SEATIZEN"]
        self.ZENODO_LINK = config_json["ZENODO_LINK"]
        
        self.params = {'access_token': self.ACCESS_TOKEN}
        self.headers = {"Content-Type": "application/json"}

        self.set_deposit_id() # Try to get current id of the session.


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
        
        # Publish.
        self.__zenodo_actions_publish()


    def edit_metadata(self, metadata):
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


    def __get_single_deposit(self):
        """ Get data from a deposit (last version). """
        r = requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}?access_token={self.ACCESS_TOKEN}")
        self.deposit_id = r.json()["id"]
        return r.json()

    def list_files(self):
        """ List all files for a session. """
        return requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}/files?access_token={self.ACCESS_TOKEN}").json()
    
    
    def get_file_data(self, link, output_file):
        """ Save file at output_file path. """
        r = requests.get(f"{link}", params={'access_token': self.ACCESS_TOKEN}, stream=True)
        with open(output_file, mode="wb") as file:
            for chunk in r.iter_content(chunk_size=10 * 1024):
                file.write(chunk)

    def __remove_restricted_files(self):
        """ Remove restricted file before publish new version. """
        print("Removing restricted files")
        files = self.list_files()

        for file in files:
            file_name = file["filename"].replace(".zip", "").replace("PROCESSED_DATA_", "") # Remove .zip and middle folder name.
            for f in RESTRICTED_FILES: 
                if f in file_name: # Exemple: DCIM in DCIM_2
                    requests.delete(f'{self.ZENODO_LINK}/{self.deposit_id}/files/{file["id"]}', params={'access_token': self.ACCESS_TOKEN})
                    continue # Get out of for because no need to check extra match if we have already delete file
        

    def __zenodo_new_deposit(self):
        """ Create a new deposit. """
        print("Create new deposit")
        r = requests.post(self.ZENODO_LINK, params=self.params, json={}, headers=self.headers)
        self.deposit_id = ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)
        return r.json()["links"]["bucket"]


    def __zenodo_actions_discard(self):
        """ Discard change of current version. """
        print("Discard change of current version")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/discard", params=self.params, json={}, headers=self.headers)
        ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)


    def __zenodo_actions_newversion(self):
        """ Create new version. Return the bucket_url to upload new files. """
        print("Create new version.")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/newversion", params=self.params, json={}, headers=self.headers)
        self.deposit_id = ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)
        return r.json()["links"]["bucket"]


    def __zenodo_actions_edit(self):
        """ Edit current version. """
        print("Edit current version.")
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/edit", params=self.params, json={}, headers=self.headers)
        ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)
    

    def __zenodo_actions_publish(self):
        """ Publish current version. Warning cannot remove file after publish. """
        r = requests.post(f"{self.ZENODO_LINK}/{self.deposit_id}/actions/publish", params={'access_token': self.ACCESS_TOKEN})
        self.deposit_id = ZenodoErrorHandler.parse(r)
        print("Version published.")


    def __zenodo_send_metadata(self, metadata):
        """ Upload metadata for a zenodo version. """
        r = requests.put(f'{self.ZENODO_LINK}/{self.deposit_id}',
                        params=self.params,
                        data=json.dumps(metadata),
                        headers=self.params
                    )
        ZenodoErrorHandler.parse(r, ParsingReturnType.NONE)


    def __zenodo_upload_files(self, tmp_folder, bucket_url):
        """ Upload a folder of file to specific version. Warning, don't check if the total size is < 50 Go (Zenodo limit)"""
        print("Uploading new file")
        path_tmp = Path(tmp_folder)
        if not Path.exists(path_tmp) or not path_tmp.is_dir():
            print("\t[WARNING] TMP folder not found")
            return
        
        for file in path_tmp.iterdir():
            print(f"Send file {file.name}")
            isSend, max_try = False, 0
            while not isSend:
                try:
                    file_size = os.stat(file).st_size
                    with open(file, "rb") as f:
                        with tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                            wrapped_file = CallbackIOWrapper(t.update, f, "read")
                            requests.put(f"{bucket_url}/{file.name}", data=wrapped_file, params=self.params)
                    isSend = True
                except KeyboardInterrupt:
                    isSend = True
                    raise NameError("Stop upload")
                except:
                    print(traceback.format_exc(), end="\n\n")
                    max_try += 1
                    if max_try >= MAX_RETRY_TO_UPLOAD_FILE: raise NameError("Abort due to max try")
                    time.sleep(0.5)


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


    def get_all_version_ids_for_deposit(self):
        """ Return a list of ids for raw data version and a list of id for processed data version for a specific session"""
        conceptrecid = self.get_conceptrecid_specific_deposit()
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN, 'size': NB_VERSION_TO_FETCH, "all_versions": True, 'q': f"conceptrecid:{conceptrecid}"})

        if len(r.json()) == 0:
            raise NameError("No global id found")

        raw_data_ids, processed_data_ids = [], []
        for deposit in r.json():
            if "RAW_DATA" in deposit["metadata"]["version"]:
                raw_data_ids.append(deposit["id"])
            elif "PROCESSED_DATA" in deposit["metadata"]["version"]:
                processed_data_ids.append(deposit["id"])
            else:
                print(f"No match for version {deposit['metadata']['version']}")
        return raw_data_ids, processed_data_ids
        

    def get_conceptrecid_specific_deposit(self):
        """ Extract conceptrecid from a deposit"""
        r = requests.get(f"{self.ZENODO_LINK}/{self.deposit_id}?access_token={self.ACCESS_TOKEN}")
        return r.json()["conceptrecid"]
    
    
    def clean_draft_no_version(self):
        """ Delete all draft version. """
        r = requests.get(self.ZENODO_LINK, params={'access_token': self.ACCESS_TOKEN, 'size': NB_VERSION_TO_FETCH})
        for deposit in r.json():
            try:
                if deposit["state"] == "unsubmitted" and deposit["submitted"] == False and deposit["title"] == "":
                    print("Delete draft version")
                    r2 = requests.post(deposit["links"]["discard"], params=self.params, json={}, headers=self.headers)
                    ZenodoErrorHandler.parse(r2, ParsingReturnType.ALL)

            except:
                continue