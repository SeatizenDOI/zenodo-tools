from datetime import datetime
from dataclasses import dataclass, field

from .base_model import AbstractBaseDAO, DataStatus
from .frame_model import FrameDTO, FrameDAO
from .ml_label import MultilabelLabelDTO, MultilabelLabelDAO

@dataclass
class MultilabelAnnotationSessionDTO():
    id: int | None
    annotation_date: str
    author_name: str
    dataset_name: str

    @property
    def annotation_date_convert(self) -> datetime:
        return datetime.strptime(self._creation_date, "%Y-%m-%d")


@dataclass
class MultilabelAnnotationDTO():
    value: str
    frame: FrameDTO
    ml_label: MultilabelLabelDTO
    ml_annotation_session: MultilabelAnnotationSessionDTO
    id: int | None = field(default=None)


@dataclass
class MultilabelAnnotationSessionDAO(AbstractBaseDAO):
    
    table_name = "multilabel_annotation_session"

    __ml_annotation_session: list[MultilabelAnnotationSessionDTO] = field(default_factory=list)
    __ml_anno_ses_by_id: dict[int, MultilabelAnnotationSessionDTO] = field(default_factory=dict)


    @property
    def ml_annotation_session(self) -> list[MultilabelAnnotationSessionDTO]:
        if len(self.__ml_annotation_session) == 0:
            self.__get_all()
        return self.__ml_annotation_session
    

    def get_ml_anno_ses_by_id(self, ml_anno_ses_id: int) -> MultilabelAnnotationSessionDTO:
        """ Get multilabel annotation session by id. """
        if ml_anno_ses_id in self.__ml_anno_ses_by_id:
            return self.__ml_anno_ses_by_id.get(ml_anno_ses_id)
        
        query = f""" SELECT id, annotation_date, author_name, dataset_name 
                     FROM {self.table_name}
                     WHERE id = ?
                 """

        param = (ml_anno_ses_id, )
        result = self.sql_connector.execute_query(query, param)
        if len(result) == 0:
            raise NameError("[ERROR] No multilabel annotation session for id.")
        
        id, annotation_date, author_name, dataset_name = result[0]
        ml_anno_ses = MultilabelAnnotationSessionDTO(
                id=id,
                annotation_date = annotation_date,
                author_name=author_name,
                dataset_name=dataset_name
            )
        self.__ml_anno_ses_by_id[id] = ml_anno_ses
        return ml_anno_ses
    

    def __get_all(self) -> None:
        """ Get all multilabel annotation session. """
        query = f""" SELECT id, annotation_date, author_name, dataset_name 
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)

        for id, annotation_date, author_name, dataset_name in results:
            self.__ml_annotation_session.append(MultilabelAnnotationSessionDTO(
                id=id,
                annotation_date = annotation_date,
                author_name=author_name,
                dataset_name=dataset_name
            ))
    

    def get_specific_annotation_session(self, anno_ses: MultilabelAnnotationSessionDTO) -> DataStatus | MultilabelAnnotationSessionDTO:
        """ Get specific multilabel annotation session. (with id)"""
        query = f"""SELECT id, annotation_date, author_name, dataset_name
                  FROM {self.table_name} 
                  WHERE annotation_date = ? AND author_name = ? AND dataset_name = ?"""
        params = (anno_ses.annotation_date, anno_ses.author_name, anno_ses.dataset_name, )
        results = self.sql_connector.execute_query(query, params)

        if len(results) == 0: return DataStatus.NO_DATA

        annotations_session = []
        for id, annotation_date, author_name, dataset_name in results:
            annotations_session.append(MultilabelAnnotationSessionDTO(
                id=id,
                annotation_date=annotation_date,
                author_name=author_name,
                dataset_name=dataset_name
            ))

        if len(annotations_session) == 0: return DataStatus.NO_DATA
        return annotations_session[0]
        

    def insert_and_get_id(self, anno_ses: MultilabelAnnotationSessionDTO) -> DataStatus | MultilabelAnnotationSessionDTO:
        """ Insert a multilabel annotation session and return a multilabel annotation session or Datastatus. """
        status = self.get_specific_annotation_session(anno_ses)
        if not isinstance(status, DataStatus): return  DataStatus.ALLREADY # Exists no need to add

        # Insert
        query = f""" INSERT INTO {self.table_name} 
                     (author_name, dataset_name, annotation_date) 
                     VALUES (?,?,?); 
                 """
        params = (anno_ses.author_name, anno_ses.dataset_name, anno_ses.annotation_date, )
        self.sql_connector.execute_query(query, params)

        return self.get_specific_annotation_session(anno_ses)
    

    def drop_annotation_session(self, anno_ses: MultilabelAnnotationSessionDTO) -> None:
        """ Remove annotation session by id. """
        query = """ DELETE FROM multilabel_annotation_session WHERE id = ?; """
        params = (anno_ses.id, )
        self.sql_connector.execute_query(query, params)


@dataclass
class MultilabelAnnotationDAO(AbstractBaseDAO):
    table_name = "multilabel_annotation"

    __annotations: list[MultilabelAnnotationDTO] = field(default_factory=list)

    __ml_labelDAO = MultilabelLabelDAO()
    __ml_anno_sesDAO = MultilabelAnnotationSessionDAO()
    __frameDAO = FrameDAO()

    @property
    def annotations(self) -> list[MultilabelAnnotationDTO]:
        if len(self.__annotations) == 0:
            self.__get_all()
        return self.__annotations
    

    def __get_all(self) -> None:
        """ Get all annotions. """
        query = f""" SELECT id, value, frame_id, ml_label_id, ml_annotation_session_id
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)

        for id, value, frame_id, ml_label_id, ml_annotation_session_id in results:
            label = self.__ml_labelDAO.get_label_by_id(ml_label_id)
            frame = self.__frameDAO.get_frame_by_id(frame_id)
            ml_anno_ses = self.__ml_anno_sesDAO.get_ml_anno_ses_by_id(ml_annotation_session_id)

            self.__annotations.append(MultilabelAnnotationDTO(
                id=id,
                value=value,
                frame_id=frame,
                ml_label=label,
                ml_annotation_session=ml_anno_ses
            )) 
    

    def insert(self, annotations: MultilabelAnnotationDTO | list[MultilabelAnnotationDTO]) -> None:
        """ Insert one or more annotations. """
        if isinstance(annotations, MultilabelAnnotationDTO):
            annotations = [annotations]
        
        if len(annotations) == 0:
            print("[WARNING] No annotations to add in database.")
        
        query = f""" INSERT INTO {self.table_name} 
                     (value, frame_id, ml_label_id, ml_annotation_session_id)
                     VALUES (?,?,?,?)
                 """
        values = []
        for a in annotations:
            values.append((a.value, a.frame.id, a.ml_label.id, a.ml_annotation_session.id, ))
        
        self.sql_connector.execute_query(query, values)
    

    def get_annotations_from_anno_ses(self, anno_ses: MultilabelAnnotationSessionDTO) -> list[MultilabelAnnotationDTO]:
        """ Get all annotations for an annotation session. """
        query = f""" SELECT id, value, frame_id, ml_label_id
                     FROM {self.table_name}
                     WHERE ml_annotation_session_id = ?
                 """
        params = (anno_ses.id, )
        results = self.sql_connector.execute_query(query, params)

        annotations = []
        for id, value, frame_id, ml_label_id in results:
            label = self.__ml_labelDAO.get_label_by_id(ml_label_id)
            frame = self.__frameDAO.get_frame_by_id(frame_id)

            annotations.append(MultilabelAnnotationDTO(
                id=id,
                value=value,
                frame=frame,
                ml_label=label,
                ml_annotation_session=anno_ses
            )) 
        return annotations
    

    def get_latest_annotations(self) -> list[MultilabelAnnotationDTO]:
        """ Get latest annotations. """
        query = """ SELECT ma.id, ma.value, ma.frame_id, ma.ml_label_id, ma.ml_annotation_session_id, MAX(mas.annotation_date) AS most_recent_annotation_date
                    FROM multilabel_annotation ma
                    JOIN multilabel_annotation_session mas ON mas.id = ma.ml_annotation_session_id
                    GROUP BY ma.frame_id, ma.ml_label_id
                 """

        results = self.sql_connector.execute_query(query)

        annotations = []
        for id, value, frame_id, ml_label_id, ml_annotation_session_id, date in results:
            label = self.__ml_labelDAO.get_label_by_id(ml_label_id)
            frame = self.__frameDAO.get_frame_by_id(frame_id)
            ml_anno_ses = self.__ml_anno_sesDAO.get_ml_anno_ses_by_id(ml_annotation_session_id)

            annotations.append(MultilabelAnnotationDTO(
                id=id,
                value=value,
                frame=frame,
                ml_label=label,
                ml_annotation_session=ml_anno_ses
            )) 
        return annotations