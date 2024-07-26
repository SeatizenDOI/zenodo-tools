import pandas as pd
from tqdm import tqdm
import geopandas as gpd
from pathlib import Path
from shapely import Polygon, LineString

from ..darwincore.d_manager import DarwinCoreManager
from ..sql_connector.sc_connector import SQLiteConnector

from ..models.frame_model import FrameDAO
from ..models.deposit_model import DepositDAO
from ..models.ml_label_model import MultilabelLabelDAO
from ..models.ml_predictions_model import MultilabelPredictionDAO
from ..models.ml_model_model import MultilabelModelDAO, MultilabelClassDAO
from ..models.ml_annotation_model import MultilabelAnnotationDAO, MultilabelAnnotationSessionDAO

class AtlasExport:

    def __init__(self, seatizen_atlas_gpkg: Path, seatizen_folder_path: Path) -> None:
        
        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        self.seatizen_folder_path = seatizen_folder_path
        
        # SQL connector.
        self.sql_connector = SQLiteConnector()

        # Manager.
        self.deposit_manager = DepositDAO()
        self.frames_manager = FrameDAO()
        self.ml_model_manager = MultilabelModelDAO()
        self.ml_class_manager = MultilabelClassDAO()
        self.ml_label_manager = MultilabelLabelDAO()
        self.ml_annotation_manager = MultilabelAnnotationDAO()
        self.ml_anno_ses_manager = MultilabelAnnotationSessionDAO()
        self.ml_prediciton_manager = MultilabelPredictionDAO()
    

    def session_doi_csv(self) -> None:
        """ Generate a csv file to map doi and session_name. """
        session_doi_file = Path(self.seatizen_folder_path, "session_doi.csv")
        print(f"\n-- Generate {session_doi_file}")
       
        list_deposit_data = []
        deposit_header = ["session_name", "place", "date", "have_raw_data", "have_processed_data",
                           "doi"]
        for d in self.deposit_manager.deposits:
            list_deposit_data.append([
                d.session_name, 
                d.location, 
                d.session_date, 
                d.have_raw_data, 
                d.have_processed_data, 
                f"https://doi.org/10.5281/zenodo.{d.doi}"
                ])
                
        df_deposits = pd.DataFrame(list_deposit_data, columns=deposit_header)
        df_deposits.to_csv(session_doi_file, index=False)


    def metadata_images_csv(self) -> None:
        """ Generate a csv file with all information about frames. """
        metadata_images_file = Path(self.seatizen_folder_path, "metadata_images.csv")
        print(f"\n-- Generate {metadata_images_file}")

        data = []
        df_header = "OriginalFileName,FileName,relative_file_path,frames_doi,\
                     GPSLatitude,GPSLongitude,GPSAltitude,GPSRoll,GPSPitch,GPSTrack,\
                     GPSDatetime,GPSFix".split(',')

        for frame in tqdm(self.frames_manager.frames):
            data.append([
                frame.original_filename,
                frame.filename,
                frame.relative_path,
                f"https://doi.org/10.5281/zenodo.{frame.version.doi}",
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
        
        last_model = self.ml_model_manager.last_model
        model_class = self.ml_class_manager.get_all_class_for_ml_model(last_model)

        class_name = [a.name for a in model_class]
        df_header = "FileName,frames_doi,GPSLatitude,GPSLongitude,GPSAltitude,GPSRoll,\
                     GPSPitch,GPSTrack,GPSFix,prediction_doi".split(",") + class_name
        
        data = []
        cpt_predictions_not_found = 0
        for frame in tqdm(self.frames_manager.frames): # Can be very long but normally when we have export metadata_images.csv we allready retrieve all frames.
            
            predictions = self.ml_prediciton_manager.get_predictions_for_specific_model_and_frame_name(frame, last_model)
            if predictions == None or len(predictions) == 0:
                cpt_predictions_not_found += 1
                continue

            pred_doi = predictions[0].version.doi
            
            # Get predictions for each class in good order.
            predictions_to_add = {cls_name: None for cls_name in class_name}
            for pred in predictions:
                if pred.ml_class.name in predictions_to_add:
                    predictions_to_add[pred.ml_class.name] = pred.score


            data.append([
                frame.filename,
                f"https://doi.org/10.5281/zenodo.{frame.version.doi}",
                frame.gps_latitude,
                frame.gps_longitude,
                frame.gps_altitude,
                frame.gps_roll,
                frame.gps_pitch,
                frame.gps_track,
                frame.gps_fix,
                f"https://doi.org/10.5281/zenodo.{pred_doi}"
            ]+[s for s in predictions_to_add.values()])
        
        if len(data) == 0:
            print("[WARNING] No data to export.")
            return
        
        print(f"On {len(self.frames_manager.frames)} images, we don't found predictions for {cpt_predictions_not_found} images.")

        df_data = pd.DataFrame(data, columns=df_header)
        df_data.to_csv(ml_predictions_file, index=False)


    def metadata_multilabel_annotation_csv(self) -> None:
        metadata_annotation_file = Path(self.seatizen_folder_path, "metadata_multilabel_annotation.csv")
        print(f"\n-- Generate {metadata_annotation_file}")
        
        all_labels = ["FileName", "frame_doi", "annotation_date", "relative_file_path"] + \
                     [l.name for l in self.ml_label_manager.labels]

        data = {}
        for annotation in self.ml_annotation_manager.get_latest_annotations():
            
            frame_name = annotation.frame.filename
            annotation_date = annotation.ml_annotation_session.annotation_date
            
            data[frame_name] = {
                "annotation_date": annotation_date,
                annotation.ml_label.name: str(annotation.value),
                "frame_doi": annotation.frame.version.doi,
                "relative_file_path":  annotation.frame.relative_path
            } 


        # Convert the dictionary to a DataFrame
        df = pd.DataFrame.from_dict(data, orient='index') \
                         .reset_index() \
                         .rename(columns={'index': 'FileName'}) \
                         .fillna("-1")

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

        darwincoreManager = DarwinCoreManager(darwincore_annotation_file)
        darwincoreManager.create_darwincore_package(self.ml_anno_ses_manager.ml_annotation_session)


    def global_map_gpkg(self) -> None:
        """ Lighter geopackage to resume all trajectory. """
        global_map_file = Path(self.seatizen_folder_path, "global_footprint.gpkg")
        print(f"\n-- Generate {global_map_file}")

        # Extract geometries and names
        polygons, linestrings, names, platform = [], [], [], []
        for deposit in self.deposit_manager.deposits:
            
            if deposit.footprint == None: continue
            
            platform.append(deposit.platform)
            names.append(deposit.session_name)

            for geom in deposit.footprint.geoms:
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

        