
import pandas as pd
from pathlib import Path
from datetime import datetime

from .ssm_base_manager import BaseSessionManager
from ...utils.lib_tools import haversine, compute_duration

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
            {self.__get_survey_information()}
            {self.__get_gps_text()}

        """


    def build_processed_description(self) -> str:
        return f"""
            {self.__get_survey_information()}
            {self.__get_gps_text()}
        """
    

    def set_start_stop_mission_str(self) -> None:

        metadata_csv = self.get_metadata_csv()
        datetime_key = "DateTimeOriginal" if "DateTimeOriginal" in metadata_csv else "SubSecDateTimeOriginal"

        self.mission_start_str = metadata_csv[datetime_key].min().split("+")[0]
        self.mission_stop_str = metadata_csv[datetime_key].max().split("+")[0]


    def zip_raw_data(self) -> None:
        self._zip_dcim()
    

    def get_tree(self) -> str:
        return """
            YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number <br>
            ├── DCIM :  folder to store videos and photos depending on the media collected. <br>
            ├── GPS :  folder to store any positioning related file. If any kind of correction is possible on files (e.g. Post-Processed Kinematic thanks to rinex data) then the distinction between device data and base data is made. If, on the other hand, only device position data are present and the files cannot be corrected by post-processing techniques (e.g. gpx files), then the distinction between base and device is not made and the files are placed directly at the root of the GPS folder. <br>
            │   ├── BASE :  files coming from rtk station or any static positioning instrument. <br>
            │   └── DEVICE : files coming from the device. <br>
            ├── METADATA : folder with general information files about the session. <br>
            ├── PROCESSED_DATA : contain all the folders needed to store the results of the data processing of the current session. <br>
            │   ├── CPCE_ANNOTATION : All cpc files annotations made with the CPCe software. <br> 
            │   ├── IA :  destination folder for image recognition predictions. <br>
            │   └── PHOTOGRAMMETRY :  destination folder for reconstructed models in photogrammetry. <br>      
            """
    

    def __get_survey_information(self) -> str:
        # Check for video
        metadata_csv = self.get_metadata_csv()
        first_image = metadata_csv.iloc[0]
        extensions = [Path(first_image["relative_file_path"]).suffix.lower()]
        size_images = self.get_file_dcim_size(extensions)
        number_images = len(metadata_csv)
        camera = "Not enough information in metadata to get camera information."
        if "Make" in first_image and "Model" in first_image:
            camera = first_image["Make"] + " " + first_image["Model"]
   
        return f"""
                <h2>Survey information</h2>
                <ul>
                    <li> <strong> Camera</strong>: {camera}</li>
                    <li> <strong> Number of images</strong>: {number_images} </li>
                    <li> <strong> Total size</strong>: {size_images} Gb</li>
                    <li> <strong> Mission start</strong>: {self.mission_start_str} </li>
                    <li> <strong> Mission end</strong>: {self.mission_stop_str}</li>
                    <li> <strong> Mission duration</strong>: {compute_duration(self.mission_start_date, self.mission_stop_date)}</li>
                    <li> <strong> Total distance</strong>: {self.__get_total_distance(metadata_csv)} m</li>
                </ul>
            """


    def __get_total_distance(self, df: pd.DataFrame) -> float:

        # Décaler les colonnes pour calculer les distances entre points consécutifs
        df['Latitude_next'] = df['GPSLatitude'].shift(-1)
        df['Longitude_next'] = df['GPSLongitude'].shift(-1)

        # Calcul de la distance entre chaque paire de points consécutifs
        df['Distance_m'] = df.apply(lambda row: haversine(row['GPSLatitude'], row['GPSLongitude'], 
                                                        row['Latitude_next'], row['Longitude_next']), axis=1)

        # Supprimer la dernière ligne qui a une valeur NaN
        df = df.dropna(subset=['Distance_m'])

        return round(df['Distance_m'].sum())
    

    def __get_gps_text(self) -> str:
        return f"""
            <h2> GPS information: </h2>
            Surveys were conducted during low spring tides on reef areas less than 20 meters deep. <br>
            A GPS device, kept in a floating waterproof bag at the surface, recorded a position every 2 seconds while following the diver’s path. <br>
            One diver took a benthic photo every 5 meters using a compass for direction, while a second diver guided the GPS bag from the surface. <br>
            Image positions were interpolated with GPS data through time synchronization, using the timestamps embedded in the image metadata. <br>
            Details of the acquisition method can be found in this <a href="https://doi.org/10.4314/wiojms.v23i2.4" target="_blank">paper</a>.
        """