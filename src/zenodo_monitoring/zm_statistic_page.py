from dash import html, dcc
import dash_bootstrap_components as dbc

from .zm_statistic_data import StatisticData
from ..models.statistic_model import StatisticSQLDAO

class ZenodoMonitoringStatistic:
    def __init__(self, app):
        self.app = app        

        self.statistic_data = StatisticData()

        self.statistic_manager = StatisticSQLDAO()

        self.fig_plafform_by_session_chart = self.statistic_data.get_platform_by_session_chart()
        self.fig_plafform_by_frames_chart = self.statistic_data.get_platform_by_frames_chart()

    
    def create_layout(self):
        return dcc.Loading(html.Div([

                dbc.Row([
                    dbc.Col([
                        # Platform by session name.
                        dcc.Graph(
                            id="platform-session-name-type",
                            figure=self.fig_plafform_by_session_chart
                        ),
                    ]),
                    dbc.Col([
                        # Platform by frames.
                        dcc.Graph(
                            id="platform-frame-count-type",
                            figure=self.fig_plafform_by_frames_chart
                        ),
                    ])
                ]),
                dbc.Row([
                    # Table of statistic data.
                    dbc.Col([
                        html.H4("Global statistics about all variables"),
                        self.__get_basic_stat(),
                    ], width=4)
                ])
            ]))
    
    def register_callbacks(self):
        pass

    def __get_basic_stat(self):
        """ Build a table from a list[StatisticSQLDTO] """
        table_header = [
            html.Thead(html.Tr([html.Th("Variable"), html.Th("Count")]))
        ]
        rows = []
        for s in self.statistic_manager.statistic:
            rows.append(html.Tr([html.Td(s.name), html.Td(s.seq)]))
        
        table_body = [html.Tbody(rows)]
        table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)
        
        return table