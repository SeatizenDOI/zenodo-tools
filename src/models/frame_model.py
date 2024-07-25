from datetime import datetime
from dataclasses import dataclass, field

from shapely import wkb
from shapely.geometry import Point

from .base_model import AbstractBaseDAO
from .deposit_model import VersionDTO, VersionDAO

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
        return Point(self.gps_longitude, self.gps_latitude).wkb

    @property
    def gps_datetime_convert(self) -> datetime:
        return datetime.strptime(self._gps_datetime, "%Y-%m-%d %H:%M:%S")
    
    def __hash__(self) -> int:
        return hash((self.id, self.filename, self.version.doi))


@dataclass
class FrameDAO(AbstractBaseDAO):
    table_name = "frame"

    __frames: list[FrameDTO] = field(default_factory=list)
    __frames_by_id: dict[int, FrameDTO] = field(default_factory=dict)

    __versionDAO = VersionDAO()
    __frame_header = [
        "id","version_doi","original_filename","filename","relative_path",
        "GPSPosition","GPSAltitude","GPSPitch","GPSRoll","GPSTrack","GPSDatetime",
        "GPSFix"
    ]


    @property
    def frames(self):
        if len(self.__frames) == 0:
            self.__get_all()
        return self.__frames


    def __parse_frame_results(self, results) -> list[FrameDTO] | FrameDTO:
        """ Method to centralize parse method. """
        frames = []
        for id, version_doi, original_filename, filename, relative_path, GPSPosition,\
            GPSAltitude, GPSPitch,GPSRoll, GPSTrack, GPSDatetime, GPSFix in results:
            
            # Get lat, lon from GPSPosition.
            lat, lon = None, None
            if GPSPosition != None:
                position = wkb.loads(GPSPosition)
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
                     (version_doi, filename, original_filename, relative_path, GPSPosition,
                      GPSAltitude, GPSPitch, GPSRoll, GPSTrack, GPSDatetime, GPSFix) 
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)
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