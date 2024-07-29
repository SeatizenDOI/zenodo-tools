import dash_leaflet as dl
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from .zm_monitoring_data import MonitoringData, EnumPred


class ZenodoMonitoringExporter:
    def __init__(self, app):
        self.app = app        

        self.monitoring_data = MonitoringData()
        self.geolocation_footprint_json = self.monitoring_data.get_footprint_geojson() 

    
    def create_layout(self):
        return dbc.Spinner(html.Div([

            dbc.Row(
                dbc.Col([
                    # Map. Geography selector.
                    html.H2(children="Select the zone to export."),
                    dl.Map(style={'width': '100%', 'height': '50vh'}, center=[-21.085198, 55.222047], zoom=14, maxZoom=18, minZoom=4 ,children=[
                        dl.TileLayer(url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attribution='Tiles © Esri'),
                        dl.GeoJSON(data=self.geolocation_footprint_json, id="polygons"),
                        dl.FeatureGroup(id="feature_group", children=[
                            dl.EditControl(
                                id="edit_control", 
                                position="topleft", 
                                draw={'polygon': False, 'rectangle': True, 'polyline': False, 'circle': False, 'marker': False, 'circlemarker': False}, 
                                edit={'edit': False}
                            )
                        ])
                    ])
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
                        self.monitoring_data.classes_map_by_model_id[self.monitoring_data.model_dash_format[0]["value"]],
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
            ], className="p-3"),
            
            dbc.Row([
                dbc.Col([
                    html.H4(children="Select the platforms that interest you."),
                    dcc.Dropdown(
                        self.monitoring_data.platform_type, 
                        id='platform_select',
                        multi=True, 
                        placeholder="If not filled, all platform are selected."
                    ),
                ], width=4),
                dbc.Col([
                    # Frame matadata.
                    html.H4(children="Select frame metadata."),
                    dcc.Dropdown(
                        self.monitoring_data.frame_manager.frames_header, 
                        multi=True, 
                        placeholder="If not filled, all metadata are selected.", 
                        id='frame_select'
                    ),
                ])
            ], className="p-3"),
            
            dbc.Row([
                # Date picker.
                html.H4(children="Select the time period."),
                self.monitoring_data.generate_date_slider(),
            ], className="p-3"),
            
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
        @self.app.callback(
            Output('class_select', 'options'),
            Input('model_select', 'value')
        )
        def update_classes_on_model_change(model_value):
            return self.monitoring_data.classes_map_by_model_id[model_value]
        

        @self.app.callback(
            [
                Output("warning-toast", "is_open"),
                Output("download-dataframe-csv", "data"),
                Output("loading-output", "fullscreen"),
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
                return True, None, False

            return False, dcc.send_data_frame(df_data.to_csv, index=False, filename="zenodo_monitoring_data.csv"), False