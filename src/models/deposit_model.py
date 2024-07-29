from dataclasses import dataclass, field

from shapely import wkb
from shapely.geometry import GeometryCollection

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
    footprint: GeometryCollection | None = field(default=None)

    @property
    def wkb_footprint(self) -> bytes | None:
        if self.footprint != None:
            return self.footprint.wkb


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
                     VALUES (?,?,?,?,?);
                """
        params = (  
                    deposit.doi, 
                    deposit.session_name, 
                    deposit.wkb_footprint, 
                    deposit.have_processed_data, 
                    deposit.have_raw_data,
                )
        self.sql_connector.execute_query(query, params)


    def get_deposit_by_doi(self, deposit_doi: str) -> DepositDTO:
        """ Retrieve deposit filter by the deposit_doi parameter. """
        if deposit_doi in self.__deposits_by_key:
            return self.__deposits_by_key.get(deposit_doi)
        
        query = f""" SELECT doi, session_name, footprint, have_processed_data, have_raw_data,
                     platform_type, session_date, alpha3_country_code, location 
                     FROM {self.table_name} WHERE doi = ?;
                """
        params = (deposit_doi, )
        result = self.sql_connector.execute_query(query, params)
        
        if result == None: 
            raise NameError("Deposit DOI not found. Foreigh key failed.")
        
        doi, session_name, footprint_wkb, hpd, hrd,\
            platform, date, country_code, location = result[0]
        
        # Convert bytes to object.
        footprint = wkb.loads(footprint_wkb)
            
        deposit = DepositDTO(
            doi=doi,session_name=session_name,session_date=date,
            have_processed_data=hpd, have_raw_data=hrd,
            platform=platform,alpha3_country_code=country_code,location=location,
            footprint=footprint 
        )
        self.__deposits_by_key[deposit.doi] = deposit

        return deposit
    

    def __get_all(self) -> list[DepositDTO]:
        """ Retrieve all deposit. """
        query = f""" SELECT doi, session_name, footprint, have_processed_data, have_raw_data,
                     platform_type, session_date, alpha3_country_code, location 
                     FROM {self.table_name};
                """
        results = self.sql_connector.execute_query(query)
        for doi, session_name, footprint_wkb, hpd, hpr,\
            platform, date, country_code, location in results:
            
            footprint = wkb.loads(footprint_wkb)
            self.__deposits.append(DepositDTO(
                doi=doi,
                session_name=session_name,
                session_date=date,
                have_processed_data=hpd,
                have_raw_data=hpr,
                platform=platform,
                alpha3_country_code=country_code,
                location=location,
                footprint=footprint 
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