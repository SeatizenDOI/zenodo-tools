from pathlib import Path

from .sa_importer import AtlasImport
from .sa_exporter import AtlasExport
from .sa_metadata import build_metadata
from .sa_tools import get_annotation_type_from_opt, AnnotationType

from ..utils.constants import SEATIZEN_ATLAS_DOI, SEATIZEN_ATLAS_GPKG

from ..zenodo_api.za_token import ZenodoAPI
from ..zenodo_api.za_tokenless import download_manager_without_token, get_version_from_doi

from ..sql_connector.sc_connector import SQLiteConnector

class AtlasManager:
    def __init__(self, config: dict, seatizen_folder_path: str, from_local: bool, force_regenerate: bool) -> None:
        
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

    def setup(self) -> None:
        
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

    def import_session(self, session: Path) -> None:
        self.importer.import_seatizen_session(session)

    
    def export_csv(self) -> None:
        print("\t\t")
        self.exporter.session_doi_csv()
        self.exporter.metadata_images_csv()
        # self.exporter.metadata_annotation_csv()
        # self.exporter.darwincore_annotation_csv()
        self.exporter.global_map_shp()


    def clean_seatizen_folder(self) -> None:
        for file in self.seatizen_folder_path.iterdir():
            file.unlink()


    def load_annotation(self, opt_annotation_path: str, opt_annotation_type: str) -> None:
        """ Add annotation in database from a file or a folder of csv. If image not found or multiple image found do nothing. """
        
        print("\n\nfunc: Preprocess to load annotations in database.")
        annotation_path = Path(opt_annotation_path)
        if not Path.exists(annotation_path):
            print(f"[WARNING] Path {annotation_path} doesn't exist.")
            return

        annotation_type = get_annotation_type_from_opt(opt_annotation_type)

        list_files = []
        if annotation_path.is_file():
            list_files.append(annotation_path)
        elif annotation_path.is_dir():
            list_files = list(annotation_path.iterdir())
        else:
            print(f"[WARNING] {annotation_path} is not a file or a folder.")
            return # Argument provide is not a file or a folder.

        for file in list_files:
            if file.suffix.lower() != ".csv": 
                print(f"File {file} is not a csv file.")

            if annotation_type == AnnotationType.MULTILABEL:
                self.importer.multilabel_annotation_importer(file)



    def publish(self, metadata_json_path) -> None:
        if self.from_local: 
            print("Work from local, don't publish data on zenodo.")
            return
        elif self.config == {}:
            print("Config file not found. We cannot processed.")
            return

        metadata = build_metadata(metadata_json_path)

        zenodoAPI = ZenodoAPI("seatizen-atlas", self.config_json)

        # Previous files to not propagate.
        previous_files = zenodoAPI.list_files()

        zenodoAPI.add_new_version_to_deposit(self.seatizen_folder_path, metadata, restricted_files=previous_files)