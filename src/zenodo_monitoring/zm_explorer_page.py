import dash_leaflet as dl
from dash import html, Input, Output
import dash_bootstrap_components as dbc

class ZenodoMonitoringExplorer:
    def __init__(self, app):
        self.app = app
    
    def create_layout(self):
  

        return html.Div([
            dbc.Row(
                dbc.Col([
                    # Map. Geography selector.
                    dl.Map(style={'width': '100%', 'height': '80vh'}, center=[-21.085198, 55.222047], zoom=14, maxZoom=26, minZoom=4,children=[
                        dl.TileLayer(
                            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                            attribution='Tiles © Esri',
                        ),
                        dl.TileLayer(
                            url="https://{s}.basemaps.cartocdn.com/rastertiles/light_only_labels/{z}/{x}/{y}{r}.png'",
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                        ),
                        dl.TileLayer(
                            url="https://tmsserver.ifremer.re/wmts?request=GetTile&layer=ortho&tilematrix={z}&tilerow={x}&tilecol={y}",
                            attribution='Tiles © Ifremer DOI',
                            maxZoom=26,
                            opacity=100,
                            id="ortho_map"
                        ),
                        dl.TileLayer(
                            url="https://tmsserver.ifremer.re/wmts?request=GetTile&layer=bathy&tilematrix={z}&tilerow={x}&tilecol={y}",
                            attribution='Tiles © Ifremer DOI',
                            maxZoom=22,
                            opacity=100,
                            id="bathy_map",
                        ),
                        # dl.TileLayer(
                        #     url="https://tmsserver.ifremer.re/wmts?request=GetTile&layer=predictions&tilematrix={z}&tilerow={x}&tilecol={y}",
                        #     attribution='Tiles © Ifremer DOI',
                        #     maxZoom=22,
                        #     opacity=0,
                        #     id="predictions_map",
                        # ),
                        dl.FeatureGroup(id="feature_group_aled", children=[
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
                 dbc.Col([
                    html.H4(children="Choose which layer to show."),
                    dbc.Checklist(
                        options=[
                            {"label": "Orthophoto", "value": 1},
                            {"label": "Bathymetry", "value": 2},
                            {"label": "Drone segmentation predictions", "value": 3, "disabled": True},
                        ],
                        value=[1, 2],
                        id="maps-options",
                        switch=True,
                        inline=True
                    ),
                ])
            ], class_name="p-3")
        ])
    
    
    def register_callbacks(self):
        @self.app.callback(
            [
                Output("ortho_map", "opacity"), 
                Output("bathy_map", "opacity"),
                # Output("predictions_map", "opacity"),
            ],
            Input("maps-options", "value"),
        )
        def on_form_change(maps_options):
            op_ortho = 100 if 1 in maps_options else 0
            op_bathy = 100 if 2 in maps_options else 0
            # op_predictions = 100 if 3 in maps_options else 0
            
            return op_ortho, op_bathy
