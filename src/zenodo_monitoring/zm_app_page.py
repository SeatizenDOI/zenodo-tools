import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from src.seatizen_atlas.sa_manager import AtlasManager
from .zm_exporter_page import ZenodoMonitoringExporter
from .zm_statistic_page import ZenodoMonitoringStatistic
from .zm_home_page import ZenodoMonitoringHome


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
        self.exporter = ZenodoMonitoringExporter(self.app)
        self.statistic = ZenodoMonitoringStatistic(self.app)
        self.home = ZenodoMonitoringHome(self.app)

        self.app.layout = self.create_layout()
        self.register_callbacks()

    def create_layout(self):
        """ Creater app layout. """
        sidebar = html.Div([
            html.H2("Seatizen Monitoring", className="display-5"),
            html.Hr(),
            html.P(
                "Simple tool to visualize or export data.", className="lead"
            ),
            dbc.Nav(
                [
                    dbc.NavLink("Home", href="/", active="exact"),
                    dbc.NavLink("Exporter", href="/exporter", active="exact"),
                    dbc.NavLink("Statistic", href="/statistic", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
        ], style=SIDEBAR_STYLE)

        content = html.Div(id="page-content", style=CONTENT_STYLE)

        return html.Div([dcc.Location(id="url", pathname="/exporter"), sidebar, content])

    def register_callbacks(self):
        """ Register all callbacks """

        # Other pages callback.
        self.home.register_callbacks()
        self.exporter.register_callbacks()
        self.statistic.register_callbacks()

        @self.app.callback(Output("page-content", "children"), [Input("url", "pathname")])
        def render_page_content(pathname):
            if pathname == "/":
                return self.home.create_layout()
            elif pathname == "/exporter":
                return self.exporter.create_layout()
            elif pathname == "/statistic":
                return self.statistic.create_layout()
            # If the user tries to reach a different page, return a 404 message
            return html.Div(
                [
                    html.H1("404: Not found", className="text-danger"),
                    html.Hr(),
                    html.P(f"The pathname {pathname} was not recognised..."),
                ],
                className="p-3 bg-light rounded-3",
            )

    def run(self, debug=False):
        """ Launch app."""
        self.app.run(debug=debug)