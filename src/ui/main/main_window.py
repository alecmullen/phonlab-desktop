from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QWidget,
)

from core.settings.app_settings import settings
from ui.base.dependency_factory import ViewModelFactory
from ui.base.state import State
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import AudioState
from ui.main.component.open_audio_dialog import OpenAudioDialog
from ui.main.component.save_audio_dialog import SaveAudioDialog
from ui.main.main_view_model import MainViewModel
from ui.spectrogram.state.audio_prepped import AudioPrepped


class MainWindow(QMainWindow):
    def __init__(
        self, view_model_factory: ViewModelFactory, parent: QWidget | None = None
    ):
        super().__init__(parent)

        self.setWindowTitle("Phonlab")
        self.resize(1200, 800)

        self.filters = "Sound files and TextGrids (*.wav *.TextGrid)"
        self.splash = None
        self.clipboard: AudioState | None = None
        self.clip_counters: dict[str, int] = {}

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        # --------- Menu --------------------
        self.create_menus()

        # ------- toolbar -------------
        self.create_toolbar()

        self.view_model_factory = view_model_factory
        self.view_model = view_model_factory.create(MainViewModel)

    def create_menus(self):
        """Create application menus"""
        mainMenu = self.menuBar()
        self.style()

        self.open_action = QAction(
            QIcon.fromTheme("document-open"), self.tr("&Open"), self
        )
        self.open_action.setStatusTip(self.tr("Open a sound file"))
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.select_new_tab_files)

        self.close_action = QAction(
            QIcon.fromTheme("window-close"), self.tr("&Close"), self
        )
        self.close_action.setStatusTip(self.tr("Close current file"))
        self.close_action.setShortcut("Ctrl+W")
        self.close_action.triggered.connect(self.close_current_tab)

        self.save_action = QAction(self.tr("&Save…"), self)
        self.save_action.setStatusTip(
            self.tr("Save the current document's audio to a file")
        )
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_audio)

        self.audio_info_action = QAction(self.tr("Audio &Info"), self)
        self.audio_info_action.setShortcut("Ctrl+I")
        self.audio_info_action.setStatusTip(
            self.tr("Show sample rate, duration, and amplitude of the current document")
        )
        self.audio_info_action.triggered.connect(self.show_audio_info)

        self.exit_action = QAction(
            QIcon.fromTheme("application-exit"), self.tr("&Quit"), self
        )
        self.exit_action.setStatusTip(self.tr("Terminate the program"))
        self.exit_action.triggered.connect(self.quit_app)

        # File Menu
        if mainMenu is not None:
            fileMenu = mainMenu.addMenu("&File")
        if fileMenu is not None:
            fileMenu.addAction(self.open_action)
            fileMenu.addAction(self.close_action)
            fileMenu.addSeparator()
            fileMenu.addAction(self.save_action)
            fileMenu.addSeparator()
            fileMenu.addAction(self.audio_info_action)
            fileMenu.addSeparator()
            fileMenu.addAction(self.exit_action)

        self.undo_action = QAction(self.tr("&Undo"), self)
        self.undo_action.setStatusTip(self.tr("Undo the last cut or paste"))
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)

        self.redo_action = QAction(self.tr("&Redo"), self)
        self.redo_action.setStatusTip(self.tr("Redo the last undone cut or paste"))
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.redo)

        self.cut_action = QAction(self.tr("Cu&t"), self)
        self.cut_action.setStatusTip(self.tr("Cut the selected audio"))
        self.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        self.cut_action.triggered.connect(self.cut_selection)

        self.copy_action = QAction(self.tr("&Copy"), self)
        self.copy_action.setStatusTip(self.tr("Copy the selected audio"))
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.triggered.connect(self.copy_selection)

        self.paste_action = QAction(self.tr("&Paste"), self)
        self.paste_action.setStatusTip(self.tr("Paste audio at the mark"))
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.triggered.connect(self.paste_at_cursor)

        self.paste_special_action = QAction(self.tr("Paste &Special..."), self)
        self.paste_special_action.setStatusTip(
            self.tr(
                "Paste the clipboard clip, optionally reversed or into a new stereo channel"
            )
        )
        self.paste_special_action.setShortcut("Ctrl+Shift+V")
        self.paste_special_action.triggered.connect(self.paste_special)

        # Edit Menu
        if mainMenu is not None:
            editMenu = mainMenu.addMenu("&Edit")
        if editMenu is not None:
            editMenu.addAction(self.undo_action)
            editMenu.addAction(self.redo_action)
            editMenu.addSeparator()
            editMenu.addAction(self.cut_action)
            editMenu.addAction(self.copy_action)
            editMenu.addAction(self.paste_action)
            editMenu.addAction(self.paste_special_action)

        self.waveview_action = QAction(
            QIcon.fromTheme("audio-x-generic"), self.tr("&Wave"), self
        )
        self.waveview_action.setStatusTip(self.tr("View audio waveform"))
        self.waveview_action.setShortcut("Ctrl+1")
        self.waveview_action.triggered.connect(self.plot_wave)

        self.sgramview_action = QAction(
            QIcon.fromTheme("view-media-visualization"), self.tr("&Spectrogram"), self
        )
        self.sgramview_action.setStatusTip(self.tr("View waveform and spectrogram"))
        self.sgramview_action.setShortcut("Ctrl+2")
        self.sgramview_action.triggered.connect(self.plot_wave_sgram)
        self.sgramview_action.setEnabled(False)

        if settings.enable_annotation:
            self.annotationview_action = QAction(
                QIcon.fromTheme("view-media-visualization"),
                self.tr("&Annotation"),
                self,
            )
            self.annotationview_action.setStatusTip(self.tr("View annotations"))
            self.annotationview_action.setShortcut("Ctrl+3")
            self.annotationview_action.triggered.connect(self.plot_annotations)

        self.viewall_action = QAction(
            QIcon.fromTheme("view-fullscreen"), self.tr("View &All"), self
        )
        self.viewall_action.setStatusTip(self.tr("Zoom out to see the whole file"))
        self.viewall_action.setShortcut("Ctrl+A")
        self.viewall_action.triggered.connect(self.show_all)

        self.recenter_action = QAction(
            QIcon.fromTheme("mail-send"), self.tr("Re-center"), self
        )
        self.recenter_action.setStatusTip(
            self.tr("Center view on the selection, or the mark if nothing is selected")
        )
        self.recenter_action.triggered.connect(self.recenter_on_selection)

        # View Menu
        if mainMenu is not None:
            viewMenu = mainMenu.addMenu("&View")
        if viewMenu is not None:
            viewMenu.addAction(self.waveview_action)
            viewMenu.addAction(self.sgramview_action)
            viewMenu.addAction(self.annotationview_action)
            viewMenu.addAction(self.viewall_action)
            viewMenu.addAction(self.recenter_action)

    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar("Main ToolBar")
        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(16, 16))

        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        toolbar.addAction(self.waveview_action)
        toolbar.addAction(self.sgramview_action)
        if settings.enable_annotation:
            toolbar.addAction(self.annotationview_action)
        toolbar.addAction(self.viewall_action)
        toolbar.addAction(self.recenter_action)

        toolbar.addSeparator()
        self.play_action = QAction(
            QIcon.fromTheme("media-playback-start"), self.tr("&Play"), self
        )
        self.play_action.setStatusTip(self.tr("Play visible audio"))
        self.play_action.triggered.connect(self.play_visible)
        toolbar.addAction(self.play_action)

        self.stop_action = QAction(
            QIcon.fromTheme("media-playback-stop"), self.tr("&Stop"), self
        )
        self.stop_action.setStatusTip(self.tr("Stop audio playback"))
        self.stop_action.triggered.connect(self.stop_audio)
        toolbar.addAction(self.stop_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.exit_action)

    def get_current_document(self) -> DocumentView | None:
        """Get the currently active DocumentView"""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, DocumentView):
            return current_widget
        return None

    @pyqtSlot(object)
    def on_doc_state_change(self, state: State):
        if isinstance(state, AudioPrepped):
            self.sgramview_action.setEnabled(True)

    @pyqtSlot()
    def select_project_to_open(self):
        files_to_load: list[tuple[str, str, str | None]] = []

        dir_path = QFileDialog.getExistingDirectory(
            self, self.tr("Open Phonlab Directory")
        )
        if dir_path == "":
            return

        dir = Path(dir_path)

        config_file = next(dir.glob("phonlab.toml"), None)
        if config_file is None:
            answer = QMessageBox.question(
                self,
                self.tr("Initialize Project"),
                self.tr(
                    "No phonlab.toml found. Initialize phonlab project at {}?"
                ).format(dir_path),
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.select_project_to_open()
                return
            else:
                self.view_model.set_dir_path(dir_path)
                self.view_model.init_toml()

        all_files = list(dir.glob("*"))
        for path in all_files:
            if str(path).endswith(".wav"):
                file_stem = path.relative_to(dir_path).with_suffix("").as_posix()

                annotation_file = next(
                    (
                        str(file)
                        for file in all_files
                        if str(file).endswith(f"{file_stem}.TextGrid")
                    ),
                    None,
                )

                files_to_load.append((file_stem, str(path), annotation_file))

        self.open_files(files_to_load, dir_path)

    def open_single_document(self, filenames: list[str], dir: str | None = None):
        audio_files = [name for name in filenames if name.endswith(".wav")]
        annotation_files = [name for name in filenames if name.endswith(".TextGrid")]
        if len(audio_files) == 0:
            raise ValueError(self.tr("Please include a .wav file"))
        if len(audio_files) > 1 or len(annotation_files) > 1:
            raise ValueError(
                self.tr("Cannot select more than one .wav file and one .TextGrid file")
            )

        audio_file = audio_files[0]
        if dir is None:
            file_stem = Path(audio_file).with_suffix("").as_posix()
        else:
            file_stem = Path(audio_file).relative_to(dir).with_suffix("").as_posix()

        annotation_file = None
        if len(annotation_files) > 0:
            annotation_file = annotation_files[0]

        self.open_files([(file_stem, audio_file, annotation_file)], dir)

    @pyqtSlot()
    def select_files_to_open(self, dir: str | None = None):
        filenames, _ = QFileDialog.getOpenFileNames(
            self, directory=dir, filter=self.filters
        )
        if len(filenames) == 0:
            return

        try:
            self.open_single_document(filenames, dir)
        except ValueError as err:
            QMessageBox.information(None, self.tr("Error"), str(err))
            self.select_files_to_open(dir)

    @pyqtSlot()
    def select_new_tab_files(self):
        self.select_files_to_open(dir=self.view_model.dir_path)

    def open_files(
        self, paired_files: list[tuple[str, str, str | None]], dir_path: str | None
    ):
        """Open as audio file in separate tabs. paired_files is a list of tuples in the format
        (file_stem, audio_file, annotation_file), where file_stem is the path to the audio file,
        minus the suffix (relative path for project, absolute for ad-hoc singal document
        editing). audio_file and annotation_file are the absolute paths to the respective .wav
        and .TextGrid files"""

        self.view_model.set_dir_path(dir_path)

        for idx, (file_stem, audio_file, annotation_file) in enumerate(paired_files):
            if idx > 4:
                return
            options = OpenAudioDialog.get_options(audio_file, self)
            if options is None:
                return

            if self.splash is not None:
                self.splash.close()
                self.splash = None

            # Create new document
            doc_view_model = self.view_model_factory.create(
                DocumentViewModel, file_stem, dir_path
            )
            doc_view_model.subscribe(self.on_doc_state_change)
            doc = DocumentView(doc_view_model)
            doc.origin_name = Path(audio_file).name
            doc.origin_path = audio_file

            # Add tab with shortened filename
            tab_name = doc.origin_name
            index = self.tab_widget.addTab(doc, tab_name)
            self.tab_widget.setCurrentIndex(index)
            self.tab_widget.setTabToolTip(index, audio_file)

            # Load the audio file
            doc.load_audio(audio_file, options)

            if annotation_file is not None:
                doc.load_textgrid(annotation_file)

    def _open_clip_tab(self, source_doc: DocumentView, clip: AudioState):
        """Open a new tab containing the just-copied/cut samples, without
        stealing focus from source_doc"""
        doc_view_model = self.view_model_factory.create(DocumentViewModel)
        doc_view_model.subscribe(self.on_doc_state_change)
        doc = DocumentView(doc_view_model)

        # Always name after the ORIGINAL source file
        origin_name = source_doc.origin_name
        if not origin_name:
            source_index = self.tab_widget.indexOf(source_doc)
            origin_name = self.tab_widget.tabText(source_index)
        doc.origin_name = origin_name
        doc.origin_path = source_doc.origin_path

        n = self.clip_counters.get(origin_name, 0) + 1
        self.clip_counters[origin_name] = n
        tab_name = self.tr("CLIP {}: {}").format(n, origin_name)
        self.tab_widget.addTab(doc, tab_name)

        doc.view_model.load_from_samples(clip)

    pyqtSlot(int)

    def on_tab_changed(self, index: int):
        doc = self.get_current_document()

        if doc is not None:
            self.sgramview_action.setEnabled(
                doc.view_model.spectrogram_view_model.prepped_audio_state is not None
            )

    def save_audio(self):
        doc = self.get_current_document()
        if not doc:
            return
        index = self.tab_widget.indexOf(doc)
        options = SaveAudioDialog.get_options(doc, self.tab_widget.tabText(index), self)
        if options is None:
            return
        try:
            doc.view_model.save_audio(
                options.channels, options.path, options.target_fs, options.scale
            )
        except RuntimeError as err:
            QMessageBox.critical(
                self,
                self.tr("Save Audio"),
                self.tr("Could not save the file:\n{}").format(err),
            )

    def show_audio_info(self):
        doc = self.get_current_document()
        if doc:
            doc.open_audio_info()

    def close_tab(self, index: int):
        """Close a tab"""
        widget = self.tab_widget.widget(index)
        if isinstance(widget, DocumentView):
            widget.cleanup()
        self.tab_widget.removeTab(index)

    def close_current_tab(self):
        """Close the currently active tab"""
        index = self.tab_widget.currentIndex()
        if index >= 0:
            self.close_tab(index)

    # Delegate actions to current document
    def plot_wave(self):
        doc = self.get_current_document()
        if doc:
            doc.toggle_wave()

    def plot_wave_sgram(self):
        doc = self.get_current_document()
        if doc:
            doc.toggle_spectrogram()

    def plot_annotations(self):
        doc = self.get_current_document()
        if doc:
            doc.toggle_annotations()

    def show_all(self):
        doc = self.get_current_document()
        if doc:
            doc.show_all()

    def play_visible(self):
        doc = self.get_current_document()
        if doc:
            doc.play_visible()

    def stop_audio(self):
        doc = self.get_current_document()
        if doc:
            doc.stop_audio()

    def recenter_on_selection(self):
        """Delegate recenter to current document"""
        doc = self.get_current_document()
        if doc:
            doc.recenter_on_selection()

    def copy_selection(self):
        doc = self.get_current_document()
        if doc:
            clip = doc.copy_selection()
            if clip is not None:
                self.clipboard = clip
                self._open_clip_tab(doc, clip)

    def cut_selection(self):
        doc = self.get_current_document()
        if doc:
            clip = doc.cut_selection()
            if clip is not None:
                self.clipboard = clip
                self._open_clip_tab(doc, clip)

    def paste_at_cursor(self):
        doc = self.get_current_document()
        if doc and self.clipboard is not None:
            doc.paste_at_cursor(self.clipboard)

    def paste_special(self):
        doc = self.get_current_document()
        if doc and self.clipboard is not None:
            doc.paste_special(self.clipboard)

    def undo(self):
        doc = self.get_current_document()
        if doc:
            doc.undo()

    def redo(self):
        doc = self.get_current_document()
        if doc:
            doc.redo()

    def keyPressEvent(self, a0: QKeyEvent | None):
        """Forward keyboard events to current document"""
        doc = self.get_current_document()
        if doc is not None and a0 is not None:
            if a0.key() == Qt.Key.Key_Left:
                doc.go_back()
            elif a0.key() == Qt.Key.Key_Right:
                doc.advance()
            elif a0.key() == Qt.Key.Key_Down:
                doc.zoom_out()
            elif a0.key() == Qt.Key.Key_Up:
                doc.zoom_in()
            else:
                super().keyPressEvent(a0)
        else:
            super().keyPressEvent(a0)

    def quit_app(self):
        """Quit the application"""
        # Clean up all open documents
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, DocumentView):
                widget.cleanup()

        self.close()
        QApplication.quit()

    def closeEvent(self, a0: QCloseEvent | None):
        """Handle window close event"""
        # Clean up all open documents
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, DocumentView):
                widget.cleanup()

        if a0 is not None:
            a0.accept()
