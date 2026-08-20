from mock.mock_entity import FAKE_ANNOTATION_STATE
from ui.annotation.annotation_state import AnnotationState
from ui.base.view_model import ViewModel


class AnnotationViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        # self.annotation_state = AnnotationState()
        self.annotation_state = FAKE_ANNOTATION_STATE