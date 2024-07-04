import abc
from dataclasses import dataclass, field
from shapely.geometry import MultiPoint, Point

from .sc_connector import SQLiteConnector

class AbstractBaseDTO(abc.ABC):

    sql_connector = SQLiteConnector()

    @property
    @abc.abstractmethod
    def table_name(self): pass

@dataclass
class Deposit(AbstractBaseDTO):

    doi: str
    session_name: str
    have_raw_data: bool
    have_processed_data: bool
    footprint: list[tuple[float, float]] = field(default_factory=list)
    table_name = "deposit"
    
    def insert(self):
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, session_name, footprint, have_raw_data, have_processed_data) VALUES (?,?,?,?,?) "
        values = (self.doi, self.session_name, self.wkb_footprint, self.have_raw_data, self.have_processed_data, )
        self.sql_connector.execute_query(query, values)
    
    @property
    def wkb_footprint(self):
        return MultiPoint(self.footprint).wkb


@dataclass
class Version(AbstractBaseDTO):
    doi: str
    deposit_doi: str
    table_name = "version"
    
    def insert(self):
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, deposit_doi) VALUES (?,?) "
        values = (self.doi, self.deposit_doi, )
        self.sql_connector.execute_query(query, values)


@dataclass
class Frame():
    version_doi: str 
    filename: str
    original_filename: str
    relative_path: str
    gps_latitude: float | None
    gps_longitude: float | None
    gps_altitude: float | None
    gps_pitch: float | None
    gps_roll: float | None
    gps_track: float | None
    gps_datetime: str

    @property
    def position(self) -> any:
        return Point(self.gps_longitude, self.gps_latitude).wkb


class FrameManager(AbstractBaseDTO):
    __frames: list[Frame] = None
    table_name = "frame"

    def append(self, frame: Frame) -> None:
        if self.__frames == None:
            self.__frames = []
        self.__frames.append(frame)

    def insert(self) -> None:
        query = f"""
        INSERT OR IGNORE INTO {self.table_name} 
        (version_doi, filename, original_filename, relative_path, GPSPosition, GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSDatetime) 
        VALUES (?,?,?,?,?,?,?,?,?,?) 
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
                        ))
        
        self.sql_connector.execute_query(query, values)
    
    def get_frame_id_from_filename(self, filename: str, frame_doi: str) -> int:
        query = f"SELECT id FROM {self.table_name} WHERE filename = ? AND version_doi = ?;"
        params = (filename, frame_doi)
        result = self.sql_connector.execute_query(query, params)

        if len(result) > 1:
            raise NameError("We found frame with the same name and same version_doi abort")
        elif len(result) == 0:
            print(f"Image named {filename} was not found in database.")
            return -1

        return result[0][0]
    
    def __len__(self):
        return len(self.__frames) if self.__frames != None else 0