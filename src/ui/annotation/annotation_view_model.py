from mock.mock_entity import FAKE_ANNOTATION_STATE
from ui.annotation.annotation_state import AnnotationState
from ui.base.view_model import ViewModel


class AnnotationViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        # self.annotation_state = AnnotationState()
        self.annotation_state = FAKE_ANNOTATION_STATE

    def change_node_state(self, drag_node: int, new_pos: float):
        self.annotation_state.nodes[drag_node] = new_pos
        for node, x in self.annotation_state.nodes.items():
            if node < drag_node and x >= new_pos:
                self.annotation_state.nodes[node] = new_pos
            if node > drag_node and x <= new_pos:
                self.annotation_state.nodes[node] = new_pos

        self.state_changed.emit(self.annotation_state)
