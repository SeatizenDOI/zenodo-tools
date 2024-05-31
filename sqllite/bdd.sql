------------------------------------
-- Mandatory table for Geopackage --
------------------------------------
-- gpkg_spatial_ref_sys table
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
('undefined geographic coordinate', 0, 'NONE', 0, 'undefined', "ndefined geographic coordinate reference systems");

-- gpkg_contents table
CREATE TABLE IF NOT EXISTS gpkg_contents (
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
('deposit', 'footprint', 'GEOMETRY', 4326, 0, 0),
('frame', 'location', 'POINT', 4326, 1, 0);

----------------------------------------
-- Base table for zenodo architecture --
----------------------------------------

-- Deposit table
CREATE TABLE IF NOT EXISTS deposit (
    doi TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    footprint GEOMETRY,
    session_date DATE GENERATED ALWAYS AS (SUBSTR(session_name, 0, 9)) VIRTUAL,
    alpha3_country_code TEXT GENERATED ALWAYS AS (SUBSTR(session_name, 10, 3)) VIRTUAL,
    location TEXT GENERATED ALWAYS AS (
        SUBSTR (
            SUBSTR(session_name, INSTR(session_name, '_') + 1),
            INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '-') + 1,
            INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1),INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '-') + 1), '_') - 1
        )
    ) VIRTUAL,
    platform_type TEXT GENERATED ALWAYS AS (
        UPPER(SUBSTR (
            SUBSTR(session_name, INSTR(session_name, '_') + 1), 
            INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1,
            CASE
                WHEN INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '-') > 0 
                THEN INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '-') - 1
                ELSE INSTR(SUBSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), INSTR(SUBSTR(session_name, INSTR(session_name, '_') + 1), '_') + 1), '_') - 1
            END
            
        ))
    ) VIRTUAL
);

INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id) VALUES 
('deposit', 'features', 'deposit', 'Table with deposit polygons', 4326);


-- Version table
CREATE TABLE IF NOT EXISTS version (
    doi TEXT PRIMARY KEY,
    deposit_doi TEXT NOT NULL,
    CONSTRAINT fk_deposit_version FOREIGN KEY (deposit_doi) REFERENCES deposit(doi)
);

-- Frame table
CREATE TABLE IF NOT EXISTS frame (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_doi TEXT NOT NULL,
    name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    GPSPosition BLOB, -- Latitude, Longitude, Depth
    GPSPitch REAL,
    GPSRoll REAL,
    GPSTrack REAL,
    GPSDatetime DATETIME,
    CONSTRAINT fk_frame_version FOREIGN KEY (version_doi) REFERENCES version(doi)
);

INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id) VALUES 
('frame', 'features', 'frame', 'Table with frame points', 4326);

------------------------------------
-- All table for multilabel stuff --
------------------------------------

-- Multilabel label
CREATE TABLE IF NOT EXISTS multilabel_label (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    creation_date DATETIME NOT NULL
);

-- Multilabel model
CREATE TABLE IF NOT EXISTS multilabel_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    link TEXT NOT NULL,
    doi TEXT,
    creation_date DATETIME NOT NULL
);

-- Multilabel class
CREATE TABLE IF NOT EXISTS multilabel_class (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT COMMENT `Alias to multilabel_label.name`,
    threshold REAL NOT NULL,
    multilabel_label_id INTEGER NOT NULL,
    multilabel_model_id INTEGER NOT NULL,
    CONSTRAINT fk_multilabel_class_multilabel_label FOREIGN KEY (multilabel_label_id) REFERENCES multilabel_label(id),
    CONSTRAINT fk_multilabel_class_multilabel_model FOREIGN KEY (multilabel_model_id) REFERENCES multilabel_model(id)
);

-- Multilabel predictions
CREATE TABLE IF NOT EXISTS multilabel_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score REAL NOT NULL,
    prediction_date DATETIME NOT NULL,
    version_doi TEXT NOT NULL,
    frame_id INTEGER NOT NULL,
    multilabel_class_id INTEGER NOT NULL,
    CONSTRAINT fk_multilabel_prediction_version FOREIGN KEY (version_doi) REFERENCES version(doi),
    CONSTRAINT fk_multilabel_prediction_frame FOREIGN KEY (frame_id) REFERENCES frame(id),
    CONSTRAINT fk_multilabel_prediction_multilabel_class FOREIGN KEY (multilabel_class_id) REFERENCES multilabel_class(id)
);

-- Multilabel annotation
CREATE TABLE IF NOT EXISTS multilabel_annotation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value TINYINT NOT NULL,
    annotation_date DATETIME NOT NULL,
    frame_id INTEGER NOT NULL,
    multilabel_label_id INTEGER NOT NULL,
    CONSTRAINT fk_multilabel_annotation_frame FOREIGN KEY (frame_id) REFERENCES frame(id),
    CONSTRAINT fk_multilabel_annotation_multilabel_label FOREIGN KEY (multilabel_label_id) REFERENCES multilabel_label(id)
);


-- FIXED DATA
INSERT INTO multilabel_label (name, creation_date) VALUES 
("Acanthasters",DATE('now')),
("Acropore_branched",DATE('now')),
("Acropore_digitised",DATE('now')),
("Acropore_sub_massive",DATE('now')),	
("Acropore_tabular",DATE('now')),
("Actinopyga_echinites",DATE('now')),
("Actinopyga_mauritiana",DATE('now')),
("Algae_assembly",DATE('now')),
("Algae_drawn_up",DATE('now')),
("Algae_limestone",DATE('now')),
("Algae_sodding",DATE('now')),
("Anemone",DATE('now')),
("Ascidia",DATE('now')),
("Atra/Leucospilota",DATE('now')),
("Bleached_coral",DATE('now')),
("Block",DATE('now')),
("Blurred",DATE('now')),
("Bohadschia_vitiensis",DATE('now')),
("Clam",DATE('now')),
("D_savignyi/S_variolaris/E_calamaris/E_diadema",DATE('now')),
("Dead_coral",DATE('now')),
("Echinometra_mathaei",DATE('now')),
("Echinostrephus_molaris",DATE('now')),
("Fish",DATE('now')),
("Gorgon",DATE('now')),
("Heterocentrotus_mamillatus",DATE('now')),
("Heterocentrus_trigonarius",DATE('now')),
("Homo_sapiens",DATE('now')),
("Human_object",DATE('now')),
("Living_coral",DATE('now')),
("Millepore",DATE('now')),
("Mud",DATE('now')),
("No_acropore_branched",DATE('now')),
("No_acropore_encrusting",DATE('now')),
("No_acropore_foliaceous",DATE('now')),
("No_acropore_massive",DATE('now')),
("No_acropore_solitary",DATE('now')),
("No_acropore_sub_massive",DATE('now')),
("No_acropore_sub_massive_pocillopores",DATE('now')),
("Other_starfish",DATE('now')),
("Rock",DATE('now')),
("Sand",DATE('now')),
("Rubble",DATE('now')),
("Sea_cucumber",DATE('now')),
("Sea_urchins",DATE('now')),
("Seagrass",DATE('now')),
("Sichopus_chloronotus",DATE('now')),
("Soft_coral",DATE('now')),
("Sponge",DATE('now')),
("Synapta_maculata",DATE('now')),
("Syringodium_isoetifolium",DATE('now')),
("Syringodium_isoetifolium_algae",DATE('now')),
("Tample",DATE('now')),
("Thalassodendron_ciliatum",DATE('now')),
("Thalassodendron_ciliatum_algae",DATE('now')),
("Toxopneustes_pileolus",DATE('now')),
("Trample",DATE('now')),
("Tripneustes_gratilla",DATE('now')),
("Turtle",DATE('now')),
("Useless",DATE('now')),
("Waste",DATE('now'));

INSERT INTO multilabel_model (name, link, creation_date) VALUES ("DinoVdeau", "https://huggingface.co/lombardata/DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze", "2024-04-03");

INSERT INTO multilabel_class (name, threshold, multilabel_label_id, multilabel_model_id) VALUES 
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
("Blurred", 0.3, 17, 1),
("Dead_coral", 0.407, 21, 1),
("Fish", 0.466, 24, 1),
("Homo_sapiens", 0.402, 28, 1),
("Human_object", 0.343, 29, 1),
("Living_coral", 0.208, 30, 1),
("Millepore", 0.292, 31, 1),
("No_acropore_encrusting", 0.227, 34, 1),
("No_acropore_foliaceous", 0.462, 35, 1),
("No_acropore_massive", 0.333, 36, 1),
("No_acropore_solitary", 0.415, 37, 1),
("No_acropore_sub_massive", 0.377, 38, 1),
("Rock", 0.476, 41, 1),
("Sand", 0.548, 42, 1),
("Rubble", 0.417, 43, 1),
("Sea_cucumber", 0.357, 44, 1),
("Sea_urchins", 0.335, 45, 1),
("Sponge", 0.152, 48, 1),
("Syringodium_isoetifolium", 0.476, 50, 1),
("Thalassodendron_ciliatum", 0.209, 53, 1),
("Useless", 0.315, 58, 1);