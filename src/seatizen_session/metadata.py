from .manager import SessionManager, BaseType, DCIMType

class SessionMetadata:

    def __init__(self, plancha_session: SessionManager, metadata_json: dict):
        self.plancha_session = plancha_session
        self.metadata_json = metadata_json


    def build_for_raw(self):
        data = {
            'metadata': {
                'title': self.__build_title(),
                'upload_type': 'dataset',
                'description': "Raw Data, soon more information incoming",
                'access_right': 'restricted',
                'keywords': self.__build_keywords(),
                'version': "RAW_DATA",
                'creators': self.metadata_json["creators"],
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json["related_identifiers"],
                'language': "eng",
                'contributors': self.metadata_json['contributors'],
                'access_conditions': "Everyone who ask"
            }
        }
        return data

    def build_for_processed_data(self):
        data = {
            'metadata': {
                'title': self.__build_title(),
                'upload_type': 'dataset',
                'keywords': self.__build_keywords(),
                'creators': self.metadata_json["creators"],
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json["related_identifiers"],
                'language': "eng",
                'description': self.__build_processed_description(),
                'access_right': 'open',
                'version': "PROCESSED_DATA",
                'license': self.metadata_json["license"],
                'contributors': self.metadata_json['contributors']
            }
        }
        return data

    def build_for_custom(self):
        """ Build for custom deposit. self.metadata_json["description"] value refer to the enum. """
        data = {
            'metadata': {
                'title': self.__build_title(),
                'upload_type': 'dataset',
                'keywords': self.__build_keywords(),
                'creators': self.metadata_json["creators"],
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}] + self.metadata_json["related_identifiers"],
                'language': "eng",
                'description': self.__get_description_custom(self.metadata_json["description"]),
                'access_right': 'open',
                'version': "RAW_DATA",
                'license': self.metadata_json["license"],
                'contributors': self.metadata_json['contributors']
            }
        }
        return data

    def __build_title(self):
        type = self.metadata_json["image_type"]
        return f"{type} images collected {self.__sub_title()}"

    def __sub_title(self):
        
        hp = self.metadata_json["platform"][self.plancha_session.platform] if self.plancha_session.platform in self.metadata_json["platform"] else "No key for platform"
        place = self.plancha_session.place
        country = self.plancha_session.country if self.plancha_session.country else "Somewhere"
        date = self.plancha_session.date
        prefix = "an"
        if self.plancha_session.platform in ["SCUBA"]:
            prefix = ""
        elif self.plancha_session.platform in ["PADDLE", "KITE", "MASK"]:
            prefix = "a"

        return f"by {prefix} {hp} in {place}, {country} - {date}"

    def __build_keywords(self):
        hp = [self.metadata_json["platform"][self.plancha_session.platform]] if self.plancha_session.platform in self.metadata_json["platform"] else []
        keywords = self.metadata_json["keywords"] + [
            self.plancha_session.country, 
            self.metadata_json["project_name"],
            self.plancha_session.platform
        ] + hp
        return sorted(keywords)


    def __build_processed_description(self):

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

                    <h2> Fundings </h2>
                    <br> {self.__get_fundings()}
                """


    def __get_image_acquistion_text(self):
        # Check for video
        isVideo, size_media = self.plancha_session.is_video_or_images()

        # Check for frames and georeferenced frames
        nb_frames, isGeoreferenced = self.plancha_session.check_frames()

        # Check for predictions
        j_name, j_useful, j_useless = self.plancha_session.get_jacques_stat()
        huggingface_name = self.plancha_session.get_hugging_face()
        link_hugging = "https://huggingface.co/"+huggingface_name.replace("lombardata_","lombardata/")
        
        prog_json = self.plancha_session.get_prog_json()
        if prog_json == None: return None
        fps = prog_json["dcim"]["frames_per_second"]

        if isVideo == DCIMType.NONE: return "No image or video acquisition for this session. <br>"

        return f"""
                This session has {size_media} GB of {isVideo.value}, which were trimmed into {nb_frames} frames (at {fps} fps). <br> 
                The frames are {'' if isGeoreferenced else 'not'} georeferenced. <br>
                {j_useful}% of these extracted images are useful and {j_useless}% are useless, according to predictions made by <a href="{j_name}" target="_blank">Jacques model</a>. <br>
                Multilabel predictions have been made on useful frames using <a href="{link_hugging}" target="_blank">DinoVd'eau</a> model. <br>
            """

  
    def __get_tree(self):
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


    def __get_bathymetry_text(self):

        prog_json = self.plancha_session.get_prog_json()
        if prog_json == None: return None

        return f"""
                {"We only keep the values which have a GPS correction in Q1.<br>" if prog_json["gps"]["filt_rtkfix"] else ""}
                {"We keep the points that are the waypoints.<br>" if prog_json["gps"]["filt_waypoint"] else ""}

                We keep the raw data where depth was estimated between {prog_json["bathy"]["dpth_range"]["min"]} m and {prog_json["bathy"]["dpth_range"]["max"]} m deep. <br>
                The data are first referenced against the {prog_json["gps"]["utm_ellips"]} ellipsoid. {"Then we apply the local geoid if available." if prog_json["bathy"]["use_geoid"] else ""}<br>
                At the end of processing, the data are projected into a homogeneous grid to create a raster and a shapefiles. <br>
                The size of the grid cells is {prog_json["mesh"]["spacing_m"]} m. <br>
                The raster and shapefiles are generated by {prog_json["mesh"]["method"]} interpolation. The 3D reconstruction algorithm is {prog_json["mesh"]["3Dalgo"]}. <br>
            """


    def __get_sensor_text(self):
        return f"The data are collected using a single-beam echosounder {self.plancha_session.get_echo_sounder_name()}. <br>"


    def __get_fundings(self):

        fundings = ""
        for f in self.metadata_json["fundings"]:
            fundings += f"<strong><i>{f}</i></strong><br>"
        
        return fundings
    
    def __get_software(self):
        return f"""
            All the raw data was processed using our <a href="{self.metadata_json["workflow-link"]}" target="_blank">plancha-worflow</a>. <br>
            All predictions were generated by our <a href="{self.metadata_json["inference-link"]}" target="_blank">inference pipeline</a>. <br>
            You can find all the necessary scripts to download this data in this <a href="{self.metadata_json["zenodo-link"]}" target="_blank">repository</a>. <br>
            Enjoy your data with <a href="{self.metadata_json["software-link"]}" target="_blank">SeatizenDOI</a>! <br>
        """

    def __get_description_2015(self):
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
    
    def __get_description_custom(self, description_value):
        
        if description_value == 2015:
            return self.__get_description_2015()
        
        return ""