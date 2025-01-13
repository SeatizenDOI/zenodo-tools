import polars as pl
from tqdm import tqdm
import geopandas as gpd
from pathlib import Path

from ..darwincore.d_manager import DarwinCoreManager
from ..sql_connector.sc_connector import SQLiteConnector

from ..models.frame_model import FrameDAO
from ..models.deposit_model import DepositLinestringDAO, DepositDAO
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
        self.deposit_linestring_manager = DepositLinestringDAO()
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
        deposit_header = {
            "session_name": pl.String, "session_doi": pl.String, "place": pl.String, 
            "date": pl.String, "raw_data": pl.UInt8, "processed_data": pl.UInt8
        }

        for d in self.deposit_manager.deposits:
            list_deposit_data.append([
                d.session_name, 
                f"https://doi.org/10.5281/zenodo.{d.doi}",
                d.location, 
                d.session_date, 
                d.have_raw_data, 
                d.have_processed_data
            ])
                
        df_deposits = pl.DataFrame(list_deposit_data, schema=deposit_header, orient="row")
        df_deposits.write_csv(session_doi_file)


    def metadata_images_csv(self) -> None:
        """ Generate a csv file with all information about frames. """
        metadata_images_file = Path(self.seatizen_folder_path, "metadata_images.csv")
        print(f"\n-- Generate {metadata_images_file}")

        data = []
        df_header = {
            "OriginalFileName": pl.String,
            "FileName": pl.String,
            "relative_file_path": pl.String,
            "frames_doi": pl.String,
            "GPSLatitude": pl.Float64,
            "GPSLongitude": pl.Float64,
            "GPSAltitude": pl.Float64,
            "GPSRoll": pl.Float64,
            "GPSPitch": pl.Float64,
            "GPSTrack": pl.Float64, 
            "GPSDatetime": pl.String,
            "GPSFix": pl.Float64
        }

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
        
        df_data = pl.DataFrame(data, schema=df_header, orient="row")
        df_data.write_csv(metadata_images_file)


    def metadata_multilabel_predictions_csv(self) -> None:
        ml_predictions_file = Path(self.seatizen_folder_path, "metadata_multilabel_predictions.csv")
        print(f"\n-- Generate {ml_predictions_file} with last model add in database.")
        
        last_model = self.ml_model_manager.last_model
        model_class = self.ml_class_manager.get_all_class_for_ml_model(last_model)

        class_name = {a.name: pl.Float64 for a in model_class}
        df_header = {
            "FileName": pl.String,
            "frames_doi": pl.String,
            "GPSLatitude": pl.Float64,
            "GPSLongitude": pl.Float64,
            "GPSAltitude": pl.Float64,
            "GPSRoll": pl.Float64,
            "GPSPitch": pl.Float64,
            "GPSTrack": pl.Float64,
            "GPSFix": pl.UInt8,
            "prediction_doi": pl.String
        } | class_name
        
        data = []
        cpt_predictions_not_found = 0
        for frame in tqdm(self.frames_manager.frames): # Can be very long but normally when we have export metadata_images.csv we already retrieve all frames.
            
            predictions = self.ml_prediciton_manager.get_predictions_for_specific_model_and_frame_name(frame, last_model)
            if predictions == None or len(predictions) == 0:
                cpt_predictions_not_found += 1
                continue

            pred_doi = predictions[0].version.doi
            
            # Get predictions for each class in good order.
            predictions_to_add = {cls_name: None for cls_name in class_name}
            for pred in predictions:
                if pred.ml_class.name in predictions_to_add:
                    predictions_to_add[pred.ml_class.name] = bool(pred.score >= pred.ml_class.threshold)


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

        df_data = pl.DataFrame(data, schema=df_header, orient="row")
        df_data.write_csv(ml_predictions_file)


    def metadata_multilabel_annotation_csv(self) -> None:
        metadata_annotation_file = Path(self.seatizen_folder_path, "metadata_multilabel_annotation.csv")
        print(f"\n-- Generate {metadata_annotation_file}")

        all_labels_schema = {"FileName": pl.String, "frame_doi": pl.String, "relative_file_path": pl.String, "annotation_date": pl.String} | \
                {l.name: pl.Int8 for l in self.ml_label_manager.labels}

        data = {}
        for annotation in self.ml_annotation_manager.get_latest_annotations():
            frame_name = annotation.frame.filename
            annotation_date = annotation.ml_annotation_session.annotation_date

            if frame_name not in data:
                data[frame_name] = {
                    "FileName": frame_name,
                    "annotation_date": annotation_date,
                    "frame_doi": annotation.frame.version.doi,
                    "relative_file_path": annotation.frame.relative_path
                } | {l.name: -1.0 for l in self.ml_label_manager.labels}
            
            data[frame_name][annotation.ml_label.name] = int(annotation.value)

        # Convert the list of dictionaries to a Polars DataFrame
        df = pl.DataFrame(list(data.values()), schema=all_labels_schema)

        # Write the DataFrame to a CSV file
        df.write_csv(metadata_annotation_file)


    def darwincore_annotation_csv(self) -> None:
        darwincore_annotation_file = Path(self.seatizen_folder_path, "darwincore_multilabel_annotation.zip")
        print(f"\n-- Generate {darwincore_annotation_file}")

        darwincoreManager = DarwinCoreManager(darwincore_annotation_file)
        darwincoreManager.create_darwincore_package(self.ml_anno_ses_manager.ml_annotation_session)
        