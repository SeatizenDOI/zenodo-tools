import polars as pl
from datetime import datetime
from dataclasses import dataclass, field

from shapely import wkt
from shapely.geometry import Point, Polygon

from .base_model import AbstractBaseDAO
from .deposit_model import VersionDTO, VersionDAO, DepositDTO

@dataclass
class FrameDTO():
    version: VersionDTO 
    filename: str
    original_filename: str
    relative_path: str | None
    gps_latitude: float | None
    gps_longitude: float | None
    gps_altitude: float | None
    gps_pitch: float | None
    gps_roll: float | None
    gps_track: float | None
    gps_fix: int | None
    gps_datetime: str
    id: int | None = field(default=None)

    @property
    def position(self) -> any:
        if self.gps_longitude == None and self.gps_latitude == None: return None
        return Point(self.gps_longitude, self.gps_latitude).wkt

    @property
    def gps_datetime_convert(self) -> datetime:
        return datetime.strptime(self.gps_datetime, "%Y-%m-%d %H:%M:%S")
    
    def __hash__(self) -> int:
        return hash((self.id, self.filename, self.version.doi))


@dataclass
class FrameDAO(AbstractBaseDAO):
    table_name = "frame"

    __frames: list[FrameDTO] = field(default_factory=list)
    __frames_by_id: dict[int, FrameDTO] = field(default_factory=dict)

    __versionDAO = VersionDAO()
    __frame_header = [
        "id","version_doi","OriginalFileName","filename","relative_file_path",
        "ST_AsText(GPSPosition)","GPSAltitude","GPSPitch","GPSRoll","GPSTrack","GPSDatetime",
        "GPSFix"
    ]

    @property
    def frames(self) -> list[FrameDTO]:
        if len(self.__frames) == 0:
            self.__get_all()
        return self.__frames

    @property
    def typed_frames_header(self) -> dict:
        return {
            "GPSLatitude": pl.Float64,
            "GPSLongitude": pl.Float64,
            "version_doi": pl.String,
            "OriginalFileName": pl.String,
            "relative_file_path": pl.String,
            "GPSAltitude": pl.Float64,
            "GPSPitch": pl.Float64,
            "GPSRoll": pl.Float64,
            "GPSTrack": pl.Float64,
            "GPSDatetime": pl.String,
            "GPSFix": pl.UInt8
        }
        

    @property
    def frames_header(self) -> list[str]:
        return [header for header in self.typed_frames_header]
    
    
    def match_frame_header_and_attribut(self, fs: str, frame: FrameDTO):
        if fs == "version_doi": return f"https://doi.org/10.5281/zenodo.{frame.version.doi}"
        elif fs == "OriginalFileName": return frame.original_filename
        elif fs == "relative_file_path": return frame.relative_path
        elif fs == "GPSLongitude": return frame.gps_longitude
        elif fs == "GPSLatitude": return frame.gps_latitude
        elif fs == "GPSAltitude": return frame.gps_altitude
        elif fs == "GPSRoll": return frame.gps_roll
        elif fs == "GPSPitch": return frame.gps_pitch
        elif fs == "GPSTrack": return frame.gps_track
        elif fs == "GPSFix": return frame.gps_fix
        elif fs == "GPSDatetime": return frame.gps_datetime
        
        return None


    def __parse_frame_results(self, results) -> list[FrameDTO] | FrameDTO:
        """ Method to centralize parse method. """
        frames = []
        for id, version_doi, original_filename, filename, relative_path, GPSPosition,\
            GPSAltitude, GPSPitch,GPSRoll, GPSTrack, GPSDatetime, GPSFix in results:
            
            # Get lat, lon from GPSPosition.
            lat, lon = None, None
            if GPSPosition != None:
                position = wkt.loads(GPSPosition)
                lat = position.y
                lon = position.x
            
            version = self.__versionDAO.get_version_by_doi(version_doi)
            
            frames.append(FrameDTO(
                id=id,
                version=version,
                original_filename=original_filename,
                filename=filename,
                relative_path=relative_path,
                gps_latitude=lat,
                gps_longitude=lon,
                gps_altitude=GPSAltitude,
                gps_pitch=GPSPitch,
                gps_roll=GPSRoll,
                gps_track=GPSTrack,
                gps_datetime=GPSDatetime,
                gps_fix=GPSFix
            ))
        if len(frames) == 1: return frames[0]
        return frames


    def get_frames_by_version(self, version: VersionDTO) -> list[FrameDTO]:
        """ Get frames filter by version. """
        query = f""" SELECT {", ".join(self.__frame_header)} 
                     FROM {self.table_name}
                     WHERE version_doi = ?;
                """
        params = (version.doi, )
        results = self.sql_connector.execute_query(query, params)
        return self.__parse_frame_results(results)
    

    def get_frame_by_id(self, frame_id: int) -> FrameDTO:
        """ Get frames filter by id"""
        if frame_id in self.__frames_by_id:
            return self.__frames_by_id.get(frame_id)
        
        query = f""" SELECT {", ".join(self.__frame_header)}
                     FROM {self.table_name}
                     WHERE id = ?
                 """
        params = (frame_id, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[ERROR] No frame found for this id.")
        
        frame = self.__parse_frame_results(result)
        if isinstance(frame, list): 
            raise NameError("[ERROR] Something goes wrong when retrieving only one frame.")

        self.__frames_by_id[frame.id] = frame
        return frame


    def get_frame_by_filename_and_version(self, filename: str, frame_version: VersionDTO) -> FrameDTO:
        """ Get frame filter by filename and version. """
        query = f""" SELECT {", ".join(self.__frame_header)}
                    FROM {self.table_name}
                    WHERE version_doi = ? AND filename = ?;
                """
        params = (frame_version.doi, filename )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[ERROR] Frame not found.") 
        
        frame = self.__parse_frame_results(result)
        if isinstance(frame, list): 
            raise NameError("[ERROR] Frame is not unique for this version and this filename.")

        return frame
    

    def get_frame_by_filename(self, filename: str) -> FrameDTO:
        """Get frame filter by name. """
        query = f""" SELECT {", ".join(self.__frame_header)}
                    FROM {self.table_name}
                    WHERE filename = ?;
                """
        params = (filename, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[ERROR] Frame not found.") 
        
        frame = self.__parse_frame_results(result)
        if isinstance(frame, list): 
            raise NameError("[ERROR] Frame is not unique this filename.")

        return frame

    
    def __get_all(self) -> None:
        """ Get all frames. """
        query = f""" SELECT {", ".join(self.__frame_header)}
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)
        self.__frames = self.__parse_frame_results(results)
    

    def insert(self, frames: FrameDTO | list[FrameDTO]) -> None:
        """ Insert one or more frames in database. """
        # Deal only with list.
        if isinstance(frames, FrameDTO):
            frames = [frames]
        
        if len(frames) == 0:
            print("[WARNING] Cannot insert frames in database, we don't have frames.")
            return
        
        query = f""" INSERT INTO {self.table_name}
                     (version_doi, filename, OriginalFileName, relative_file_path, GPSPosition,
                      GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSDatetime, GPSFix) 
                     VALUES (?,?,?,?,ST_GeomFromText(?),?,?,?,?,?,?)
                 """
        values = []
        for f in frames:
            values.append((f.version.doi, 
                           f.filename, 
                           f.original_filename, 
                           f.relative_path, 
                           f.position,
                           f.gps_altitude, 
                           f.gps_pitch, 
                           f.gps_roll, 
                           f.gps_track, 
                           f.gps_datetime,
                           f.gps_fix,
                        ))
        self.sql_connector.execute_query(query, values)
    
    def get_frame_by_date_type_position(self, list_poly: list[Polygon], date_range, platform_type) -> list[FrameDTO]:
        """ Get frames with three filter: Position polygon, Date range and platform type. """

        # Base date filtering.
        q_with = f""
        q_select = f"""SELECT {", ".join(self.__frame_header)}"""
        q_from = f" FROM {self.table_name} f "
        q_join = f"""
                JOIN version v ON f.version_doi = v.doi
                JOIN deposit d ON v.deposit_doi = d.doi
            """
        q_where = f" WHERE strftime('%Y-%m-%d', d.session_date) >= ? AND strftime('%Y-%m-%d', d.session_date) <= ?"

        params = (date_range[0], date_range[1])

        # Platform type filtering
        if platform_type:
            q_where += f""" AND d.platform_type IN ({', '.join(['?' for _ in platform_type])})"""
            params = params + tuple(platform_type)
        
        # Geoposition
        if len(list_poly) != 0:
            q_with += "WITH polygons AS ("
            for i, polygon in enumerate(list_poly):
                q_with += f"""
                    SELECT ST_GeomFromText(?, 4326) AS geom
                """
                params = (polygon.wkt, ) + params        # Parameters will not be add in the same order but it's not useful.
                
                if i < len(list_poly) -1: 
                    q_with += """
                    UNION ALL
                """
            q_with += f"""),
                        combined_polygon AS (
                            SELECT ST_Union(geom) AS geom FROM polygons
                        )
                        """
            q_where += " AND f.GPSPosition NOT NULL AND ST_Contains((SELECT geom FROM combined_polygon), f.GPSPosition) "
        
        query = q_with + q_select + q_from + q_join + q_where
        results = self.sql_connector.execute_query(query, params)
        parsed_result = self.__parse_frame_results(results) 
        return parsed_result
    
    def get_number_images_by_platform(self) -> dict[str, int]:
        query = f"""
            SELECT COUNT(f.filename) AS "frame_count", d.platform_type
            FROM frame f
            JOIN version v on v.doi = f.version_doi
            JOIN deposit d on d.doi = v.deposit_doi
            GROUP BY d.platform_type;
        """

        result = self.sql_connector.execute_query(query)

        data = {}
        for frame_count, platform_type in result:
            data[platform_type] = frame_count
        
        return data
    
    def get_min_max_depth_by_deposit(self, deposit: DepositDTO) -> tuple[float, float]:
        """ Return min max depth """
        
        query = f"""
            SELECT MIN(f.GPSAltitude), MAX(f.GPSAltitude)
            FROM frame f
            JOIN version v on f.version_doi = v.doi
            WHERE v.deposit_doi = ?
        """
        params = (deposit.doi, )
        v_min, v_max = self.sql_connector.execute_query(query, params)[0]

        if v_min == None or v_max == None: return
        if v_min > v_max: v_min, v_max = v_max, v_min

        return round(v_min, 2), round(v_max, 2)

        
