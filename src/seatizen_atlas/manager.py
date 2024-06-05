from pathlib import Path

from .metadata import build_metadata
from .importer import AtlasImport
from .exporter import AtlasExport


from ..utils.constants import SEATIZEN_ATLAS_DOI, SEATIZEN_ATLAS_GPKG

from ..zenodo_api.token import ZenodoAPI
from ..zenodo_api.tokenless import download_manager_without_token, get_version_from_doi

from ..sql_connector.connector import SQLiteConnector

class AtlasManager:
    def __init__(self, config: dict, seatizen_folder_path: str, from_local: bool, force_regenerate: bool):
        
        # Config
        self.config = config

        # Bool.
        self.from_local = from_local
        self.force_regenerate = force_regenerate

        # Path.
        self.seatizen_folder_path = Path(seatizen_folder_path)
        self.seatizen_atlas_gpkg = Path(self.seatizen_folder_path, SEATIZEN_ATLAS_GPKG)
        self.sql_connector = SQLiteConnector()

        # Seatizen session importer and exporter
        self.importer = AtlasImport(self.seatizen_atlas_gpkg)
        self.exporter = AtlasExport(self.seatizen_atlas_gpkg, self.seatizen_folder_path)
        
        self.setup()

    def setup(self):
        
        # Create folder if not exists.
        self.seatizen_folder_path.mkdir(exist_ok=True, parents=True)

        # Clean folder if we download from zenodo or if we force to regenerate.
        if self.force_regenerate or not self.from_local:
            print("Clean local seatizen atlas folder.")
            self.clean_seatizen_folder()
        
        # Download data if we don't force to regenerate.
        if not self.force_regenerate and not self.from_local:
            print("Download seatizen atlas files from zenodo.")

            # Get last version information.
            version_json = get_version_from_doi(SEATIZEN_ATLAS_DOI)

            # Download data.
            download_manager_without_token(version_json["files"], self.seatizen_folder_path, ".", SEATIZEN_ATLAS_DOI)
        
        # Try to figure out if we have a gpkg file.
        if not Path.exists(self.seatizen_atlas_gpkg) or not self.seatizen_atlas_gpkg.is_file():
            print("Generating base gpkg file.")
            self.sql_connector.generate(self.seatizen_atlas_gpkg)
        else:
            # If we have a file, connect with it
            self.sql_connector.connect(self.seatizen_atlas_gpkg)

    def import_session(self, session: Path):


        pass
    
    def export_csv(self):
        pass

    def clean_seatizen_folder(self):
        for file in self.seatizen_folder_path.iterdir():
            file.unlink()


    def publish(self, metadata_json_path):
        if self.from_local: 
            print("Work from local, don't publish data on zenodo.")
            return
        elif self.config == {}:
            print("Config file not found. We cannot processed.")
            return

        metadata = build_metadata(metadata_json_path)

        zenodoAPI = ZenodoAPI("", self.config)
        zenodoAPI.deposit_id = SEATIZEN_ATLAS_DOI

        # Previous files to not propagate.
        previous_files = zenodoAPI.list_files()
        print(metadata)
        print(previous_files)
        # zenodoAPI.add_new_version_to_deposit(self.seatizen_folder_path, metadata, restricted_files=previous_files)