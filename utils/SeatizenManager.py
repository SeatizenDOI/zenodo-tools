import pandas as pd
from pathlib import Path
from .ZenodoUploader import ZenodoUploader

class SeatizenManager:
    def __init__(self, config):
        self.config = config
        self.metadata_image, self.mi_is_changed = None, False
        self.session_doi, self.sd_is_changed = None, False

        self.uploader = ZenodoUploader("seatizen-global", self.config)
        self.setup()

    def setup(self):
        """ Retrieve all file who need to upload. """
        for file in self.uploader.list_files():
            save_path = Path("/tmp", file["filename"])
            if file["filename"] == "session_doi.csv":
                dl_link = file["links"]["download"]
                self.uploader.get_file_data(dl_link, save_path)
                self.session_doi = pd.read_csv(save_path)
            
            elif file["filename"] == "metadata_image.csv":
                dl_link = file["links"]["download"]
                self.uploader.get_file_data(dl_link, save_path)
                self.metadata_image = pd.read_csv(save_path)
        

    def add_to_metadata_image(self, predictions_gps):
        self.mi_is_changed = True


    def add_to_session_doi(self, session_name, doi):
        self.session_doi = pd.concat([self.session_doi, pd.DataFrame([{"session_name": session_name, "doi": doi}])])   
        self.sd_is_changed = True
    
    def save_and_published(self):
        print(self.session_doi)