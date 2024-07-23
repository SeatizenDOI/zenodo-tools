import pandas as pd
from tqdm import tqdm
from shapely import wkb, Polygon, LineString
import geopandas as gpd
from pathlib import Path
from datetime import datetime
import fiona

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
        print(f"\n-- Generate {session_doi_file}")

        deposit_manager = DepositManager()
        
        list_deposit_data = []
        deposit_header = ["session_name", "place", "date", "have_raw_data", "have_processed_data", "doi"]
        for d in deposit_manager.get_deposits():
            list_deposit_data.append([d.session_name, d.place, d.date, d.have_raw_data, d.have_processed_data, f"https://doi.org/10.5281/zenodo.{d.doi}"])
                
        df_deposits = pd.DataFrame(list_deposit_data, columns=deposit_header)
        df_deposits.to_csv(session_doi_file, index=False)


    def metadata_images_csv(self) -> None:
        """ Generate a csv file with all information about frames. """
        metadata_images_file = Path(self.seatizen_folder_path, "metadata_images.csv")
        print(f"\n-- Generate {metadata_images_file}")

        frameManager = FrameManager()
        data = []
        df_header = "OriginalFileName,FileName,relative_file_path,frames_doi,GPSLatitude,GPSLongitude,GPSAltitude,GPSRoll,GPSPitch,GPSTrack,GPSDatetime,GPSFix".split(',')

        for frame in tqdm(frameManager.retrieve_frames()):
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
                frame.gps_fix
            ])
        
        if len(data) == 0:
            print("[WARNING] No data to export.")
            return
        
        df_data = pd.DataFrame(data, columns=df_header)
        df_data.to_csv(metadata_images_file, index=False)
        

    def metadata_multilabel_predictions_csv(self) -> None:
        ml_predictions_file = Path(self.seatizen_folder_path, "metadata_multilabel_predictions.csv")
        print(f"\n-- Generate {ml_predictions_file} with last model add in database.")
        
        frameManager = FrameManager()
        generalMultilabelManager = GeneralMultilabelManager()
        last_model = generalMultilabelManager.get_last_multilabel_model()
        model_class = generalMultilabelManager.get_class_for_specific_model(last_model.id)

        class_name = list(map(lambda x: getattr(x, "name"), model_class))
        df_header = "FileName,frames_doi,GPSLatitude,GPSLongitude,GPSAltitude,GPSRoll,GPSPitch,GPSTrack,GPSFix,prediction_doi".split(",") + class_name
        data = []

        for frame in tqdm(frameManager.retrieve_frames_from_specific_multilabel_model(last_model.id)):
            predictions_for_frame, pred_doi = generalMultilabelManager.get_predictions_from_frame_id(frame.id)
            predictions_to_add = [predictions_for_frame[cls_name] for cls_name in class_name] if len(predictions_for_frame) != 0  else [None for _ in class_name]

            data.append([
                frame.filename,
                f"https://doi.org/10.5281/zenodo.{frame.version_doi}",
                frame.gps_latitude,
                frame.gps_longitude,
                frame.gps_altitude,
                frame.gps_roll,
                frame.gps_pitch,
                frame.gps_track,
                frame.gps_fix,
                f"https://doi.org/10.5281/zenodo.{pred_doi}"
            ]+predictions_to_add)
        
        if len(data) == 0:
            print("[WARNING] No data to export.")
            return
        
        df_data = pd.DataFrame(data, columns=df_header)
        df_data.to_csv(ml_predictions_file, index=False)


    def metadata_multilabel_annotation_csv(self) -> None:
        metadata_annotation_file = Path(self.seatizen_folder_path, "metadata_annotation.csv")
        print(f"\n-- Generate {metadata_annotation_file}")
        
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
        darwincore_annotation_file = Path(self.seatizen_folder_path, "darwincore_multilabel_annotation.zip")
        print(f"\n-- Generate {darwincore_annotation_file}")

        general_ml_manager = GeneralMultilabelManager()
        darwincoreManager = DarwinCoreManager(darwincore_annotation_file)
        
        darwincoreManager.create_darwincore_package(general_ml_manager.get_all_ml_annotations_session())


    def global_map_gpkg(self) -> None:
        """ Lighter geopackage to resume all trajectory. """
        global_map_file = Path(self.seatizen_folder_path, "global_footprint.gpkg")
        print(f"\n-- Generate {global_map_file}")

        depositManager = DepositManager()

        # Extract geometries and names
        polygons, linestrings, names, platform = [], [], [], []
        for deposit in depositManager.get_deposits():
            geometryCollection = wkb.loads(deposit.footprint)
            
            if geometryCollection == None: continue
            
            platform.append(deposit.platform)
            names.append(deposit.session_name)

            for geom in geometryCollection.geoms:
                if isinstance(geom, Polygon):
                    polygons.append(geom)
                if isinstance(geom, LineString):
                    linestrings.append(geom)

        if len(names) == 0:
            print("[WARNING] No session to export in global_map.")
            return
        
        # Create a GeoDataFrame with geometry and name
        gdf_linestrings = gpd.GeoDataFrame({'name': names, 'geometry': linestrings, 'platform': platform})
        gdf_linestrings.set_crs(epsg=4326, inplace=True)
        gdf_linestrings.to_file(global_map_file, layer='footprint_linestrings', driver="GPKG")

        gdf_polygons = gpd.GeoDataFrame({'name': names, 'geometry': polygons, 'platform': platform})
        gdf_polygons.set_crs(epsg=4326, inplace=True)
        gdf_polygons.to_file(global_map_file, layer='footprint_polygons', driver="GPKG")

        