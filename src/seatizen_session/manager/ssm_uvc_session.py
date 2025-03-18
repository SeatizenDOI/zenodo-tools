import geopandas as gpd
from pathlib import Path
from datetime import datetime
from shapely.geometry import Polygon

from .ssm_base_manager import BaseSessionManager

class UVCSession(BaseSessionManager):

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
            # {self.__get_survey_information()}
        """


    def build_processed_description(self) -> str:
        return f"""
            {self.__get_survey_information()}

        """
    

    def zip_raw_data(self) -> None:
        self._zip_dcim()
    

    def __get_survey_information(self) -> str:
        # Check for video
        metadata_csv = self.get_metadata_csv()
        first_image = metadata_csv.iloc[0]
        extensions = [Path(first_image["relative_file_path"]).suffix.lower()]
        size_images = self.get_file_dcim_size(extensions)
        number_images = len(metadata_csv)

        flight_start = metadata_csv["DateTime"].min()
        flight_end = metadata_csv["DateTime"].max()
   
        return f"""
                <h2>Survey information</h2>
                <ul>
                    <li> <strong> Camera</strong>: Amoros camera</li>
                    <li> <strong> Number of images</strong>: {number_images} </li>
                    <li> <strong> Total size</strong>: {size_images} Gb</li>
                    <li> <strong> Mission start</strong>: {flight_start} </li>
                    <li> <strong> Mission end</strong>: {flight_end}</li>
                    <li> <strong> Mission duration</strong>: {self.__get_duration(flight_start, flight_end)}</li>
                </ul>
            """

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
