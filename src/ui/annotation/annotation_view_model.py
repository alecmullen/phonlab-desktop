from dataclasses import replace

from core.parse_textgrid.annotation import Annotation
from core.parse_textgrid.parse_textgrid import ParseTextGrid, ParseTextGridError
from ui.annotation.state.annotation_label_state import AnnotationLabelState
from ui.annotation.state.annotation_node_state import AnnotationNodeState
from ui.annotation.state.annotation_selected_state import AnnotationSelectedState
from ui.annotation.state.annotation_state import (
    AnnotationState,
    to_annotation_state,
    update_annotation_state_from_window,
)
from ui.base.view_model import ViewModel
from ui.document.state.status_message_state import StatusMessageState


class AnnotationViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        self.annotation_state = AnnotationState()
        self.window_state: tuple[float, float] = (0.0, 0.0)

        self.annotation_view_state = AnnotationState()

    def change_node_state(self, drag_node: AnnotationNodeState, new_pos: float):
        new_pos = max(self.window_state[0], new_pos)
        new_pos = min(self.window_state[1], new_pos)

        if not all(extent.has_point_label for extent in drag_node.extents):
            for node in self.annotation_state.nodes.values():
                if node.node == drag_node.node:
                    continue
                if node.x < drag_node.x and node.x >= new_pos:
                    new_pos = node.x
                if node.x > drag_node.x and node.x <= new_pos:
                    new_pos = node.x

        self.annotation_state.nodes[drag_node.node] = replace(
            self.annotation_state.nodes[drag_node.node], x=new_pos
        )
        self.annotation_view_state.nodes[drag_node.node] = replace(
            self.annotation_view_state.nodes[drag_node.node], x=new_pos
        )

        self.update_visible_annotation_change()

    def update_visible_annotation_change(self):
        """For changes that will not change which nodes and labels are visible
        (i.e. dragging a node)"""
        self.annotation_view_state = update_annotation_state_from_window(
            self.annotation_view_state, *self.window_state
        )
        self.state_changed.emit(self.annotation_view_state)

    def update_annotation_change(self):
        """Will update view for any changes to annotation or window"""
        self.annotation_view_state = update_annotation_state_from_window(
            self.annotation_state, *self.window_state
        )
        self.state_changed.emit(self.annotation_view_state)

    def set_annotation_state(self, annotation: Annotation):
        self.annotation_state = to_annotation_state(annotation)
        self.update_annotation_change()

    def set_window_state(self, start: float, end: float):
        self.window_state = (start, end)
        self.update_annotation_change()

    def select_label(self, label_view_state: AnnotationLabelState):
        try:
            sel_start = self.annotation_state.nodes[label_view_state.s_node].x
            sel_end = self.annotation_state.nodes[label_view_state.e_node].x
            self.state_changed.emit(AnnotationSelectedState(sel_start, sel_end))
        except (KeyError, AttributeError):
            raise ValueError("Missing node in annotation")

    def parse_textgrid(self, path: str):
        use_case = ParseTextGrid(path)
        try:
            annotation = use_case.invoke()
            self.set_annotation_state(annotation)
        except ParseTextGridError:
            self.state_changed.emit(
                StatusMessageState(self.tr("Error parsing TextGrid"))
            )

    def change_label_text(self, label_id: int, text: str):
        self.annotation_state = self._change_label_text_in_state(
            label_id, text, self.annotation_state
        )
        self.annotation_view_state = self._change_label_text_in_state(
            label_id, text, self.annotation_view_state
        )

    def _change_label_text_in_state(
        self, label_id: int, text: str, annotation: AnnotationState
    ) -> AnnotationState:
        for type_idx, type in enumerate(annotation.types):
            for label_idx, label in enumerate(type.labels):
                if label.id == label_id:
                    new_label = replace(label, label=text)
                    labels = type.labels.copy()
                    labels[label_idx] = new_label

                    new_type = replace(type, labels=labels)
                    types = annotation.types.copy()
                    types[type_idx] = new_type

                    return replace(annotation, types=types)

        return annotation
