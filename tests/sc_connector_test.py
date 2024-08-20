import unittest
from pathlib import Path

from src.sql_connector.sc_connector import SQLiteConnector

FOLDER = Path("/tmp/00_plancha")
FILE = Path(FOLDER, "test.gpkg")

class TestSQLConnector(unittest.TestCase):

    def test_db_creation(self):
        FOLDER.mkdir(exist_ok=True, parents=True)
        if Path.exists(FILE):
            FILE.unlink()

        sqliteconnector = SQLiteConnector()
        sqliteconnector.generate(FILE)

        self.assertTrue(Path.exists(FILE) and FILE.is_file() and FILE.suffix == ".gpkg")

    def test_select_model(self):
        sqliteconnector = SQLiteConnector()
        sqliteconnector.connect(FILE)

        print(sqliteconnector.execute_query("SELECT * FROM multilabel_model"))

        sqliteconnector.close()



if __name__ == "__main__":
    unittest.main()