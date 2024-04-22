from .PlanchaSession import PlanchaSession, BaseType, DCIMType

class PlanchaMetadata:

    def __init__(self, plancha_session: PlanchaSession, metadata_json: dict):
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
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}],
                'language': "eng"
            }
        }

        return data

    def __build_title(self):
        hp = self.metadata_json["human_readable_platform"]
        type = self.metadata_json["image_type"]
        place = self.plancha_session.place
        country = self.plancha_session.country if self.plancha_session.country else "Somewhere"
        date = self.plancha_session.date

        return f"{type} images collected by {hp} in {place}, {country} - {date}"

    
    def __build_keywords(self):
        keywords = self.metadata_json["keywords"] + [
            self.plancha_session.country, 
            self.metadata_json["project_name"],
            self.metadata_json["human_readable_platform"],
            self.metadata_json["platform"]
        ]
        return sorted(keywords)
    
    def build_for_processed_data(self):
        data = {
            'metadata': {
                'title': self.__build_title(),
                'upload_type': 'dataset',
                'keywords': self.__build_keywords(),
                'creators': self.metadata_json["creators"],
                'related_identifiers': [{'identifier': 'urn:'+self.plancha_session.session_name, 'relation': 'isAlternateIdentifier'}],
                'language': "eng",
                'description': self.__build_processed_description(),
                'access_right': 'open',
                'version': "PROCESSED_DATA",
                'license': self.metadata_json["license"]
            }
        }

        return data
    
    def __build_processed_description(self):

        # Find if we do ppk
        isPPK = self.plancha_session.check_ppk() 
        q1, q2, q5 = self.plancha_session.get_percentage(isPPK)
        basetype = self.plancha_session.get_base_type() if isPPK else BaseType.NONE
        isGPX = self.plancha_session.check_gpx() # LLH from reach or LLH generated from gpx file (Garmin watch)

        # Check for bathy
        haveSensorFile = self.plancha_session.check_sensor_file()
        isBathyGenerated = self.plancha_session.get_bathy_stat()

        hp = self.metadata_json["human_readable_platform"]
        place = self.plancha_session.place
        country = self.plancha_session.country if self.plancha_session.country else "Somewhere"
        date = self.plancha_session.date

        return f"""

                    <i>This dataset was collected by {hp} in {place} {country}, {date}.</i> <br>

                    <h2>Image acquisition</h2>
                    {self.__get_image_acquistion_text()}
                                       
                    <h2> GPS information: </h2>
                    Base : {basetype.value} <br>
                    Device GPS : {"GPX file from Garmin watch" if isGPX else "Emlid Reach M2"} <br>
                    {"The data was processed with a PPK workflow to achieve centimeter GPS accuracy. <br>" if isPPK else ""}
                    Quality of our data - Q1: {q1} %, Q2: {q2} %, Q5: {q5} % <br>

                    <h2> Bathymetry </h2>

                    {self.__get_sensor_text() if haveSensorFile else "No sensor file for this session."}
                    {(self.__get_bathymetry_text() if isBathyGenerated else "No bathy file, something failed during process.<br>") if haveSensorFile else ""}                  


                    <h2> Generic folder structure </h2>
                    {self.__get_tree()}
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

        if isVideo == DCIMType.NONE: return "No image or video acquisition for this session. <br>"

        return f"""
                This session have {size_media} Go of {isVideo.value}, which were trimmed in {nb_frames} frames. <br> 
                The frames are {'' if isGeoreferenced else 'not'} georeferenced. <br>
                {j_useful}% of these are useful and {j_useless}% are useless, according to predictions made by <a href="{j_name}" target="_blank">Jacques model</a>. <br>
                Multilabel predictions have been made on useful frames thanks to <a href="{link_hugging}" target="_blank">DinoVd'eau</a> model. <br>
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
                {"We keep the points that are between the mission waypoints.<br>" if prog_json["gps"]["filt_waypoint"] else ""}

                We keep the raw data between {prog_json["bathy"]["dpth_range"]["min"]}m and {prog_json["bathy"]["dpth_range"]["max"]}m. <br>
                The data are first referenced against the {prog_json["gps"]["utm_ellips"]} ellipsoid. {"Then we apply the local geoid." if prog_json["bathy"]["use_geoid"] else ""}<br>
                At the end of processing, the data is projected into a homogeneous grid to create a raster and shapefiles. <br>
                The size of the grid cells is {prog_json["mesh"]["spacing_m"]}m. <br>
                The previous files were generated by {prog_json["mesh"]["method"]} interpolation.  The 3D reconstruction algorithm is {prog_json["mesh"]["3Dalgo"]}. <br>
            """
    
    def __get_sensor_text(self):
        return f"The data were acquired with a single-beam echosounder {self.plancha_session.get_echo_sounder_name()}. <br>"