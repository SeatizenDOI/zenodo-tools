from datetime import datetime
from dataclasses import dataclass, field

from .base_model import AbstractBaseDAO
from .ml_label import MultilabelLabelDAO, MultilabelLabelDTO

@dataclass
class MultilabelModelDTO():
    id: int
    name: str
    link: str
    doi: str | None
    creation_date: str

    @property
    def creation_date_convert(self) -> datetime:
        return datetime.strptime(self._creation_date, "%Y-%m-%d")


@dataclass
class MultilabelClassDTO():
    id: int | None
    name: str
    threshold: float
    ml_label: MultilabelLabelDTO
    ml_model: MultilabelModelDTO


@dataclass
class MultilabelModelDAO(AbstractBaseDAO):
    table_name = "multilabel_model"

    __models: list[MultilabelModelDTO] = field(default_factory=list)
    __models_by_id: dict[int, MultilabelModelDTO] = field(default_factory=dict)
    __last_model: MultilabelModelDTO = field(default=None)


    @property
    def models(self) -> list[MultilabelModelDTO]:
        if len(self.__models) == 0:
            self.__get_all()
        return self.__models


    @property
    def last_model(self) -> MultilabelModelDTO:
        """ Getter to get the lastest model. """
        if self.__last_model == None:
            self.__last_model = max(self.models, key=lambda model: model.creation_date)
        return self.__last_model
    

    def get_model_by_id(self, model_id: int) -> MultilabelModelDTO:
        """ Get model with specific id. """
        if model_id in self.__models_by_id:
            return self.__models_by_id.get(model_id)

        query = f""" SELECT id, name, link, doi, creation_date 
                     FROM {self.table_name}
                     WHERE id = ?
                 """
        params = (model_id, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[WARNING] No multilabel model found for this id.")
        
        id, name, link, doi, creation_date = result[0]
        model = MultilabelModelDTO(
                id=id,
                name=name,
                creation_date=creation_date,
                doi=doi,
                link=link
        )
        self.__models_by_id[id] = model
        return model
    

    def get_model_by_name(self, model_name: str) -> MultilabelModelDTO:
        """ Get model with specific name. """
        query = f""" SELECT id, name, link, doi, creation_date 
                     FROM {self.table_name}
                     WHERE link LIKE "%{model_name}%"
                 """
        result = self.sql_connector.execute_query(query)

        if len(result) == 0:
            raise NameError("[WARNING] No multilabel model found for this name.")
        
        id, name, link, doi, creation_date = result[0]
        model = MultilabelModelDTO(
                id=id,
                name=name,
                creation_date=creation_date,
                doi=doi,
                link=link
        )

        return model

    
    def __get_all(self) -> None:
        """ Get all models. """
        query = f""" SELECT id, name, link, doi, creation_date 
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)

        for id, name, link, doi, creation_date in results:
            self.__models.append(MultilabelModelDTO(
                id=id,
                name=name,
                creation_date=creation_date,
                doi=doi,
                link=link
            ))

@dataclass
class MultilabelClassDAO(AbstractBaseDAO):
    table_name = "multilabel_class"

    __classes: list[MultilabelClassDTO] = field(default_factory=list)
    __classes_by_id: dict[int, MultilabelClassDTO] = field(default_factory=dict)
    __classes_by_name_and_model: dict[str, MultilabelClassDTO] = field(default_factory=dict)

    __ml_modelDAO = MultilabelModelDAO()
    __ml_labelDAO = MultilabelLabelDAO()


    @property
    def classes(self) -> list[MultilabelClassDTO]:
        if len(self.__classes) == 0:
            self.__get_all()
        return self.__classes
    

    def get_class_by_id(self, class_id: int) -> MultilabelClassDTO:
        """ Get class by id. """
        if class_id in self.__classes_by_id:
            return self.__classes_by_id.get(class_id)
        
        query = f""" SELECT id, name, threshold, ml_label_id, ml_model_id 
                     FROM {self.table_name}
                     WHERE id = ?
                 """
        params = (class_id, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[ERROR] No multilabel class found for this id.")
        
        id, name, threshold, ml_label_id, ml_model_id = result[0]

        ml_model = self.__ml_modelDAO.get_model_by_id(ml_model_id)
        ml_label = self.__ml_labelDAO.get_label_by_id(ml_label_id) 

        ml_class = MultilabelClassDTO(
            id=id,
            name=name,
            ml_label=ml_label,
            ml_model=ml_model,
            threshold=threshold
        )

        self.__classes_by_id[id] = ml_class
        return ml_class
    

    def get_class_by_name_and_model(self, class_name: str, ml_model: MultilabelModelDTO) -> MultilabelClassDTO:
        """ Get class by model and by name. """
        if (class_name, ml_model.id) in self.__classes_by_name_and_model:
            return self.__classes_by_name_and_model.get((class_name, ml_model.id))
        
        query = f""" SELECT id, name, threshold, ml_label_id 
                     FROM {self.table_name}
                     WHERE name = ?
                 """
        params = (class_name, )
        result = self.sql_connector.execute_query(query, params)

        if len(result) == 0:
            raise NameError("[ERROR] No multilabel class found for this name.")
        
        id, name, threshold, ml_label_id = result[0]

        ml_label = self.__ml_labelDAO.get_label_by_id(ml_label_id) 

        ml_class = MultilabelClassDTO(
            id=id,
            name=name,
            ml_label=ml_label,
            ml_model=ml_model,
            threshold=threshold
        )

        self.__classes_by_name_and_model[(ml_class.name, ml_model.id)] = ml_class
        return ml_class


    def get_all_class_for_ml_model(self, ml_model: MultilabelModelDTO) -> list[MultilabelClassDTO]:
        """ Get all class for a model. """
        query = f""" SELECT id, name, threshold, ml_label_id 
                     FROM {self.table_name}
                     WHERE ml_model_id = ?
                 """
        params = (ml_model.id, )
        results = self.sql_connector.execute_query(query, params)
        ml_class = []
        for id, name, threshold, ml_label_id in results:

            ml_label = self.__ml_labelDAO.get_label_by_id(ml_label_id) 

            ml_class.append(MultilabelClassDTO(
                id=id,
                name=name,
                ml_label=ml_label,
                ml_model=ml_model,
                threshold=threshold
            ))
        return ml_class


    def __get_all(self) -> None:
        """ Get all classes. """
        query = f""" SELECT id, name, threshold, ml_label_id, ml_model_id 
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)

        for id, name, threshold, ml_label_id, ml_model_id in results:
            
            ml_model = self.__ml_modelDAO.get_model_by_id(ml_model_id)
            ml_label = self.__ml_labelDAO.get_label_by_id(ml_label_id) 

            self.__classes.append(MultilabelClassDTO(
                id=id,
                name=name,
                ml_label=ml_label,
                ml_model=ml_model,
                threshold=threshold
            ))