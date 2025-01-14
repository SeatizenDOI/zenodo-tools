from pathlib import Path
from datetime import datetime
import pyproj
import geopandas as gpd
from .ssm_base_manager import BaseSessionManager
from shapely.geometry import Polygon
from shapely.ops import transform
class UAVSession(BaseSessionManager):

    def __init__(self, session_path, temp_folder):
        super().__init__(session_path, temp_folder)
    
    # -- Mandatory methods
    def get_restricted_files_on_zenodo(self) -> list[str]:
        return []


    def get_raw_access_right(self) -> str:
        return "open"


    def get_processed_access_right(self) -> str:
        return "open"


    def build_raw_description(self) -> str:
        return f"""
            {self.__get_survey_information()}
        """


    def build_processed_description(self) -> str:
        return f"""
            {self.__get_survey_information()}

            {self._build_photog_description()}

        """
    

    def zip_raw_data(self) -> None:
        self._zip_dcim()
        self._zip_folder("METADATA")
        self._zip_folder("GPS")
    

    def __get_survey_information(self) -> str:
        # Check for video
        metadata_csv = self.get_metadata_csv()
        first_image = metadata_csv.iloc[0]
        extension = Path(first_image["relative_file_path"]).suffix.lower()
        size_images = self.get_file_dcim_size(extension)
        number_images = len(metadata_csv)
        camera = first_image["Make"] + " " + first_image["Model"]

        median_height = metadata_csv["GPSAltitude"].median()
   
        return f"""
                <h2>Survey information</h2>
                <ul>
                    <li> <strong> Camera</strong>: {camera}</li>
                    <li> <strong> Number of images</strong>: {number_images} </li>
                    <li> <strong> Total size in Gb</strong>: {size_images}</li>
                    <li> <strong> Flight start</strong>: {first_image["DateTimeOriginal"]} </li>
                    <li> <strong> Flight end</strong>: {metadata_csv.iloc[-1]["DateTimeOriginal"]}</li>
                    <li> <strong> Flight duration</strong>: {self.__get_duration(first_image["DateTimeOriginal"], metadata_csv.iloc[-1]["DateTimeOriginal"])}</li>
                    <li> <strong> Median height</strong>: {median_height}</li>
                    <li> <strong> Area covered</strong>: {self.__get_area_in_hectare()}</li>
                </ul>
            """


    def __get_area_in_hectare(self) -> float:
        """ Return area in hectare """
        metadata_csv = self.get_metadata_csv()

        metadata_gdf = gpd.GeoDataFrame(metadata_csv, geometry = gpd.points_from_xy(metadata_csv['GPSLongitude'], metadata_csv['GPSLatitude']), crs = 'EPSG:4326')
        gdfutm = metadata_gdf.to_crs(metadata_gdf.estimate_utm_crs())

        survey_area = round(Polygon(gdfutm.geometry.to_list()).convex_hull.area / 10000, 2) # Area in Hectare.

        return survey_area
    
    def __get_duration(self, start_str: str, end_str: str) -> str:
        """ Compute and format duration. """
        start = datetime.strptime(start_str, "%Y:%m:%d %H:%M:%S")
        end = datetime.strptime(end_str, "%Y:%m:%d %H:%M:%S")

        total_seconds = int((end-start).total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        # Format the output
        return f"{hours}h {minutes}min {seconds}sec"
