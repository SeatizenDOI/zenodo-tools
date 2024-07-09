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

    table_name = "multilabel_model"

@dataclass
class MultilabelClass():
    id: int | None
    name: str
    threshold: float
    multilabel_label_id: int
    multilabel_model_id: int

    table_name = "multilabel_class"

@dataclass
class MultilabelPrediction():
    score: float
    version_doi: str
    frame_id: int
    multilabel_class_id: int

    table_name = "multilabel_prediction"

@dataclass
class MultilabelAnnotation():
    value: str
    annotation_date: str
    frame_id: int
    multilabel_label_id: int

    table_name = "multilabel_annotation"

@dataclass
class MultilabelLabel():
    id: int
    name: str
    creation_date: str
    description: str

    table_name = "multilabel_label"

@dataclass
class GeneralMultilabelManager(AbstractManagerDTO):
    
    __model: MultilabelModel = field(default=None)
    __class_ml: list[MultilabelClass] = field(default_factory=list)
    __labels: list[MultilabelLabel] = field(default_factory=list)
    __predictions: list[MultilabelPrediction] = field(default_factory=list)
    __annotations: list[MultilabelAnnotation] = field(default_factory=list)

    classIdMapByClassName: dict[str, int] = field(default=dict)
    labelIdMapByClassName: dict[str, int] = field(default=dict)

    
    def __post_init__(self) -> None:
        self.setup_model()
        self.setup_class()
        self.setup_label()

        self.classIdMapByClassName = map_id_by_name(self.__class_ml, "name", "id")
        self.labelIdMapByClassName = map_id_by_name(self.__labels, "name", "id")

    
    @property
    def class_ml(self) -> list[MultilabelClass]:
        return self.__class_ml


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
            SELECT mc.id, mc.name, mc.threshold, mc.multilabel_label_id, mc.multilabel_model_id 
            FROM multilabel_class mc
            INNER JOIN multilabel_model mm ON mm.id = mc.multilabel_model_id
            WHERE mm.id = ?;
        """
        params = (self.__model.id, )
        result = self.sql_connector.execute_query(query, params)
        
        for id, name, threshold, ml_label_id, ml_model_id in result:
            ml_class = MultilabelClass(
                id=id,
                name=name,
                threshold=threshold,
                multilabel_label_id=ml_label_id,
                multilabel_model_id=ml_model_id
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
        if len(self.__predictions) == 0:
            print("[WARNING] Cannot insert predictions in database, we don't have predictions.")
            return 

        query = f"""
        INSERT OR IGNORE INTO multilabel_prediction
        (score, frame_id, multilabel_class_id, version_doi) 
        VALUES (?,?,?,?);
        """
        values = []
        for p in self.__predictions:
            values.append((p.score, 
                           p.frame_id, 
                           p.multilabel_class_id, 
                           p.version_doi
                        ))
        self.sql_connector.execute_query(query, values)
    
    def insert_annotations(self) -> None:
        """ Insert all annotations store in object into sql database. """
        if len(self.__annotations) == 0:
            print("[WARNING] Cannot insert annotations in database, we don't have annotations.")
            return 

        query = f"""
        INSERT OR IGNORE INTO multilabel_annotation
        (value, frame_id, multilabel_label_id, annotation_date) 
        VALUES (?,?,?,?);
        """
        values = []
        for a in self.__annotations:
            values.append((a.value, 
                           a.frame_id, 
                           a.multilabel_label_id, 
                           a.annotation_date
                        ))
        self.sql_connector.execute_query(query, values)
    

    def get_predictions_from_frame_id(self, frame_id: int) -> tuple[dict[str, bool], str]:
        """ Return an object with class_name map with prediction. """
        query = """
                SELECT mp.score, mc.name, mc.threshold, (mp.score >= mc.threshold) AS pred, mp.version_doi
                FROM multilabel_prediction mp 
                JOIN frame f ON mp.frame_id = f.id
                JOIN multilabel_class mc ON mc.id = mp.multilabel_class_id
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
        """ Return frame id is frame is in db else None """
        query = """
                SELECT id from frame WHERE filename = ?;
            """
        params = (frame_name, )
        result = self.sql_connector.execute_query(query, params)
        if len(result) == 1: return result[0][0] # Access to frame_id
        return None