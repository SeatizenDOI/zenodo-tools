from datetime import datetime
from dataclasses import dataclass, field

from .base_model import AbstractBaseDAO

@dataclass
class MultilabelLabelDTO():
    id: int
    name: str
    creation_date: str
    description: str

    @property
    def creation_date_convert(self) -> datetime:
        return datetime.strptime(self._creation_date, "%Y-%m-%d")
    

@dataclass
class MultilabelLabelDAO(AbstractBaseDAO):
    table_name = "multilabel_label"

    __labels: list[MultilabelLabelDTO] = field(default_factory=list)
    __labels_by_id: dict[int, MultilabelLabelDTO] = field(default_factory=dict)
    __labels_by_name: dict[str, int] = field(default_factory=dict)


    @property
    def labels(self) -> list[MultilabelLabelDTO]:
        if len(self.__labels) == 0:
            self.__get_all()
        return self.__labels
    

    def get_label_by_id(self, label_id: int) -> MultilabelLabelDTO:
        """ Get label with specific id. """
        if label_id in self.__labels_by_id:
            return self.__labels_by_id.get(label_id)

        query = f""" SELECT id, name, creation_date, description 
                     FROM {self.table_name}
                     WHERE id = ?
                 """
        params = (label_id, )
        result = self.sql_connector.execute_query(query, params)
        if len(result) == 0:
            raise NameError("[ERROR] No multilabel label for this id.")
        
        id, name, creation_date, description = result[0]
        label = MultilabelLabelDTO(
                id=id,
                name=name,
                creation_date=creation_date,
                description=description
            )
        self.__labels_by_id[id] = label
        return label
    

    def get_label_by_name(self, label_name) -> MultilabelLabelDTO:
        """ Get label with specific name. """
        if label_name in self.__labels_by_name:
            return self.__labels_by_name.get(label_name)

        query = f""" SELECT id, name, creation_date, description 
                     FROM {self.table_name}
                     WHERE name = ?
                 """
        params = (label_name, )
        result = self.sql_connector.execute_query(query, params)
        
        if len(result) == 0:
            raise NameError("[ERROR] No multilabel label for this name.")
        
        if len(result) > 1:
            raise NameError("[ERROR] Too much multilabel label name for this name.")
        
        id, name, creation_date, description = result[0]
        label = MultilabelLabelDTO(
                id=id,
                name=name,
                creation_date=creation_date,
                description=description
            )
        self.__labels_by_name[name] = label
        return label


    def __get_all(self) -> None:
        """ Get all labels. """
        query = f""" SELECT id, name, creation_date, description 
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query)

        for id, name, creation_date, description in results:
            self.__labels.append(MultilabelLabelDTO(
                id=id,
                name=name,
                creation_date=creation_date,
                description=description
            ))
    