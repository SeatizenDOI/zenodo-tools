import pandas as pd
from pathlib import Path

from ..sql_connector.sc_connector import SQLiteConnector
from ..sql_connector.sc_base_dto import Deposit, DepositManager


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

        deposit_manager = DepositManager()
        
        list_deposit_data = []
        deposit_header = ["session_name", "place", "date", "have_raw_data", "have_processed_data", "doi"]
        for d in deposit_manager.get_deposits():
            list_deposit_data.append([d.session_name, d.place, d.date, d.have_raw_data, d.have_processed_data, f"https://zenodo.org/records/{d.doi}"])
                
        df_deposits = pd.DataFrame(list_deposit_data, columns=deposit_header)
        df_deposits.to_csv(session_doi_file, index=False)


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
