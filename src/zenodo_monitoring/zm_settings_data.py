from src.models.ml_model_model import MultilabelModelDAO, MultilabelClassDAO

class SettingsData:
    
    def __init__(self) -> None:
        self.classes_map_by_model_id = {}
        self.model_dash_format = []

        self.ml_model_manager = MultilabelModelDAO()
        self.ml_classes_manager = MultilabelClassDAO()

        self.group_name_and_ids = {}

        self.setup_data()
    
    def setup_data(self) -> None:
        """ Setup data. """

        # Model name.
        self.model_dash_format = [{'label': m.name, 'value': m.id} for m in self.ml_model_manager.models]
        
        # Classe by model id.
        for model in self.ml_model_manager.models:
            classes = self.ml_classes_manager.get_all_class_for_ml_model(model)
            self.classes_map_by_model_id[model.id] = [{'label': cls.name, 'value': cls.id} for cls in classes]


    def get_class_by_model(self, model_id: int) -> list:
        return self.classes_map_by_model_id[model_id] if model_id in self.classes_map_by_model_id else []


    def add_group(self, session_id: str, group_name: str, model_id: int, class_ids: list) -> None:
        # Ensure session_id in group_name_and_ids
        if session_id not in self.group_name_and_ids:
            self.group_name_and_ids[session_id] = {}
        self.group_name_and_ids[session_id][(group_name, model_id)] = class_ids


    def get_group(self, session_id: str) -> dict:
        return self.group_name_and_ids[session_id]
    
    
    def delete_group(self, session_id: str, group_name: str, model_id: int) -> None:
        """ Remove a group_name in group_name_and_ids. """
        del self.group_name_and_ids[session_id][(group_name, model_id)]
    

    def serialize_data(self, session_id: str):
        """ Convert key(name, model_id) into name_/\_id. """
        serialize_data = {}

        for name, id in self.group_name_and_ids[session_id]:
            serialize_data[f"{name}_/\_{id}"] = self.group_name_and_ids[session_id][(name, id)]
        
        return serialize_data
    
    def set_serialized_data(self, session_id: str, data: dict):
        """ Unconvert name_/\_id into key(name, model_id) and save it. """
        # Ensure session_id in group_name_and_ids
        if session_id not in self.group_name_and_ids:
            self.group_name_and_ids[session_id] = {}

        for serialized_key in data:
            name, id = serialized_key.split("_/\_")
            self.group_name_and_ids[session_id][(name, int(id))] = data[serialized_key]
    
    def set_and_verify_serialize_data(self, session_id: str, data: dict):
        """ Try to unserialize and verify it data is good before to keep it. """
        
        # Ensure session_id in group_name_and_ids
        if session_id not in self.group_name_and_ids:
            self.group_name_and_ids[session_id] = {}

        for serialized_key in data:
            try:
                group_name, model_id = serialized_key.split("_/\_")
                model_id = int(model_id)
                # Get model and check if exists.
                model = self.ml_model_manager.get_model_by_id(model_id)
                class_ids = data.get(serialized_key, [])

            except Exception as e:
                print(e)
                continue
            
            # Verify if not exists
            if (group_name, model_id) in self.group_name_and_ids[session_id]:
                print(f"Group name already exists. : {group_name}")
                continue
            
            # Verify if class match with model and exists.
            all_classes_id_for_specific_model = [cls.id for cls in self.ml_classes_manager.get_all_class_for_ml_model(model)]
            try:
                class_ids_to_keep = []
                for cls_id in [int(cls_id) for cls_id in class_ids]:
                    if cls_id not in all_classes_id_for_specific_model:
                        print(f"Class id {cls_id} not found for {group_name}")
                    else:
                        class_ids_to_keep.append(cls_id)
            except Exception as e:
                print(e)
                continue

            self.group_name_and_ids[session_id][(group_name, model_id)] = class_ids_to_keep 