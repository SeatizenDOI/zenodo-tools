from dataclasses import dataclass, field

from shapely import wkt
from shapely.geometry import Polygon, LineString

from .base_model import AbstractBaseDAO

@dataclass
class DepositDTO():
    doi: str
    session_name: str
    have_raw_data: bool
    have_processed_data: bool
    location: str | None = field(default=None)
    alpha3_country_code: str | None = field(default=None)
    session_date: str | None = field(default=None)
    platform: str | None = field(default=None)
    footprint: Polygon | None = field(default=None)

    @property
    def wkt_footprint(self) -> str | None:
        if self.footprint != None:
            return self.footprint.wkt
    
    @property
    def centroid(self) -> tuple[float | None, float | None]:
        if self.footprint == None: return None, None
        return self.footprint.centroid.x, self.footprint.centroid.y

@dataclass
class DepositLinestringDTO():
    deposit: DepositDTO
    footprint_linestring: LineString | None = field(default=None)
    id: int | None = field(default=None)

    @property
    def wkt_footprint_linestring(self) -> str | None:
        if self.footprint_linestring != None:
            return self.footprint_linestring.wkt


@dataclass
class VersionDTO():
    doi: str
    deposit: DepositDTO


@dataclass
class DepositDAO(AbstractBaseDAO):

    table_name = "deposit"
    __deposits: list[DepositDTO] = field(default_factory=list)
    __deposits_by_key: dict[str, DepositDTO] = field(default_factory=dict)


    @property
    def deposits(self) -> list[DepositDTO]:
        """ Getter to have all deposits. """
        if len(self.__deposits) == 0:
            self.__get_all()
        return self.__deposits


    def insert(self, deposit: DepositDTO) -> None:
        """ Insert one deposit in database. """
        query = f""" INSERT OR IGNORE INTO {self.table_name} 
                     (doi, session_name, footprint, have_processed_data, have_raw_data) 
                     VALUES (?,?,ST_GeomFromText(?),?,?);
                """
        params = (  
                    deposit.doi, 
                    deposit.session_name, 
                    deposit.wkt_footprint,
                    deposit.have_processed_data, 
                    deposit.have_raw_data,
                )
        self.sql_connector.execute_query(query, params)


    def get_deposit_by_doi(self, deposit_doi: str) -> DepositDTO:
        """ Retrieve deposit filter by the deposit_doi parameter. """
        if deposit_doi in self.__deposits_by_key:
            return self.__deposits_by_key.get(deposit_doi)
        
        query = f""" SELECT doi, session_name, ST_AsText(footprint), have_processed_data, have_raw_data,
                     platform_type, session_date, alpha3_country_code, location 
                     FROM {self.table_name} WHERE doi = ?;
                """
        params = (deposit_doi, )
        result = self.sql_connector.execute_query(query, params)
        
        if result == None: 
            raise NameError("Deposit DOI not found. Foreigh key failed.")
        
        doi, session_name, footprint_wkt, hpd, hrd,\
            platform, date, country_code, location = result[0]
        
        # Convert bytes to object.
        footprint = wkt.loads(footprint_wkt)
            
        deposit = DepositDTO(
            doi=doi,session_name=session_name,session_date=date,
            have_processed_data=hpd, have_raw_data=hrd,
            platform=platform,alpha3_country_code=country_code,
            location=location, footprint=footprint
        )
        self.__deposits_by_key[deposit.doi] = deposit

        return deposit
    

    def __get_all(self) -> None:
        """ Retrieve all deposit. """
        query = f""" SELECT doi, session_name, ST_AsText(footprint),
                     have_processed_data, have_raw_data, platform_type, session_date,
                     alpha3_country_code, location 
                     FROM {self.table_name};
                """
        results = self.sql_connector.execute_query(query)
        for doi, session_name, footprint_wkt, hpd, hrd,\
            platform, date, country_code, location in results:
            
            footprint = wkt.loads(footprint_wkt)

            self.__deposits.append(DepositDTO(
                doi=doi,
                session_name=session_name,
                session_date=date,
                have_processed_data=hpd,
                have_raw_data=hrd,
                platform=platform,
                alpha3_country_code=country_code,
                location=location,
                footprint=footprint
            ))

@dataclass
class DepositLinestringDAO(AbstractBaseDAO):
    table_name = "deposit_linestring"
    __depositDAO = DepositDAO()

    __deposits_linestrings: list[DepositLinestringDTO] = field(default_factory=list)
    __deposits_linestrings_by_key: dict[int, DepositLinestringDTO] = field(default_factory=dict)


    @property
    def deposits_linestring(self) -> list[DepositLinestringDTO]:
        """ Getter to have all deposit_linestring. """
        if len(self.__deposits_linestrings) == 0:
            self.__get_all()
        return self.__deposits_linestrings
    
    
    def insert(self, deposit_linestring: DepositLinestringDTO) -> None:
        """ Insert one deposit_linestring in database. """
        query = f""" INSERT OR IGNORE INTO {self.table_name} 
                     (deposit_doi, footprint_linestring) 
                     VALUES (?,ST_GeomFromText(?));
                """
        params = (  
            deposit_linestring.deposit.doi, 
            deposit_linestring.wkt_footprint_linestring, 
        )
        self.sql_connector.execute_query(query, params)

    # !FIXME All get by ID need to be retrieve in one time to avoid n select in the database
    # !FIXME If too much occurences, get all id to retrieve and do only one select with IN statement
    def get_deposit_linestring_by_id(self, deposit_linestring_id: int) -> DepositLinestringDTO:
        """ Retrieve deposit_linestring filter by the deposit_doi parameter. """
        if deposit_linestring_id in self.__deposits_linestrings_by_key:
            return self.__deposits_linestrings_by_key.get(deposit_linestring_id)
        
        query = f""" SELECT id, deposit_doi, ST_AsText(footprint_linestring)
                     FROM {self.table_name} WHERE id = ?;
                """
        params = (deposit_linestring_id, )
        result = self.sql_connector.execute_query(query, params)
        
        if result == None: 
            raise NameError("Deposit linestring ID not found. Foreigh key failed.")
        
        id, deposit_doi, footprint_linestring_wkt = result[0]
        
        # Convert bytes to object.
        footprint = wkt.loads(footprint_linestring_wkt)
        deposit = self.__depositDAO.get_deposit_by_doi(deposit_doi)

        deposit_linestring = DepositLinestringDTO(
            id=id, deposit=deposit, footprint_linestring=footprint
        )
        self.__deposits_linestrings_by_key[deposit_linestring.id] = deposit_linestring

        return deposit_linestring


    def __get_all(self) -> None:
        """ Retrieve all deposit_linestring. """
        query = f""" SELECT id, deposit_doi, ST_AsText(footprint_linestring)
                     FROM {self.table_name};
                """
        results = self.sql_connector.execute_query(query)
        
        for id, deposit_doi, footprint_linestring_wkt in results:
            
            footprint_linestring = wkt.loads(footprint_linestring_wkt)
            deposit = self.__depositDAO.get_deposit_by_doi(deposit_doi)

            self.__deposits_linestrings.append(DepositLinestringDTO(
                id=id,
                deposit=deposit,
                footprint_linestring=footprint_linestring
            ))


@dataclass
class VersionDAO(AbstractBaseDAO):

    table_name = "version"
    __depositDAO = DepositDAO()

    __versions: list[VersionDTO] = field(default_factory=list)
    __versions_by_doi: dict[str, VersionDTO] = field(default_factory=dict)


    @property
    def versions(self) -> list[VersionDTO]:
        """ Getter to have all versions. """
        if len(self.__versions) == 0:
            self.__get_all()
        return self.__versions


    def insert(self, version: VersionDTO) -> None:
        """ Insert one version in database. """
        query = f""" INSERT OR IGNORE INTO {self.table_name} (doi, deposit_doi)
                     VALUES (?,?)
                 """
        params = (version.doi, version.deposit.doi)
        self.sql_connector.execute_query(query, params)


    def get_version_by_doi(self, version_doi: str) -> VersionDTO:
        """ Get version filter by doi. """        
        if version_doi in self.__versions_by_doi:
            return self.__versions_by_doi.get(version_doi)
        
        query = f""" SELECT doi, deposit_doi FROM {self.table_name} WHERE doi = ?; """
        params = (version_doi, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[WARNING] No version found for this doi.")
        
        doi, deposit_doi = result[0]
        deposit = self.__depositDAO.get_deposit_by_doi(deposit_doi)
        
        version = VersionDTO(doi=doi, deposit=deposit)
        self.__versions_by_doi[doi] = version
        return version


    def __get_all(self) -> None:
        """ Retrieve all versions. """
        query = f""" SELECT doi, deposit_doi FROM {self.table_name} """
        for doi, deposit_doi in self.sql_connector.execute_query(query):
            deposit = self.__depositDAO.get_deposit_by_doi(deposit_doi)
            
            self.__versions.append(VersionDTO(
                doi=doi, deposit=deposit
            ))