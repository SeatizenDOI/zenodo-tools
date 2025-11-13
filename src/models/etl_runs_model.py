from dataclasses import dataclass, field

from .base_model import AbstractBaseDAO

@dataclass
class ETLRunsDTO():
    last_sql_script_executed: int
    last_zenodo_harvest_at: str
    last_version_on_zenodo: str
    id: int | None = field(default=None)


@dataclass
class ETLRunsDAO(AbstractBaseDAO):

    table_name = "etl_runs"
    __etl_runs: list[ETLRunsDTO] = field(default_factory=list)


    @property
    def etl_runs(self) -> list[ETLRunsDTO]:
        """ Getter to have all deposits. """
        if len(self.__etl_runs) == 0:
            self.__get_all()
        return self.__etl_runs


    def update(self, sql_script_number: str | None = None, zenodo_harvest_at: str | None = None, version: str | None = None) -> None:
        # Get last ETL run to get the sql_script_number.
        last_etl_run = self.get_last_etl_run()
        
        # Create the new etl run.
        new_etl_run = ETLRunsDTO(
            last_sql_script_executed=sql_script_number if sql_script_number else last_etl_run.last_sql_script_executed,
            last_zenodo_harvest_at=zenodo_harvest_at if zenodo_harvest_at else last_etl_run.last_zenodo_harvest_at,
            last_version_on_zenodo=version if version else last_etl_run.last_version_on_zenodo
        )

        # Insert into the db.
        self.__insert_row(new_etl_run)


    def __insert_row(self, etl_run: ETLRunsDTO) -> None:
        """ Insert one etl_run in database. """
        query = f""" INSERT OR IGNORE INTO {self.table_name} 
                     (last_sql_script_executed, last_zenodo_harvest_at, last_version_on_zenodo) 
                     VALUES (?,?,?);
                """
        params = (  
                    etl_run.last_sql_script_executed, 
                    etl_run.last_zenodo_harvest_at,
                    etl_run.last_version_on_zenodo
                )
        self.sql_connector.execute_query(query, params)

        pass


    def __get_all(self) -> None:
        """ Retrieve all deposit. """
        query = f""" SELECT id, last_sql_script_executed, last_zenodo_harvest_at, last_version_on_zenodo
                     FROM {self.table_name};
                """
        results = self.sql_connector.execute_query(query)
        for id, last_sql_script_executed, last_zenodo_harvest_at, last_version_on_zenodo in results:
    

            self.__etl_runs.append(ETLRunsDTO(
                id=id,
                last_sql_script_executed=last_sql_script_executed,
                last_zenodo_harvest_at=last_zenodo_harvest_at,
                last_version_on_zenodo=last_version_on_zenodo
            ))


    def get_last_etl_run(self) -> ETLRunsDTO:
        query = f""" SELECT id, last_sql_script_executed, last_zenodo_harvest_at, last_version_on_zenodo
                     FROM {self.table_name}
                     ORDER BY id DESC
                     LIMIT 1;
                """
        results = self.sql_connector.execute_query(query)
        id, last_sql_script_executed, last_zenodo_harvest_at, last_version_on_zenodo = results[0]

        return ETLRunsDTO(
            id=id,
            last_sql_script_executed=last_sql_script_executed,
            last_zenodo_harvest_at=last_zenodo_harvest_at,
            last_version_on_zenodo=last_version_on_zenodo
        )
