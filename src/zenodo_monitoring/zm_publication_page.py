import json
from dash import html
from pathlib import Path

class ZenodoMonitoringPublication:
    def __init__(self, app):
        self.app = app        

        self.data_path = Path("data/publications.json")

        if not self.data_path.exists():
            raise FileNotFoundError("Publications not found")
        
        with open(self.data_path) as f:
            self.data = json.load(f)
        
    
    def create_layout(self):
        return html.Div([
            html.H1("Related Publications by Category"),
            html.Div(self.generate_publication_blocks())
        ], style={"display": "flex", "flex-direction": "column", "align-items": "center"})
    
    # Group by category
    def generate_publication_blocks(self):
        categories = ["Data Descriptor", "Artificial Intelligence", "eDNA"]
        blocks = []
        for category in categories:
            blocks.append(html.H2(category, className="mt-5"))
            for pub in self.data:
                if category != pub["category"]: continue

                blocks.append(
                    html.Div([
                        html.Strong(pub['citation']), 
                        html.Br(),
                        html.Span("Doi: "),
                        html.A(pub['doi'], href=pub['doi'], target="_blank", style={"color": "#1a0dab"})
                    ], className="mb-3", style={"max-width": "1200px"})
                )
        return blocks

    
    def register_callbacks(self):
        pass