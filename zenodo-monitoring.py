import argparse
import pandas as pd
import plotly.express as px
import dash_leaflet as dl
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State
import shapely
from shapely import Polygon, Point
import enum

from src.seatizen_atlas.sa_manager import AtlasManager

from src.models.deposit_model import DepositDAO
from src.models.statistic_model import StatisticSQLDAO
from src.models.ml_model_model import MultilabelModelDAO, MultilabelClassDAO
from src.models.frame_model import FrameDAO, FrameDTO
from src.models.ml_predictions_model import MultilabelPredictionDAO

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

        self.setup_model_data()

    def generate_date_slider(self):
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

    def get_platform_pie_chart(self):
        # Extract platform value.
        deposits = self.deposit_manager.deposits
        platforms = [] if len(deposits) == 0 else [deposit.platform for deposit in deposits]
        self.platform_type = list(set(platforms))
        platform_counts = {b: platforms.count(b) for b in set(platforms)}
        
        df = pd.DataFrame(list(platform_counts.items()), columns=['Plaftorm', 'Count'])
        
        # Create the pie chart
        fig = px.pie(df, names='Plaftorm', values='Count', title='Plaftorm Distribution')

        return fig
    
    def get_footprint_geojson(self) -> dict:
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

        polygons = []
        if not geo_json: return polygons

        for feature in geo_json.get("features", []):        
            geometry = feature.get("geometry", {})
            coordinates = geometry.get("coordinates", [])
            points = [Point(lat, lon) for lat, lon in coordinates[0]] # Seems to have an extra array useless
            polygons.append(Polygon(points))

        return polygons

    def setup_model_data(self):
        self.model_dash_format = [{'label': m.name, 'value': m.id} for m in self.ml_model_manager.models]
        
        for model in self.ml_model_manager.models:
            classes = self.ml_classes_manager.get_all_class_for_ml_model(model)
            self.classes_map_by_model_id[model.id] = [{'label': 'All class', 'value': -1}] + [{'label': cls.name, 'value': cls.id} for cls in classes]
    
    def parse_date_interval(self, date_range):
        min_user, max_user = date_range

        min_user_year = min_user // 12 + self.min_date
        min_user_month = min_user % 12 + 1 # Add one to get the correct month

        max_user_year = max_user // 12 + self.min_date
        max_user_month = max_user % 12 + 1 

        return [f"{min_user_year}-{str(min_user_month).rjust(2,'0')}", f"{max_user_year}-{str(max_user_month).rjust(2,'0')}"]
    
    def match_metadata_frame_key(self, fs, frame: FrameDTO):
        if fs == "version_doi": return frame.version.doi
        elif fs == "original_filename": return frame.original_filename
        elif fs == "relative_path": return frame.relative_path
        elif fs == "GPSLongitude": return frame.gps_longitude
        elif fs == "GPSLatitude": return frame.gps_latitude
        elif fs == "GPSAltitude": return frame.gps_altitude
        elif fs == "GPSRoll": return frame.gps_roll
        elif fs == "GPSPitch": return frame.gps_pitch
        elif fs == "GPSTrack": return frame.gps_track
        elif fs == "GPSFix": return frame.gps_fix
        elif fs == "GPSDatetime": return frame.gps_datetime
        
        return None

    def build_dataframe_for_csv(self, geo_json, model_id, class_ids, date_range, frame_metadata_header, platform_type, type_pred_select) -> pd.DataFrame:
        
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
                frame_meta.append(self.match_metadata_frame_key(fs, frame))

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
        return df_data


def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-monitoring", description="Interface to retrieve data from sqlite database.")

    # Seatizen atlas folder path
    parser.add_argument("-psa", "--path_seatizen_atlas_folder", default="./seatizen_atlas_folder", help="Folder to store data.")
    parser.add_argument("-ulo", "--use_from_local", action="store_true", help="Work from a local folder. Update if exists else Create. Default behaviour is to download data from zenodo.")

    return parser.parse_args()


def __get_basic_stat(statistic_manager: StatisticSQLDAO):
    txt = []
    for s in statistic_manager.statistic:
        txt.append(html.P([s.name, ": ", s.seq, html.Br()]))
    return txt


def setup(opt):
    
    # Init database connection.
    atlasManager = AtlasManager({}, opt.path_seatizen_atlas_folder, from_local=opt.use_from_local, force_regenerate=False)

    statistic_manager = StatisticSQLDAO()
    monitoring_data = MonitoringData()

    geolocation_footprint_json = monitoring_data.get_footprint_geojson()
    pie_chart_platform = monitoring_data.get_platform_pie_chart()

    app = Dash(__name__,suppress_callback_exceptions=True)
    app.title = "Zenodo-monitoring"

    app.layout = html.Div([
        html.H1(children="Zenodo Monitoring"),

        dcc.Tabs(id='tabs-header', value='tab-1', children=[
            dcc.Tab(label='Exporter', value='tab-1'),
            dcc.Tab(label='Statistics', value='tab-2'),
        ]),
        html.Div(id='tabs-content'),
    ])


    @app.callback(
        Output('tabs-content', 'children'),
        Input('tabs-header', 'value')
    )
    def render_content(tab):
        if tab == 'tab-1':
            return html.Div([

                # Map. Geography selector.
                html.H2(children="All footprint in database for ASV and UAV"),
                dl.Map(style={'width': '100%', 'height': '50vh'}, center=[-21.085198, 55.222047], zoom=14, maxZoom=18, minZoom=4 ,children=[
                    dl.TileLayer(url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attribution='Tiles © Esri'),
                    dl.GeoJSON(data=geolocation_footprint_json, id="polygons"),
                    dl.FeatureGroup(id="feature_group", children=[
                        dl.EditControl(
                            id="edit_control", 
                            position="topleft", 
                            draw={'polygon': False, 'rectangle': True, 'polyline': False, 'circle': False, 'marker': False, 'circlemarker': False}, 
                            edit={'edit': False}
                        )
                    ])
                ]),

                # Model picker.
                dcc.Dropdown(monitoring_data.model_dash_format, monitoring_data.model_dash_format[0]["value"] ,id='model_select', clearable=False),
                
                dcc.Dropdown(
                    monitoring_data.classes_map_by_model_id[monitoring_data.model_dash_format[0]["value"]],
                    value=-1,
                    id='class_select',
                    multi=True,
                    placeholder="If not filled, no class are selected."
                ),
                
                dcc.Dropdown(
                    monitoring_data.platform_type, 
                    id='platform_select',
                    multi=True, 
                    placeholder="If not filled, all platform are selected."
                ),
                
                dcc.Checklist(
                    [EnumPred.PRED.value, EnumPred.SCORE.value], 
                    value=[EnumPred.SCORE.value], 
                    id="type_pred_select",
                    inline=True,

                ),

                # Date picker.
                monitoring_data.generate_date_slider(),

                # Frame matadata.
                dcc.Dropdown(
                    monitoring_data.frame_manager.frames_header, 
                    multi=True, 
                    placeholder="If not filled, all metadata are selected.", 
                    id='frame_select'
                ),

                html.Button("Download your data", id="btn-dl"),
                dcc.Download(id="download-dataframe-csv"),

                dcc.Loading(
                    id="loading-1",
                    type="circle",
                    children=html.Div(id="loading-output-1"),
                    overlay_style={"visibility":"visible", "opacity": .5, "backgroundColor": "white"},
                ),
            ])
        elif tab == 'tab-2':
            return html.Div([
                dcc.Graph(
                    id="platform-type",
                    figure=pie_chart_platform
                ),
                html.Div(children=__get_basic_stat(statistic_manager)),
            ])
    

    @app.callback(
        Output('class_select', 'options'),
        Input('model_select', 'value')
    )
    def update_classes_on_model_change(model_value):
        return monitoring_data.classes_map_by_model_id[model_value]
    

    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("btn-dl", "n_clicks"), 
        [
            State("edit_control", "geojson"), 
            State("model_select", "value"),
            State("class_select", "value"), 
            State("date-picker", "value"),
            State("frame_select", "value"),
            State("platform_select", "value"),
            State("type_pred_select", "value"),
        ],
        prevent_initial_call=True,
    )
    def generate_csv(n_clicks, geo_json, model_id, class_ids, date_range, frame_select, platform_type, type_pred_select):
        
        df_data = monitoring_data.build_dataframe_for_csv(geo_json, model_id, class_ids, date_range, frame_select, platform_type, type_pred_select)
        if len(df_data) == 0:
            print("No data to download")
            return None

        return dcc.send_data_frame(df_data.to_csv, index=False, filename="test.csv")
    return app

if __name__ == "__main__":
    opt = parse_args()
    app = setup(opt)

    app.run(debug=True)