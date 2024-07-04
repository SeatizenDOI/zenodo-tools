# Tips to learn Sqlite from MySQL

Load a file into sqlite : `sqlite3 file.db`


To use spatial function, we need to have spatialite package : `sudo apt-get install sqlite3 libsqlite3-mod-spatialite spatialite-bin `

We have two choices :

* We can use sqlite3 and load libsqlite3-mod-spatialite extension
* Use spatialite terminal


Interresting features to change

* `.headers on`
* `.mode column` Mode have 14 differents format (box, csv, insert, table)

By default, all table have a rowid as unique identifiers and can be access like `SELECT rowid, * FROM table_name`

SQLite has a selftest table to perform unit test see `.selftest`

Pour accéder à une valeur rentré en wkb : 
* `SELECT ST_AsText(ST_GeomFromWKB(footprint)) FROM deposit;` pour deposit
* `SELECT ST_AsText(ST_PointFromWKB(GPSPosition)) FROM frame;` pour frame si on a pas coché z dans gpkg_geometry_columns
* `SELECT ST_AsText(ST_GeomFromWKB(GPSPosition)) FROM frame;` pour frame si on a pas coché z dans gpkg_geometry_columns


