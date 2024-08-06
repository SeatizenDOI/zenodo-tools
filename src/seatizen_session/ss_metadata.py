import numpy as np
import pandas as pd
from pathlib import Path

from .ss_manager import SessionManager, BaseType, DCIMType
from ..utils.constants import JACQUES_MODEL_NAME, MULTILABEL_MODEL_NAME, MULTILABEL_AUTHOR

from .ss_tools import *


class SessionMetadata:

    def __init__(self, plancha_session: SessionManager, metadata_json: dict) -> None:
        
        # JSON DATA.
        self.plancha_session = plancha_session
        self.metadata_json = metadata_json
        
        # Check if all key are presents in JSON File.
        self.check_keys()

        # Create global data.
        self.creators, self.contributors = self.__get_all_contributors()
        self.communities = self.__build_communities()


    def build_for_raw(self) -> dict:
        data = {
            'metadata': {
                'title': self.__build_title(),
                'upload_type': 'dataset',
                'description': "Raw Data, soon more information incoming",
                'access_right': 'restricted',
                'keywords': self.__build_keywords(),
                'version': "RAW_DATA",
                'creators': self.creators,
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json["related_identifiers"],
                'language': "eng",
                'contributors': self.contributors,
                'access_conditions': "Everyone who ask",
                'communities': self.communities
            }
        }
        return data


    def build_for_processed_data(self) -> dict:
        # Can add custom description for processed data.
        description = self.__build_processed_description() if DESCRIPTION_KEY not in self.metadata_json else self.__get_description_custom(self.metadata_json[DESCRIPTION_KEY])
        data = {
            'metadata': {
                'title': self.__build_title(),
                'upload_type': 'dataset',
                'keywords': self.__build_keywords(),
                'creators': self.creators,
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json[IDENTIFIER_KEY],
                'language': "eng",
                'description': description,
                'access_right': 'open',
                'version': "PROCESSED_DATA",
                'license': self.metadata_json[LICENSE_KEY],
                'contributors': self.contributors,
                'notes': self.__get_fundings(),
                'communities': self.communities
            }
        }
        return data


    def build_for_custom(self) -> dict:
        """ Build for custom deposit. self.metadata_json["description"] value refer to the enum. """
        if DESCRIPTION_KEY not in self.metadata_json or VERSION_KEY not in self.metadata_json:
            raise KeyError("Description is a mandatory for custom upload.")
        
        data = {
            'metadata': {
                'title': self.__build_title() if TITLE_KEY not in self.metadata_json else self.metadata_json[TITLE_KEY],
                'upload_type': 'dataset',
                'keywords': self.__build_keywords(),
                'creators': self.creators,
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json[IDENTIFIER_KEY],
                'language': "eng",
                'description': self.__get_description_custom(self.metadata_json[DESCRIPTION_KEY]),
                'access_right': self.metadata_json[ACCESS_RIGHT_KEY],
                'version': self.metadata_json[VERSION_KEY],
                'license': self.metadata_json[LICENSE_KEY],
                'contributors': self.contributors,
                'notes': self.__get_fundings(),
                'communities': self.communities
            }
        }
        return data


    def __build_title(self) -> str:
        type = self.metadata_json[IMG_TYPE_KEY]
        return f"{type} images collected {self.__sub_title()}"


    def __sub_title(self) -> str:
        hp = self.metadata_json[PLATFORM_KEY][self.plancha_session.platform] if self.plancha_session.platform in self.metadata_json[PLATFORM_KEY] else "No key for platform"
        place = self.plancha_session.place
        country = self.plancha_session.country if self.plancha_session.country else "Somewhere"
        date = self.plancha_session.date
        prefix = "an"
        if self.plancha_session.platform in ["SCUBA"]:
            prefix = ""
        elif self.plancha_session.platform in ["PADDLE", "KITE", "MASK"]:
            prefix = "a"

        return f"by {prefix} {hp} in {place}, {country} - {date}"


    def __build_keywords(self) -> list:
        keywords = self.metadata_json[KEYWORDS_KEY]
        if self.plancha_session.country != None: # Don't add calculate keyword if country is None. Something bad occurs.
            hp = [self.metadata_json[PLATFORM_KEY][self.plancha_session.platform]] if self.plancha_session.platform in self.metadata_json[PLATFORM_KEY] else []
            keywords +=  [
                self.plancha_session.country, 
                self.metadata_json[PROJECT_KEY],
                self.plancha_session.platform
            ] + hp
        return sorted(keywords)


    def __build_processed_description(self) -> str:

        # Find if we do ppk
        isPPK = self.plancha_session.check_ppk() 
        q1, q2, q5 = self.plancha_session.get_percentage(isPPK)
        basetype = self.plancha_session.get_base_type() if isPPK else BaseType.NONE
        isGPX = self.plancha_session.check_gpx() # LLH from reach or LLH generated from gpx file (Garmin watch)

        # Check for bathy
        haveSensorFile = self.plancha_session.check_sensor_file()
        isBathyGenerated = self.plancha_session.get_bathy_stat()

        return f"""

                    <i>This dataset was collected {self.__sub_title()}.</i> <br>

                    <br><br>Underwater or aerial images collected by scientists or citizens can have a wide variety of use for science, management, or conservation.
                    These images can be annotated and shared to train IA models which can in turn predict the objects on the images.
                    We provide a set of tools (hardware and software) to collect marine data, predict species or habitat, and provide maps.<br>
        

                    <h2>Image acquisition</h2>
                    {self.__get_image_acquistion_text()}
                                       
                    <h2> GPS information: </h2>
                    {"The data was processed with a PPK workflow to achieve centimeter-level GPS accuracy. <br>" if isPPK else ""}
                    Base : {"Files coming from rtk a GPS-fixed station or any static positioning instrument which can provide with correction frames." if basetype != BaseType.NONE else basetype.value} <br>
                    Device GPS : {"GPX file from Garmin watch" if isGPX else "Emlid Reach M2"} <br>
                    Quality of our data - Q1: {q1} %, Q2: {q2} %, Q5: {q5} % <br>

                    <h2> Bathymetry </h2>

                    {self.__get_sensor_text() if haveSensorFile else "No sensor file for this session."}
                    {(self.__get_bathymetry_text() if isBathyGenerated else "No bathy file, something failed during process.<br>") if haveSensorFile else ""}                  

                    <h2> Generic folder structure </h2>
                    {self.__get_tree()}

                    <h2> Software </h2>
                    <br> {self.__get_software()}
                """


    def __get_image_acquistion_text(self) -> str:
        # Check for video
        isVideo, size_media = self.plancha_session.is_video_or_images()
        if isVideo == DCIMType.NONE: return "No image or video acquisition for this session. <br>"

        # Check for frames and georeferenced frames
        nb_frames, isGeoreferenced = self.plancha_session.check_frames()
        if nb_frames == 0: return f"This session has {size_media} GB of {isVideo.value}, but no images were trimmed."

        # Check for predictions
        j_useful, j_useless = self.plancha_session.get_jacques_stat()
        link_hugging = f"https://huggingface.co/{MULTILABEL_AUTHOR}/{MULTILABEL_MODEL_NAME}"
        
        prog_json = self.plancha_session.get_prog_json()
        if len(prog_json) == 0: return ""
        fps = prog_json["dcim"]["frames_per_second"]


        return f"""
                This session has {size_media} GB of {isVideo.value}, which were trimmed into {nb_frames} frames (at {fps} fps). <br> 
                The frames are {'' if isGeoreferenced else 'not'} georeferenced. <br>
                {j_useful}% of these extracted images are useful and {j_useless}% are useless, according to predictions made by <a href="{JACQUES_MODEL_NAME}" target="_blank">Jacques model</a>. <br>
                Multilabel predictions have been made on useful frames using <a href="{link_hugging}" target="_blank">DinoVd'eau</a> model. <br>
            """

  
    def __get_tree(self) -> str:
        return """
            YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number <br>
            ├── DCIM :  folder to store videos and photos depending on the media collected. <br>
            ├── GPS :  folder to store any positioning related file. If any kind of correction is possible on files (e.g. Post-Processed Kinematic thanks to rinex data) then the distinction between device data and base data is made. If, on the other hand, only device position data are present and the files cannot be corrected by post-processing techniques (e.g. gpx files), then the distinction between base and device is not made and the files are placed directly at the root of the GPS folder. <br>
            │   ├── BASE :  files coming from rtk station or any static positioning instrument. <br>
            │   └── DEVICE : files coming from the device. <br>
            ├── METADATA : folder with general information files about the session. <br>
            ├── PROCESSED_DATA : contain all the folders needed to store the results of the data processing of the current session. <br>
            │   ├── BATHY :  output folder for bathymetry raw data extracted from mission logs. <br>
            │   ├── FRAMES :  output folder for georeferenced frames extracted from DCIM videos. <br>
            │   ├── IA :  destination folder for image recognition predictions. <br>
            │   └── PHOTOGRAMMETRY :  destination folder for reconstructed models in photogrammetry. <br>
            └── SENSORS : folder to store files coming from other sources (bathymetry data from the echosounder, log file from the autopilot,  mission plan etc.). <br>      
            """


    def __get_bathymetry_text(self) -> str:

        prog_json = self.plancha_session.get_prog_json()
        if len(prog_json) == 0: return None

        return f"""
                {"We only keep the values which have a GPS correction in Q1.<br>" if prog_json["gps"]["filt_rtkfix"] else ""}
                {"We keep the points that are the waypoints.<br>" if prog_json["gps"]["filt_waypoint"] else ""}

                We keep the raw data where depth was estimated between {prog_json["bathy"]["dpth_range"]["min"]} m and {prog_json["bathy"]["dpth_range"]["max"]} m deep. <br>
                The data are first referenced against the {prog_json["gps"]["utm_ellips"]} ellipsoid. {"Then we apply the local geoid if available." if prog_json["bathy"]["use_geoid"] else ""}<br>
                At the end of processing, the data are projected into a homogeneous grid to create a raster and a shapefiles. <br>
                The size of the grid cells is {prog_json["mesh"]["spacing_m"]} m. <br>
                The raster and shapefiles are generated by {prog_json["mesh"]["method"]} interpolation. The 3D reconstruction algorithm is {prog_json["mesh"]["3Dalgo"]}. <br>
            """


    def __get_sensor_text(self) -> str:
        return f"The data are collected using a single-beam echosounder {self.plancha_session.get_echo_sounder_name()}. <br>"


    def __get_fundings(self) -> str:

        fundings = ""
        for f in self.metadata_json[FUNDINGS_KEY]:
            fundings += f"{f}<br>"
        
        return fundings
    
    def __get_software(self) -> str:
        return f"""
            All the raw data was processed using our <a href="{self.metadata_json[LINK_W_KEY]}" target="_blank">plancha-worflow</a>. <br>
            All predictions were generated by our <a href="{self.metadata_json[LINK_I_KEY]}" target="_blank">inference pipeline</a>. <br>
            You can find all the necessary scripts to download this data in this <a href="{self.metadata_json[LINK_Z_KEY]}" target="_blank">repository</a>. <br>
            Enjoy your data with <a href="{self.metadata_json[LINK_S_KEY]}" target="_blank">SeatizenDOI</a>! <br>
        """

    def __get_description_2015(self) -> str:
        return f"""
            <i>This dataset was collected {self.__sub_title()}.</i> <br>

            <br><br>Underwater or aerial images collected by scientists or citizens can have a wide variety of use for science, management, or conservation.
            These images can be annotated and shared to train IA models which can in turn predict the objects on the images.
            We provide a set of tools (hardware and software) to collect marine data, predict species or habitat, and provide maps.<br>


            Underwater Images Collected by Scuba Diving in Réunion Island during the Hyscores Project. <br>
            For more details, visit the <a href="https://archimer.ifremer.fr/doc/00350/46122/" target="_blank">Hyscores Project</a>.<br><br>


            <h2> Generic folder structure </h2>
            {self.__get_tree()}

            <h2> Software </h2>
            <br> {self.__get_software()}
        """
    
    def __get_description_deprecated(self) -> str:
        return """
            This version is considered deprecated, please refer to the latest version of this deposit.
        """
    def __get_description_custom(self, description_value) -> str:
        if isinstance(description_value, str):
            path_description = Path(description_value)
            if not Path.exists(path_description) or not path_description.is_file():
                return ""
            
            data = ""
            with open(path_description, "r") as f:
                data = "".join(f.readlines()).replace("\n", "")
            return data

        if description_value == 2015:
            return self.__get_description_2015()
        elif description_value == -1:
            return self.__get_description_deprecated()
        return ""

    def __get_all_contributors(self) -> tuple[list, list]:
        """ Retrieve all contributors from csv. Warning, will fail if multiple abbr. """
        suivi_session_path = Path(Path.cwd(),self.metadata_json[CSV_SESSION_KEY])
        contributors_path = Path(Path.cwd(),self.metadata_json[CSV_CONTRIBUTORS_KEY])

        df_contributors = pd.read_csv(contributors_path, index_col=0)
        df_suivi_session = pd.read_csv(suivi_session_path, index_col=0)

        def build_colaborator_information(data: dict, type_work: str = "Creators") -> dict:
            if isinstance(data, pd.DataFrame):
                raise NameError("Your contributors file have two contributors with the same abbreviation. Please change it.")
            
            a = {
                    "name": data["name"],
                    "affiliation": "" if data["affiliation"] != data["affiliation"] else data["affiliation"] 
            }
            if type_work.lower() != "creators": a["type"] = type_work
            if not data["orcid"] != data["orcid"] and not data["orcid"] in ["", None, np.nan]:
                a["orcid"] = data["orcid"]
            return a


        session_info = df_suivi_session.loc[self.plancha_session.session_name]
        creators, contributors, memory = [], [], []

        # Add creators.
        for creator_abbr in session_info["Creators"].replace(" ", "").split(","):
            memory.append(creator_abbr)
            creators.append(build_colaborator_information(df_contributors.loc[creator_abbr]))
        
        # Add all abbr name for each classes.
        for col in [n for n in list(df_suivi_session) if n not in ["session_name", "Creators"]]:
            if session_info[col] != session_info[col]: continue
            for other_abbr in session_info[col].replace(" ", "").split(","):
                memory.append(other_abbr)
                contributors.append(build_colaborator_information(df_contributors.loc[other_abbr], col)) 
        
        # To avoid forgetting someone, we check if the people have been added somewhere and if not, we put them in ProjectMember.
        for remain_people_id in (df_contributors.index):
            if remain_people_id in memory: continue
            contributors.append(build_colaborator_information(df_contributors.loc[remain_people_id], "ProjectMember"))


        return creators, contributors
    
    def __build_communities(self) -> dict | None:
        communities = [{'identifier': name} for name in self.metadata_json[COMMUNITIES_KEY]]
        return None if len(communities) == 0 else communities
    
    def check_keys(self) -> None:
        for key_mandatory in ALL_MANDATORY_KEY_METADATA_JSON:
            if key_mandatory not in self.metadata_json:
                raise KeyError(f"{key_mandatory} is a mandatory field for metadata_json.")