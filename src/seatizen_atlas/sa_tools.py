import enum
import pandas as pd
from pathlib import Path

class AnnotationType(enum.Enum):
    MULTILABEL = "multilabel"


def get_annotation_type_from_opt(opt_annotation_type: str) -> AnnotationType:
    
    if opt_annotation_type == AnnotationType.MULTILABEL.value: return AnnotationType.MULTILABEL

    raise NameError("[ERROR] Annotation type provide is not valid.")


def load_and_build_parser_old_new_multilabel_class() -> dict:
    """ 
        During the paper creation and submission process, 
        the multilabel class names changed but were not updated in the model metadata. 
        All sessions using the model DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze are impacted. 
        See https://zenodo.org/records/13951614
    """

    filepath = Path("src/seatizen_atlas/matching_between_old_new_label_multilabel.csv")

    if not filepath.exists():
        raise FileNotFoundError(f"Cannot get the file {filepath}")
    
    df_data = pd.read_csv(filepath)

    new_label_map_by_old_label = {}
    for i, row in df_data.iterrows():
        new_label_map_by_old_label[row["old_label"]] = row["label"]
    
    return new_label_map_by_old_label