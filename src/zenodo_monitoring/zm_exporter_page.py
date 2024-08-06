import math
import polars as pl
from pathlib import Path
from datetime import datetime

import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash_extensions.javascript import Namespace
from dash import html, dcc, Input, Output, State, ctx

from .zm_monitoring_data import MonitoringData, EnumPred
from .zm_settings_data import SettingsData

from ..utils.constants import MAX_CSV_FILE_TO_DOWNLOAD

class ZenodoMonitoringExporter:
    def __init__(self, app, settings_data: SettingsData):
        self.app = app        
        self.settings_data = settings_data
        self.monitoring_data = MonitoringData(settings_data)
        self.geolocation_footprint_json = self.monitoring_data.get_footprint_geojson() 

    
    def create_layout(self):
        ns = Namespace("PlatformSpace", "PlatformSpaceColor")
        return dbc.Spinner(html.Div([
            dcc.Store(id='local-settings-data', storage_type='local'),
            dcc.Store(id='temp-to-remove-file', storage_type='session'), # Use to remove csv file.
            dbc.Row(
                dbc.Col([
                    # Map. Geography selector.
                    html.H2(children="Select the zone to export."),
                    dl.Map(style={'width': '100%', 'height': '50vh'}, center=[-21.085198, 55.222047], zoom=14, maxZoom=18, minZoom=4 ,children=[
                        dl.TileLayer(
                            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                            attribution='Tiles © Esri'
                        ),
                        dl.TileLayer(
                            url="https://{s}.basemaps.cartocdn.com/rastertiles/light_only_labels/{z}/{x}/{y}{r}.png'",
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                        ),
                        dl.GeoJSON(
                            data=self.monitoring_data.get_footprint_geojson() ,
                            id="session_footprint",
                            style=ns("platformToColorMap")
                        ),
                        dl.FeatureGroup(id="feature_group", children=[
                            dl.EditControl(
                                id="edit_control", 
                                position="bottomleft", 
                                draw={'polygon': False, 'rectangle': True, 'polyline': False, 'circle': False, 'marker': False, 'circlemarker': False}, 
                                edit={'edit': False}
                            ),
                            dl.FullScreenControl(position="topleft"),
                            dl.MeasureControl(
                                position="topleft", 
                                primaryLengthUnit="kilometers", 
                                primaryAreaUnit="hectares",
                                activeColor="#214097", 
                                completedColor="#972158"
                            ),
                            dl.ScaleControl(position="bottomright", imperial=False)
                        ])
                    ]),
                ])
            ),

            dbc.Row([
                # Model picker.
                dbc.Col([
                    html.H4(children="Choose your multilabel model."),
                    dbc.Select(
                        self.monitoring_data.model_dash_format,
                        self.monitoring_data.model_dash_format[0]["value"],
                        id='model_select'
                    )
                ], width=3),
                # Model class picker.
                dbc.Col([
                    html.H4(children="Select classes you want to export."),
                    dcc.Dropdown(
                        self.monitoring_data.get_class_by_model(self.monitoring_data.model_dash_format[0]["value"]),
                        value=-1,
                        id='class_select',
                        multi=True,
                        placeholder="If not filled, no class are selected."
                    ),
                ]),
                # Type of prediction.
                dbc.Col([
                    html.H4(children="Select the type of value."),
                    dbc.RadioItems(
                        [EnumPred.PRED.value, EnumPred.SCORE.value], 
                        value=EnumPred.SCORE.value, 
                        id="type_pred_select",
                        inline=True,

                    ),
                ], width=3)
            ], class_name="p-3"),
            
            dbc.Row([
                # Platform selector.
                dbc.Col([
                    html.H4(children="Select the platforms that interest you."),
                    dcc.Dropdown(
                        self.monitoring_data.platform_type, 
                        id='platform_select',
                        value=[], # Avoid None value
                        multi=True, 
                        placeholder="If not filled, all platform are selected."
                    ),
                ], width=4),
                dbc.Col([
                    # Frame matadata selector.
                    html.H4(children="Select frame metadata."),
                    dcc.Dropdown(
                        self.monitoring_data.frame_manager.frames_header,
                        value=["GPSLatitude", "GPSLongitude", "version_doi", "relative_file_path"], # TODO use enum ?
                        multi=True, 
                        placeholder="If not filled, all metadata are selected.", 
                        id='frame_select'
                    ),
                ])
            ], class_name="p-3"),
            
            dbc.Row([
                # Date picker.
                html.H4(children="Select the time period."),
                self.monitoring_data.generate_date_slider(),
            ], class_name="p-3"),
            
            dbc.Button(html.Span(["Download your data  ", html.I(className="fa-solid fa-download")]), id="btn-dl", ),
            dcc.Download(id="download-dataframe-csv"),
            
            dbc.Toast(
                "After applying filters, no data remaining to export.",
                id="warning-toast",
                header="No data to export",
                is_open=False,
                dismissable=True,
                duration=10000,
                icon="danger",
                style={"position": "fixed", "bottom": 20, "right": 10, "width": 350},
            ),
        ]), id="loading-output", color="grey")
    
    
    def register_callbacks(self):

        # Update map when we select a specific platform.
        @self.app.callback(
            Output('session_footprint', 'data'), 
            Input('platform_select', 'value'),
            Input('date-picker', 'value'),
            prevent_initial_call=True,
        )
        def update_platform(platform_to_include, date_interval):
            self.geolocation_footprint_json = self.monitoring_data.get_footprint_geojson(platform_to_include, date_interval)
            return self.geolocation_footprint_json


        # Change class options with model and custom classes.
        @self.app.callback(
            Output('class_select', 'options'),
            [
                Input('model_select', 'value'),
                Input("local-settings-data", "modified_timestamp")
            ],
            State("local-settings-data", 'data')
        )
        def update_classes_on_model_change(model_id, ts, local_data):
            
            # Trigger on page load.
            if (ctx.triggered_id == "local-settings-data"):
                local_data = local_data or {}
                self.settings_data.set_serialized_data(local_data)

            # Return on page load or model change.
            return self.monitoring_data.get_class_by_model(int(model_id))
        
        
        # On download, retrieve all data into a dataframe and export to csv.
        @self.app.callback(
            [
                Output("warning-toast", "is_open"),
                Output("loading-output", "fullscreen"),
                Output("temp-to-remove-file", "data"),
            ],
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
            df_data = self.monitoring_data.build_dataframe_for_csv(geo_json, model_id, class_ids, date_range, frame_select, platform_type, type_pred_select)
            
            if len(df_data) == 0:
                # Close spinner and show a Toast.
                return True, False, None
            
            list_csv = self.build_list_split_csv(df_data)
            
            return False, False, {'files': list_csv, 'index': -1}
        
        # Remove csv file save localy.
        @self.app.callback(
            Output("download-dataframe-csv", "data"),
            Output("temp-to-remove-file", "data", allow_duplicate=True),
            Input("temp-to-remove-file", "modified_timestamp"),
            State("temp-to-remove-file", "data"),
            prevent_initial_call=True,
        )
        def download_and_remove(ts, list_files_with_index):
            if list_files_with_index == None: return None, None

            current_index = list_files_with_index['index'] + 1
            list_files = list_files_with_index['files']

            if current_index != 0:
                try:
                    file_to_del = Path(list_files[current_index-1])
                    file_to_del.unlink()
                except Exception as e:
                    print(e)
            
            if current_index == len(list_files):
                return None, None
            
            list_files_with_index['index'] = current_index
            return dcc.send_file(list_files[current_index]), list_files_with_index
    
    def build_list_split_csv(self, df_data: pl.DataFrame) -> list[str]:

        # Step 2: Split the DataFrame into chunks
        def split_dataframe(df, rows_per_file):
            for i in range(0, len(df), rows_per_file):
                yield df.slice(i, rows_per_file)

        # Step 1: Calculate approximate number of rows per MAX_CSV_FILE_TO_DOWNLOAD MB file
        df_size_bytes = df_data.write_csv().encode('utf-8')
        df_size_mb = len(df_size_bytes) / (1024 * 1024)
        nb_file = int(math.ceil(df_size_mb / MAX_CSV_FILE_TO_DOWNLOAD))
        rows_per_file = len(df_data) // nb_file
        
        basename = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_zenodo_monitoring_data'
        list_csv = []
        for i, chunk in enumerate(split_dataframe(df_data, rows_per_file)):
            csv_name = f"{basename}_{i + 1}.csv"
            list_csv.append(csv_name)
            chunk.write_csv(csv_name)
        
        return list_csv