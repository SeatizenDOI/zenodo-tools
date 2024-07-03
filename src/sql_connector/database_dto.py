import abc
from dataclasses import dataclass, field
from shapely.geometry import MultiPoint, Point

from .connector import SQLiteConnector

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
        footprint = MultiPoint(self.footprint).wkb
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, session_name, footprint) VALUES (?,?,?) "
        values = (self.doi, self.session_name, footprint)
        self.sql_connector.execute_query(query, values)


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
class Frame(AbstractBaseDTO):
    version_doi: str 
    filename: str
    original_filename: str
    relative_path: str
    gps_latitude: float
    gps_longitude: float
    gps_altitude: float
    gps_pitch: float
    gps_roll: float
    gps_track: float
    creation_date: str

    table_name = "frame"
    
    def insert(self):
        query = f"INSERT OR IGNORE INTO {self.table_name} (filename, version_doi) VALUES (?,?) "
        values = (self.filename, self.version_doi, )
        self.sql_connector.execute_query(query, values)