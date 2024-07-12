import pandas as pd
from tqdm import tqdm
from shapely import wkb
import geopandas as gpd
from pathlib import Path
from datetime import datetime

from ..sql_connector.sc_connector import SQLiteConnector
from ..sql_connector.sc_base_dto import  DepositManager, FrameManager
from ..sql_connector.sc_multilabel_dto import GeneralMultilabelManager
from ..darwincore.d_manager import DarwinCoreManager


class AtlasExport:

    def __init__(self, seatizen_atlas_gpkg: Path, seatizen_folder_path: Path) -> None:
        
        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        self.seatizen_folder_path = seatizen_folder_path
        
        # SQL connector.
        self.sql_connector = SQLiteConnector()
    

    def session_doi_csv(self) -> None:
        """ Generate a csv file to map doi and session_name. """
        session_doi_file = Path(self.seatizen_folder_path, "session_doi.csv")
        print(f"Generate {session_doi_file}")

        deposit_manager = DepositManager()
        
        list_deposit_data = []
        deposit_header = ["session_name", "place", "date", "have_raw_data", "have_processed_data", "doi"]
        for d in deposit_manager.get_deposits():
            list_deposit_data.append([d.session_name, d.place, d.date, d.have_raw_data, d.have_processed_data, f"https://doi.org/10.5281/zenodo.{d.doi}"])
                
        df_deposits = pd.DataFrame(list_deposit_data, columns=deposit_header)
        df_deposits.to_csv(session_doi_file, index=False)


    def metadata_images_csv(self) -> None: # !FIXME Doesn't support multiple model
        """ Generate a csv file with all information about frames. """
        metadata_images_file = Path(self.seatizen_folder_path, "metadata_images.csv")
        print(f"Generate {metadata_images_file}")

        frameManager = FrameManager()
        generalMultilabelManager = GeneralMultilabelManager()

        class_name = list(map(lambda x: getattr(x, "name"), generalMultilabelManager.class_ml))
        df_header = "OriginalFileName,FileName,relative_file_path,frames_doi,GPSLatitude,GPSLongitude,GPSAltitude,GPSRoll,GPSPitch,GPSTrack,GPSDatetime,prediction_doi".split(",") + class_name
        data = []
        for frame in tqdm(frameManager.retrieve_frames()):
            predictions_for_frame, pred_doi = generalMultilabelManager.get_predictions_from_frame_id(frame.id)

            data.append([
                frame.original_filename,
                frame.filename,
                frame.relative_path,
                f"https://doi.org/10.5281/zenodo.{frame.version_doi}",
                frame.gps_latitude,
                frame.gps_longitude,
                frame.gps_altitude,
                frame.gps_roll,
                frame.gps_pitch,
                frame.gps_track,
                frame.gps_datetime,
                f"https://doi.org/10.5281/zenodo.{pred_doi}"
            ]+[predictions_for_frame[cls_name] for cls_name in class_name])
        
        df_data = pd.DataFrame(data, columns=df_header)
        df_data.to_csv(metadata_images_file, index=False)
        

    def metadata_annotation_csv(self) -> None:
        metadata_annotation_file = Path(self.seatizen_folder_path, "metadata_annotation.csv")
        print(f"Generate {metadata_annotation_file}")
        
        generalMultilabelManager = GeneralMultilabelManager()
        all_labels = ["FileName", "frame_doi", "annotation_date", "relative_file_path"] + list(generalMultilabelManager.labelIdMapByLabelName)

        data = {}
        for value, annotation_date, frame_name, relative_file_path, frame_doi, multilabel_label_name in generalMultilabelManager.get_latest_annotations():
            if frame_name not in data: data[frame_name] = {} 
            if "annotation_date" not in data[frame_name]: data[frame_name]["annotation_date"] = annotation_date

            d1, d2 = datetime.strptime(annotation_date, "%Y-%m-%d %H:%M:%S"), datetime.strptime(data[frame_name]["annotation_date"], "%Y-%m-%d %H:%M:%S")
            if max([d1, d2]) == d1: data[frame_name]["annotation_date"] = annotation_date
            
            data[frame_name][multilabel_label_name] = str(value)
            data[frame_name]["frame_doi"] = frame_doi
            data[frame_name]["relative_file_path"] = relative_file_path


        # Convert the dictionary to a DataFrame
        df = pd.DataFrame.from_dict(data, orient='index').reset_index().rename(columns={'index': 'FileName'}).fillna("-1")

        # Ensure all target columns are in the DataFrame, fill missing columns with -1
        for col in all_labels:
            if col not in df.columns:
                df[col] = "-1"

        # Reorder the DataFrame to match the target columns
        df = df[all_labels]

        df.to_csv(metadata_annotation_file, index=False)


    def darwincore_annotation_csv(self) -> None:
        darwincore_annotation_file = Path(self.seatizen_folder_path, "darwincore_annotation.zip")
        print(f"Generate {darwincore_annotation_file}")

        general_ml_manager = GeneralMultilabelManager()
        
        darwincoreManager = DarwinCoreManager(darwincore_annotation_file)
        darwincoreManager.create_darwincore_package(general_ml_manager.get_all_ml_annotations_session())


    def global_map_shp(self) -> None:
        """ Lighter geopackage to resume all trajectory. """
        global_map_file = Path(self.seatizen_folder_path, "global_map.gpkg")
        print(f"Generate {global_map_file}")

        depositManager = DepositManager()

        # Extract geometries and names
        geometries, names = [], []
        for deposit in depositManager.get_deposits():
            polygon = wkb.loads(deposit.footprint)
            if polygon.area == 0: continue
            geometries.append(polygon)
            names.append(deposit.session_name)

        # Create a GeoDataFrame with geometry and name
        gdf = gpd.GeoDataFrame({'name': names, 'geometry': geometries})
        gdf.set_crs(epsg=4326, inplace=True)
        gdf.to_file(global_map_file, driver="GPKG")