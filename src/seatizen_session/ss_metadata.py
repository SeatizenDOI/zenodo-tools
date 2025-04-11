import numpy as np
import pandas as pd
from pathlib import Path

from .manager.ssm_base_manager import BaseSessionManager

from .ss_tools import *


class SessionMetadata:

    def __init__(self, plancha_session: BaseSessionManager, metadata_json: dict) -> None:

        # JSON DATA.
        self.plancha_session = plancha_session
        self.metadata_json = metadata_json
        
        # Check if all key are presents in JSON File.
        self.check_keys()

        # Create global data.
        self.creators, self.contributors = self.__get_all_contributors()
        self.communities = self.__build_communities()


    def build_for_raw(self) -> dict:
        
        description = self.build_description(isRaw=True) if DESCRIPTION_KEY not in self.metadata_json else self.__get_description_custom(self.metadata_json[DESCRIPTION_KEY])
        title = self.__build_title() if TITLE_KEY not in self.metadata_json else self.metadata_json[TITLE_KEY]
        data = {
            'metadata': {
                'title': title,
                'upload_type': 'dataset',
                'description': description,
                'access_right': self.plancha_session.get_raw_access_right(),
                'keywords': self.__build_keywords(),
                'version': "RAW_DATA",
                'creators': self.creators,
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json["related_identifiers"],
                'language': "eng",
                'contributors': self.contributors,
                'access_conditions': "Everyone who ask",
                'communities': self.communities,
                'license': self.metadata_json[LICENSE_KEY],
                'notes': self.__get_fundings()
            }
        }
        return data


    def build_for_processed_data(self) -> dict:

        description = self.build_description(isRaw=False) if DESCRIPTION_KEY not in self.metadata_json else self.__get_description_custom(self.metadata_json[DESCRIPTION_KEY])
        title = self.__build_title() if TITLE_KEY not in self.metadata_json else self.metadata_json[TITLE_KEY]
        data = {
            'metadata': {
                'title': title,
                'upload_type': 'dataset',
                'description': description,
                'access_right': self.plancha_session.get_processed_access_right(),
                'keywords': self.__build_keywords(),
                'version': "PROCESSED_DATA",
                'creators': self.creators,
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json[IDENTIFIER_KEY],
                'language': "eng",
                'contributors': self.contributors,
                'communities': self.communities,
                'license': self.metadata_json[LICENSE_KEY],
                'notes': self.__get_fundings()
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


    def build_description(self, isRaw: bool) -> str:
        return f"""
            <i>This dataset was collected {self.__sub_title()}.</i> <br>

            <br><br>Underwater or aerial images collected by scientists or citizens can have a wide variety of use for science, management, or conservation.
            These images can be annotated and shared to train IA models which can in turn predict the objects on the images.
            We provide a set of tools (hardware and software) to collect marine data, predict species or habitat, and provide maps.<br>

            {self.plancha_session.build_raw_description() if isRaw else self.plancha_session.build_processed_description()}

            <h2> Generic folder structure </h2>
            {self.plancha_session.get_tree() if hasattr(self.plancha_session, "get_tree") else self.__get_tree()}

            <h2> Software </h2>
            {self.__get_software()}
        """


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
            keywords += [
                self.plancha_session.country, 
                self.metadata_json[PROJECT_KEY],
                self.plancha_session.platform
            ] + hp
        return sorted(list(set(keywords)))


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


    def __get_fundings(self) -> str:

        fundings = ""
        for f in self.metadata_json[FUNDINGS_KEY]:
            fundings += f"{f}<br>"
        return fundings
    

    def __get_software(self) -> str:

        txt = ""
        if self.metadata_json[LINK_W_KEY] != "":
            txt += f'All the raw data was processed using our <a href="{self.metadata_json[LINK_W_KEY]}" target="_blank">worflow</a>. <br>'
        if self.metadata_json[LINK_I_KEY] != "":
            txt += f'All predictions were generated by our <a href="{self.metadata_json[LINK_I_KEY]}" target="_blank">inference pipeline</a>. <br>'
        
        txt += f'You can find all the necessary scripts to download this data in this <a href="{self.metadata_json[LINK_Z_KEY]}" target="_blank">repository</a>. <br>'
        txt += f'Enjoy your data with <a href="{self.metadata_json[LINK_S_KEY]}" target="_blank">SeatizenDOI</a>! <br>'

        return txt
    

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
    

    def __build_communities(self) -> list | None:
        communities = [{'identifier': name} for name in self.metadata_json[COMMUNITIES_KEY]]
        return None if len(communities) == 0 else communities
    

    def check_keys(self) -> None:
        for key_mandatory in ALL_MANDATORY_KEY_METADATA_JSON:
            if key_mandatory not in self.metadata_json:
                raise KeyError(f"{key_mandatory} is a mandatory field for metadata_json.")