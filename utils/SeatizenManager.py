import pandas as pd
from pathlib import Path

from .lib_tools import md5
from .ZenodoAPI import ZenodoAPI
from .constants import TMP_PATH_MANAGER, SEATIZEN_MANAGER_FILES, SESSION_DOI_CSV, METADATA_IMAGE_CSV

class SeatizenManager:
    def __init__(self, config, metadata):
        self.config = config
        self.metadata_json = metadata
        self.files, self.f_is_changed, self.f_path = {}, {}, {}
        self.tmp_folder = Path(TMP_PATH_MANAGER)

        self.zenodoAPI = ZenodoAPI("seatizen-global", self.config)
        self.setup()


    def setup(self):
        """ Retrieve all file who need to upload. """

        # Create tmp folder.
        self.tmp_folder.mkdir(exist_ok=True, parents=True)
        
        # Delete all previous file in case we have past files.
        self.clean_tmp_folder()

        # Get all files we want to update
        for file in self.zenodoAPI.list_files():
            filename = file["filename"]
            if filename not in SEATIZEN_MANAGER_FILES: continue

            self.f_path[filename] = Path(self.tmp_folder, filename) # Save path for filename
            self.zenodoAPI.zenodo_download_file(file["links"]["download"], self.f_path[filename]) # Download the file in tmp directory
            # Retry while checksum is different.
            while md5(self.f_path[filename]) != file["checksum"]:
                print(f"[WARNING] Checksum error when downloading {filename}. We retry.")
                self.f_path[filename].unlink()
                self.zenodoAPI.zenodo_download_file(file["links"]["download"], self.f_path[filename])

            self.f_is_changed[filename] = False # Init change variable at false
            self.files[filename] = pd.read_csv(self.f_path[filename]) # Get data
        

    def add_to_metadata_image(self, predictions_gps):
        """ Add predictions of image in metadata_image. """
        # TODO Define how to present file
        # self.files[METADATA_IMAGE_CSV] = pd.concat([self.files[METADATA_IMAGE_CSV], predictions_gps])   
        self.f_is_changed[METADATA_IMAGE_CSV] = True


    def add_to_session_doi(self, session_name, doi):
        """ Add session_name and doi in csv file. """
        self.files[SESSION_DOI_CSV] = pd.concat([self.files[SESSION_DOI_CSV], pd.DataFrame([{"session_name": session_name, "doi": doi}])])   
        self.f_is_changed[SESSION_DOI_CSV] = True


    def save_and_published(self):
        """ Save all data if changed and create a new version. """
        # Export files.
        for filename in self.f_is_changed:
            if self.f_is_changed[filename] == True:
                self.files[filename].to_csv(self.f_path[filename], index=False)
            else:
                print(f"Remove {filename} because file not change to avoid update it.")
                self.f_path[filename].unlink() # Delete file to avoid upload it if not changed
        
        self.zenodoAPI.add_new_version_to_deposit(self.tmp_folder, self.get_metadata())
        self.clean_tmp_folder()


    def get_metadata(self):
        """ Create metadata. """
        data = {
            'metadata': {
                'title': "Seatizen - Dataset Global",
                'upload_type': 'dataset',
                'description': "Raw Data, soon more information incoming",
                'access_right': 'open',
                'version': "TEST",
                'creators': self.metadata_json["creators"],
                'related_identifiers': [{'identifier': 'urn:seatizen-global', 'relation': 'isAlternateIdentifier'}],
                'language': "eng",
                'license': self.metadata_json["license"],
                'contributors': self.metadata_json['contributors']
            }
        }
        return data


    def clean_tmp_folder(self):
        """ Delete all file in tmp folder. """
        for file in self.tmp_folder.iterdir():
            print(f"Remove {file}")
            file.unlink()