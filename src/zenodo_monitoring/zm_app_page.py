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


SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

class ZenodoMonitoringApp:
    def __init__(self, opt):

        # Init app.
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.SKETCHY, dbc.icons.FONT_AWESOME], 
            assets_folder="../../assets/", 
            suppress_callback_exceptions=True
        )
        self.app.title = "Seatizen monitoring"

        # Init database connection.
        atlasManager = AtlasManager({}, opt.path_seatizen_atlas_folder, from_local=opt.use_from_local, force_regenerate=False)
        
        # Other pages.
        self.settings = ZenodoMonitoringSettings(self.app)
        self.explorer = ZenodoMonitoringExplorer(self.app)
        self.exporter = ZenodoMonitoringExporter(self.app, self.settings.settings_data)
        self.statistic = ZenodoMonitoringStatistic(self.app)
        self.home = ZenodoMonitoringHome(self.app)

        self.app.layout = self.create_layout()
        self.register_callbacks()

    def create_layout(self):
        """ Creater app layout. """
        sidebar = html.Div([
            dcc.Store(id='local-session-id', storage_type='local'),
            html.H2("Seatizen Monitoring", className="display-5"),
            html.Hr(),
            html.P(
                "Simple tool to visualize or export data.", className="lead"
            ),
            dbc.Nav(
                [
                    dbc.NavLink("Home", href="/home", active="exact"),
                    dbc.NavLink("Explorer", href="/", active="exact"),
                    dbc.NavLink("Exporter", href="/exporter", active="exact"),
                    dbc.NavLink("Statistic", href="/statistic", active="exact"),
                    dbc.NavLink("Settings", href="/settings", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
        ], style=SIDEBAR_STYLE)

        content = html.Div(id="page-content", style=CONTENT_STYLE)

        return html.Div([dcc.Location(id="url"), sidebar, content])


    def register_callbacks(self):
        """ Register all callbacks """

        # Other pages callback.
        self.home.register_callbacks()
        self.settings.register_callbacks()
        self.exporter.register_callbacks()
        self.explorer.register_callbacks()
        self.statistic.register_callbacks()

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
            # If the user tries to reach a different page, return a 404 message
            return html.Div(
                [
                    html.H1("404: Not found", class_name="text-danger"),
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

    def run(self, debug=False):
        """ Launch app."""
        self.app.run(debug=debug)