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
('deposit', 'footprint', 'GEOMETRYCOLLECTION', 4326, 0, 0),
('frame', 'GPSPosition', 'POINT', 4326, 0, 0);

----------------------------------------
-- Base table for zenodo architecture --
----------------------------------------

-- Deposit table
CREATE TABLE IF NOT EXISTS deposit (
    doi TEXT NOT NULL PRIMARY KEY,
    session_name TEXT NOT NULL,
    footprint GEOMETRYCOLLECTION,
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

INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id) VALUES 
('deposit', 'features', 'deposit', 'Table with deposit Geometry as footprint', 4326);


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
    original_filename TEXT NOT NULL,
    filename TEXT NOT NULL,
    relative_path TEXT,
    GPSPosition POINT, -- Latitude, Longitude
    GPSAltitude REAL,
    GPSPitch REAL,
    GPSRoll REAL,
    GPSTrack REAL,
    GPSDatetime DATETIME,
    GPSFix INTEGER,
    CONSTRAINT fk_frame_version FOREIGN KEY (version_doi) REFERENCES version(doi)
);

INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id, min_x, min_y, max_x, max_y) VALUES 
('frame', 'features', 'frame', 'Table with frame points', 4326, -200, -80, 200, 80);

------------------------------------
-- All table for multilabel stuff --
------------------------------------

-- Multilabel label
CREATE TABLE IF NOT EXISTS multilabel_label (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    creation_date DATETIME NOT NULL
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


-- FIXED DATA
INSERT INTO multilabel_label (name, creation_date, description) VALUES 
("Acanthasters", DATE("now"), "Coral-eating starfish (e.g. Acanthaster planci)."),
("Acropore_branched", DATE("now"), "With secondary branches (e.g. A. formosa, A. palmata)."),
("Acropore_digitised", DATE("now"), "No secondary branches (e.g. A. digitifera, A. humilis)."),
("Acropore_sub_massive", DATE("now"), "Robust with few digitized branches (e.g. A. monticulosa)."),
("Acropore_tabular", DATE("now"), "Large horizontal plates (e.g. A. hyacinthus, A. cytherea)."),
("Actinopyga_echinites", DATE("now"), "Holothurian: Color ranging from yellowish beige to orange-brown."),
("Actinopyga_mauritiana", DATE("now"), "Holothurian: Prefers hard substrates, dark brown back and grayish sides."),
("Algae_assembly", DATE("now"), "Algal turfs containing several species of algae."),
("Algae_drawn_up", DATE("now"), "Green, brown or red algae (e.g. Halimeda, Turbinaria)."),
("Algae_limestone", DATE("now"), "Often encrusting, of the corallinaceous type."),
("Algae_sodding", DATE("now"), "Short filamentous algae (e.g. Turf algal)."),
("Anemone", DATE("now"), "Marine invertebrates that belong to the phylum Cnidaria, typically characterized by a columnar body topped with a ring of tentacles."),
("Ascidia", DATE("now"), "Also known as sea squirts, these are sessile filterfeeding tunicates, often found attached to substrates in the ocean."),
("Atra/Leucospilota", DATE("now"), "Holothurian: Set of species with bodies sometimes to often covered with a thin layer of sand, of variable color and size ranging up to 30 to 60 cm in length and 10 cm in width."),
("Bleached_coral", DATE("now"), "Coral that has lost its color and turned white, typically due to stress factors."),
("Block", DATE("now"), "nan"),
("Blurred", DATE("now"), "Part of the image with blur or air bubbles without rendering the image useless."),
("Bohadschia_vitiensis", DATE("now"), "Holothurian: Yellowish color with a black spot at the base of each portion."),
("Clam", DATE("now"), "Bivalve mollusks with two hinged shells, commonly found burrowed in sand or mud in marine environments."),
("D_savignyi/S_variolaris/E_calamaris/E_diadema", DATE("now"), "Sea urchin: Set of black colored species with gray or blue reflections and generally numerous and long radioles."),
("Dead_coral", DATE("now"), "Recent mortality (different bleached coral), white to light brown coral."),
("Echinometra_mathaei", DATE("now"), "Sea urchin: Uniform color (e.g. beige, purple, gray)."),
("Echinostrephus_molaris", DATE("now"), "Sea urchin: Color ranging from purple to black to brown, radioles long and thin."),
("Fish", DATE("now"), "Generic class for all fishes."),
("Gorgon", DATE("now"), "A type of soft coral characterized by a flexible, tree-like structure."),
("Heterocentrotus_mamillatus", DATE("now"), "Sea urchin: Radioles of large diameter, body and radioles tending towards brown/red in color."),
("Heterocentrus_trigonarius", DATE("now"), "Sea urchin: Radioles with triangular section, body and radioles tending towards brown/dark red."),
("Homo_sapiens", DATE("now"), "Part of human body."),
("Human_object", DATE("now"), "Human object that is not waste (e.g. fins, pens)"),
("Living_coral", DATE("now"), "Used only when coral cannot be distinguished and not for every living coral."),
("Millepore", DATE("now"), "Fire coral (e.g. Millepora platyphylla)."),
("Mud", DATE("now"), "nan"),
("No_acropore_branched", DATE("now"), "With secondary branches (e.g. Seriatopora hystrix)."),
("No_acropore_encrusting", DATE("now"), "A large part is attached to the substrate (e.g. Porites vaughani, Montipora undata)."),
("No_acropore_foliaceous", DATE("now"), "Attached to the substrate by one or more points, leaf-like appearance (e.g. Echinopora mammiformis, Pavona cactus)."),
("No_acropore_massive", DATE("now"), "Massive form resembling a large rock (e.g. Porites lutea, Platygyra daedalea)."),
("No_acropore_solitary", DATE("now"), "Free-living solitary coral (e.g. Fungia)."),
("No_acropore_sub_massive", DATE("now"), "Tends to form small colonies without digitization (e.g. Porites nigrescens, Pocillopora verrucosa)."),
("No_acropore_sub_massive_pocillopores", DATE("now"), "Spatula-shaped colonies. This is a substitute coral that easily colonizes substrates."),
("Other_starfish", DATE("now"), "Starfish other than Acanthaster."),
("Rock", DATE("now"), "Basaltic, granitic or other nature."),
("Sand", DATE("now"), "Sand of coral or basaltic nature,etc."),
("Rubble", DATE("now"), "Scrap, debris, particularly coral."),
("Sea_cucumber", DATE("now"), "Generic class for all sea cucumber."),
("Sea_urchins", DATE("now"), "Generic class for all sea urchins."),
("Sichopus_chloronotus", DATE("now"), "Holothurian: Body with quadrangular section, dark green and covered with radius."),
("Soft_coral", DATE("now"), "Generic class for all soft coral."),
("Sponge", DATE("now"), "e.g. Cliona sp."),
("Synapta_maculata", DATE("now"), "Holothurian: Up to 3m in length and 5cm in width, beige body with brown bands."),
("Syringodium_isoetifolium", DATE("now"), "A species of seagrass known for its long, cylindrical leaves."),
("Syringodium_isoetifolium_algae", DATE("now"), "nan"),
("Thalassodendron_ciliatum", DATE("now"), "A species of seagrass with flattened, strap-like leaves."),
("Thalassodendron_ciliatum_algae", DATE("now"), "nan"),
("Toxopneustes_pileolus", DATE("now"), "Sea urchin: Body slightly flattened, radioles beige, short and flower-shaped."),
("Trample", DATE("now"), "All the pieces of coral removed mechanically."),
("Tripneustes_gratilla", DATE("now"), "Sea urchin: 10 bands dotted with short radioles separated by bands without radioles."),
("Turtle", DATE("now"), "Generic class for all marine turtles."),
("Useless", DATE("now"), "Images that cannot be used because they were taken out of the water or show great depths with a lot of blue."),
("Waste", DATE("now"), "Human waste.");

INSERT INTO multilabel_model (name, link, creation_date) VALUES 
("DinoVdeau", "https://huggingface.co/lombardata/DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze", "2024-04-03");

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
("Thalassodendron_ciliatum", 0.209, 52, 1),
("Useless", 0.315, 58, 1);