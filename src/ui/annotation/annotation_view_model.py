import logging
from dataclasses import replace

from PyQt6.QtCore import pyqtSlot

from core.annotation.create_label import CreateLabel, ZeroLengthLabelError
from core.annotation.delete_node import DeleteNode, DeleteNodeError
from core.annotation.entity.annotation import Annotation
from core.annotation.load_annotation import LoadAnnotation
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode
from core.parse_textgrid.parse_textgrid import ParseTextGrid, ParseTextGridError
from core.parse_textgrid.write_textgrid import TextgridType, WriteTextGrid
from ui.annotation.state.annotation_label_state import AnnotationLabelState, to_label
from ui.annotation.state.annotation_node_state import AnnotationNodeState
from ui.annotation.state.annotation_selected_state import AnnotationSelectedState
from ui.annotation.state.annotation_state import (
    AnnotationState,
    to_annotation,
    to_annotation_state,
    update_annotation_state_from_window,
)
from ui.annotation.state.save_to_textgrid_state import SaveToTextGridAction
from ui.base.view_model import ViewModel
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.status_message_state import StatusMessageState

logger = logging.getLogger(__name__)


class AnnotationViewModel(ViewModel):
    def __init__(
        self,
        create_label: CreateLabel,
        update_label: UpdateLabel,
        update_node: UpdateNode,
        delete_node: DeleteNode,
        parse_text_grid: ParseTextGrid,
        write_text_grid: WriteTextGrid,
        load_annotation: LoadAnnotation,
        filestem: str | None = None,
    ):
        super().__init__()

        self.annotation_state = AnnotationState()
        self.loading_state = LoadProgressState()

        self.filestem = filestem
        self.load_annotation_use_case = load_annotation

        if filestem is not None:
            annotation = load_annotation(filestem)
            if annotation is not None:
                self.annotation_state = to_annotation_state(annotation)

        self.window_state: tuple[float, float] = (0.0, 0.0)

        self.annotation_view_state = AnnotationState()

        self.create_label_use_case = create_label
        self.update_label_use_case = update_label
        self.update_node_use_case = update_node
        self.delete_node_use_case = delete_node
        self.parse_textgrid_use_case = parse_text_grid
        self.write_textgrid_use_case = write_text_grid

    def change_node_state(self, drag_node: AnnotationNodeState, new_pos: float):
        new_pos = max(self.window_state[0], new_pos)
        new_pos = min(self.window_state[1], new_pos)

        if not all(extent.has_point_label for extent in drag_node.extents):
            for node in self.annotation_state.nodes.values():
                if node.id == drag_node.id:
                    continue
                if node.x < drag_node.x and node.x >= new_pos:
                    new_pos = node.x
                if node.x > drag_node.x and node.x <= new_pos:
                    new_pos = node.x

        self.update_node_use_case(drag_node.id, new_pos)

        self.annotation_state.nodes[drag_node.id] = replace(
            self.annotation_state.nodes[drag_node.id], x=new_pos
        )
        self.annotation_view_state.nodes[drag_node.id] = replace(
            self.annotation_view_state.nodes[drag_node.id], x=new_pos
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

    def reload_annotation(self):
        """Show the annotation currently in the database, e.g. after files were added
        to the project"""
        if self.filestem is None:
            return
        annotation = self.load_annotation_use_case(self.filestem)
        if annotation is None:
            self.annotation_state = AnnotationState()
            self.update_annotation_change()
        else:
            self.set_annotation_state(annotation)

    def has_annotation(self) -> bool:
        """True if there are any nodes or tiers, e.g. loaded from the project database"""
        return bool(self.annotation_state.nodes or self.annotation_state.types)

    def parse_textgrid(self, file_path: str, file_stem: str, overwrite: bool = False):
        @pyqtSlot(object)
        def on_success(annotation: Annotation):
            self.set_loading_state(False)
            self.set_annotation_state(annotation)

        @pyqtSlot(object)
        def on_error(error: Exception):
            self.set_loading_state(False)
            if isinstance(error, ParseTextGridError):
                self.state_changed.emit(
                    StatusMessageState(self.tr("Error parsing TextGrid"))
                )
                logger.exception("Error parsing TextGrid")
            else:
                raise error

        self.set_loading_state(True)

        self.launch_task(
            "parse_textgrid",
            self.parse_textgrid_use_case(file_path, file_stem, overwrite),
            on_success,
            on_error,
        )

    def trigger_write_textgrid_dialog(self):
        self.state_changed.emit(SaveToTextGridAction())

    def write_textgrid(self, file_path: str, tg_type: str):
        try:
            tg_type = TextgridType(tg_type)
        except ValueError:
            raise ValueError("TextGrid type parameter must be 'short' or 'long'")

        @pyqtSlot()
        def on_success():
            self.state_changed.emit(StatusMessageState(self.tr("TextGrid saved")))

        @pyqtSlot(object)
        def on_error(error: Exception):
            self.state_changed.emit(
                StatusMessageState(self.tr("TextGrid failed to save"))
            )
            logger.error("Write TextGrid", exc_info=error)

        self.launch_task(
            "write_textgrid",
            self.write_textgrid_use_case(
                to_annotation(self.annotation_state), file_path, tg_type
            ),
            on_success,
            on_error,
        )

    def set_loading_state(self, is_loading: bool):
        self.loading_state = LoadProgressState(is_loading)
        self.state_changed.emit(self.loading_state)

    def change_label_text(self, label: AnnotationLabelState, text: str):
        label = replace(label, label=text)
        self.update_label_use_case(to_label(label))

        self.annotation_state = self._change_label_text_in_state(
            label, self.annotation_state
        )
        self.annotation_view_state = self._change_label_text_in_state(
            label, self.annotation_view_state
        )

    def _change_label_text_in_state(
        self, updated_label: AnnotationLabelState, annotation: AnnotationState
    ) -> AnnotationState:
        for type_idx, type in enumerate(annotation.types):
            for label_idx, label in enumerate(type.labels):
                if label.id == updated_label.id:
                    new_label = replace(label, label=updated_label.label)
                    labels = type.labels.copy()
                    labels[label_idx] = new_label

                    new_type = replace(type, labels=labels)
                    types = annotation.types.copy()
                    types[type_idx] = new_type

                    return replace(annotation, types=types)

        return annotation

    def delete_node(self, node: int):
        try:
            annotation = self.delete_node_use_case(
                to_annotation(self.annotation_state), node
            )
        except DeleteNodeError:
            self.state_changed.emit(
                StatusMessageState(self.tr("Cannot delete node due to attached labels"))
            )
            return
        self.annotation_state = to_annotation_state(annotation)
        self.update_annotation_change()

    def create_label_from_selection(
        self,
        type_idx: int,
        start: float,
        end: float,
        same_node_threshold: float,
    ):
        try:
            annotation = to_annotation(self.annotation_state)
            annotation = self.create_label_use_case(
                annotation,
                annotation.types[type_idx].get_id(),
                start,
                end,
                same_node_threshold,
            )
        except ZeroLengthLabelError:
            self.state_changed.emit(
                StatusMessageState(self.tr("Zoom in to create shorter labels"))
            )
            return

        self.annotation_state = to_annotation_state(annotation)
        self.update_annotation_change()
