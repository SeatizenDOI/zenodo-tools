import pandas as pd
from pathlib import Path

from .lib_tools import md5
from .ZenodoAPI import ZenodoAPI
from .constants import TMP_PATH_MANAGER, SEATIZEN_MANAGER_FILES, SESSION_DOI_CSV, METADATA_IMAGE_CSV

class SeatizenManager:
    def __init__(self, config, seatizen_folder_path, from_local, force_regenerate):
        self.config = config

        self.seatizen_folder_path = Path(seatizen_folder_path)
        self.from_local = from_local
        self.force_regenerate = force_regenerate

        self.setup()

    def setup(self):
        
        # Create folder if not exists
        self.seatizen_folder_path.mkdir(exist_ok=True, parents=True)

        if self.force_regenerate:
            self.clean_seatizen_folder()
        
        elif not self.force_regenerate and not self.from_local:
            # Download data.
            pass
        
    
    def clean_seatizen_folder(self):
        
        for file in self.seatizen_folder_path.iterdir():
            file.unlink()

