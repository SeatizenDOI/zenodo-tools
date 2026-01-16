from pathlib import Path

from .ssm_base_manager import BaseSessionManager

from ...utils.lib_tools import compute_duration

class AUVSession(BaseSessionManager):

    def __init__(self, session_path, temp_folder):
        super().__init__(session_path, temp_folder)
    
    # -- Mandatory methods
    def get_restricted_files_on_zenodo(self) -> list[str]:
        return ["DCIM"]


    def get_raw_access_right(self) -> str:
        return "open"


    def get_processed_access_right(self) -> str:
        return "open"


    def build_raw_description(self) -> str:
        return f"""
<br>
This dataset was collected by an Autonomous Underwater Vehicle, Réunion - 2021-12 (project RECIF 3D) <br>
This dataset was processed with tools developped by different subsequent projects  - 2025-12 (projects PLANCHA, ...) <br>
3D reconstruction and mapping of Reunion coral ecosystems from underwater images.<br>


            {self.__get_survey_information()}
        """


    def build_processed_description(self) -> str:
        return f"""
<br>
This dataset was collected by an Autonomous Underwater Vehicle, Réunion - 2021-12 (project RECIF 3D) <br>
This dataset was processed with tools developped by different subsequent projects  - 2025-12 (projects PLANCHA, ...) <br>
3D reconstruction and mapping of Reunion coral ecosystems from underwater images.<br>


            {self.__get_survey_information()}

            {self._build_photog_description()}

        """
    
    def set_start_stop_mission_str(self) -> None:

        metadata_csv = self.get_metadata_csv()
        if metadata_csv.empty: return
        
        self.mission_start_str = metadata_csv["GPSDateTime"].min().split(".")[0].replace('-', ':')
        self.mission_stop_str = metadata_csv["GPSDateTime"].max().split(".")[0].replace('-', ':')
        

    def zip_raw_data(self) -> None:
        self._zip_dcim()
        

    def __get_survey_information(self) -> str:
        # Check for video
        metadata_csv = self.get_metadata_csv()
        first_image = metadata_csv.iloc[0]
        extensions = [Path(first_image["relative_file_path"]).suffix.lower()]
        size_images = self.get_file_dcim_size(extensions)
        number_images = len(metadata_csv)
        camera = first_image["CameraModel"]
        depth = metadata_csv["Depth"].max()
   
        return f"""
                <h2>Survey information</h2>
                <ul>
                    <li> <strong> Camera</strong>: {camera}</li>
                    <li> <strong> Number of images</strong>: {number_images} </li>
                    <li> <strong> Total size</strong>: {size_images} Gb</li>
                    <li> <strong> Flight start</strong>: {self.mission_start_str} </li>
                    <li> <strong> Flight end</strong>: {self.mission_stop_str}</li>
                    <li> <strong> Flight duration</strong>: {compute_duration(self.mission_start_date, self.mission_stop_date)}</li>
                    <li> <strong> Max depth</strong>: {depth} m</li>

                </ul>
            """