from dash import html, dcc

from .zm_monitoring_data import MonitoringData
from ..models.statistic_model import StatisticSQLDAO

class ZenodoMonitoringStatistic:
    def __init__(self, app):
        self.app = app        

        self.monitoring_data = MonitoringData()
        self.piechart_platform = self.monitoring_data.get_platform_pie_chart() 

        self.statistic_manager = StatisticSQLDAO()
    
    def create_layout(self):
        return html.Div([
                dcc.Graph(
                    id="platform-type",
                    figure=self.piechart_platform
                ),
                html.Div(children=self.__get_basic_stat()),
            ])
    
    def register_callbacks(self):
        pass

    def __get_basic_stat(self):
        txt = []
        for s in self.statistic_manager.statistic:
            txt.append(html.P([s.name, ": ", s.seq, html.Br()]))
        return txt