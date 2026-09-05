from pathlib import Path

from PyQt6.QtCore import QSize, Qt
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

from core.load_audio.entity.audio_signal import AudioSignal
from core.save_audio.save_audio import SaveAudio
from core.settings.app_settings import settings
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.main.audio_info_dialog import AudioInfoDialog
from ui.main.open_audio_dialog import OpenAudioDialog
from ui.main.save_audio_dialog import SaveAudioDialog


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("Phonlab")
        self.resize(1200, 800)

        self.filters = "Sound files (*.wav)"
        self.splash = None
        self.clipboard: AudioSignal | None = None
        self.clip_counters: dict[str, int] = {}

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # --------- Menu --------------------
        self.create_menus()

        # ------- toolbar -------------
        self.create_toolbar()

    def create_menus(self):
        """Create application menus"""
        mainMenu = self.menuBar()
        self.style()

        self.open_action = QAction(
            QIcon.fromTheme("document-open"), self.tr("&Open"), self
        )
        self.open_action.setStatusTip(self.tr("Open a sound file"))
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file)

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
        self.recenter_action.setStatusTip(self.tr("Center view on selection"))
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

    def open_file(self, filename: str | None = None):
        """Open a new audio file in a new tab"""
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(self, filter=self.filters)

        if filename:
            options = OpenAudioDialog.get_options(filename, self)
            if options is None:
                return

            if self.splash is not None:
                self.splash.close()
                self.splash = None

            # Create new document
            doc = DocumentView(DocumentViewModel())
            doc.origin_name = Path(filename).name
            doc.origin_path = filename

            # Add tab with shortened filename
            tab_name = doc.origin_name
            index = self.tab_widget.addTab(doc, tab_name)
            self.tab_widget.setCurrentIndex(index)
            self.tab_widget.setTabToolTip(index, filename)

            # Load the audio file
            doc.load_audio(filename, options)

    def _open_clip_tab(self, source_doc: DocumentView, clip: AudioSignal):
        """Open a new tab containing the just-copied/cut samples, without
        stealing focus from source_doc"""
        doc = DocumentView(DocumentViewModel())

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

        target_fs = source_doc.view_model.primary_prepped_channel().fs
        doc.view_model.load_from_samples(clip, target_fs)

    def save_audio(self):
        doc = self.get_current_document()
        if not doc:
            return
        index = self.tab_widget.indexOf(doc)
        options = SaveAudioDialog.get_options(doc, self.tab_widget.tabText(index), self)
        if options is None:
            return
        raw = doc.view_model.primary_raw_channel()
        try:
            SaveAudio(
                options.path, raw.x, raw.fs, options.target_fs, options.scale
            ).invoke()
        except RuntimeError as err:
            QMessageBox.critical(
                self,
                self.tr("Save Audio"),
                self.tr("Could not save the file:\n{}").format(err),
            )

    def show_audio_info(self):
        doc = self.get_current_document()
        if doc:
            index = self.tab_widget.indexOf(doc)
            AudioInfoDialog.show_info(doc, self.tab_widget.tabText(index), self)

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
