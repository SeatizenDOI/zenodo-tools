import abc
from shapely.geometry import MultiPoint, Point
from dataclasses import dataclass

from .connector import SQLiteConnector

class Geometry:
    aled: str

class AbstractBaseDTO(abc.ABC):

    sql_connector = SQLiteConnector()

    @abc.abstractproperty
    def table_name(self): pass
    
    @abc.abstractmethod
    def add_or_update(self) -> None:
        raise NotImplementedError("Not implemented")

@dataclass
class Deposit(AbstractBaseDTO):

    doi: str
    session_name: str
    footprint: list((float, float))
    table_name = "deposit"

    def add_or_update(self):
        a = self.sql_connector.execute_query("SELECT * FROM deposit WHERE doi = ? AND session_name = ?", (self.doi, self.session_name, ))
        print(self.doi)
    
    def insert(self):
        footprint = MultiPoint(self.footprint).wkb
        print(footprint)
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, session_name, footprint) VALUES (?,?,?) "
        values = (self.doi, self.session_name, footprint)
        a = self.sql_connector.execute_query(query, values)
        print(a)


@dataclass
class Version(AbstractBaseDTO):
    doi: str
    deposit_doi: str
    table_name = "version"

    def add_or_update(self) -> None:
        print()
    
    def insert(self):
        query = f"INSERT OR IGNORE INTO {self.table_name} (doi, deposit_doi) VALUES (?,?) "
        values = (self.doi, self.deposit_doi, )
        a = self.sql_connector.execute_query(query, values)
        print(a)