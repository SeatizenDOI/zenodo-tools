import enum
import pandas as pd
from dash import dcc

import shapely
from shapely import Polygon, Point

from src.models.deposit_model import DepositDAO
from src.models.ml_model_model import MultilabelModelDAO, MultilabelClassDAO
from src.models.frame_model import FrameDAO
from src.models.ml_predictions_model import MultilabelPredictionDAO
from src.models.statistic_model import Benchmark

class EnumPred(enum.Enum):
    SCORE = "Score"
    PRED = "Prediction"

class MonitoringData:
    
    def __init__(self) -> None:
        self.min_date, self.max_date = 100000, 0
        self.classes_map_by_model_id = {}
        self.model_dash_format = []
        self.platform_type = []


        self.deposit_manager = DepositDAO()
        self.ml_model_manager = MultilabelModelDAO()
        self.ml_classes_manager = MultilabelClassDAO()
        self.frame_manager = FrameDAO()
        self.prediction_manager = MultilabelPredictionDAO()

        self.setup_data()

    def generate_date_slider(self):
        """ Build a date slider based on session year. """
        for deposit in self.deposit_manager.deposits:
            if deposit.session_date == None: continue

            try:
                deposit_year = int(str(deposit.session_date)[0:4])
                self.min_date = min(deposit_year, self.min_date)
                self.max_date = max(deposit_year, self.max_date)
            except:
                continue

        years_month = {}
        for i in range(0, (self.max_date-self.min_date+1) * 12):
            if i % 12 == 0:
                years_month[i] = str(self.min_date + i//12)
            else:
                years_month[i] = ""

        return dcc.RangeSlider(
            id = "date-picker", 
            min = 0, max = len(years_month), 
            step = None, 
            marks = years_month, 
            allowCross = False,
            tooltip = {
                "always_visible": False, 
                "transform": "markToDate",
            },
            value = [0, (self.max_date-self.min_date+1) * 12 - 1])
    

    def get_footprint_geojson(self) -> dict:
        """ Get the footprint for each session. """
        features = []
        for deposit in self.deposit_manager.deposits:
            if deposit.footprint == None: continue
            
            for geom in deposit.footprint.geoms:
                # Keep only polygon.
                if not isinstance(geom, Polygon): continue

                geojson_polygon = shapely.geometry.mapping(geom)
                features.append({
                    "type": "Feature",
                    "geometry": geojson_polygon,           
                })

        geojson_feature_collection = {
            "type": "FeatureCollection",
            "features": features
        }

        return geojson_feature_collection
    

    def extract_polygons(self, geo_json) -> list:
        """ Extract all polygons from user input. """
        polygons = []
        if not geo_json: return polygons

        for feature in geo_json.get("features", []):        
            geometry = feature.get("geometry", {})
            coordinates = geometry.get("coordinates", [])
            points = [Point(lat, lon) for lat, lon in coordinates[0]] # Seems to have an extra array useless
            polygons.append(Polygon(points))

        return polygons


    def setup_data(self):
        """ Setup data. """

        # Model name.
        self.model_dash_format = [{'label': m.name, 'value': m.id} for m in self.ml_model_manager.models]
        
        # Classe by model id.
        for model in self.ml_model_manager.models:
            classes = self.ml_classes_manager.get_all_class_for_ml_model(model)
            self.classes_map_by_model_id[model.id] = [{'label': 'All class', 'value': -1}] + [{'label': cls.name, 'value': cls.id} for cls in classes]

        # Platform type.
        self.platform_type = list(set([deposit.platform for deposit in self.deposit_manager.deposits]))


    def parse_date_interval(self, date_range):
        """ Parse date interval from user input. Retrieve a list of ["2023-12", "2024-11"]"""
        min_user, max_user = date_range

        min_user_year = min_user // 12 + self.min_date
        min_user_month = min_user % 12 + 1 # Add one to get the correct month

        max_user_year = max_user // 12 + self.min_date
        max_user_month = max_user % 12 + 1 

        return [f"{min_user_year}-{str(min_user_month).rjust(2,'0')}", f"{max_user_year}-{str(max_user_month).rjust(2,'0')}"]


    def build_dataframe_for_csv(self, geo_json, model_id, class_ids, date_range, frame_metadata_header, platform_type, type_pred_select) -> pd.DataFrame:
        """ Parse all data and request database to build dataframe. """
        # Internal statistic.
        benchmarck = Benchmark()
        benchmarck.start()

        # Deal with list.
        if isinstance(class_ids, int):
            class_ids = [class_ids]

        # Get all metadata if not selected.
        if not frame_metadata_header: 
            frame_metadata_header = self.frame_manager.frames_header
        
        # Set prediction type.
        pred_select = EnumPred.SCORE.value if len(type_pred_select) != 1 else type_pred_select[0]

        # Parse and fetch all basics information.
        list_poly = self.extract_polygons(geo_json)
        date_range = self.parse_date_interval(date_range)
        ml_model = self.ml_model_manager.get_model_by_id(model_id)
        classes = self.ml_classes_manager.get_all_class_for_ml_model(ml_model)
        class_name = [cls.name for cls in classes if -1 in class_ids or cls.id in class_ids]

        # Get frames base on filter.
        frames = self.frame_manager.get_frame_by_date_type_position(list_poly, date_range, platform_type)
        
        # Init dataframe value.
        df_header = ["FileName"] + frame_metadata_header + class_name
        data = []

        for frame in frames:

            frame_meta = []
            for fs in frame_metadata_header:
                frame_meta.append(self.frame_manager.match_frame_header_and_attribut(fs, frame))

            predictions = []
            if -1 not in class_ids:
                predictions = self.prediction_manager.get_predictions_frame_and_class(frame, class_ids)
            else:
                predictions = self.prediction_manager.get_predictions_for_specific_model_and_frame_name(frame, ml_model)         

            # Get predictions for each class in good order.
            predictions_to_add = {cls_name: None for cls_name in class_name}
            
            for pred in predictions:
                if pred.ml_class.name in predictions_to_add:
                    predictions_to_add[pred.ml_class.name] = pred.score if pred_select == EnumPred.SCORE.value else int(pred.score >= pred.ml_class.threshold)
            
            data.append([frame.filename] + frame_meta + [s if s != None else -1 for s in predictions_to_add.values()])
        

        df_data = pd.DataFrame(data, columns=df_header)

        benchmarck.stop_and_show("Time to prepare, request and build dataframe")
        return df_data
