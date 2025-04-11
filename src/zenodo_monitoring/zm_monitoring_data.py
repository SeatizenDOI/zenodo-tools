import enum
import calendar
import polars as pl
from dash import dcc
from datetime import datetime

import shapely
from shapely import Polygon, Point
from pyproj import Geod

from src.models.deposit_model import DepositLinestringDAO
from src.models.ml_model_model import MultilabelModelDAO, MultilabelClassDAO, MultilabelClassDTO
from src.models.frame_model import FrameDAO
from src.models.ml_predictions_model import MultilabelPredictionDAO
from src.models.statistic_model import Benchmark
from .zm_settings_data import SettingsData

class EnumPred(enum.Enum):
    SCORE = "Score"
    PRED = "Prediction"

PLATFORM_BETTER_WITH_LINESTRING = ["SCUBA", "PADDLE", "UVC"]

class MonitoringData:
    
    def __init__(self, settings_data: SettingsData) -> None:
        self.min_date, self.max_date = 100000, 0
        self.classes_map_by_model_id = {}
        self.model_dash_format = []
        self.platform_type = []

        self.settings_data = settings_data
        self.deposit_linestrings_manager = DepositLinestringDAO()
        self.ml_model_manager = MultilabelModelDAO()
        self.ml_classes_manager = MultilabelClassDAO()
        self.frame_manager = FrameDAO()
        self.prediction_manager = MultilabelPredictionDAO()

        self.setup_data()

    def generate_date_slider(self):
        """ Build a date slider based on session year. """
        for deposit_line in self.deposit_linestrings_manager.deposits_linestring:
            if deposit_line.deposit.session_date == None: continue

            try:
                deposit_year = int(str(deposit_line.deposit.session_date)[0:4])
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
            min = 0, max = len(years_month) - 1, 
            step = None, 
            marks = years_month, 
            allowCross = False,
            tooltip = {
                "always_visible": False, 
                "transform": "markToDate",
            },
            value = [0, (self.max_date-self.min_date+1) * 12 - 1])
    

    def get_footprint_geojson(self, platform_to_include = [], date_interval = []) -> dict:
        """ Get the footprint for each session. """
        # Extract date before continue
        d_start, d_end = None, None
        if len(date_interval):
            parsed_date = self.parse_date_interval(date_interval)
            d_start = datetime.strptime(parsed_date[0], "%Y-%m-%d")
            d_end = datetime.strptime(parsed_date[1], "%Y-%m-%d")


        features = []
        for dl in self.deposit_linestrings_manager.deposits_linestring:
            
            if dl.deposit.footprint == None: continue
            
            # Filter by platform.
            if len(platform_to_include) > 0 and dl.deposit.platform not in platform_to_include: continue
            
            # Filter by date
            if d_start != None and d_end != None:
                d_compare = datetime.strptime(dl.deposit.session_date, "%Y-%m-%d")
                if d_compare < d_start or d_compare > d_end: continue

            # Footprint.
            geojson_polygon = shapely.geometry.mapping(dl.footprint_linestring if dl.deposit.platform in PLATFORM_BETTER_WITH_LINESTRING else dl.deposit.footprint)
        
            # Area in squared meters.
            geod = Geod(ellps="WGS84")
            poly_area, poly_perimeter = geod.geometry_area_perimeter(dl.deposit.footprint)

            # Add min max depth
            # self.frame_manager.get_min_max_depth_by_deposit(deposit) # Too much time consuming.
            
            # Add predict classes
            # self.ml_classes_manager.get_first_n_class_deposit(self.ml_model_manager.last_model, deposit, 3) # Too much time consuming.

            tooltip_data = {
                "type": "Feature",
                "geometry": geojson_polygon,
                "platform": dl.deposit.platform,
                "name": dl.deposit.session_name,
                "date": dl.deposit.session_date,
                "doi": dl.deposit.doi
            }
            
            if dl.deposit.platform in PLATFORM_BETTER_WITH_LINESTRING:
                tooltip_data["perimeter"] = f"{round(poly_perimeter / 2)} m" # Magic smoke.
            else:
                tooltip_data["area"] = f"{round(poly_area , 2)} m²"


            features.append(tooltip_data)

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
        self.platform_type = list(set([dl.deposit.platform for dl in self.deposit_linestrings_manager.deposits_linestring]))
    
    def get_class_by_model(self, model_id: int, session_id: str):
        # Classic class from db.
        classes_with_model = self.classes_map_by_model_id[model_id] if model_id in self.classes_map_by_model_id else []
        
        # Custom group.
        for group_name, model_group_id in self.settings_data.get_group(session_id):
            if model_group_id != model_id: continue
            classes_with_model = [{'label': group_name, 'value': group_name}] + classes_with_model

        return classes_with_model


    def parse_date_interval(self, date_range: tuple[int, int]):
        """ Parse date interval from user input. Retrieve a list of ["2023-12-01", "2024-11-30"]"""
        min_user, max_user = date_range

        min_user_year = min_user // 12 + self.min_date
        min_user_month = min_user % 12 + 1 # Add one to get the correct month

        max_user_year = max_user // 12 + self.min_date
        max_user_month = max_user % 12 + 1 
        max_user_day = calendar.monthrange(max_user_year, max_user_month)[1]

        return [
            f"{min_user_year}-{str(min_user_month).rjust(2,'0')}-01", 
            f"{max_user_year}-{str(max_user_month).rjust(2,'0')}-{max_user_day}"
        ]


    def build_dataframe_for_csv(self, session_id, geo_json, model_id, class_to_retrieve, date_range, frame_metadata_header, platform_type, type_pred_select) -> pl.DataFrame:
        """ Parse all data and request database to build dataframe. """
        # Internal statistic.
        benchmarck = Benchmark()
        benchmarck.start()

        # Deal with list. We can have class id or Group name.
        if isinstance(class_to_retrieve, int) or isinstance(class_to_retrieve, str):
            class_to_retrieve = [class_to_retrieve]

        class_ids = [id for id in class_to_retrieve if isinstance(id, int)]
        group_class = [name for name in class_to_retrieve if isinstance(name, str)]

        # For each group_class, we need to get ml_class object
        group_class_by_name: dict[str, list[MultilabelClassDTO]] = {}
        for group_name in group_class:
            group_class_by_name[group_name] = [self.ml_classes_manager.get_class_by_id(id) for id in self.settings_data.group_name_and_ids[session_id][(group_name, model_id)]]

        # Get all metadata if not selected.
        if not frame_metadata_header: 
            frame_metadata_header = self.frame_manager.frames_header

        # Parse and fetch all basics information.
        list_poly = self.extract_polygons(geo_json)
        date_range = self.parse_date_interval(date_range)
        ml_model = self.ml_model_manager.get_model_by_id(model_id)
        classes = self.ml_classes_manager.get_all_class_for_ml_model(ml_model)
        class_name = [cls.name for cls in classes if -1 in class_ids or cls.id in class_ids]

        # Get frames base on filter.
        frames = self.frame_manager.get_frame_by_date_type_position(list_poly, date_range, platform_type)
        
        # Init dataframe header. Force header type due to polars library.
        df_header = ["FileName"] + frame_metadata_header
        if len(class_name) > 0 or len(group_class) > 0:
            df_header += ["pred_doi"] + group_class + class_name
        
        data = []
        for frame in frames:
            data_to_add = [frame.filename]

            # Add frame metadata
            for fs in frame_metadata_header:
                data_to_add.append(self.frame_manager.match_frame_header_and_attribut(fs, frame))

            predictions = []
            if -1 not in class_ids:
                predictions = self.prediction_manager.get_predictions_frame_and_class(frame, class_ids)
            else:
                predictions = self.prediction_manager.get_predictions_for_specific_model_and_frame_name(frame, ml_model)         

            # Get predictions for each class in good order.
            predictions_to_add = {cls_name: None for cls_name in class_name}
            pred_doi = ""
            for pred in predictions:
                pred_doi = pred.version.doi
                if pred.ml_class.name in predictions_to_add:
                    predictions_to_add[pred.ml_class.name] = pred.score if type_pred_select == EnumPred.SCORE.value else int(pred.score >= pred.ml_class.threshold)
            
            # For each group class, we try to get predictions 
            group_predictions = {gp: None for gp in group_class_by_name}
            for group_name in group_class_by_name:
                predictions = self.prediction_manager.get_predictions_frame_and_class(frame, [cls.id for cls in group_class_by_name.get(group_name, [])])
                if len(predictions) == 0:
                    group_predictions[group_name] = -1.0
                else:
                    group_predictions[group_name] = int(bool(sum([p.score >= p.ml_class.threshold for p in predictions]))) 

            if len(class_name) != 0 or len(group_class) != 0:
                data_to_add.append(f"{'https://doi.org/10.5281/zenodo.' if pred_doi != '' else ''}{pred_doi}")
             
            data.append(
                data_to_add + 
                [s if s != None else -1.0 for s in group_predictions.values()] + 
                [s if s != None else -1.0 for s in predictions_to_add.values()]
            )
        
        df_data = pl.DataFrame(data, schema=df_header, schema_overrides=self.frame_manager.typed_frames_header, orient="row")

        benchmarck.stop_and_show("Time to prepare, request and build dataframe")
        return df_data
