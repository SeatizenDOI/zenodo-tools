from pathlib import Path
import json
import shapely


class EDNAData:
    def __init__(self):
        
        self.data_path = Path("data/edna/data.json")
        self.data = []
        
        if not self.data_path.exists():
            raise FileNotFoundError("edna_data not found")
        
        with open(self.data_path) as f:
            self.data = json.load(f)
        

    def get_edna_data(self, year: int, empty: bool = False) -> dict:
        
        if empty:
            return {
                "type": "FeatureCollection",
                "features": []
            }
        features = []

        for sample in self.data:
            if sample.get("date")[0:4] != year: continue

            tooltip_data = {
                "type": "Feature",
                "geometry": shapely.geometry.mapping(shapely.Point(sample.get("GPSLongitude"), sample.get("GPSLatitude"))),
                "place": sample.get("place"),
                "date": sample.get("date"),
                "publication_name": sample.get("publication")["name"],
                "publication_link": sample.get("publication")["link"],
                "data_name": sample.get("data")["name"],
                "data_link": sample.get("data")["link"],
                "thumbnail": sample.get("thumbnail"),
                "description": sample.get("description"),
                "GPSLatitude": sample.get("GPSLatitude"),
                "GPSLongitude": sample.get("GPSLongitude")
            }
            features.append(tooltip_data)

        geojson_feature_collection = {
            "type": "FeatureCollection",
            "features": features
        }

        return geojson_feature_collection
    