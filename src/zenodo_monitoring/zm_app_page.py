import dash
import uuid
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html, State

from src.seatizen_atlas.sa_manager import AtlasManager

from .zm_home_page import ZenodoMonitoringHome
from .zm_exporter_page import ZenodoMonitoringExporter
from .zm_explorer_page import ZenodoMonitoringExplorer
from .zm_settings_page import ZenodoMonitoringSettings
from .zm_statistic_page import ZenodoMonitoringStatistic
from .zm_publication_page import ZenodoMonitoringPublication

class ZenodoMonitoringApp:
    def __init__(self, opt):

        # Init app.
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.SKETCHY, dbc.icons.FONT_AWESOME], 
            assets_folder="../../assets/", 
            suppress_callback_exceptions=True,
            meta_tags = [
                {"name": "Cache-Control", "content": "no-cache, no-store, must-revalidate"},
                {"name": "Pragma", "content": "no-cache"},
                {"name": "Expires", "content": "0"},
                {"name": "viewport", "content": "width=device-width, initial-scale=1"}
            ]
        )
        self.app.title = "Seatizen monitoring"

        # Init database connection.
        atlasManager = AtlasManager({}, opt.path_seatizen_atlas_folder, from_local=opt.use_from_local, force_regenerate=False)
        
        # Other pages.
        self.settings = ZenodoMonitoringSettings(self.app)
        self.explorer = ZenodoMonitoringExplorer(self.app)
        self.exporter = ZenodoMonitoringExporter(self.app, self.settings.settings_data)
        self.statistic = ZenodoMonitoringStatistic(self.app)
        self.publication = ZenodoMonitoringPublication(self.app)
        self.home = ZenodoMonitoringHome(self.app)

        self.app.layout = self.create_layout()
        self.register_callbacks()

    def create_layout(self):
        """ Creater app layout. """
        sidebar_header = dbc.Row([
            dbc.Col(html.H2("Seatizen Monitoring", className="display-5")),
            dbc.Col(
                html.Button(
                    # use the Bootstrap navbar-toggler classes to style the toggle
                    html.Span(className="navbar-toggler-icon"),
                    className="navbar-toggler",
                    # the navbar-toggler classes don't set color, so we do it here
                    style={
                        "color": "rgba(0,0,0,.5)",
                        "border-color": "rgba(0,0,0,.1)",
                    },
                    id="toggle",
                ),
                # the column containing the toggle will be only as wide as the
                # toggle, resulting in the toggle being right aligned
                width="auto",
                # vertically align the toggle in the center
                align="center",
            ),
        ])
        sidebar = html.Div([
            dcc.Store(id='local-session-id', storage_type='local'),
            sidebar_header,
            html.Div([
                html.Hr(),
                html.P(
                    "Simple tool to visualize or export data.", className="lead"
                ),
            ], id="blurb"),

            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavLink("Home", href="/home", active="exact"),
                        dbc.NavLink("Explorer", href="/", active="exact"),
                        dbc.NavLink("Exporter", href="/exporter", active="exact"),
                        dbc.NavLink("Statistic", href="/statistic", active="exact"),
                        dbc.NavLink("Settings", href="/settings", active="exact"),
                        dbc.NavLink("Publications", href="/publications", active="exact"),
                    ],
                    vertical=True,
                    pills=True,
                ),
            id="collapse")
        ], id="sidebar")

        content = html.Div(id="page-content")

        return html.Div([dcc.Location(id="url"), sidebar, content])


    def register_callbacks(self):
        """ Register all callbacks """

        # Other pages callback.
        self.home.register_callbacks()
        self.settings.register_callbacks()
        self.exporter.register_callbacks()
        self.explorer.register_callbacks()
        self.statistic.register_callbacks()
        self.publication.register_callbacks()

        @self.app.callback(Output("page-content", "children"), [Input("url", "pathname")])
        def render_page_content(pathname):
            if pathname == "/home":
                return self.home.create_layout()
            elif pathname == "/exporter":
                return self.exporter.create_layout()
            elif pathname == "/statistic":
                return self.statistic.create_layout()
            elif pathname == "/settings":
                return self.settings.create_layout()
            elif pathname == "/":
                return self.explorer.create_layout()
            elif pathname == "/publications":
                return self.publication.create_layout()
            # If the user tries to reach a different page, return a 404 message
            return html.Div(
                [
                    html.H1("404: Not found", className="text-danger"),
                    html.Hr(),
                    html.P(f"The pathname {pathname} was not recognised..."),
                ],
                class_name="p-3 bg-light rounded-3",
            )

        @self.app.callback(
            Output("local-session-id", 'data'),
            Input("local-session-id", "modified_timestamp"),
            State("local-session-id", 'data')
        )
        def get_or_create_local_session_id(ts, data):
            # Create uuid to get a session_id by user.
            if data == None:
                data = str(uuid.uuid4())
            return data
        
        @self.app.callback(
            Output("collapse", "is_open"),
            [Input("toggle", "n_clicks")],
            [State("collapse", "is_open")],
        )
        def toggle_collapse(n, is_open):
            if n:
                return not is_open
            return is_open


    def run(self, debug=False):
        """ Launch app."""
        self.app.run(debug=debug)