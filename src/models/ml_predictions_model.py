from dataclasses import dataclass, field

from .base_model import AbstractBaseDAO
from .deposit_model import VersionDTO, VersionDAO
from .frame_model import FrameDAO, FrameDTO
from .ml_model_model import MultilabelClassDAO, MultilabelClassDTO, MultilabelModelDTO

@dataclass
class MultilabelPredictionDTO():
    score: float
    version: VersionDTO
    frame: FrameDTO
    ml_class: MultilabelClassDTO
    id: int | None = field(default=None)


@dataclass
class MultilabelPredictionDAO(AbstractBaseDAO):
    table_name = "multilabel_prediction"

    __predictions: list[MultilabelPredictionDTO] = field(default_factory=list)

    __frameDAO = FrameDAO()
    __ml_classDAO = MultilabelClassDAO()
    __versionDAO = VersionDAO()


    @property
    def predictions(self) -> list[MultilabelPredictionDTO]:
        if len(self.__predictions) == 0:
            self.__get_all()
        return self.__predictions
    

    def __get_all(self) -> None:
        """ Get all predictions. """
        query = f""" SELECT id, score, version_doi, frame_id, ml_class_id
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)

        for id, score, version_doi, frame_id, ml_class_id in results:
            version = self.__versionDAO.get_version_by_doi(version_doi)
            frame = self.__frameDAO.get_frame_by_id(frame_id)
            ml_class = self.__ml_classDAO.get_class_by_id(ml_class_id)

            self.__predictions.append(MultilabelPredictionDTO(
                id=id,
                score=score,
                version=version,
                frame=frame,
                ml_class=ml_class
            ))
    

    def get_pred_by_frame_version(self, p_ver: VersionDTO, frame: FrameDTO) -> list[MultilabelPredictionDTO]:
        """ Get predictions by frame and version. """
        query = f""" SELECT id, score, version_doi, frame_id, ml_class_id
                     FROM {self.table_name}
                     WHERE version_doi = ? AND frame_id = ?;
                 """
        params = (p_ver.doi, frame.id, )
        results = self.sql_connector.execute_query(query, params)

        predictions = []
        for id, score, version_doi, frame_id, ml_class_id in results:
            version = self.__versionDAO.get_version_by_doi(version_doi)
            frame = self.__frameDAO.get_frame_by_id(frame_id)
            ml_class = self.__ml_classDAO.get_class_by_id(ml_class_id)

            predictions.append(MultilabelPredictionDTO(
                id=id,
                score=score,
                version=version,
                frame=frame,
                ml_class=ml_class
            ))
        return predictions
    

    def insert(self, preds: MultilabelPredictionDTO | list[MultilabelPredictionDTO]) -> None:
        """ Insert one or more predictions."""
        # Deal only with list.
        if isinstance(preds, MultilabelPredictionDTO):
            preds = [preds]
        
        if len(preds) == 0:
            print("[WARNING] Cannot insert preds in database, we don't have preds.")
            return
        
        query = f""" INSERT INTO {self.table_name}
                     (score, version_doi, frame_id, ml_class_id) 
                     VALUES (?,?,?,?)
                 """
        values = []
        for p in preds:
            values.append((p.score, p.version.doi, p.frame.id, p.ml_class.id))
        
        self.sql_connector.execute_query(query, values)
    

    def get_predictions_for_specific_model_and_frame_name(self, frame: FrameDTO, ml_model: MultilabelModelDTO) -> list[MultilabelPredictionDTO]:
        """ Get predictions for specific model and frame """
        query = f""" SELECT mlp.id, mlp.score, mlp.version_doi, mlp.ml_class_id
                     FROM {self.table_name} mlp 
                     JOIN multilabel_class mlc ON mlc.id = mlp.ml_class_id
                     JOIN multilabel_model mlm ON mlm.id = mlc.ml_model_id
                     WHERE mlp.frame_id = ? AND mlc.ml_model_id = ?;
                 """
        params = (frame.id, ml_model.id, )
        results = self.sql_connector.execute_query(query, params)

        predictions = []

        for id, score, version_doi, ml_class_id in results:
            version = self.__versionDAO.get_version_by_doi(version_doi)
            ml_class = self.__ml_classDAO.get_class_by_id(ml_class_id)
            
            predictions.append(MultilabelPredictionDTO(
                id=id,
                score=score,
                version=version,
                frame=frame,
                ml_class=ml_class
            ))
        return predictions
    

    def get_predictions_frame_and_class(self, frame: FrameDTO, class_ids: list[int]) -> list[MultilabelPredictionDTO]:
        """ Get predictions by frames and list of class_id """
        query = f""" SELECT id, score, version_doi, ml_class_id
                     FROM {self.table_name}  
                     WHERE frame_id = ? AND ml_class_id IN ({', '.join(['?' for _ in class_ids])});
                 """
        params = (frame.id, ) + tuple(class_ids)
        results = self.sql_connector.execute_query(query, params)

        predictions = []

        for id, score, version_doi, ml_class_id in results:
            version = self.__versionDAO.get_version_by_doi(version_doi)
            ml_class = self.__ml_classDAO.get_class_by_id(ml_class_id)
            
            predictions.append(MultilabelPredictionDTO(
                id=id,
                score=score,
                version=version,
                frame=frame,
                ml_class=ml_class
            ))
        return predictions
