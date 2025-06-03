from dash import html
import dash_bootstrap_components as dbc

class ZenodoMonitoringHome:
    def __init__(self, app):
        self.app = app        

    
    def create_layout(self):
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H1("Seatizen Atlas: a collaborative dataset of underwater and aerial marine imagery"),
                    html.P(
                        "Citizen Science initiatives have a worldwide impact on environmental research by providing data at a global scale and high"
                        "resolution. Mapping marine biodiversity however still remains a challenge. This dataset is made of both underwater and"
                        "aerial imagery collected in shallow tropical coastal areas by using various low cost platforms that can be operated either"
                        "by citizen-scientists or researchers. Covering various areas in the south west Indian Ocean region, this dataset is regularly"
                        "updated to list a significant number of images. Most of images are geolocated, and some of them are also annotated with 51"
                        "distinct classes (e.g. corals, associated fauna, and habitats) to train AI models. The quality of these photos which are taken by"
                        "action cameras along the trajectories of different platforms, is highly heterogeneous (due to varying speed, depth, lighting,"
                        "turbidity, and perspectives) and well reflects the challenges of underwater image recognition. Data discovery and access rely "
                        "on DOI assignement while data interoperability and reuse is ensured by complying with widely used community standards."
                    ),
                ], align="center")
            ]),
            
            dbc.Row([
                dbc.Card([
        
                    dbc.CardImg(src="assets/img/zenodo.jpeg", alt="Zenodo"),
                    dbc.CardBody([
                        html.H4("Seatizen Atlas", className="card-title"),
                        html.P(
                            "Our data are stored on Zenodo, an open-source scientific community plafform.",
                            className="card-text",
                        ),
                        dbc.Button("Explore our data", color="primary", href="https://zenodo.org/records/11125847"),
                    ]),
                ], style={"width": "25rem"}),

            dbc.Card([
        
                    dbc.CardImg(src="assets/img/github.png", alt="Github"),
                    dbc.CardBody([
                        html.H4("Our codes", className="card-title"),
                        html.P(
                            "The entire workflow to create and group the data is open-source.",
                            className="card-text",
                        ),
                        dbc.Button("Explore our codes", color="primary", href="https://github.com/SeatizenDOI"),
                    ]),
                ], style={"width": "25rem"}),

            dbc.Card([
        
                    dbc.CardImg(src="assets/img/logo_partenaire.png", alt="Partnership"),
                    dbc.CardBody([
                        html.H4("Our partners", className="card-title"),
                        html.P(
                            "Birthplace of the project alongside our loyal partners."
                            "Thanks to them for this adventure.",
                            className="card-text",
                        ),
                        dbc.Button("Visit our website", color="primary", href="https://ocean-indien.ifremer.fr/"),
                    ]),
                ], style={"width": "25rem"})
            ], justify="around", className="mt-5 pt-5"),
        ])
    
    def register_callbacks(self):
        pass