import enum

class AnnotationType(enum.Enum):
    MULTILABEL = "multilabel"


def get_annotation_type_from_opt(opt_annotation_type: str) -> AnnotationType:
    
    if opt_annotation_type == AnnotationType.MULTILABEL.value: return AnnotationType.MULTILABEL

    raise NameError("[ERROR] Annotation type provide is not valid.")