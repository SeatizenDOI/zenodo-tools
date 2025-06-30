-- Create a view to get deposit_linestring with footprint.
CREATE VIEW IF NOT EXISTS vw_deposit_linestring_with_platform AS
SELECT 
    dl.id,
    dl.deposit_doi,
    dl.footprint_linestring,
    d.platform_type
FROM 
    deposit_linestring dl
JOIN 
    deposit d ON dl.deposit_doi = d.doi;

-- Insert data into gpkg table, thanks to this qgis see the view as a geometry table.
INSERT OR IGNORE INTO gpkg_geometry_columns (table_name, column_name, geometry_type_name, srs_id, z, m)
VALUES ('vw_deposit_linestring_with_platform', 'footprint_linestring', 'LINESTRING', 4326, 0, 0);

INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, last_change, min_x, min_y, max_x, max_y, srs_id)
VALUES (
    'vw_deposit_linestring_with_platform',
    'features',
    'vw_deposit_linestring_with_platform',
    'View joining deposit_linestring with platform_type',
    CURRENT_TIMESTAMP,
    -- Use ST_MinX etc. from SpatiaLite or compute manually:
    (SELECT MIN(ST_MinX(footprint_linestring)) FROM vw_deposit_linestring_with_platform),
    (SELECT MIN(ST_MinY(footprint_linestring)) FROM vw_deposit_linestring_with_platform),
    (SELECT MAX(ST_MaxX(footprint_linestring)) FROM vw_deposit_linestring_with_platform),
    (SELECT MAX(ST_MaxY(footprint_linestring)) FROM vw_deposit_linestring_with_platform),
    4326
);

-- Drop O,0 GPSPosition Point
DELETE FROM frame
WHERE ST_X(GPSPosition) = 0 AND ST_Y(GPSPosition) = 0;

-- Update the boundingbx in the gpkg content
UPDATE gpkg_contents
SET 
  min_x = (SELECT MIN(ST_MinX(GPSPosition)) FROM frame WHERE GPSPosition IS NOT NULL),
  max_x = (SELECT MAX(ST_MaxX(GPSPosition)) FROM frame WHERE GPSPosition IS NOT NULL),
  min_y = (SELECT MIN(ST_MinY(GPSPosition)) FROM frame WHERE GPSPosition IS NOT NULL),
  max_y = (SELECT MAX(ST_MaxY(GPSPosition)) FROM frame WHERE GPSPosition IS NOT NULL)
WHERE table_name = 'frame';


-- Add layer styles table to auto style data
DROP TABLE IF EXISTS layer_styles;
CREATE TABLE layer_styles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    f_table_catalog TEXT,
    f_table_schema TEXT,
    f_table_name TEXT,
    f_geometry_column TEXT,
    styleName TEXT,
    styleQML TEXT,
    styleSLD TEXT,
    useAsDefault BOOLEAN,
    description TEXT,
    owner TEXT,
    ui TEXT,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO layer_styles (
    f_table_catalog, f_table_schema, f_table_name, f_geometry_column,
    styleName, styleQML, styleSLD, useAsDefault, description, owner, ui
) VALUES 
('', '', 'deposit', 'footprint', 'footprint style',
-- styleQML
'
    <!DOCTYPE qgis PUBLIC "http://mrcc.com/qgis.dtd" "SYSTEM">
    <qgis version="3.34" styleCategories="Symbology">
    <renderer-v2 type="categorizedSymbol" attr="platform_type" forceraster="0" symbollevels="0" enableorderby="0">
        <categories>
        <category value="ASV" label="ASV" render="true" symbol="0"/>
        <category value="PADDLE" label="PADDLE" render="false" symbol="1"/>
        <category value="SCUBA" label="SCUBA" render="false" symbol="2"/>
        <category value="UAV" label="UAV" render="true" symbol="3"/>
        <category value="UVC" label="UVC" render="false" symbol="4"/>
        <category value="" label="No platform type found" render="false" symbol="5"/>
        </categories>
        <symbols>
        <symbol name="0" type="fill" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleFill">
            <prop k="color" v="35,115,201,127"/>
            <prop k="outline_color" v="35,35,35,127"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="1" type="fill" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleFill">
            <prop k="color" v="224,128,176,127"/>
            <prop k="outline_color" v="35,35,35,127"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="2" type="fill" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleFill">
            <prop k="color" v="207,142,78,127"/>
            <prop k="outline_color" v="35,35,35,127"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="3" type="fill" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleFill">
            <prop k="color" v="156,213,99,127"/>
            <prop k="outline_color" v="35,35,35,127"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="4" type="fill" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleFill">
            <prop k="color" v="101,212,157,127"/>
            <prop k="outline_color" v="35,35,35,127"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="5" type="fill" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleFill">
            <prop k="color" v="125,40,210,127"/>
            <prop k="outline_color" v="35,35,35,127"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        </symbols>
        <rotation/>
        <sizescale/>
    </renderer-v2>
    <layerTransparency>0</layerTransparency>
    <displayfield>platform_type</displayfield>
    <labeling>none</labeling>
    <customproperties/>
    </qgis>
', 
-- styleSLD
'
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1.0" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.1.0/StyledLayerDescriptor.xsd" xmlns:se="http://www.opengis.net/se">
 <NamedLayer>
  <se:Name>deposit</se:Name>
  <UserStyle>
   <se:Name>deposit</se:Name>
   <se:FeatureTypeStyle>
    <se:Rule>
     <se:Name>ASV</se:Name>
     <se:Description>
      <se:Title>ASV</se:Title>
     </se:Description>
     <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:PropertyIsEqualTo>
       <ogc:PropertyName>platform_type</ogc:PropertyName>
       <ogc:Literal>ASV</ogc:Literal>
      </ogc:PropertyIsEqualTo>
     </ogc:Filter>
     <se:PolygonSymbolizer>
      <se:Fill>
       <se:SvgParameter name="fill">#2373c9</se:SvgParameter>
      </se:Fill>
      <se:Stroke>
       <se:SvgParameter name="stroke">#232323</se:SvgParameter>
       <se:SvgParameter name="stroke-width">1</se:SvgParameter>
       <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
      </se:Stroke>
     </se:PolygonSymbolizer>
    </se:Rule>
    <se:Rule>
     <se:Name>PADDLE</se:Name>
     <se:Description>
      <se:Title>PADDLE</se:Title>
     </se:Description>
     <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:PropertyIsEqualTo>
       <ogc:PropertyName>platform_type</ogc:PropertyName>
       <ogc:Literal>PADDLE</ogc:Literal>
      </ogc:PropertyIsEqualTo>
     </ogc:Filter>
     <se:PolygonSymbolizer>
      <se:Fill>
       <se:SvgParameter name="fill">#e080b0</se:SvgParameter>
      </se:Fill>
      <se:Stroke>
       <se:SvgParameter name="stroke">#232323</se:SvgParameter>
       <se:SvgParameter name="stroke-width">1</se:SvgParameter>
       <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
      </se:Stroke>
     </se:PolygonSymbolizer>
    </se:Rule>
    <se:Rule>
     <se:Name>SCUBA</se:Name>
     <se:Description>
      <se:Title>SCUBA</se:Title>
     </se:Description>
     <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:PropertyIsEqualTo>
       <ogc:PropertyName>platform_type</ogc:PropertyName>
       <ogc:Literal>SCUBA</ogc:Literal>
      </ogc:PropertyIsEqualTo>
     </ogc:Filter>
     <se:PolygonSymbolizer>
      <se:Fill>
       <se:SvgParameter name="fill">#cf8e4e</se:SvgParameter>
      </se:Fill>
      <se:Stroke>
       <se:SvgParameter name="stroke">#232323</se:SvgParameter>
       <se:SvgParameter name="stroke-width">1</se:SvgParameter>
       <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
      </se:Stroke>
     </se:PolygonSymbolizer>
    </se:Rule>
    <se:Rule>
     <se:Name>UAV</se:Name>
     <se:Description>
      <se:Title>UAV</se:Title>
     </se:Description>
     <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:PropertyIsEqualTo>
       <ogc:PropertyName>platform_type</ogc:PropertyName>
       <ogc:Literal>UAV</ogc:Literal>
      </ogc:PropertyIsEqualTo>
     </ogc:Filter>
     <se:PolygonSymbolizer>
      <se:Fill>
       <se:SvgParameter name="fill">#9cd563</se:SvgParameter>
      </se:Fill>
      <se:Stroke>
       <se:SvgParameter name="stroke">#232323</se:SvgParameter>
       <se:SvgParameter name="stroke-width">1</se:SvgParameter>
       <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
      </se:Stroke>
     </se:PolygonSymbolizer>
    </se:Rule>
    <se:Rule>
     <se:Name>UVC</se:Name>
     <se:Description>
      <se:Title>UVC</se:Title>
     </se:Description>
     <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
      <ogc:PropertyIsEqualTo>
       <ogc:PropertyName>platform_type</ogc:PropertyName>
       <ogc:Literal>UVC</ogc:Literal>
      </ogc:PropertyIsEqualTo>
     </ogc:Filter>
     <se:PolygonSymbolizer>
      <se:Fill>
       <se:SvgParameter name="fill">#65d49d</se:SvgParameter>
      </se:Fill>
      <se:Stroke>
       <se:SvgParameter name="stroke">#232323</se:SvgParameter>
       <se:SvgParameter name="stroke-width">1</se:SvgParameter>
       <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
      </se:Stroke>
     </se:PolygonSymbolizer>
    </se:Rule>
    <se:Rule>
     <se:Name></se:Name>
     <se:Description>
      <se:Title>"platform_type" is ''</se:Title>
     </se:Description>
     <se:ElseFilter xmlns:se="http://www.opengis.net/se"/>
     <se:PolygonSymbolizer>
      <se:Fill>
       <se:SvgParameter name="fill">#7d28d2</se:SvgParameter>
      </se:Fill>
      <se:Stroke>
       <se:SvgParameter name="stroke">#232323</se:SvgParameter>
       <se:SvgParameter name="stroke-width">1</se:SvgParameter>
       <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
      </se:Stroke>
     </se:PolygonSymbolizer>
    </se:Rule>
   </se:FeatureTypeStyle>
  </UserStyle>
 </NamedLayer>
</StyledLayerDescriptor>
',
1, 'Footprint by platform type', 'Ifremer DOI', ''),
('', '', 'frame', 'GPSPosition', 'frame position',
'
    <!DOCTYPE qgis PUBLIC "http://mrcc.com/qgis.dtd" "SYSTEM">
    <qgis version="3.34" styleCategories="Symbology">
    <renderer-v2 type="categorizedSymbol" attr="GPSFix" forceraster="0" symbollevels="0" enableorderby="0">
        <categories>
        <category value="1" label="PPK Q1" render="true" symbol="0"/>
        <category value="2" label="PPK Q2" render="true" symbol="1"/>
        <category value="5" label="PPK Q5" render="true" symbol="2"/>
        <category value="" label="No details provided" render="true" symbol="3"/>
        </categories>
        <symbols>
        <symbol name="0" type="marker" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleMarker">
            <prop k="color" v="117,255,51,255"/>
            <prop k="outline_color" v="35,35,35,255"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="name" v="circle"/>
            <prop k="size" v="3"/>
            </layer>
        </symbol>
        <symbol name="1" type="marker" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleMarker">
            <prop k="color" v="255,189,51,255"/>
            <prop k="outline_color" v="35,35,35,255"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="name" v="circle"/>
            <prop k="size" v="3"/>
            </layer>
        </symbol>
        <symbol name="2" type="marker" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleMarker">
            <prop k="color" v="255,87,51,255"/>
            <prop k="outline_color" v="35,35,35,255"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="name" v="circle"/>
            <prop k="size" v="3"/>
            </layer>
        </symbol>
        <symbol name="3" type="marker" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleMarker">
            <prop k="color" v="206,206,206,255"/>
            <prop k="outline_color" v="35,35,35,255"/>
            <prop k="outline_width" v="0.26"/>
            <prop k="name" v="circle"/>
            <prop k="size" v="3"/>
            </layer>
        </symbol>
        </symbols>
        <rotation/>
        <sizescale/>
    </renderer-v2>
    <layerTransparency>0</layerTransparency>
    <displayfield>platform_type</displayfield>
    <labeling>none</labeling>
    <customproperties/>
    </qgis>
',
'
<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld"
                           xmlns:ogc="http://www.opengis.net/ogc"
                           xmlns:gml="http://www.opengis.net/gml"
                           xmlns="http://www.opengis.net/sld"
                           version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>GPSFix points</sld:Name>
    <sld:UserStyle>
      <sld:Title>GPSFix Point Symbology</sld:Title>
      <sld:FeatureTypeStyle>

        <!-- PPK Q1 -->
        <sld:Rule>
          <sld:Name>PPK Q1</sld:Name>
          <sld:Title>PPK Q1</sld:Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>GPSFix</ogc:PropertyName>
              <ogc:Literal>1</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <sld:PointSymbolizer>
            <sld:Graphic>
              <sld:Mark>
                <sld:WellKnownName>circle</sld:WellKnownName>
                <sld:Fill>
                  <sld:CssParameter name="fill">#75FF33</sld:CssParameter>
                </sld:Fill>
                <sld:Stroke>
                  <sld:CssParameter name="stroke">#232323</sld:CssParameter>
                  <sld:CssParameter name="stroke-width">0.26</sld:CssParameter>
                </sld:Stroke>
              </sld:Mark>
              <sld:Size>3</sld:Size>
            </sld:Graphic>
          </sld:PointSymbolizer>
        </sld:Rule>

        <!-- PPK Q2 -->
        <sld:Rule>
          <sld:Name>PPK Q2</sld:Name>
          <sld:Title>PPK Q2</sld:Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>GPSFix</ogc:PropertyName>
              <ogc:Literal>2</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <sld:PointSymbolizer>
            <sld:Graphic>
              <sld:Mark>
                <sld:WellKnownName>circle</sld:WellKnownName>
                <sld:Fill>
                  <sld:CssParameter name="fill">#FFBD33</sld:CssParameter>
                </sld:Fill>
                <sld:Stroke>
                  <sld:CssParameter name="stroke">#232323</sld:CssParameter>
                  <sld:CssParameter name="stroke-width">0.26</sld:CssParameter>
                </sld:Stroke>
              </sld:Mark>
              <sld:Size>3</sld:Size>
            </sld:Graphic>
          </sld:PointSymbolizer>
        </sld:Rule>

        <!-- PPK Q5 -->
        <sld:Rule>
          <sld:Name>PPK Q5</sld:Name>
          <sld:Title>PPK Q5</sld:Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>GPSFix</ogc:PropertyName>
              <ogc:Literal>5</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <sld:PointSymbolizer>
            <sld:Graphic>
              <sld:Mark>
                <sld:WellKnownName>circle</sld:WellKnownName>
                <sld:Fill>
                  <sld:CssParameter name="fill">#FF5733</sld:CssParameter>
                </sld:Fill>
                <sld:Stroke>
                  <sld:CssParameter name="stroke">#232323</sld:CssParameter>
                  <sld:CssParameter name="stroke-width">0.26</sld:CssParameter>
                </sld:Stroke>
              </sld:Mark>
              <sld:Size>3</sld:Size>
            </sld:Graphic>
          </sld:PointSymbolizer>
        </sld:Rule>

        <!-- No details provided -->
        <sld:Rule>
          <sld:Name>No details provided</sld:Name>
          <sld:Title>No details provided</sld:Title>
          <ogc:Filter>
            <ogc:Or>
              <ogc:PropertyIsNull>
                <ogc:PropertyName>GPSFix</ogc:PropertyName>
              </ogc:PropertyIsNull>
              <ogc:PropertyIsEqualTo>
                <ogc:PropertyName>GPSFix</ogc:PropertyName>
                <ogc:Literal></ogc:Literal>
              </ogc:PropertyIsEqualTo>
            </ogc:Or>
          </ogc:Filter>
          <sld:PointSymbolizer>
            <sld:Graphic>
              <sld:Mark>
                <sld:WellKnownName>circle</sld:WellKnownName>
                <sld:Fill>
                  <sld:CssParameter name="fill">#CECECE</sld:CssParameter>
                </sld:Fill>
                <sld:Stroke>
                  <sld:CssParameter name="stroke">#232323</sld:CssParameter>
                  <sld:CssParameter name="stroke-width">0.26</sld:CssParameter>
                </sld:Stroke>
              </sld:Mark>
              <sld:Size>3</sld:Size>
            </sld:Graphic>
          </sld:PointSymbolizer>
        </sld:Rule>

      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
',
1, 'Footprint by platform type', 'Ifremer DOI', ''),
('', '', 'vw_deposit_linestring_with_platform', 'footprint_linestring', 'Footprint in linestring',
-- styleQML
'
    <!DOCTYPE qgis PUBLIC "http://mrcc.com/qgis.dtd" "SYSTEM">
    <qgis version="3.34" styleCategories="Symbology">
    <renderer-v2 type="categorizedSymbol" attr="platform_type" forceraster="0" symbollevels="0" enableorderby="0">
        <categories>
        <category value="ASV" label="ASV" render="false" symbol="0"/>
        <category value="PADDLE" label="PADDLE" render="true" symbol="1"/>
        <category value="SCUBA" label="SCUBA" render="true" symbol="2"/>
        <category value="UAV" label="UAV" render="false" symbol="3"/>
        <category value="UVC" label="UVC" render="true" symbol="4"/>
        <category value="" label="No platform type found" render="false" symbol="5"/>
        </categories>
        <symbols>
        <symbol name="0" type="line" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleLine">
            <prop k="color" v="35,115,201,255"/>
            <prop k="width" v="0.66"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="1" type="line" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleLine">
            <prop k="color" v="224,128,176,255"/>
            <prop k="width" v="0.66"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="2" type="line" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleLine">
            <prop k="color" v="207,142,78,255"/>
            <prop k="width" v="0.66"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="3" type="line" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleLine">
            <prop k="color" v="156,213,99,255"/>
            <prop k="width" v="0.66"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="4" type="line" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleLine">
            <prop k="color" v="101,212,157,255"/>
            <prop k="width" v="0.66"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        <symbol name="5" type="line" alpha="1" force_rhr="0">
            <layer pass="0" class="SimpleLine">
            <prop k="color" v="125,40,210,255"/>
            <prop k="width" v="0.66"/>
            <prop k="joinstyle" v="bevel"/>
            </layer>
        </symbol>
        </symbols>
        <rotation/>
        <sizescale/>
    </renderer-v2>
    <layerTransparency>0</layerTransparency>
    <displayfield>platform_type</displayfield>
    <labeling>none</labeling>
    <customproperties/>
    </qgis>
', 
-- styleSLD
'
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld
                      http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">

  <NamedLayer>
    <Name>deposit_linestring</Name>
    <UserStyle>
      <Title>Platform Type Categorized Style</Title>
      <FeatureTypeStyle>

        <!-- PADDLE -->
        <Rule>
          <Name>PADDLE</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>platform_type</ogc:PropertyName>
              <ogc:Literal>PADDLE</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#E080B0</CssParameter> <!-- RGB 224,128,176 -->
              <CssParameter name="stroke-width">0.66</CssParameter>
              <CssParameter name="stroke-linejoin">bevel</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>

        <!-- SCUBA -->
        <Rule>
          <Name>SCUBA</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>platform_type</ogc:PropertyName>
              <ogc:Literal>SCUBA</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#CF8E4E</CssParameter> <!-- RGB 207,142,78 -->
              <CssParameter name="stroke-width">0.66</CssParameter>
              <CssParameter name="stroke-linejoin">bevel</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>

        <!-- UVC -->
        <Rule>
          <Name>UVC</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>platform_type</ogc:PropertyName>
              <ogc:Literal>UVC</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#65D49D</CssParameter> <!-- RGB 101,212,157 -->
              <CssParameter name="stroke-width">0.66</CssParameter>
              <CssParameter name="stroke-linejoin">bevel</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>

        <!-- ASV -->
        <Rule>
          <Name>ASV</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>platform_type</ogc:PropertyName>
              <ogc:Literal>ASV</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">0.66</CssParameter>
              <CssParameter name="stroke-linejoin">bevel</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>

        <!-- UAV -->
        <Rule>
          <Name>UAV</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>platform_type</ogc:PropertyName>
              <ogc:Literal>UAV</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">0.66</CssParameter>
              <CssParameter name="stroke-linejoin">bevel</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>

      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
',
1, 'Linestring by platform type', 'Ifremer DOI', '');
