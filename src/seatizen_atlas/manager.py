from pathlib import Path

from ..utils.constants import SEATIZEN_ATLAS_DOI, SEATIZEN_ATLAS_GPKG

from ..zenodo_api.token import ZenodoAPI
from ..sql_connector.connector import SQLiteConnector

class SeatizenManager:
    def __init__(self, config, seatizen_folder_path, from_local, force_regenerate):
        
        # Config
        self.config = config
        # TODO Add metadata

        # Bool.
        self.from_local = from_local
        self.force_regenerate = force_regenerate

        # Path.
        self.seatizen_folder_path = Path(seatizen_folder_path)
        self.seatizen_atlas_gpkg = Path(self.seatizen_folder_path, SEATIZEN_ATLAS_GPKG)
        self.sql_connector = SQLiteConnector(self.seatizen_atlas_gpkg)

        # TODO Add exporter.

        # TODO Add importer.

        self.setup()

    def setup(self):
        
        # Create folder if not exists.
        self.seatizen_folder_path.mkdir(exist_ok=True, parents=True)

        # Clean folder if we download from zenodo or if we force to regenerate.
        if self.force_regenerate or not self.from_local:
            self.clean_seatizen_folder()
        
        # Download data if we don't force to regenerate.
        if not self.force_regenerate and not self.from_local:
            
            # Get last version information.
            version_json = ZenodoAPI.get_version_from_doi(SEATIZEN_ATLAS_DOI)

            # Download data.
            ZenodoAPI.download_manager_without_token(version_json["files"], self.seatizen_folder_path, ".", SEATIZEN_ATLAS_DOI)
        
        # Try to figure out if we have a gpkg file.
        if not Path.exists(self.seatizen_atlas_gpkg) or not self.seatizen_atlas_gpkg.is_file():
            print("Generating base gpkg file.")
            self.sql_connector.generate()

    def import_session(self, session: Path):
        pass
    
    def export_csv(self):


        pass

    def clean_seatizen_folder(self):
        
        for file in self.seatizen_folder_path.iterdir():
            file.unlink()


    def publish(self):
        if self.from_local: 
            print("Work from local, don't publish data on zenodo.")
            return
    