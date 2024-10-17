------------------------------------
-- Mandatory table for Geopackage --
------------------------------------

-- gpkg_spatial_ref_sys table: Contains all referential
CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
    srs_name TEXT NOT NULL,
    srs_id INTEGER NOT NULL PRIMARY KEY,
    organization TEXT NOT NULL,
    organization_coordsys_id INTEGER NOT NULL,
    definition TEXT NOT NULL,
    description TEXT
);

INSERT OR IGNORE INTO gpkg_spatial_ref_sys (srs_name, srs_id, organization, organization_coordsys_id, definition, description) VALUES 
('WGS 84', 4326, 'EPSG', 4326, 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]', 'World Geodetic System 1984'),
('undefined Cartesian coordinate', -1, 'NONE', -1, 'undefined', "undefined Cartesian coordinate reference systems"),
('undefined geographic coordinate', 0, 'NONE', 0, 'undefined', "undefined geographic coordinate reference systems");

-- gpkg_contents table
CREATE TABLE gpkg_contents (
    table_name TEXT NOT NULL PRIMARY KEY,
    data_type TEXT NOT NULL,
    identifier TEXT UNIQUE,
    description TEXT DEFAULT '',
    last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    min_x DOUBLE,
    min_y DOUBLE,
    max_x DOUBLE,
    max_y DOUBLE,
    srs_id INTEGER,
    CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
);
INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id, min_x, min_y, max_x, max_y) VALUES 
('deposit', 'features', 'deposit', 'Table with deposit Polygon as footprint', 4326, 200, 80, -200, -80),
('deposit_linestring', 'features', 'deposit_linestring', 'Table with deposit linestring as footprint', 4326, 200, 80, -200, -80),
('frame', 'features', 'frame', 'Table with frame points', 4326, 200, 80, -200, -80);


-- gpkg_geometry_columns table
CREATE TABLE gpkg_geometry_columns (
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    geometry_type_name TEXT NOT NULL,
    srs_id INTEGER NOT NULL,
    z TINYINT NOT NULL,
    m TINYINT NOT NULL,
    PRIMARY KEY (table_name, column_name),
    CONSTRAINT fk_gpkg_geometry_columns_gpkg_contents FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
    CONSTRAINT fk_gpkg_geometry_columns_gpkg_spatial_ref_sys FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
);

INSERT INTO gpkg_geometry_columns (table_name, column_name, geometry_type_name, srs_id, z, m) VALUES
('deposit', 'footprint', 'POLYGON', 4326, 0, 0),
('deposit_linestring', 'footprint_linestring', 'LINESTRING', 4326, 0, 0),
('frame', 'GPSPosition', 'POINT', 4326, 0, 0);

-- gpkg_extensions. Mandatory to use with rtree
CREATE TABLE gpkg_extensions (
    table_name TEXT,
    column_name TEXT,
    extension_name TEXT NOT NULL,
    definition TEXT NOT NULL,
    scope TEXT NOT NULL,
    CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name)
);
INSERT INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope) VALUES
('deposit', 'footprint', 'gpkg_rtree_index', "https://www.geopackage.org/spec140/#extension_rtree", "write-only"),
('deposit_linestring', 'footprint_linestring', 'gpkg_rtree_index', "https://www.geopackage.org/spec140/#extension_rtree", "write-only"),
('frame', 'GPSPosition', 'gpkg_rtree_index', "https://www.geopackage.org/spec140/#extension_rtree", "write-only");

----------------------------------------
-- Base table for zenodo architecture --
----------------------------------------

-- Deposit table
CREATE TABLE IF NOT EXISTS deposit (
    doi TEXT NOT NULL PRIMARY KEY,
    session_name TEXT NOT NULL,
    footprint POLYGON,
    have_processed_data INTEGER NOT NULL,
    have_raw_data INTEGER NOT NULL,
    session_date TEXT GENERATED ALWAYS AS (
        SUBSTR(session_name, 1, 4) || '-' ||
        SUBSTR(session_name, 5, 2) || '-' ||
        SUBSTR(session_name, 7, 2)
    ) VIRTUAL,
    alpha3_country_code TEXT GENERATED ALWAYS AS (SUBSTR(session_name, 10, 3)) VIRTUAL,
    location TEXT GENERATED ALWAYS AS (
        UPPER(SUBSTR (
            SUBSTR(session_name, INSTR(session_name, '_') + 1),
            INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '-') + 1,
            INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1),INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '-') + 1), '_') - 1
        ))
    ) VIRTUAL,
    platform_type TEXT GENERATED ALWAYS AS (
        UPPER(SUBSTR (
            SUBSTR(session_name, INSTR(session_name, '_') + 1), 
            INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1,
			CASE
                WHEN INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '-') > 0 -- 20230906_REU-BOUCAN_ASV-1_01
                THEN INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '-') - 1
				WHEN INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '_') = 0 -- 20230906_REU-BOUCAN_ASV
				THEN LENGTH(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1))
                ELSE INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '_') - 1 -- 20230906_REU-BOUCAN_ASV_01
            END
        ))
    ) VIRTUAL
);
CREATE VIRTUAL TABLE rtree_deposit_footprint USING rtree(id, minx, maxx, miny, maxy);


-- Deposit linestring
CREATE TABLE IF NOT EXISTS deposit_linestring (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    deposit_doi TEXT NOT NULL,
    footprint_linestring LINESTRING,
    CONSTRAINT fk_deposit_deposit_linestring FOREIGN KEY (deposit_doi) REFERENCES deposit(doi)
);
CREATE VIRTUAL TABLE rtree_deposit_linestring_footprint_linestring USING rtree(id, minx, maxx, miny, maxy);


-- Version table
CREATE TABLE IF NOT EXISTS version (
    doi TEXT NOT NULL PRIMARY KEY,
    deposit_doi TEXT NOT NULL,
    CONSTRAINT fk_deposit_version FOREIGN KEY (deposit_doi) REFERENCES deposit(doi)
);

-- Frame table
CREATE TABLE IF NOT EXISTS frame (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    version_doi TEXT NOT NULL,
    OriginalFileName TEXT NOT NULL,
    filename TEXT NOT NULL,
    relative_file_path TEXT,
    GPSPosition POINT, -- Latitude, Longitude
    GPSAltitude REAL,
    GPSPitch REAL,
    GPSRoll REAL,
    GPSTrack REAL,
    GPSDatetime DATETIME,
    GPSFix INTEGER,
    CONSTRAINT fk_frame_version FOREIGN KEY (version_doi) REFERENCES version(doi)
);
CREATE VIRTUAL TABLE rtree_frame_GPSPosition USING rtree(id, minx, maxx, miny, maxy);

------------------------------------
-- All table for multilabel stuff --
------------------------------------

-- Multilabel label
CREATE TABLE IF NOT EXISTS multilabel_label (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    creation_date DATETIME NOT NULL,
    description TEXT,
    id_gbif INTEGER,
    code_gcrmn TEXT
);

-- Multilabel model
CREATE TABLE IF NOT EXISTS multilabel_model (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    link TEXT NOT NULL,
    doi TEXT,
    creation_date DATETIME NOT NULL
);

-- Multilabel class
CREATE TABLE IF NOT EXISTS multilabel_class (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT COMMENT `Alias to multilabel_label.name`,
    threshold REAL NOT NULL,
    ml_label_id INTEGER NOT NULL,
    ml_model_id INTEGER NOT NULL,
    CONSTRAINT fk_ml_class_ml_label FOREIGN KEY (ml_label_id) REFERENCES multilabel_label(id),
    CONSTRAINT fk_ml_class_ml_model FOREIGN KEY (ml_model_id) REFERENCES multilabel_model(id)
);

-- Multilabel predictions
CREATE TABLE IF NOT EXISTS multilabel_prediction (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    score REAL NOT NULL,
    version_doi TEXT NOT NULL,
    frame_id INTEGER NOT NULL,
    ml_class_id INTEGER NOT NULL,
    CONSTRAINT fk_ml_prediction_version FOREIGN KEY (version_doi) REFERENCES version(doi),
    CONSTRAINT fk_ml_prediction_frame FOREIGN KEY (frame_id) REFERENCES frame(id),
    CONSTRAINT fk_ml_prediction_ml_class FOREIGN KEY (ml_class_id) REFERENCES multilabel_class(id)
);

-- Multilabel annotation session
CREATE TABLE IF NOT EXISTS multilabel_annotation_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    annotation_date DATETIME NOT NULL,
    dataset_name TEXT NOT NULL,
    author_name TEXT NOT NULL
);

-- Multilabel annotation 
CREATE TABLE IF NOT EXISTS multilabel_annotation (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    value TINYINT NOT NULL,
    frame_id INTEGER NOT NULL,
    ml_label_id INTEGER NOT NULL,
    ml_annotation_session_id INTEGER NOT NULL,
    CONSTRAINT fk_ml_annotation_frame FOREIGN KEY (frame_id) REFERENCES frame(id),
    CONSTRAINT fk_ml_annotation_ml_label FOREIGN KEY (ml_label_id) REFERENCES multilabel_label(id),
    CONSTRAINT fk_ml_annotation_ml_anno_session FOREIGN KEY (ml_annotation_session_id) REFERENCES multilabel_annotation_session(id)
);


-- Create all index
CREATE INDEX IF NOT EXISTS idx_frame_id ON frame (id);
CREATE INDEX IF NOT EXISTS idx_filename_version_doi ON frame (filename, version_doi);

CREATE INDEX IF NOT EXISTS idx_multilabel_prediction_frame_id_version ON multilabel_prediction (frame_id, version_doi);

----------------------------------------------------------
-- Trigger to update all footprint size in gpkg_contents --
----------------------------------------------------------

/* Trigger to update max footprint of geopackage */
CREATE TRIGGER gpkg_contents_deposit_footprint_update AFTER INSERT ON deposit
  WHEN (new.footprint NOT NULL AND NOT ST_IsEmpty(NEW.footprint))
BEGIN
  UPDATE gpkg_contents SET
    min_x = MIN(ST_MinX(NEW.footprint), min_x),
    max_x = MAX(ST_MaxX(NEW.footprint), max_x),
    min_y = MIN(ST_MinY(NEW.footprint), min_y),
    max_y = MAX(ST_MaxY(NEW.footprint), max_y)
  WHERE table_name = "deposit";
END;

/* Trigger to update max footprint of geopackage */
CREATE TRIGGER gpkg_contents_deposit_footprint_linestring_update AFTER INSERT ON deposit_linestring
  WHEN (new.footprint_linestring NOT NULL AND NOT ST_IsEmpty(NEW.footprint_linestring))
BEGIN
  UPDATE gpkg_contents SET
    min_x = MIN(ST_MinX(NEW.footprint_linestring), min_x),
    max_x = MAX(ST_MaxX(NEW.footprint_linestring), max_x),
    min_y = MIN(ST_MinY(NEW.footprint_linestring), min_y),
    max_y = MAX(ST_MaxY(NEW.footprint_linestring), max_y)
  WHERE table_name = "deposit_linestring";
END;

CREATE TRIGGER gpkg_contents_frame_GPSPosition_update AFTER INSERT ON frame
  WHEN (new.GPSPosition NOT NULL AND NOT ST_IsEmpty(NEW.GPSPosition))
BEGIN
  UPDATE gpkg_contents SET
    min_x = MIN(ST_MinX(NEW.GPSPosition), min_x),
    max_x = MAX(ST_MaxX(NEW.GPSPosition), max_x),
    min_y = MIN(ST_MinY(NEW.GPSPosition), min_y),
    max_y = MAX(ST_MaxY(NEW.GPSPosition), max_y)
  WHERE table_name = "frame";
END;


-----------------------------------------------------------------
-- Trigger to update rtree value when manipulating frame table. --
-----------------------------------------------------------------

/* Conditions: Insertion of non-empty geometry
   Actions   : Insert record into R-tree */
CREATE TRIGGER rtree_frame_GPSPosition_insert AFTER INSERT ON frame
  WHEN (new.GPSPosition NOT NULL AND NOT ST_IsEmpty(NEW.GPSPosition))
BEGIN
  INSERT OR REPLACE INTO rtree_frame_GPSPosition VALUES (
    NEW.id,
    ST_MinX(NEW.GPSPosition), ST_MaxX(NEW.GPSPosition),
    ST_MinY(NEW.GPSPosition), ST_MaxY(NEW.GPSPosition)
  );
END;

/* rtree_frame_GPSPosition_update1 is deprecated and is replaced by
    rtree_frame_GPSPosition_update6 and rtree_frame_GPSPosition_update7 */

/* Conditions: Update of geometry column to empty geometry
               No row ID change
   Actions   : Remove record from R-tree */
CREATE TRIGGER rtree_frame_GPSPosition_update2 AFTER UPDATE OF GPSPosition ON frame
  WHEN OLD.id = NEW.id AND
       (NEW.GPSPosition ISNULL OR ST_IsEmpty(NEW.GPSPosition))
BEGIN
  DELETE FROM rtree_frame_GPSPosition WHERE id = OLD.id;
END;

/* rtree_frame_GPSPosition_update3 is deprecated and is replaced by
    rtree_frame_GPSPosition_update5 */

/* Conditions: Update of any column
               Row ID change
               Empty geometry
   Actions   : Remove record from R-tree for old and new id */
CREATE TRIGGER rtree_frame_GPSPosition_update4 AFTER UPDATE ON frame
  WHEN OLD.id != NEW.id AND
       (NEW.GPSPosition ISNULL OR ST_IsEmpty(NEW.GPSPosition))
BEGIN
  DELETE FROM rtree_frame_GPSPosition WHERE id IN (OLD.id, NEW.id);
END;

/* Conditions: Update of any column
               Row ID change
               Non-empty geometry
   Actions   : Remove record from R-tree for old id
               Insert record into R-tree for new id */
CREATE TRIGGER rtree_frame_GPSPosition_update5 AFTER UPDATE ON frame
  WHEN OLD.id != NEW.id AND
       (NEW.GPSPosition NOTNULL AND NOT ST_IsEmpty(NEW.GPSPosition))
BEGIN
  DELETE FROM rtree_frame_GPSPosition WHERE id = OLD.id;
  INSERT OR REPLACE INTO rtree_frame_GPSPosition VALUES (
    NEW.id,
    ST_MinX(NEW.GPSPosition), ST_MaxX(NEW.GPSPosition),
    ST_MinY(NEW.GPSPosition), ST_MaxY(NEW.GPSPosition)
  );
END;

/* Conditions: Update a non-empty geometry with another non-empty geometry
   Actions   : Replace record from R-tree for id */
CREATE TRIGGER rtree_frame_GPSPosition_update6 AFTER UPDATE OF GPSPosition ON frame
  WHEN OLD.id = NEW.id AND
       (NEW.GPSPosition NOTNULL AND NOT ST_IsEmpty(NEW.GPSPosition)) AND
       (OLD.GPSPosition NOTNULL AND NOT ST_IsEmpty(OLD.GPSPosition))
BEGIN
  UPDATE rtree_frame_GPSPosition SET
    minx = ST_MinX(NEW.GPSPosition),
    maxx = ST_MaxX(NEW.GPSPosition),
    miny = ST_MinY(NEW.GPSPosition),
    maxy = ST_MaxY(NEW.GPSPosition)
  WHERE id = NEW.id;
END;

/* Conditions: Update a null/empty geometry with a non-empty geometry
   Actions   : Insert record into R-tree for new id */
CREATE TRIGGER rtree_frame_GPSPosition_update7 AFTER UPDATE OF GPSPosition ON frame
  WHEN OLD.id = NEW.id AND
       (NEW.GPSPosition NOTNULL AND NOT ST_IsEmpty(NEW.GPSPosition)) AND
       (OLD.GPSPosition ISNULL OR ST_IsEmpty(OLD.GPSPosition))
BEGIN
  INSERT INTO rtree_frame_GPSPosition VALUES (
    NEW.id,
    ST_MinX(NEW.GPSPosition), ST_MaxX(NEW.GPSPosition),
    ST_MinY(NEW.GPSPosition), ST_MaxY(NEW.GPSPosition)
  );
END;

/* Conditions: Row deleted
   Actions   : Remove record from R-tree for old id */
CREATE TRIGGER rtree_frame_GPSPosition_delete AFTER DELETE ON frame
  WHEN old.GPSPosition NOT NULL
BEGIN
  DELETE FROM rtree_frame_GPSPosition WHERE id = OLD.id;
END;

--------------------------------------------------------------------
-- Trigger to update rtree value when manipulating deposit table. --
--------------------------------------------------------------------


/* Conditions: Insertion of non-empty geometry
   Actions   : Insert record into R-tree */
CREATE TRIGGER rtree_deposit_footprint_insert AFTER INSERT ON deposit
  WHEN (new.footprint NOT NULL AND NOT ST_IsEmpty(NEW.footprint))
BEGIN
  INSERT OR REPLACE INTO rtree_deposit_footprint VALUES (
    NEW.doi,
    ST_MinX(NEW.footprint), ST_MaxX(NEW.footprint),
    ST_MinY(NEW.footprint), ST_MaxY(NEW.footprint)
  );
END;

/* rtree_deposit_footprint_update1 is deprecated and is replaced by
    rtree_deposit_footprint_update6 and rtree_deposit_footprint_update7 */

/* Conditions: Update of geometry column to empty geometry
               No row ID change
   Actions   : Remove record from R-tree */
CREATE TRIGGER rtree_deposit_footprint_update2 AFTER UPDATE OF footprint ON deposit
  WHEN OLD.doi = NEW.doi AND
       (NEW.footprint ISNULL OR ST_IsEmpty(NEW.footprint))
BEGIN
  DELETE FROM rtree_deposit_footprint WHERE id = OLD.doi;
END;

/* rtree_deposit_footprint_update3 is deprecated and is replaced by
    rtree_deposit_footprint_update5 */

/* Conditions: Update of any column
               Row ID change
               Empty geometry
   Actions   : Remove record from R-tree for old and new doi */
CREATE TRIGGER rtree_deposit_footprint_update4 AFTER UPDATE ON deposit
  WHEN OLD.doi != NEW.doi AND
       (NEW.footprint ISNULL OR ST_IsEmpty(NEW.footprint))
BEGIN
  DELETE FROM rtree_deposit_footprint WHERE id IN (OLD.doi, NEW.doi);
END;

/* Conditions: Update of any column
               Row ID change
               Non-empty geometry
   Actions   : Remove record from R-tree for old doi
               Insert record into R-tree for new doi */
CREATE TRIGGER rtree_deposit_footprint_update5 AFTER UPDATE ON deposit
  WHEN OLD.doi != NEW.doi AND
       (NEW.footprint NOTNULL AND NOT ST_IsEmpty(NEW.footprint))
BEGIN
  DELETE FROM rtree_deposit_footprint WHERE id = OLD.doi;
  INSERT OR REPLACE INTO rtree_deposit_footprint VALUES (
    NEW.doi,
    ST_MinX(NEW.footprint), ST_MaxX(NEW.footprint),
    ST_MinY(NEW.footprint), ST_MaxY(NEW.footprint)
  );
END;

/* Conditions: Update a non-empty geometry with another non-empty geometry
   Actions   : Replace record from R-tree for doi */
CREATE TRIGGER rtree_deposit_footprint_update6 AFTER UPDATE OF footprint ON deposit
  WHEN OLD.doi = NEW.doi AND
       (NEW.footprint NOTNULL AND NOT ST_IsEmpty(NEW.footprint)) AND
       (OLD.footprint NOTNULL AND NOT ST_IsEmpty(OLD.footprint))
BEGIN
  UPDATE rtree_deposit_footprint SET
    minx = ST_MinX(NEW.footprint),
    maxx = ST_MaxX(NEW.footprint),
    miny = ST_MinY(NEW.footprint),
    maxy = ST_MaxY(NEW.footprint)
  WHERE id = NEW.doi;
END;

/* Conditions: Update a null/empty geometry with a non-empty geometry
   Actions   : Insert record into R-tree for new doi */
CREATE TRIGGER rtree_deposit_footprint_update7 AFTER UPDATE OF footprint ON deposit
  WHEN OLD.doi = NEW.doi AND
       (NEW.footprint NOTNULL AND NOT ST_IsEmpty(NEW.footprint)) AND
       (OLD.footprint ISNULL OR ST_IsEmpty(OLD.footprint))
BEGIN
  INSERT INTO rtree_deposit_footprint VALUES (
    NEW.doi,
    ST_MinX(NEW.footprint), ST_MaxX(NEW.footprint),
    ST_MinY(NEW.footprint), ST_MaxY(NEW.footprint)
  );
END;

/* Conditions: Row deleted
   Actions   : Remove record from R-tree for old doi */
CREATE TRIGGER rtree_deposit_footprint_delete AFTER DELETE ON deposit
  WHEN old.footprint NOT NULL
BEGIN
  DELETE FROM rtree_deposit_footprint WHERE id = OLD.doi;
END;

-------------------------------------------------------------------------------
-- Trigger to update rtree value when manipulating deposit_linestring table. --
-------------------------------------------------------------------------------

/* Conditions: Insertion of non-empty geometry
   Actions   : Insert record into R-tree */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_insert AFTER INSERT ON deposit_linestring
  WHEN (new.footprint_linestring NOT NULL AND NOT ST_IsEmpty(NEW.footprint_linestring))
BEGIN
  INSERT OR REPLACE INTO rtree_deposit_linestring_footprint_linestring VALUES (
    NEW.id,
    ST_MinX(NEW.footprint_linestring), ST_MaxX(NEW.footprint_linestring),
    ST_MinY(NEW.footprint_linestring), ST_MaxY(NEW.footprint_linestring)
  );
END;

/* rtree_deposit_linestring_footprint_linestring_update1 is deprecated and is replaced by
    rtree_deposit_linestring_footprint_linestring_update6 and rtree_deposit_linestring_footprint_linestring_update7 */

/* Conditions: Update of geometry column to empty geometry
               No row ID change
   Actions   : Remove record from R-tree */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_update2 AFTER UPDATE OF footprint_linestring ON deposit_linestring
  WHEN OLD.id = NEW.id AND
       (NEW.footprint_linestring ISNULL OR ST_IsEmpty(NEW.footprint_linestring))
BEGIN
  DELETE FROM rtree_deposit_linestring_footprint_linestring WHERE id = OLD.id;
END;

/* rtree_deposit_linestring_footprint_linestring_update3 is deprecated and is replaced by
    rtree_deposit_linestring_footprint_linestring_update5 */

/* Conditions: Update of any column
               Row ID change
               Empty geometry
   Actions   : Remove record from R-tree for old and new id */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_update4 AFTER UPDATE ON deposit_linestring
  WHEN OLD.id != NEW.id AND
       (NEW.footprint_linestring ISNULL OR ST_IsEmpty(NEW.footprint_linestring))
BEGIN
  DELETE FROM rtree_deposit_linestring_footprint_linestring WHERE id IN (OLD.id, NEW.id);
END;

/* Conditions: Update of any column
               Row ID change
               Non-empty geometry
   Actions   : Remove record from R-tree for old id
               Insert record into R-tree for new id */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_update5 AFTER UPDATE ON deposit_linestring
  WHEN OLD.id != NEW.id AND
       (NEW.footprint_linestring NOTNULL AND NOT ST_IsEmpty(NEW.footprint_linestring))
BEGIN
  DELETE FROM rtree_deposit_linestring_footprint_linestring WHERE id = OLD.id;
  INSERT OR REPLACE INTO rtree_deposit_linestring_footprint_linestring VALUES (
    NEW.id,
    ST_MinX(NEW.footprint_linestring), ST_MaxX(NEW.footprint_linestring),
    ST_MinY(NEW.footprint_linestring), ST_MaxY(NEW.footprint_linestring)
  );
END;

/* Conditions: Update a non-empty geometry with another non-empty geometry
   Actions   : Replace record from R-tree for id */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_update6 AFTER UPDATE OF footprint_linestring ON deposit_linestring
  WHEN OLD.id = NEW.id AND
       (NEW.footprint_linestring NOTNULL AND NOT ST_IsEmpty(NEW.footprint_linestring)) AND
       (OLD.footprint_linestring NOTNULL AND NOT ST_IsEmpty(OLD.footprint_linestring))
BEGIN
  UPDATE rtree_deposit_linestring_footprint_linestring SET
    minx = ST_MinX(NEW.footprint_linestring),
    maxx = ST_MaxX(NEW.footprint_linestring),
    miny = ST_MinY(NEW.footprint_linestring),
    maxy = ST_MaxY(NEW.footprint_linestring)
  WHERE id = NEW.id;
END;

/* Conditions: Update a null/empty geometry with a non-empty geometry
   Actions   : Insert record into R-tree for new id */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_update7 AFTER UPDATE OF footprint_linestring ON deposit_linestring
  WHEN OLD.id = NEW.id AND
       (NEW.footprint_linestring NOTNULL AND NOT ST_IsEmpty(NEW.footprint_linestring)) AND
       (OLD.footprint_linestring ISNULL OR ST_IsEmpty(OLD.footprint_linestring))
BEGIN
  INSERT INTO rtree_deposit_linestring_footprint_linestring VALUES (
    NEW.id,
    ST_MinX(NEW.footprint_linestring), ST_MaxX(NEW.footprint_linestring),
    ST_MinY(NEW.footprint_linestring), ST_MaxY(NEW.footprint_linestring)
  );
END;

/* Conditions: Row deleted
   Actions   : Remove record from R-tree for old id */
CREATE TRIGGER rtree_deposit_linestring_footprint_linestring_delete AFTER DELETE ON deposit_linestring
  WHEN old.footprint_linestring NOT NULL
BEGIN
  DELETE FROM rtree_deposit_linestring_footprint_linestring WHERE id = OLD.id;
END;

--------------------
-- All fixed data --
--------------------
INSERT INTO multilabel_label (name, creation_date, description) VALUES 
("Acanthasters", "2024-04-03", "Coral-eating starfish (e.g. Acanthaster planci)."),
("Acropore_branched", "2024-04-03", "With secondary branches (e.g. A. formosa, A. palmata)."),
("Acropore_digitised", "2024-04-03", "No secondary branches (e.g. A. digitifera, A. humilis)."),
("Acropore_sub_massive", "2024-04-03", "Robust with few digitized branches (e.g. A. monticulosa)."),
("Acropore_tabular", "2024-04-03", "Large horizontal plates (e.g. A. hyacinthus, A. cytherea)."),
("Actinopyga_echinites", "2024-04-03", "Holothurian: Color ranging from yellowish beige to orange-brown."),
("Actinopyga_mauritiana", "2024-04-03", "Holothurian: Prefers hard substrates, dark brown back and grayish sides."),
("Algae_assembly", "2024-04-03", "Algal turfs containing several species of algae."),
("Algae_drawn_up", "2024-04-03", "Green, brown or red algae (e.g. Halimeda, Turbinaria)."),
("Algae_limestone", "2024-04-03", "Often encrusting, of the corallinaceous type."),
("Algae_sodding", "2024-04-03", "Short filamentous algae (e.g. Turf algal)."),
("Anemone", "2024-04-03", "Marine invertebrates that belong to the phylum Cnidaria, typically characterized by a columnar body topped with a ring of tentacles."),
("Ascidia", "2024-04-03", "Also known as sea squirts, these are sessile filterfeeding tunicates, often found attached to substrates in the ocean."),
("Atra/Leucospilota", "2024-04-03", "Holothurian: Set of species with bodies sometimes to often covered with a thin layer of sand, of variable color and size ranging up to 30 to 60 cm in length and 10 cm in width."),
("Bleached_coral", "2024-04-03", "Coral that has turned white due to the loss of its symbiont zooxanthellae, typically as a result of stress factors."),
("Blurred", "2024-04-03", "Part of the image that is blurred or has air bubbles in it but does not render the image useless."),
("Bohadschia_vitiensis", "2024-04-03", "Holothurian: Yellowish color with a black spot at the base of each portion."),
("Clam", "2024-04-03", "Bivalve mollusks with two hinged shells, commonly found burrowed in sand or mud in marine environments."),
("D_savignyi/S_variolaris/E_calamaris/E_diadema", "2024-04-03", "Sea urchin: Set of black colored species with gray or blue reflections and generally numerous and long radioles."),
("Dead_coral", "2024-04-03", "Recent mortality (different bleached coral), white to light brown coral."),
("Echinometra_mathaei", "2024-04-03", "Sea urchin: Uniform color (e.g. beige, purple, gray)."),
("Echinostrephus_molaris", "2024-04-03", "Sea urchin: Color ranging from purple to black to brown, radioles long and thin."),
("Fish", "2024-04-03", "Generic class for all fishes."),
("Gorgon", "2024-04-03", "A type of soft coral characterized by a flexible, tree-like structure."),
("Heterocentrotus_mamillatus", "2024-04-03", "Sea urchin: Radioles of large diameter, body and radioles tending towards brown/red in color."),
("Heterocentrus_trigonarius", "2024-04-03", "Sea urchin: Radioles with triangular section, body and radioles tending towards brown/dark red."),
("Homo_sapiens", "2024-04-03", "Part of human body."),
("Human_object", "2024-04-03", "Human object that is not waste (e.g., snorkelling fins, surfboard fins)"),
("Living_coral", "2024-04-03", "Used only when coral cannot be distinguished and not for every living coral."),
("Millepore", "2024-04-03", "Fire coral (e.g. Millepora platyphylla)."),
("No_acropore_branched", "2024-04-03", "With secondary branches (e.g. Seriatopora hystrix)."),
("No_acropore_encrusting", "2024-04-03", "A large part is attached to the substrate (e.g. Porites vaughani, Montipora undata)."),
("No_acropore_foliaceous", "2024-04-03", "Attached to the substrate by one or more points, leaf-like appearance (e.g. Echinopora mammiformis, Pavona cactus)."),
("No_acropore_massive", "2024-04-03", "Massive form resembling a large rock (e.g. Porites lutea, Platygyra daedalea)."),
("No_acropore_solitary", "2024-04-03", "Free-living solitary coral (e.g. Fungia)."),
("No_acropore_sub_massive", "2024-04-03", "Very large group. Corals that tend to form small colonies without digitization (e.g., Porites nigrescens, Pocillopora verrucosa)."),
("Other_starfish", "2024-04-03", "Starfish other than Acanthaster."),
("Rock", "2024-04-03", "Basaltic, granitic or other nature."),
("Sand", "2024-04-03", "Sand of coral or basaltic nature,etc."),
("Rubble", "2024-04-03", "Scrap, debris, particularly coral."),
("Sea_cucumber", "2024-04-03", "Generic class for all sea cucumber."),
("Sea_urchins", "2024-04-03", "Generic class for all sea urchins."),
("Sichopus_chloronotus", "2024-04-03", "Holothurian: Body with quadrangular section, dark green and covered with radii."),
("Soft_coral", "2024-04-03", "Generic class for all soft coral."),
("Sponge", "2024-04-03", "Filter-feeding organism through their aquifer system, e.g. Cliona sp."),
("Synapta_maculata", "2024-04-03", "Holothurian: Up to 3m in length and 5cm in width, beige body with brown bands."),
("Syringodium_isoetifolium", "2024-04-03", "A species of seagrass known for its long, cylindrical leaves."),
("Thalassodendron_ciliatum", "2024-04-03", "A species of seagrass with flattened, strap-like leaves."),
("Toxopneustes_pileolus", "2024-04-03", "Sea urchin: Body slightly flattened, radioles beige, short and flower-shaped."),
("Trample", "2024-04-03", "All the pieces of coral removed mechanically."),
("Tripneustes_gratilla", "2024-04-03", "Sea urchin: 10 bands dotted with short radioles separated by bands without radioles."),
("Turtle", "2024-04-03", "Generic class for all marine turtles."),
("Useless", "2024-04-03", "Images that cannot be used because they were taken out of the water or show great depths with a lot of blue."),
("Waste", "2024-04-03", "Human waste.");


INSERT INTO multilabel_model (name, link, creation_date, doi) VALUES 
("DinoVdeau", "https://huggingface.co/lombardata/DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze", "2024-04-03", "https://doi.org/10.57967/hf/2947");

INSERT INTO multilabel_class (name, threshold, ml_label_id, ml_model_id) VALUES 
("Acropore_branched", 0.351, 2, 1),
("Acropore_digitised", 0.349, 3, 1),
("Acropore_sub_massive", 0.123, 4, 1),
("Acropore_tabular", 0.415, 5, 1),
("Algae_assembly", 0.434, 8, 1),
("Algae_drawn_up", 0.193, 9, 1),
("Algae_limestone", 0.346, 10, 1),
("Algae_sodding", 0.41, 11, 1),
("Atra/Leucospilota", 0.586, 14, 1),
("Bleached_coral", 0.408, 15, 1),
("Blurred", 0.3, 16, 1),
("Dead_coral", 0.407, 20, 1),
("Fish", 0.466, 23, 1),
("Homo_sapiens", 0.402, 27, 1),
("Human_object", 0.343, 28, 1),
("Living_coral", 0.208, 29, 1),
("Millepore", 0.292, 30, 1),
("No_acropore_encrusting", 0.227, 32, 1),
("No_acropore_foliaceous", 0.462, 33, 1),
("No_acropore_massive", 0.333, 34, 1),
("No_acropore_solitary", 0.415, 35, 1),
("No_acropore_sub_massive", 0.377, 36, 1),
("Rock", 0.476, 38, 1),
("Sand", 0.548, 39, 1),
("Rubble", 0.417, 40, 1),
("Sea_cucumber", 0.357, 41, 1),
("Sea_urchins", 0.335, 42, 1),
("Sponge", 0.152, 45, 1),
("Syringodium_isoetifolium", 0.476, 47, 1),
("Thalassodendron_ciliatum", 0.209, 48, 1),
("Useless", 0.315, 53, 1);