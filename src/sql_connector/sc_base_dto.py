import abc
from dataclasses import dataclass, field

from shapely import wkb
from shapely.geometry import Polygon, Point, GeometryCollection

from .sc_connector import SQLiteConnector

class AbstractBaseDTO(abc.ABC):

    sql_connector = SQLiteConnector()

    @property
    @abc.abstractmethod
    def table_name(self): pass

class AbstractManagerDTO(abc.ABC):

    sql_connector = SQLiteConnector()

@dataclass
class Deposit(AbstractBaseDTO):

    doi: str
    session_name: str
    have_raw_data: bool
    have_processed_data: bool
    place: str | None = field(default=None)
    date: str | None = field(default=None)
    platform: str | None = field(default=None)
    footprint: GeometryCollection | None = field(default=None)
    table_name = "deposit"
    
    def insert(self):
        # We can do INSERT OR IGNORE because primary key is not an autoincrement.
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, session_name, footprint, have_raw_data, have_processed_data) VALUES (?,?,?,?,?) "
        values = (self.doi, self.session_name, self.wkb_footprint, self.have_raw_data, self.have_processed_data, )
        self.sql_connector.execute_query(query, values)
    
    @property
    def wkb_footprint(self):
        if self.footprint != None:
            return self.footprint.wkb

class DepositManager(AbstractManagerDTO):

    __deposits: list[Deposit] = None

    def get_deposits(self) -> list[Deposit]:
        if self.__deposits == None:
            self.__deposits = []
            self.__retrieve_deposits()
        return self.__deposits
    
    def __retrieve_deposits(self) -> None:

        query = "SELECT doi, session_name, alpha3_country_code, session_date, have_raw_data, have_processed_data, footprint, platform_type FROM deposit;"
        results = self.sql_connector.execute_query(query)
        for doi, session_name, place, date, have_raw_data, have_processed_data, footprint, platform_type in results:
            self.__deposits.append(Deposit(
                doi=doi,
                session_name=session_name,
                have_raw_data=have_raw_data,
                have_processed_data=have_processed_data,
                date=date,
                place=place,
                footprint=footprint,
                platform=platform_type
            ))


@dataclass
class Version(AbstractBaseDTO):
    doi: str
    deposit_doi: str
    table_name = "version"
    
    def insert(self):
        # We can do INSERT OR IGNORE because primary key is not an autoincrement.
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, deposit_doi) VALUES (?,?) " 
        values = (self.doi, self.deposit_doi, )
        self.sql_connector.execute_query(query, values)


@dataclass
class Frame():
    version_doi: str 
    filename: str
    original_filename: str
    relative_path: str | None
    gps_latitude: float | None
    gps_longitude: float | None
    gps_altitude: float | None
    gps_pitch: float | None
    gps_roll: float | None
    gps_track: float | None
    gps_fix: int | None
    gps_datetime: str
    id: int | None = field(default=None)

    @property
    def position(self) -> any:
        if self.gps_longitude == None and self.gps_latitude == None: return None
        return Point(self.gps_longitude, self.gps_latitude).wkb


class FrameManager(AbstractManagerDTO):
    __frames: list[Frame] = None


    def append(self, frame: Frame) -> None:
        if self.__frames == None:
            self.__frames = []
        self.__frames.append(frame)


    def insert(self) -> None:
        if self.__frames == None:
            print("[WARNING] Cannot insert frames in database, we don't have frames.")
            return 
        query = f"""
        INSERT INTO frame
        (version_doi, filename, original_filename, relative_path, GPSPosition, GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSDatetime, GPSFix) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?) 
        """
        values = []
        for f in self.__frames:
            values.append((f.version_doi, 
                           f.filename, 
                           f.original_filename, 
                           f.relative_path, 
                           f.position,
                           f.gps_altitude, 
                           f.gps_pitch, 
                           f.gps_roll, 
                           f.gps_track, 
                           f.gps_datetime,
                           f.gps_fix,
                        ))
        
        self.sql_connector.execute_query(query, values)
    

    def get_frame_id_from_filename(self, filename: str, frame_doi: str) -> int:
        query = f"SELECT id FROM frame WHERE version_doi = ? AND filename = ?;"
        params = (frame_doi, filename, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) > 1:
            raise NameError("We found frame with the same name and same version_doi abort")
        elif len(result) == 0:
            print(f"Image named {filename} was not found in database.")
            return -1

        return result[0][0]
    

    def __len__(self):
        return len(self.__frames) if self.__frames != None else 0


    def retrieve_frames(self) -> list[Frame]:
        """ Get all frames. """

        query = """
            SELECT id, version_doi, original_filename, filename, relative_path, GPSPosition, GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSDatetime, GPSFix 
            FROM frame 
            ORDER BY filename;
                """
        result = self.sql_connector.execute_query(query)
        
        for id, version_doi, original_filename, filename, relative_path, GPSPosition, GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSDatetime, GPSFix in result:
            lat, lon = None, None
            if GPSPosition != None:
                position = wkb.loads(GPSPosition)
                lat = position.y
                lon = position.x

            self.append(Frame(
                id=id,
                version_doi=version_doi,
                original_filename=original_filename,
                filename=filename,
                relative_path=relative_path,
                gps_latitude=lat,
                gps_longitude=lon,
                gps_altitude=GPSAltitude,
                gps_pitch=GPSPitch,
                gps_roll=GPSRoll,
                gps_track=GPSTrack,
                gps_datetime=GPSDatetime,
                gps_fix=GPSFix
            ))

        return self.__frames if self.__frames != None else []

    def retrieve_frames_from_specific_multilabel_model(self, model_id) -> list[Frame]:
        """ Get all frames with predictions from a specific multilabel_model. """

        query = """
            SELECT DISTINCT f.id, f.version_doi, f.filename, f.GPSPosition, f.GPSAltitude, f.GPSPitch, f.GPSRoll, f.GPSTrack, f.GPSFix 
            FROM frame f 
            JOIN multilabel_prediction mlp ON mlp.frame_id = f.id
            JOIN multilabel_class mlc ON mlc.id = mlp.ml_class_id
            WHERE ml_model_id = ?
            ORDER BY f.filename;
            """
        params = (model_id, )
        result = self.sql_connector.execute_query(query, params)
        
        frames = []
        for id, version_doi, filename, GPSPosition, GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSFix in result:
            lat, lon = None, None
            if GPSPosition != None:
                position = wkb.loads(GPSPosition)
                lat = position.y
                lon = position.x

            frames.append(Frame(
                id=id,
                version_doi=version_doi,
                original_filename="",
                filename=filename,
                relative_path="",
                gps_latitude=lat,
                gps_longitude=lon,
                gps_altitude=GPSAltitude,
                gps_pitch=GPSPitch,
                gps_roll=GPSRoll,
                gps_track=GPSTrack,
                gps_datetime="",
                gps_fix=GPSFix
            ))

        return frames


    def get_all_frame_name_for_specific_version(self, frame_doi: str) -> list[str]:
        """ Get all frame name for specific version """

        query = "SELECT filename FROM frame WHERE version_doi = ?"
        params = (frame_doi, )
        result = self.sql_connector.execute_query(query, params)

        return [filename for filename, in result]