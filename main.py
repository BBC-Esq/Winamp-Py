import sys
from pathlib import Path
import ctypes
from threading import Lock

import numpy as np
import pyaudio
import vlc
from PySide6.QtCore import Qt, QTimer, Signal, QSettings, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QWheelEvent, QMouseEvent, QSurfaceFormat, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QStyle,
    QMenu,
    QMenuBar,
    QStyleOptionSlider,
    QFileDialog,
    QSplitter,
    QFrame,
    QGraphicsOpacityEffect,
)

from visual_geiss import GeissVisualization


VISUALIZATIONS = [
    ("Geiss", GeissVisualization),
]


class ClickableSlider(QSlider):
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            groove_rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderGroove, self
            )
            handle_rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderHandle, self
            )
            
            if self.orientation() == Qt.Orientation.Horizontal:
                slider_length = handle_rect.width()
                slider_min = groove_rect.x()
                slider_max = groove_rect.right() - slider_length + 1
                pos = event.position().x()
            else:
                slider_length = handle_rect.height()
                slider_min = groove_rect.y()
                slider_max = groove_rect.bottom() - slider_length + 1
                pos = event.position().y()
            
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                int(pos - slider_min), slider_max - slider_min,
                opt.upsideDown
            )
            self.setValue(value)
            self.sliderMoved.emit(value)
            event.accept()
        else:
            super().mousePressEvent(event)


AudioPlayCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_int64)
AudioPauseCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
AudioResumeCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
AudioFlushCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
AudioDrainCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


class AudioAnalyzer:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 2
        self.lock = Lock()
        
        self.fft_size = 2048
        self.num_bars = 64
        self.bar_values = np.zeros(self.num_bars)
        self.waveform = np.zeros(512)
        self.audio_buffer = []
        
        self.bass_level = 0.0
        self.mid_level = 0.0
        self.treble_level = 0.0
        self.beat_detected = False
        self.energy_history = []
        
        self.pyaudio_instance = pyaudio.PyAudio()
        self.stream = None
        self.volume = 1.0
        
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        self._play_cb = AudioPlayCb(self._on_play)
        self._pause_cb = AudioPauseCb(self._on_pause)
        self._resume_cb = AudioResumeCb(self._on_resume)
        self._flush_cb = AudioFlushCb(self._on_flush)
        self._drain_cb = AudioDrainCb(self._on_drain)
    
    def _on_play(self, data, samples, count, pts):
        try:
            audio_data = ctypes.string_at(samples, count * self.channels * 2)
            samples_array = np.frombuffer(audio_data, dtype=np.int16).copy()
            
            if self.volume != 1.0:
                samples_array = (samples_array * self.volume).astype(np.int16)
                audio_data = samples_array.tobytes()
            
            if self.stream and self.stream.is_active():
                self.stream.write(audio_data)
            
            with self.lock:
                self.audio_buffer.extend(samples_array)
                if len(self.audio_buffer) > self.fft_size * 4:
                    self.audio_buffer = self.audio_buffer[-self.fft_size * 2:]
                
                if len(self.audio_buffer) >= self.fft_size:
                    self._process_audio()
        except Exception:
            pass
    
    def _on_pause(self, data, pts):
        pass
    
    def _on_resume(self, data, pts):
        pass
    
    def _on_flush(self, data, pts):
        with self.lock:
            self.audio_buffer.clear()
    
    def _on_drain(self, data):
        pass
    
    def _process_audio(self):
        samples = np.array(self.audio_buffer[-self.fft_size:], dtype=np.float32)
        
        if self.channels == 2:
            samples = samples.reshape(-1, 2).mean(axis=1)
        
        samples = samples / 32768.0
        
        waveform_indices = np.linspace(0, len(samples) - 1, len(self.waveform), dtype=int)
        self.waveform = samples[waveform_indices].copy()
        
        window = np.hanning(len(samples))
        windowed = samples * window
        
        fft = np.fft.rfft(windowed)
        magnitudes = np.abs(fft)
        
        freq_bins = len(magnitudes)
        bar_values = np.zeros(self.num_bars)
        
        for i in range(self.num_bars):
            low = int((i / self.num_bars) ** 2 * freq_bins * 0.5)
            high = int(((i + 1) / self.num_bars) ** 2 * freq_bins * 0.5)
            high = max(high, low + 1)
            if high <= freq_bins:
                bar_values[i] = np.mean(magnitudes[low:high])
        
        max_val = np.max(bar_values)
        if max_val > 0:
            bar_values = bar_values / max_val
        
        bar_values = np.power(bar_values, 0.6)
        self.bar_values = self.bar_values * 0.3 + bar_values * 0.7
        
        bass_bins = int(freq_bins * 0.05)
        mid_bins = int(freq_bins * 0.2)
        
        self.bass_level = np.mean(magnitudes[:bass_bins]) / (max_val + 0.001) if max_val > 0 else 0
        self.mid_level = np.mean(magnitudes[bass_bins:mid_bins]) / (max_val + 0.001) if max_val > 0 else 0
        self.treble_level = np.mean(magnitudes[mid_bins:]) / (max_val + 0.001) if max_val > 0 else 0
        
        current_energy = np.sum(magnitudes[:bass_bins])
        self.energy_history.append(current_energy)
        if len(self.energy_history) > 43:
            self.energy_history.pop(0)
        
        if len(self.energy_history) >= 43:
            avg_energy = np.mean(self.energy_history)
            self.beat_detected = current_energy > avg_energy * 1.5
        else:
            self.beat_detected = False
    
    def start_stream(self):
        if self.stream is None or not self.stream.is_active():
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024
            )
    
    def stop_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        with self.lock:
            self.audio_buffer.clear()
            self.bar_values = np.zeros(self.num_bars)
            self.waveform = np.zeros(512)
    
    def set_volume(self, volume):
        self.volume = volume
    
    def get_bar_values(self):
        with self.lock:
            return self.bar_values.copy()
    
    def get_waveform(self):
        with self.lock:
            return self.waveform.copy()
    
    def get_levels(self):
        with self.lock:
            return self.bass_level, self.mid_level, self.treble_level, self.beat_detected
    
    def cleanup(self):
        self.stop_stream()
        self.pyaudio_instance.terminate()


class PlaylistWidget(QListWidget):
    
    files_dropped = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):
                    files.append(file_path)
            if files:
                self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
    
    def show_context_menu(self, position):
        item = self.itemAt(position)
        if item:
            menu = QMenu(self)
            
            delete_action = QAction("Remove from queue", self)
            delete_action.triggered.connect(lambda: self.remove_item(item))
            menu.addAction(delete_action)
            
            menu.exec(self.mapToGlobal(position))
    
    def remove_item(self, item):
        row = self.row(item)
        self.takeItem(row)


class FullscreenWindow(QWidget):
    exit_fullscreen = Signal()
    volume_change = Signal(int)
    track_double_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setMouseTracking(True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.visualizer = None

        self.panel_height = 350
        self.panel_visible = False
        self.panel_animating = False
        self.trigger_zone = 60
        self.mouse_in_panel = False

        panel_style = """
            QWidget#fullscreenPanel {
                background-color: rgba(25, 25, 25, 230);
                border-top: 1px solid rgba(80, 80, 80, 150);
            }
            QPushButton {
                background-color: rgba(60, 60, 60, 200);
                border: none;
                border-radius: 5px;
                padding: 8px;
                min-width: 36px;
                min-height: 36px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 200);
            }
            QLabel {
                background-color: transparent;
                color: white;
            }
            QSlider::groove:horizontal {
                background: rgba(60, 60, 60, 200);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(0, 120, 200, 200);
                border-radius: 3px;
            }
            QListWidget {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 1px solid rgba(80, 80, 80, 100);
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 200, 180);
            }
            QListWidget::item:hover {
                background-color: rgba(70, 70, 70, 200);
            }
        """

        self.panel_widget = QWidget(self)
        self.panel_widget.setObjectName("fullscreenPanel")
        self.panel_widget.setStyleSheet(panel_style)
        self.panel_widget.setMouseTracking(True)

        panel_layout = QVBoxLayout(self.panel_widget)
        panel_layout.setContentsMargins(20, 12, 20, 12)
        panel_layout.setSpacing(8)

        self.now_playing_label = QLabel("Now playing:")
        self.now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.now_playing_label.setStyleSheet("font-size: 13px; font-weight: bold; color: white;")
        panel_layout.addWidget(self.now_playing_label)

        time_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet("color: white; font-size: 12px;")
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet("color: white; font-size: 12px;")
        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.progress_slider)
        time_layout.addWidget(self.duration_label)
        panel_layout.addLayout(time_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setStyleSheet("font-size: 16px;")
        self.play_btn = QPushButton("⏸")
        self.play_btn.setStyleSheet("font-size: 16px;")
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setStyleSheet("font-size: 16px;")
        self.next_btn = QPushButton("⏭")
        self.next_btn.setStyleSheet("font-size: 16px;")

        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("font-size: 14px;")
        self.volume_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setMaximumWidth(100)
        self.volume_value_label = QLabel("70%")
        self.volume_value_label.setStyleSheet("color: white; font-size: 12px;")
        self.volume_value_label.setMinimumWidth(35)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.prev_btn)
        buttons_layout.addWidget(self.play_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.next_btn)
        buttons_layout.addSpacing(20)
        buttons_layout.addWidget(volume_label)
        buttons_layout.addWidget(self.volume_slider)
        buttons_layout.addWidget(self.volume_value_label)
        buttons_layout.addStretch()
        panel_layout.addLayout(buttons_layout)

        queue_label = QLabel("Queue:")
        queue_label.setStyleSheet("font-weight: bold; color: rgba(200, 200, 200, 200); font-size: 12px;")
        panel_layout.addWidget(queue_label)

        self.playlist_mirror = QListWidget()
        self.playlist_mirror.setMouseTracking(True)
        self.playlist_mirror.itemDoubleClicked.connect(self._on_playlist_double_click)
        panel_layout.addWidget(self.playlist_mirror, 1)

        hint_label = QLabel("Double-click to exit fullscreen • ESC to exit")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: rgba(200, 200, 200, 120); font-size: 10px;")
        panel_layout.addWidget(hint_label)

        self.slide_animation = QPropertyAnimation(self.panel_widget, b"geometry")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.slide_animation.finished.connect(self._on_animation_finished)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._on_hide_timeout)

        self.cursor_timer = QTimer(self)
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.timeout.connect(self._hide_cursor)
        self.cursor_hide_delay = 3000

        self.mouse_poll_timer = QTimer(self)
        self.mouse_poll_timer.timeout.connect(self._poll_mouse_position)
        self.mouse_poll_timer.start(100)
        self.last_cursor_pos = None

    def _on_playlist_double_click(self, item):
        row = self.playlist_mirror.row(item)
        self.track_double_clicked.emit(row)

    def sync_playlist(self, playlist_widget, current_index):
        self.playlist_mirror.clear()
        for i in range(playlist_widget.count()):
            source_item = playlist_widget.item(i)
            mirror_item = QListWidgetItem(source_item.text())
            mirror_item.setToolTip(source_item.toolTip())
            self.playlist_mirror.addItem(mirror_item)
        if 0 <= current_index < self.playlist_mirror.count():
            self.playlist_mirror.setCurrentRow(current_index)

    def update_playlist_selection(self, index):
        if 0 <= index < self.playlist_mirror.count():
            self.playlist_mirror.setCurrentRow(index)

    def set_visualizer(self, visualizer):
        if self.visualizer:
            self.main_layout.removeWidget(self.visualizer)
        self.visualizer = visualizer
        if visualizer:
            self.main_layout.addWidget(visualizer)
            visualizer.double_clicked.connect(self.on_double_click)

    def take_visualizer(self):
        self.mouse_poll_timer.stop()
        vis = self.visualizer
        if vis:
            vis.double_clicked.disconnect(self.on_double_click)
            self.main_layout.removeWidget(vis)
            self.visualizer = None
        return vis

    def showEvent(self, event):
        super().showEvent(event)
        self.panel_visible = False
        self.panel_widget.raise_()
        QTimer.singleShot(100, self._deferred_init)

    def _deferred_init(self):
        self._position_panel_hidden()
        self._reset_cursor_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.panel_visible:
            self.panel_widget.setGeometry(0, self.height() - self.panel_height, self.width(), self.panel_height)
        else:
            self._position_panel_hidden()

    def _position_panel_hidden(self):
        self.panel_widget.setGeometry(0, self.height(), self.width(), self.panel_height)

    def _poll_mouse_position(self):
        if not self.isVisible():
            return

        global_pos = QCursor.pos()
        if not self.geometry().contains(global_pos):
            return

        local_pos = self.mapFromGlobal(global_pos)
        y = local_pos.y()

        if self.last_cursor_pos != global_pos:
            self.last_cursor_pos = global_pos
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self._reset_cursor_timer()

        if y >= self.height() - self.trigger_zone and not self.panel_visible:
            self._slide_panel_up()

        if self.panel_visible:
            panel_top = self.height() - self.panel_height
            self.mouse_in_panel = y >= panel_top
            if self.mouse_in_panel:
                self.hide_timer.stop()
            else:
                if not self.hide_timer.isActive():
                    self.hide_timer.start(1500)

    def _slide_panel_up(self):
        if self.panel_animating:
            return
        self.panel_visible = True
        self.panel_animating = True
        self.hide_timer.stop()

        self.slide_animation.stop()

        self.panel_widget.raise_()
        start = QRect(0, self.height(), self.width(), self.panel_height)
        end = QRect(0, self.height() - self.panel_height, self.width(), self.panel_height)
        self.slide_animation.setStartValue(start)
        self.slide_animation.setEndValue(end)
        self.panel_widget.show()
        self.slide_animation.start()

    def _slide_panel_down(self):
        if self.panel_animating:
            return
        self.panel_animating = True

        self.slide_animation.stop()

        start = QRect(0, self.height() - self.panel_height, self.width(), self.panel_height)
        end = QRect(0, self.height(), self.width(), self.panel_height)
        self.slide_animation.setStartValue(start)
        self.slide_animation.setEndValue(end)
        self.slide_animation.start()

    def _on_animation_finished(self):
        self.panel_animating = False
        if not self.panel_visible:
            pass

    def _on_hide_timeout(self):
        if self.panel_visible and not self.mouse_in_panel:
            self.panel_visible = False
            self._slide_panel_down()

    def _reset_cursor_timer(self):
        self.cursor_timer.stop()
        if not self.panel_visible:
            self.cursor_timer.start(self.cursor_hide_delay)

    def _hide_cursor(self):
        if not self.panel_visible:
            self.setCursor(QCursor(Qt.CursorShape.BlankCursor))

    def on_double_click(self):
        self.exit_fullscreen.emit()

    def mouseDoubleClickEvent(self, event):
        self.exit_fullscreen.emit()
        event.accept()

    def wheelEvent(self, event: QWheelEvent):
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if widget_under_cursor and (widget_under_cursor is self.playlist_mirror or self.playlist_mirror.isAncestorOf(widget_under_cursor)):
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        step = 5
        if delta > 0:
            new_volume = min(100, self.volume_slider.value() + step)
        else:
            new_volume = max(0, self.volume_slider.value() - step)
        self.volume_slider.setValue(new_volume)
        self.volume_change.emit(new_volume)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.exit_fullscreen.emit()
        else:
            super().keyPressEvent(event)


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Music Player")
        self.setMinimumSize(500, 700)
        
        self.settings = QSettings("MyMusicPlayer", "VLCPlayer")
        
        self.audio_analyzer = AudioAnalyzer()
        
        self.vlc_instance = vlc.Instance([
            '--quiet',
            '--no-video',
        ])
        self.player = self.vlc_instance.media_player_new()
        
        self.player.audio_set_format("S16N", 44100, 2)
        self.player.audio_set_callbacks(
            self.audio_analyzer._play_cb,
            self.audio_analyzer._pause_cb,
            self.audio_analyzer._resume_cb,
            self.audio_analyzer._flush_cb,
            self.audio_analyzer._drain_cb,
            None
        )
        
        self.current_index = -1
        self.is_playing = False
        
        self.current_visualization_index = 0
        self.visualizer = None
        
        self.fullscreen_window = None
        self.is_fullscreen = False
        
        self.setup_menu()
        self.setup_ui()
        self.setup_timer()
        self.load_settings()
    
    def setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Files...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_files)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        clear_playlist_action = QAction("Clear Playlist", self)
        clear_playlist_action.triggered.connect(self.clear_playlist)
        file_menu.addAction(clear_playlist_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        vis_menu = menubar.addMenu("Visualization")
        
        self.vis_action_group = []
        for i, (name, vis_class) in enumerate(VISUALIZATIONS):
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(i == 0)
            action.triggered.connect(lambda checked, idx=i: self.set_visualization(idx))
            vis_menu.addAction(action)
            self.vis_action_group.append(action)
        
        vis_menu.addSeparator()
        
        no_vis_action = QAction("None", self)
        no_vis_action.setCheckable(True)
        no_vis_action.triggered.connect(lambda: self.set_visualization(-1))
        vis_menu.addAction(no_vis_action)
        self.vis_action_group.append(no_vis_action)
        
        vis_menu.addSeparator()
        
        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        vis_menu.addAction(fullscreen_action)
        
        vis_menu.addSeparator()
        
        settings_action = QAction("Visualization Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_visualization_settings)
        vis_menu.addAction(settings_action)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.now_playing_label = QLabel("Drag and drop music files to begin")
        self.now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.now_playing_label.setWordWrap(True)
        self.now_playing_label.setStyleSheet("font-weight: bold; padding: 10px;")
        main_layout.addWidget(self.now_playing_label)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(8)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555555;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #888888;
            }
            QSplitter::handle:pressed {
                background-color: #aaaaaa;
            }
        """)
        
        self.visualizer_container = QFrame()
        self.visualizer_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.visualizer_container.setMinimumHeight(150)
        self.visualizer_layout = QVBoxLayout(self.visualizer_container)
        self.visualizer_layout.setContentsMargins(0, 0, 0, 0)
        self.visualizer_layout.setSpacing(0)
        
        self.playlist_container = QFrame()
        self.playlist_container.setMinimumHeight(100)
        playlist_frame_layout = QVBoxLayout(self.playlist_container)
        playlist_frame_layout.setContentsMargins(0, 5, 0, 0)
        playlist_frame_layout.setSpacing(5)
        
        queue_label = QLabel("Queue:")
        queue_label.setStyleSheet("font-weight: bold;")
        playlist_frame_layout.addWidget(queue_label)
        
        self.playlist = PlaylistWidget()
        self.playlist.files_dropped.connect(self.add_files)
        self.playlist.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.playlist.model().rowsRemoved.connect(self.on_playlist_changed)
        self.playlist.model().rowsMoved.connect(self.on_rows_moved)
        playlist_frame_layout.addWidget(self.playlist)
        
        self.splitter.addWidget(self.visualizer_container)
        self.splitter.addWidget(self.playlist_container)
        
        self.splitter.setSizes([400, 200])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter, 1)
        
        self.set_visualization(0)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 10, 0, 0)
        controls_layout.setSpacing(10)
        
        time_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.duration_label = QLabel("0:00")
        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.progress_slider)
        time_layout.addWidget(self.duration_label)
        controls_layout.addLayout(time_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)
        
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_btn.clicked.connect(self.play_previous)
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.clicked.connect(self.toggle_play)
        
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop)
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_btn.clicked.connect(self.play_next)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.prev_btn)
        buttons_layout.addWidget(self.play_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.next_btn)
        buttons_layout.addStretch()
        
        controls_layout.addLayout(buttons_layout)
        
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        self.volume_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(150)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_value_label = QLabel("70%")
        self.volume_value_label.setMinimumWidth(35)
        
        volume_layout.addStretch()
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        volume_layout.addStretch()
        
        controls_layout.addLayout(volume_layout)
        
        main_layout.addWidget(controls_widget)
        
        self.audio_analyzer.set_volume(0.7)
        
        instructions = QLabel("Drag files to reorder • Right-click to remove • Double-click visualization for fullscreen")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("color: gray; font-size: 11px;")
        main_layout.addWidget(instructions)

    def show_visualization_settings(self):
        if self.visualizer and hasattr(self.visualizer, 'show_settings_dialog'):
            self.visualizer.show_settings_dialog(self)

    def set_visualization(self, index):
        if self.is_fullscreen:
            self.exit_fullscreen()
        
        if self.visualizer:
            self.visualizer.cleanup()
            self.visualizer.setParent(None)
            self.visualizer.deleteLater()
            self.visualizer = None
        
        for i, action in enumerate(self.vis_action_group):
            action.setChecked(i == index or (index == -1 and i == len(self.vis_action_group) - 1))
        
        if index >= 0 and index < len(VISUALIZATIONS):
            name, vis_class = VISUALIZATIONS[index]
            self.visualizer = vis_class(self.audio_analyzer)
            self.visualizer.set_playing(self.is_playing)
            self.visualizer.double_clicked.connect(self.toggle_fullscreen)
            self.visualizer_layout.addWidget(self.visualizer)
            self.visualizer_container.setMinimumHeight(150)
            self.visualizer_container.show()
            self.current_visualization_index = index
        else:
            self.visualizer_container.setMinimumHeight(0)
            self.visualizer_container.hide()
            self.current_visualization_index = -1
    
    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()
    
    def enter_fullscreen(self):
        if not self.visualizer or self.is_fullscreen:
            return
        
        self.is_fullscreen = True
        
        self.visualizer.double_clicked.disconnect(self.toggle_fullscreen)
        self.visualizer_layout.removeWidget(self.visualizer)
        
        self.fullscreen_window = FullscreenWindow()
        self.fullscreen_window.exit_fullscreen.connect(self.exit_fullscreen)
        self.fullscreen_window.set_visualizer(self.visualizer)

        self.fullscreen_window.prev_btn.clicked.connect(self.play_previous)
        self.fullscreen_window.play_btn.clicked.connect(self.toggle_play)
        self.fullscreen_window.stop_btn.clicked.connect(self.stop)
        self.fullscreen_window.next_btn.clicked.connect(self.play_next)
        self.fullscreen_window.volume_slider.setValue(self.volume_slider.value())
        self.fullscreen_window.volume_slider.valueChanged.connect(self.set_volume)
        self.fullscreen_window.volume_change.connect(self.set_volume)
        self.fullscreen_window.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.fullscreen_window.progress_slider.sliderReleased.connect(self.on_fullscreen_slider_released)
        self.fullscreen_window.progress_slider.sliderMoved.connect(self.on_slider_moved)
        self.fullscreen_window.track_double_clicked.connect(self.play_track)
        self.fullscreen_window.sync_playlist(self.playlist, self.current_index)

        self.update_fullscreen_ui()

        self.fullscreen_window.showFullScreen()
    
    def exit_fullscreen(self):
        if not self.is_fullscreen or not self.fullscreen_window:
            return
        
        self.is_fullscreen = False
        
        self.visualizer = self.fullscreen_window.take_visualizer()
        
        if self.visualizer:
            self.visualizer.double_clicked.connect(self.toggle_fullscreen)
            self.visualizer_layout.addWidget(self.visualizer)
        
        self.fullscreen_window.close()
        self.fullscreen_window = None
    
    def on_fullscreen_slider_released(self):
        self.slider_is_pressed = False
        if self.player.get_media():
            position = self.fullscreen_window.progress_slider.value() / 1000
            self.player.set_position(position)
    
    def update_fullscreen_ui(self):
        if not self.fullscreen_window:
            return

        if self.current_index >= 0 and self.current_index < self.playlist.count():
            item = self.playlist.item(self.current_index)
            self.fullscreen_window.now_playing_label.setText(f"Now playing: {item.text()}")
        else:
            self.fullscreen_window.now_playing_label.setText("No track playing")

        self.fullscreen_window.play_btn.setText("⏸" if self.is_playing else "▶")
        self.fullscreen_window.time_label.setText(self.time_label.text())
        self.fullscreen_window.duration_label.setText(self.duration_label.text())
        self.fullscreen_window.progress_slider.setValue(self.progress_slider.value())
        self.fullscreen_window.volume_value_label.setText(self.volume_value_label.text())
        self.fullscreen_window.update_playlist_selection(self.current_index)
    
    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Music Files",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)"
        )
        if files:
            self.add_files(files)
    
    def clear_playlist(self):
        self.stop()
        self.playlist.clear()
        self.current_index = -1
        self.now_playing_label.setText("Drag and drop music files to begin")
    
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100)
        
        self.slider_is_pressed = False
    
    def load_settings(self):
        self.restoreGeometry(self.settings.value("geometry", b""))
        
        volume = self.settings.value("volume", 70, type=int)
        self.volume_slider.setValue(volume)
        self.audio_analyzer.set_volume(volume / 100.0)
        
        vis_index = self.settings.value("visualization", 0, type=int)
        self.set_visualization(vis_index)
        
        splitter_state = self.settings.value("splitter_state")
        if splitter_state:
            self.splitter.restoreState(splitter_state)
        
        playlist_files = self.settings.value("playlist", [], type=list)
        for file_path in playlist_files:
            if Path(file_path).exists():
                item = QListWidgetItem(Path(file_path).name)
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                item.setToolTip(file_path)
                self.playlist.addItem(item)
    
    def save_settings(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("volume", self.volume_slider.value())
        self.settings.setValue("visualization", self.current_visualization_index)
        self.settings.setValue("splitter_state", self.splitter.saveState())
        
        playlist_files = []
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            playlist_files.append(item.data(Qt.ItemDataRole.UserRole))
        self.settings.setValue("playlist", playlist_files)
    
    def add_files(self, files: list):
        for file_path in files:
            item = QListWidgetItem(Path(file_path).name)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setToolTip(file_path)
            self.playlist.addItem(item)
    
    def on_item_double_clicked(self, item: QListWidgetItem):
        row = self.playlist.row(item)
        self.play_track(row)
    
    def play_track(self, index: int):
        if 0 <= index < self.playlist.count():
            item = self.playlist.item(index)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            
            self.audio_analyzer.start_stream()
            
            media = self.vlc_instance.media_new(file_path)
            self.player.set_media(media)
            self.player.play()
            
            self.current_index = index
            self.is_playing = True
            if self.visualizer:
                self.visualizer.set_playing(True)
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.now_playing_label.setText(f"Now playing: {item.text()}")
            
            self.playlist.setCurrentRow(index)
            
            if self.fullscreen_window:
                self.fullscreen_window.play_btn.setText("⏸")
                self.fullscreen_window.now_playing_label.setText(f"Now playing: {item.text()}")
                self.fullscreen_window.update_playlist_selection(index)

    def toggle_play(self):
        if self.player.get_media() is None:
            if self.playlist.count() > 0:
                self.play_track(0)
            return
        
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            if self.visualizer:
                self.visualizer.set_playing(False)
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            if self.fullscreen_window:
                self.fullscreen_window.play_btn.setText("▶")
        else:
            self.audio_analyzer.start_stream()
            self.player.play()
            self.is_playing = True
            if self.visualizer:
                self.visualizer.set_playing(True)
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            if self.fullscreen_window:
                self.fullscreen_window.play_btn.setText("⏸")
    
    def stop(self):
        self.player.stop()
        self.audio_analyzer.stop_stream()
        self.is_playing = False
        if self.visualizer:
            self.visualizer.set_playing(False)
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.progress_slider.setValue(0)
        self.time_label.setText("0:00")
        if self.fullscreen_window:
            self.fullscreen_window.play_btn.setText("▶")
            self.fullscreen_window.progress_slider.setValue(0)
            self.fullscreen_window.time_label.setText("0:00")
    
    def play_next(self):
        if self.playlist.count() == 0:
            return
        next_index = self.current_index + 1
        if next_index < self.playlist.count():
            self.play_track(next_index)
        else:
            self.stop()
            self.now_playing_label.setText("End of queue")
            if self.fullscreen_window:
                self.fullscreen_window.now_playing_label.setText("End of queue")
    
    def play_previous(self):
        if self.playlist.count() == 0:
            return
        prev_index = self.current_index - 1
        if prev_index >= 0:
            self.play_track(prev_index)
    
    def set_volume(self, value: int):
        self.audio_analyzer.set_volume(value / 100.0)
        self.volume_value_label.setText(f"{value}%")
        self.volume_slider.setValue(value)
        if self.fullscreen_window:
            self.fullscreen_window.volume_slider.blockSignals(True)
            self.fullscreen_window.volume_slider.setValue(value)
            self.fullscreen_window.volume_slider.blockSignals(False)
            self.fullscreen_window.volume_value_label.setText(f"{value}%")
    
    def on_slider_pressed(self):
        self.slider_is_pressed = True
    
    def on_slider_released(self):
        self.slider_is_pressed = False
        if self.player.get_media():
            position = self.progress_slider.value() / 1000
            self.player.set_position(position)
    
    def on_slider_moved(self, value: int):
        if self.player.get_media():
            position = value / 1000
            self.player.set_position(position)
    
    def update_ui(self):
        if not self.player.get_media():
            return
        
        state = self.player.get_state()
        if state == vlc.State.Ended:
            self.play_next()
            return
        
        if not self.slider_is_pressed:
            position = self.player.get_position()
            if position >= 0:
                self.progress_slider.setValue(int(position * 1000))
                if self.fullscreen_window:
                    self.fullscreen_window.progress_slider.setValue(int(position * 1000))
        
        current_time = self.player.get_time()
        duration = self.player.get_length()
        
        if current_time >= 0:
            time_str = self.format_time(current_time)
            self.time_label.setText(time_str)
            if self.fullscreen_window:
                self.fullscreen_window.time_label.setText(time_str)
        if duration >= 0:
            duration_str = self.format_time(duration)
            self.duration_label.setText(duration_str)
            if self.fullscreen_window:
                self.fullscreen_window.duration_label.setText(duration_str)
    
    def format_time(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            return f"{hours}:{minutes % 60:02d}:{seconds % 60:02d}"
        return f"{minutes}:{seconds % 60:02d}"
    
    def on_playlist_changed(self):
        if self.playlist.count() == 0:
            self.current_index = -1
            self.stop()
            self.now_playing_label.setText("Queue is empty")
        elif self.current_index >= self.playlist.count():
            self.current_index = self.playlist.count() - 1
    
    def on_rows_moved(self):
        if self.current_index >= 0 and self.player.get_media():
            current_item = self.playlist.currentItem()
            if current_item:
                self.current_index = self.playlist.row(current_item)
    
    def wheelEvent(self, event: QWheelEvent):
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if widget_under_cursor and (widget_under_cursor is self.playlist or self.playlist.isAncestorOf(widget_under_cursor)):
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        step = 5

        if delta > 0:
            new_volume = min(100, self.volume_slider.value() + step)
        else:
            new_volume = max(0, self.volume_slider.value() - step)

        self.volume_slider.setValue(new_volume)
        event.accept()
    
    def closeEvent(self, event):
        if self.is_fullscreen:
            self.exit_fullscreen()
        
        if self.visualizer:
            self.visualizer.save_settings()
            self.visualizer.cleanup()
        
        self.save_settings()
        self.player.stop()
        self.audio_analyzer.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    fmt.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    player = MusicPlayer()
    player.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()