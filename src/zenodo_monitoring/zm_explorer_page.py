import io
import requests
from PIL import Image
from urllib.parse import urlencode, parse_qs

import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import html, Input, Output, dcc, Dash, State, no_update

from .zm_edna_data import EDNAData
from .zm_ortho_asv_footprint import OrthoASVFootprint
from .zm_utils import ON_EACH_FEATURE_EXPLORER, ON_EACH_FEATURE_EXPLORER_ASV

BATHY_YEAR = [2022, 2023, 2024, 2025]
ORTHO_YEAR = [2022, 2023, 2024, 2025]
PRED_YEAR = [2023, 2024, 2025]
EDNA_YEAR = [2023]

BASE_URL = "https://tmsserver.ifremer.re"

DEFAULT_CENTER = {'lat': -21.085198, 'lng': 55.222047}
DEFAULT_ZOOM = 14
DEFAULT_YEAR = 2023
ORTHO_VALUE = "ortho"
BATHY_VALUE = "bathy"
ORTHO_PRED_VALUE = "pred"
EDNA_VALUE = "edna"

IMG_SIZE = 512

class ZenodoMonitoringExplorer:
    def __init__(self, app: Dash):
        self.app = app
        self.edna_data = EDNAData()
        self.ortho_asv_footprint = OrthoASVFootprint()
    
    def create_layout(self):

        return html.Div([
            dcc.Location(id="url-explorer", refresh=False),
            dcc.Store(id="url-parameters-cache", storage_type='memory'),
            dcc.Store(id="cache-clean", storage_type='memory'),
            dbc.Row(
                dbc.Col([
                    # Map. Geography selector.
                    dl.Map(
                        id="map-explorer", 
                        style={'width': '100%', 'height': '80vh'},
                        center=DEFAULT_CENTER,
                        zoom=DEFAULT_ZOOM,
                        maxZoom=28, 
                        minZoom=4,
                        children = [
                            dl.TileLayer(
                                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                                attribution='Tiles © Esri',
                            ),
                            dl.TileLayer(
                                url="https://{s}.basemaps.cartocdn.com/rastertiles/light_only_labels/{z}/{x}/{y}{r}.png'",
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                            ),
                            dl.TileLayer(
                                url=BASE_URL+"https://tmsserver.ifremer.re/wmts?request=GetTile&layer=ortho&year=2023&tilematrix={z}&tilerow={x}&tilecol={y}",
                                attribution='Tiles © Ifremer DOI',
                                maxZoom=28,
                                opacity=100,
                                detectRetina=True,
                                id="ortho_map"
                            ),
                            dl.TileLayer(
                                url=BASE_URL+"/wmts?request=GetTile&layer=bathy&tilematrix={z}&tilerow={x}&tilecol={y}",
                                attribution='Tiles © Ifremer DOI',
                                maxZoom=22,
                                opacity=100,
                                id="bathy_map",
                            ),
                            dl.TileLayer(
                                url=BASE_URL+"/wmts?request=GetTile&layer=predictions&year=2023&tilematrix={z}&tilerow={x}&tilecol={y}",
                                attribution='Tiles © Ifremer DOI',
                                maxZoom=22,
                                opacity=0,
                                id="predictions_map",
                            ),
                            dl.GeoJSON(
                                data=self.edna_data.get_edna_data(EDNA_YEAR[0]),
                                id="edna_marker",
                                onEachFeature=ON_EACH_FEATURE_EXPLORER
                            ),
                            dl.GeoJSON(
                                data=self.ortho_asv_footprint.get_data("2023"),
                                id="ortho_asv_footprint",
                                onEachFeature=ON_EACH_FEATURE_EXPLORER_ASV
                            ),
                            dl.FeatureGroup(id="feature_group_aled", children= [
                                dl.FullScreenControl(position="topleft"),
                                dl.MeasureControl(
                                    position="topleft", 
                                    primaryLengthUnit="meters", 
                                    primaryAreaUnit="sqmeters",
                                    activeColor="#214097", 
                                    completedColor="#972158"
                                ),
                                dl.ScaleControl(position="bottomright", imperial=False)
                            ])
                    ]),
                ])
            ),
            dbc.Row([
                 dbc.Col([
                    html.H4(children="Choose which layer to show."),
                    dbc.Checklist(
                        options=[
                            {"label": "Orthophoto", "value": ORTHO_VALUE},
                            {"label": "Bathymetry", "value": BATHY_VALUE},
                            {"label": "Habitat map", "value": ORTHO_PRED_VALUE},
                            {"label": "eDNA", "value": EDNA_VALUE},
                        ],
                        value = [], # Default values are managed in callback
                        id="maps-options",
                        switch=True,
                    ),
                ]),
                dbc.Col([
                    html.H4(children="Choose the year."),
                    # Orthophoto year radios
                    html.Div([
                        html.Label("Orthophoto year:  ", className="mx-2"),
                        dbc.RadioItems(
                            options=[{"label": str(y), "value": str(y)} for y in ORTHO_YEAR],
                            value="2023",
                            id="orthophoto-year-radio",
                            inline=True
                        )
                    ], id="orthophoto-year-container"),


                    # Bathymetry year radios
                    html.Div([
                        html.Label("Bathymetry year:  ", className="mx-2"),
                        dbc.RadioItems(
                            options=[{"label": str(y), "value": str(y)} for y in BATHY_YEAR] +
                                    [{"label": "All", "value": "all"}],
                            value="all",
                            id="bathymetry-year-radio",
                            inline=True
                        )
                    ], id="bathymetry-year-container"),

                    # Prediction year radios
                    html.Div([
                        html.Label("Habitat year:  ", className="mx-2"),
                        dbc.RadioItems(
                            options=[{"label": str(y), "value": str(y)} for y in PRED_YEAR],
                            value="2023",
                            id="orthophoto-pred-year-radio",
                            inline=True
                        )
                    ], id="prediction-year-container"),

                    # eDNA data by year
                    html.Div([
                        html.Label("eDNA year:  ", className="mx-2"),
                        dbc.RadioItems(
                            options=[{"label": str(y), "value": str(y)} for y in EDNA_YEAR],
                            value="2023",
                            id="edna-year-radio",
                            inline=True
                        )
                    ], id="edna-year-container"),
                ]),
                dbc.Col([
                    dcc.Clipboard(id="clipboard-url", style={"display": "None"}),
                    dbc.Button(html.Span([
                        "Share your map   ", 
                        html.I(className="fa-solid fa-share")
                    ]), 
                    id="btn-share"),
                    dbc.Toast(
                        [html.P("Your position is in the clipboard. You can paste it anywhere.", className="mb-0")],
                        id="btn-share-toast",
                        header="Copy !",
                        icon="info",
                        dismissable=True,
                        is_open=False,
                        duration=3000,
                        style={"position": "fixed", "bottom": 10, "right": 20, "width": 350},
                    ),
                ], style={"display": "flex","justify-content": "flex-end" ,"align-items": "flex-start"}),

            ], class_name="p-3"),
            dbc.Row([
                dbc.Col(id="bathy_gradient_fig"),
                dbc.Col(id="predictions_gradient_fig"),
            ], class_name="p-3")
        ])

    
    def register_callbacks(self):

        @self.app.callback(
            [
                Output("ortho_map", "opacity"), 
                Output("bathy_map", "opacity"),
                Output("predictions_map", "opacity"),
                Output("edna_marker", "data"),
            ],
            Input("maps-options", "value"),
            State("edna-year-radio", "value")
        )
        def on_form_change(maps_options, edna_year):
            op_ortho = 100 if ORTHO_VALUE in maps_options else 0
            op_bathy = 100 if BATHY_VALUE in maps_options else 0
            op_predictions = 100 if ORTHO_PRED_VALUE in maps_options else 0 
            edna_data = self.edna_data.get_edna_data(edna_year, EDNA_VALUE not in maps_options)

            return op_ortho, op_bathy, op_predictions, edna_data

        @self.app.callback(
            Output("orthophoto-year-container", "style"),
            Output("bathymetry-year-container", "style"),
            Output("prediction-year-container", "style"),
            Output("edna-year-container", "style"),
            Input("maps-options", "value")
        )
        def toggle_radio_visibility(selected_layers):
            return (
                {"display": "inline-flex"} if ORTHO_VALUE in selected_layers else {"display": "none"},
                {"display": "inline-flex"} if BATHY_VALUE in selected_layers else {"display": "none"},
                {"display": "inline-flex"} if ORTHO_PRED_VALUE in selected_layers else {"display": "none"},
                {"display": "inline-flex"} if EDNA_VALUE in selected_layers else {"display": "none"},
            )

        @self.app.callback(
            Output("bathy_gradient_fig", "children"),
            Input("bathy_map", "opacity")
        )
        def bathy_opacity(op):

            if op == 0: return

            r = requests.get(f"{BASE_URL}/legend?layer=bathy")
            if r.status_code != 200:
                return

            imageStream = io.BytesIO(r.content)
            imageFile = Image.open(imageStream)  

            return [
                html.H4(children="Bathymetry legend."),
                html.Img(src=imageFile, width=IMG_SIZE)
            ]
        
        @self.app.callback(
            Output("predictions_gradient_fig", "children"),
            Input("predictions_map", "opacity")
        )
        def pred_opacity(op):

            if op == 0: return

            r = requests.get(f"{BASE_URL}/legend?layer=predictions")
            if r.status_code != 200:
                return

            imageStream = io.BytesIO(r.content)
            imageFile = Image.open(imageStream)  

            return [
                html.H4(children="Predictions legend."),
                html.Img(src=imageFile, width=IMG_SIZE)
            ]

        @self.app.callback(
            Output("predictions_map", "url"),
            Input("orthophoto-pred-year-radio", "value")
        )
        def load_url_pred(data):
            data = DEFAULT_YEAR if data == None else data
            return BASE_URL+"/wmts?request=GetTile&layer=predictions&year="+data+"&tilematrix={z}&tilerow={x}&tilecol={y}"
        
        @self.app.callback(
            Output("bathy_map", "url"),
            Input("bathymetry-year-radio", "value")
        )
        def load_url_bathy(data):
            data = DEFAULT_YEAR if data == None else data
            return BASE_URL+"/wmts?request=GetTile&layer=bathy&year="+data+"&tilematrix={z}&tilerow={x}&tilecol={y}"
        
        @self.app.callback(
            Output("ortho_map", "url"),
            Output("ortho_asv_footprint", "data"),
            Input("orthophoto-year-radio", "value"),
            State("map-explorer", "zoom")
        )
        def load_url_pred(data, zoom):
            data = DEFAULT_YEAR if data == None else data
            new_ortho_url = BASE_URL+"/wmts?request=GetTile&layer=ortho&year="+data+"&tilematrix={z}&tilerow={x}&tilecol={y}"

            return new_ortho_url, self.ortho_asv_footprint.get_data(data, zoom >= 21)
        
        @self.app.callback(
            Output("edna_marker", "data", allow_duplicate=True),
            Input("edna-year-radio", "value"),
            prevent_initial_call='initial_duplicate'
        )
        def load_edna_data(edna_year):
            return self.edna_data.get_edna_data(edna_year)
        
        @self.app.callback(
            Output("map-explorer", "viewport"),
            Output("maps-options", "value"),
            Output("orthophoto-year-radio", "value"),
            Output("bathymetry-year-radio", "value"),
            Output("orthophoto-pred-year-radio", "value"),
            Output("edna-year-radio", "value"),
            Output("cache-clean", "value", allow_duplicate=True),
            Input("url-parameters-cache", "value"),
            State("url-explorer", "search"),
            State("cache-clean", "value"),
            State("orthophoto-year-radio", "value"),
            State("bathymetry-year-radio", "value"),
            State("orthophoto-pred-year-radio", "value"),
            State("edna-year-radio", "value"),
            prevent_initial_call='initial_duplicate'
        )
        def update_map_from_cache(cache, search, cache_clean, ortho_radio, bathy_radio, ortho_pred_radio, edna_year_radio):
           
            if cache == search and not cache_clean:
                raise PreventUpdate
            
            params = parse_qs(cache.lstrip("?"))

            lat = float(params.get("lat", [DEFAULT_CENTER["lat"]])[0])
            lng = float(params.get("lng", [DEFAULT_CENTER["lng"]])[0])
            zoom = int(params.get("zoom", [DEFAULT_ZOOM])[0])
            current_checkbox = [ORTHO_VALUE, EDNA_VALUE] if cache_clean else [] # Default value for checkbox
            if ORTHO_VALUE in params:
                current_checkbox.append(ORTHO_VALUE)
                ortho_radio = params.get(ORTHO_VALUE)[0]
            
            if BATHY_VALUE in params:
                current_checkbox.append(BATHY_VALUE)
                bathy_radio = params.get(BATHY_VALUE)[0]
            
            if ORTHO_PRED_VALUE in params:
                current_checkbox.append(ORTHO_PRED_VALUE)
                ortho_pred_radio = params.get(ORTHO_PRED_VALUE)[0]

            if EDNA_VALUE in params:
                current_checkbox.append(EDNA_VALUE)
                edna_year_radio = params.get(EDNA_VALUE)[0]
            
            map_move = {"center": [lat, lng], "zoom": int(zoom), "transition":"setView"}

            return map_move, current_checkbox, ortho_radio, bathy_radio, ortho_pred_radio, edna_year_radio, False

        @self.app.callback(
            Output("url-parameters-cache", "value"),
            Output("cache-clean", "value"),
            Input("url-explorer", "search"),
            State("url-parameters-cache", "value")
        )
        def update_cache_from_url(search, cache):
            return search, cache == None

        # Update URL when the map moves
        @self.app.callback(
            [
                Output("url-explorer", "search", allow_duplicate=True),
                Output("url-parameters-cache", "value", allow_duplicate=True)
            ],
            Input("map-explorer", "center"),
            Input("map-explorer", "zoom"),
            Input("maps-options", "value"),
            Input("orthophoto-year-radio", "value"),
            Input("bathymetry-year-radio", "value"),
            Input("orthophoto-pred-year-radio", "value"),
            Input("edna-year-radio", "value"),
            State("url-parameters-cache", "value"),
            prevent_initial_call="True"
        )
        def update_url_from_map(center, zoom, checkbox, ortho_radio, bathy_radio, ortho_pred_radio, edna_radio, cache):
            
            query = self.format_query_with_parameters(center, zoom, checkbox, ortho_radio, bathy_radio, ortho_pred_radio, edna_radio)
            # Avoid cyclic update.
            if query == cache: 
                raise PreventUpdate
            
            return query, query


        @self.app.callback(
            Output("clipboard-url", "n_clicks"),
            Input("btn-share", "n_clicks"),
            prevent_initial_call=True
        )
        def intermediate_function_to_fire_clipboard_event(click):
            return click
        
        @self.app.callback(
            Output("clipboard-url", "content"),
            Output("btn-share-toast", "is_open"),
            Input("clipboard-url", "n_clicks"),
            State("map-explorer", "center"),
            State("map-explorer", "zoom"),
            State("maps-options", "value"),
            State("orthophoto-year-radio", "value"),
            State("bathymetry-year-radio", "value"),
            State("orthophoto-pred-year-radio", "value"),
            State("edna-year-radio", "value"),
            prevent_initial_call=True
        )
        def share_url(click, center, zoom, checkbox, ortho_radio, bathy_radio, ortho_pred_radio, edna_radio):
            if click == 0: return no_update, False

            query = self.format_query_with_parameters(center, zoom, checkbox, ortho_radio, bathy_radio, ortho_pred_radio, edna_radio)
            
            return f'https://seatizenmonitoring.ifremer.re/{query}', True
        
        @self.app.callback(
            Output("ortho_asv_footprint", "data", allow_duplicate=True),
            Input("map-explorer", "zoom"),
            State("orthophoto-year-radio", "value"),
            prevent_initial_call=True
        )
        def update_asv_ortho(zoom, ortho_year):
            return self.ortho_asv_footprint.get_data(ortho_year, zoom >= 21)

        
    
    def format_query_with_parameters(self, center, zoom, checkbox, ortho_radio, bathy_radio, ortho_pred_radio, edna_radio) -> str:
        
        if isinstance(center, list):
            center = {"lat": center[0], "lng": center[1]}

        base_query = {"lat": round(center["lat"], 5), "lng": round(center["lng"], 5), "zoom": zoom}
        
        if ORTHO_VALUE in checkbox:
            base_query[ORTHO_VALUE] = ortho_radio
        
        if BATHY_VALUE in checkbox:
            base_query[BATHY_VALUE] = bathy_radio
        
        if ORTHO_PRED_VALUE in checkbox:
            base_query[ORTHO_PRED_VALUE] = ortho_pred_radio
        
        if EDNA_VALUE in checkbox:
            base_query[EDNA_VALUE] = edna_radio
        
        return f"?{urlencode(base_query)}"