from pathlib import Path

from ..sql_connector.connector import SQLiteConnector

class AtlasExport:

    def __init__(self, seatizen_atlas_gpkg: Path, seatizen_folder_path: Path) -> None:
        
        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        self.seatizen_folder_path = seatizen_folder_path
        
        # SQL connector.
        self.sql_connector = SQLiteConnector()
    

    def session_doi_csv(self) -> None:
        session_doi_file = Path(self.seatizen_folder_path, "session_doi.csv")
        print(f"Generate {session_doi_file}")



    def metadata_images_csv(self) -> None:
        metadata_images_file = Path(self.seatizen_folder_path, "metadata_images.csv")
        print(f"Generate {metadata_images_file}")


    def metadata_annotation_csv(self) -> None:
        metadata_annotation_file = Path(self.seatizen_folder_path, "metadata_annotation.csv")
        print(f"Generate {metadata_annotation_file}")


    def darwincore_annotation_csv(self) -> None:
        darwincore_annotation_file = Path(self.seatizen_folder_path, "darwincore_annotation.csv")
        print(f"Generate {darwincore_annotation_file}")


    def global_map_shp(self) -> None:
        global_map_file = Path(self.seatizen_folder_path, "global_map.shp")
        print(f"Generate {global_map_file}")

