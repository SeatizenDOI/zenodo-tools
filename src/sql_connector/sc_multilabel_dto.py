from shapely import wkb
from dataclasses import dataclass, field

from .sc_base_dto import AbstractManagerDTO

from ..utils.lib_tools import map_id_by_name
from ..utils.constants import MULTILABEL_MODEL_NAME

@dataclass
class MultilabelModel():
    id: int
    name: str
    link: str
    doi: str | None
    creation_date: str

@dataclass
class MultilabelClass():
    id: int | None
    name: str
    threshold: float
    ml_label_id: int
    ml_model_id: int

@dataclass
class MultilabelPrediction():
    score: float
    version_doi: str
    frame_id: int
    ml_class_id: int

@dataclass
class MultilabelAnnotationSession():
    annotation_date: str
    author_name: str
    dataset_name: str
    id: int | None

@dataclass
class MultilabelAnnotation():
    value: str
    frame_id: int
    ml_label_id: int
    ml_annotation_session_id: int

@dataclass
class MultilabelLabel():
    id: int
    name: str
    creation_date: str
    description: str

@dataclass
class MultilabelAnnotationSessionManager(AbstractManagerDTO):

    annotation_session: MultilabelAnnotationSession
    
    def get_all_annotations_informations(self) -> list:
        query = """SELECT ml.name, f.GPSPosition, f.GPSDatetime, f.GPSFix, f.version_doi, f.filename
                    FROM multilabel_annotation ma
                    JOIN multilabel_annotation_session mas ON mas.id = ma.ml_annotation_session_id
                    JOIN frame f ON f.id = ma.frame_id
                    JOIN multilabel_label ml on ml.id = ma.ml_label_id
                    WHERE mas.id = ? AND ma.value = 1;
                """
        params = (self.annotation_session.id, )

        result = []
        for label, GPSPosition, GPSDatetime, GPSFix, version_doi, filename in self.sql_connector.execute_query(query, params):
            position = wkb.loads(GPSPosition)
            result.append((label, position.y, position.x, GPSDatetime, GPSFix, f"{version_doi}/{filename}"))
        return result
        


@dataclass
class GeneralMultilabelManager(AbstractManagerDTO):
    
    __model: MultilabelModel = field(default=None)
    __class_ml: list[MultilabelClass] = field(default_factory=list)
    __labels: list[MultilabelLabel] = field(default_factory=list)
    __predictions: list[MultilabelPrediction] = field(default_factory=list)
    __annotations: list[MultilabelAnnotation] = field(default_factory=list)

    classIdMapByClassName: dict[str, int] = field(default=dict)
    labelIdMapByLabelName: dict[str, int] = field(default=dict)

    
    def __post_init__(self) -> None:
        self.setup_model()
        self.setup_class()
        self.setup_label()

        self.classIdMapByClassName = map_id_by_name(self.__class_ml, "name", "id")
        self.labelIdMapByLabelName = map_id_by_name(self.__labels, "name", "id")

    @property
    def class_ml(self) -> list[MultilabelClass]:
        return self.__class_ml

    @property
    def annotations_size(self) -> int:
        return len(self.__annotations)
    
    @property
    def predictions_size(self) -> int:
        return len(self.__predictions)


    def setup_model(self) -> None:
        """ Get the model link to constant """
        query = f"""
            SELECT *
            FROM multilabel_model
            WHERE link LIKE "%{MULTILABEL_MODEL_NAME}%";
        """
        result = self.sql_connector.execute_query(query)
        if len(result) != 1:
            raise NameError("Multilabel model is twice in database. Abort to fetch.")

        try:
            id, name, link , doi, creation_date = result[0]
            self.__model = MultilabelModel(id=id, name=name, link=link, doi=doi, creation_date=creation_date)
        except Exception:
            raise NameError("Something occurs during parse. May be the dto and the database doesn't match.")


    def setup_class(self) -> None:
        """ Get all class link to the model. """
        query = f"""
            SELECT mc.id, mc.name, mc.threshold, mc.ml_label_id, mc.ml_model_id 
            FROM multilabel_class mc
            INNER JOIN multilabel_model mm ON mm.id = mc.ml_model_id
            WHERE mm.id = ?;
        """
        params = (self.__model.id, )
        result = self.sql_connector.execute_query(query, params)
        
        for id, name, threshold, ml_label_id, ml_model_id in result:
            ml_class = MultilabelClass(
                id=id,
                name=name,
                threshold=threshold,
                ml_label_id=ml_label_id,
                ml_model_id=ml_model_id
            )
            self.__class_ml.append(ml_class)
    

    def setup_label(self) -> None:
        """ Get all labels for the class. """
        query = "SELECT * FROM multilabel_label"
        result = self.sql_connector.execute_query(query)
        for id, name, creation_date, description in result:
            self.__labels.append(MultilabelLabel(
                id=id,
                name=name,
                creation_date=creation_date,
                description=description
            ))
    

    def append(self, value: MultilabelPrediction | MultilabelAnnotation) -> None:
        """ Add predictions or annotations to object. """
        if isinstance(value, MultilabelPrediction):
            self.__predictions.append(value)
        elif isinstance(value, MultilabelAnnotation):
            self.__annotations.append(value)


    def insert_predictions(self) -> None:
        """ Insert all predictions store in object into sql database. """
        if self.predictions_size == 0:
            print("[WARNING] Cannot insert predictions in database, we don't have predictions.")
            return 

        query = f"""
        INSERT INTO multilabel_prediction
        (score, frame_id, ml_class_id, version_doi) 
        VALUES (?,?,?,?);
        """
        values = []
        for p in self.__predictions:
            values.append((p.score, 
                           p.frame_id, 
                           p.ml_class_id, 
                           p.version_doi
                        ))
        self.sql_connector.execute_query(query, values)
    
    def insert_annotations(self) -> None:
        """ Insert all annotations store in object into sql database. """
        if self.annotations_size == 0:
            print("[WARNING] Cannot insert annotations in database, we don't have annotations.")
            return 

        query = f"""
        INSERT INTO multilabel_annotation
        (value, frame_id, ml_label_id, ml_annotation_session_id) 
        VALUES (?,?,?,?);
        """
        values = []
        for a in self.__annotations:
            values.append((a.value, 
                           a.frame_id, 
                           a.ml_label_id, 
                           a.ml_annotation_session_id
                        ))
        self.sql_connector.execute_query(query, values)
    

    def get_predictions_from_frame_id(self, frame_id: int) -> tuple[dict[str, bool], str]:
        """ Return an object with class_name map with prediction. """
        query = """
                SELECT mp.score, mc.name, mc.threshold, (mp.score >= mc.threshold) AS pred, mp.version_doi
                FROM multilabel_prediction mp 
                JOIN frame f ON mp.frame_id = f.id
                JOIN multilabel_class mc ON mc.id = mp.ml_class_id
                WHERE f.id = ?;
            """
        params = (frame_id, )
        result = self.sql_connector.execute_query(query, params)

        class_name_with_pred, version_doi = {}, ""
        for score, class_name, threshold, pred, version_doi in result:
            class_name_with_pred[class_name] = pred
            version_doi = str(version_doi)
        
        return class_name_with_pred, version_doi


    def get_frame_id_from_frame_name(self, frame_name: str) -> int | None:
        """ Return frame_id is frame in db and we only have one frame_id else None """
        query = """ SELECT id from frame WHERE filename = ?; """
        params = (frame_name, )
        result = self.sql_connector.execute_query(query, params)
        if len(result) == 1: return result[0][0] # Access to frame_id
        return None
    

    def get_number_of_predictions_for_specific_version(self, prediction_version: str, frame_id: int) -> int:
        """ Return the count of predictions for the frame id and specific version. """
        query = """ SELECT COUNT(score) FROM multilabel_prediction WHERE version_doi = ? AND frame_id = ? ;"""
        params = (prediction_version, frame_id, )
        result = self.sql_connector.execute_query(query, params)
        return result[0][0]
    

    def get_specific_annotation_session(self, ml_annotation_session: MultilabelAnnotationSession) -> int: # TODO Use enum
        """ Return id if annotation exist else -1"""
        query = """ SELECT id from multilabel_annotation_session WHERE author_name = ? AND dataset_name = ? AND annotation_date = ?; """
        params = (ml_annotation_session.author_name, ml_annotation_session.dataset_name, ml_annotation_session.annotation_date, )
        result = self.sql_connector.execute_query(query, params)
        return -1 if len(result) == 0 else result[0][0]


    def insert_annotations_session(self, ml_annotation_session: MultilabelAnnotationSession) -> int:

        # Check if not in db.
        id = self.get_specific_annotation_session(ml_annotation_session)
        if id != -1: return -1 # Already exist 
        
        # Insert
        query = """ INSERT INTO multilabel_annotation_session (author_name, dataset_name, annotation_date) VALUES (?,?,?); """
        params = (ml_annotation_session.author_name, ml_annotation_session.dataset_name, ml_annotation_session.annotation_date, )
        self.sql_connector.execute_query(query, params)

        return self.get_specific_annotation_session(ml_annotation_session)


    def drop_annotation_session(self, id) -> None:
        query = """ DELETE FROM multilabel_annotation_session WHERE id = ?; """
        params = (id, )
        self.sql_connector.execute_query(query, params)
    
    
    def get_all_ml_annotations_session(self) -> list[MultilabelAnnotationSession]:
        query = """SELECT id, author_name, annotation_date, dataset_name FROM multilabel_annotation_session"""
        
        ml_anno_session = []
        for id, author_name, annotation_date, dataset_name in self.sql_connector.execute_query(query):
            ml_anno_session.append(MultilabelAnnotationSession(
                annotation_date=annotation_date,
                author_name=author_name,
                dataset_name=dataset_name,
                id=id
            ))
        return ml_anno_session

    def get_latest_annotations(self) -> list:
        """ Return latest annotations. """

        query = """
                WITH latest_annotations AS (
                    SELECT ma.frame_id, ma.ml_label_id, MAX(mas.annotation_date) AS most_recent_annotation_date
                    FROM multilabel_annotation ma
                    JOIN multilabel_annotation_session mas ON mas.id = ma.ml_annotation_session_id
                    GROUP BY ma.frame_id, ma.ml_label_id

                )
                SELECT ma.value, mas.annotation_date, f.filename, f.relative_path, f.version_doi, ml.name
                FROM multilabel_annotation ma
                JOIN multilabel_annotation_session mas ON mas.id = ma.ml_annotation_session_id
                JOIN latest_annotations la
                ON ma.frame_id = la.frame_id 
                    AND mas.annotation_date = la.most_recent_annotation_date
                    AND ma.ml_label_id = la.ml_label_id
                JOIN frame f ON f.id = ma.frame_id
                JOIN multilabel_label ml on ml.id = ma.ml_label_id;
        """
        return self.sql_connector.execute_query(query)