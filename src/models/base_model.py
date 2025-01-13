import abc
import enum

from ..sql_connector.sc_connector import SQLiteConnector

# State use for data in database. 
class DataStatus(enum.Enum):
    NO_DATA = 1
    MISSING_VALUE = 2
    ALREADY = 3

# Base DAO (Data Access Object).
class AbstractBaseDAO(abc.ABC):

    # Common sqlite connector.
    sql_connector = SQLiteConnector()

    # Mandatory table name.
    @property
    @abc.abstractmethod
    def table_name(self): pass