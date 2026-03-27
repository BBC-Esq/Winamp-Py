import random
from math import sin, cos, pi, exp

import numpy as np
from PySide6.QtCore import QTimer, Signal, QSettings
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QCheckBox, QSlider, QPushButton, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from OpenGL import GL


class GeissSettingsDialog(QDialog):
    
    settings_changed = Signal()
    
    def __init__(self, visualization, parent=None):
        super().__init__(parent)
        self.visualization = visualization
        self.setWindowTitle("Geiss Settings")
        self.setMinimumWidth(400)
        
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        wave_group = QGroupBox("Waveform")
        wave_layout = QFormLayout(wave_group)
        
        self.wave_combo = QComboBox()
        self.wave_combo.addItems([
            "Horizontal Oscilloscope",
            "Circular",
            "Spiral",
            "Stereo Bars",
            "Mirrored Wave",
            "Vertical Oscilloscope",
            "Dots/Particles",
            "Spectrum Bars"
        ])
        self.wave_combo.currentIndexChanged.connect(self.on_wave_changed)
        wave_layout.addRow("Wave Mode:", self.wave_combo)
        
        layout.addWidget(wave_group)
        
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout(color_group)
        
        self.palette_combo = QComboBox()
        self.palette_combo.addItems([
            "Electric Blue/Purple",
            "Fire Orange/Red",
            "Ocean Teal/Cyan",
            "Neon Pink/Cyan",
            "Aurora Green/Purple",
            "Sunset Purple/Orange",
            "Deep Space Blue",
            "Plasma Red/Purple"
        ])
        self.palette_combo.currentIndexChanged.connect(self.on_palette_changed)
        color_layout.addRow("Color Palette:", self.palette_combo)
        
        layout.addWidget(color_group)
        
        warp_group = QGroupBox("Warp Motion")
        warp_layout = QFormLayout(warp_group)
        
        self.warp_combo = QComboBox()
        self.warp_combo.addItems([
            "Zoom + Rotate CW",
            "Zoom + Rotate CCW",
            "Drift",
            "Zoom Out + Rotate",
            "Zoom + Drift Right",
            "Zoom + Drift Up",
            "Slow Rotate",
            "Zoom + Spiral",
            "Drift Right",
            "Drift Up",
            "Zoom Out Slow",
            "Diagonal Drift CW",
            "Diagonal Drift CCW",
            "Fast Rotate",
            "Fast Zoom"
        ])
        self.warp_combo.currentIndexChanged.connect(self.on_warp_changed)
        warp_layout.addRow("Warp Mode:", self.warp_combo)
        
        self.instant_warp_check = QCheckBox("Instant warp transitions (like original Geiss)")
        self.instant_warp_check.stateChanged.connect(self.on_instant_warp_changed)
        warp_layout.addRow(self.instant_warp_check)
        
        layout.addWidget(warp_group)
        
        decay_group = QGroupBox("Trails")
        decay_layout = QVBoxLayout(decay_group)
        
        decay_slider_layout = QHBoxLayout()
        decay_slider_layout.addWidget(QLabel("Shorter"))
        self.decay_slider = QSlider(Qt.Orientation.Horizontal)
        self.decay_slider.setRange(970, 995)
        self.decay_slider.setValue(985)
        self.decay_slider.valueChanged.connect(self.on_decay_changed)
        decay_slider_layout.addWidget(self.decay_slider)
        decay_slider_layout.addWidget(QLabel("Longer"))
        decay_layout.addLayout(decay_slider_layout)
        
        self.beat_decay_check = QCheckBox("Beat-reactive trails (trails shorten on beats)")
        self.beat_decay_check.stateChanged.connect(self.on_beat_decay_changed)
        decay_layout.addWidget(self.beat_decay_check)
        
        self.dither_check = QCheckBox("Error diffusion grain (like original Geiss)")
        self.dither_check.stateChanged.connect(self.on_dither_changed)
        decay_layout.addWidget(self.dither_check)
        
        dither_slider_layout = QHBoxLayout()
        dither_slider_layout.addWidget(QLabel("Subtle"))
        self.dither_slider = QSlider(Qt.Orientation.Horizontal)
        self.dither_slider.setRange(1, 20)
        self.dither_slider.setValue(8)
        self.dither_slider.valueChanged.connect(self.on_dither_amount_changed)
        dither_slider_layout.addWidget(self.dither_slider)
        dither_slider_layout.addWidget(QLabel("Heavy"))
        decay_layout.addLayout(dither_slider_layout)
        
        layout.addWidget(decay_group)
        
        effects_group = QGroupBox("Effects")
        effects_layout = QVBoxLayout(effects_group)
        
        self.nebula_check = QCheckBox("Nebula Particles")
        self.nebula_check.stateChanged.connect(self.on_effect_changed)
        effects_layout.addWidget(self.nebula_check)
        
        self.solar_check = QCheckBox("Solar Rays (bass-reactive)")
        self.solar_check.stateChanged.connect(self.on_effect_changed)
        effects_layout.addWidget(self.solar_check)
        
        self.dots_check = QCheckBox("Random Dots")
        self.dots_check.stateChanged.connect(self.on_effect_changed)
        effects_layout.addWidget(self.dots_check)
        
        self.grid_check = QCheckBox("Grid Overlay")
        self.grid_check.stateChanged.connect(self.on_effect_changed)
        effects_layout.addWidget(self.grid_check)
        
        self.border_check = QCheckBox("Color Border")
        self.border_check.stateChanged.connect(self.on_effect_changed)
        effects_layout.addWidget(self.border_check)
        
        layout.addWidget(effects_group)
        
        auto_group = QGroupBox("Auto-Change")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_change_check = QCheckBox("Automatically change visualization over time")
        self.auto_change_check.stateChanged.connect(self.on_auto_change_changed)
        auto_layout.addWidget(self.auto_change_check)
        
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Change speed:"))
        duration_layout.addWidget(QLabel("Faster"))
        self.duration_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_slider.setRange(200, 1200)
        self.duration_slider.setValue(600)
        self.duration_slider.valueChanged.connect(self.on_duration_changed)
        duration_layout.addWidget(self.duration_slider)
        duration_layout.addWidget(QLabel("Slower"))
        auto_layout.addLayout(duration_layout)
        
        layout.addWidget(auto_group)
        
        button_layout = QHBoxLayout()
        
        self.randomize_btn = QPushButton("Randomize All")
        self.randomize_btn.clicked.connect(self.randomize_all)
        button_layout.addWidget(self.randomize_btn)
        
        button_layout.addStretch()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_current_settings(self):
        self.wave_combo.setCurrentIndex(self.visualization.wave_mode)
        self.palette_combo.setCurrentIndex(self.visualization.palette_index)
        self.warp_combo.setCurrentIndex(self.visualization.warp_mode)
        
        self.instant_warp_check.setChecked(self.visualization.instant_warp)
        
        self.decay_slider.setValue(int(self.visualization.base_decay * 1000))
        self.beat_decay_check.setChecked(self.visualization.beat_decay)
        
        self.dither_check.setChecked(self.visualization.dither_enabled)
        self.dither_slider.setValue(int(self.visualization.dither_amount * 1000))
        self.dither_slider.setEnabled(self.visualization.dither_enabled)
        
        self.nebula_check.setChecked(self.visualization.effect_nebula)
        self.solar_check.setChecked(self.visualization.effect_solar)
        self.dots_check.setChecked(self.visualization.effect_dots)
        self.grid_check.setChecked(self.visualization.effect_grid)
        self.border_check.setChecked(self.visualization.effect_border)
        
        self.auto_change_check.setChecked(self.visualization.auto_change)
        self.duration_slider.setValue(self.visualization.warp_duration)
        self.duration_slider.setEnabled(self.visualization.auto_change)
    
    def on_wave_changed(self, index):
        self.visualization.wave_mode = index
        self.settings_changed.emit()
    
    def on_palette_changed(self, index):
        self.visualization.palette_index = index
        self.settings_changed.emit()
    
    def on_warp_changed(self, index):
        self.visualization.apply_warp_mode(index, instant=True)
        self.settings_changed.emit()
    
    def on_instant_warp_changed(self, state):
        self.visualization.instant_warp = state == Qt.CheckState.Checked.value
        self.settings_changed.emit()
    
    def on_decay_changed(self, value):
        self.visualization.base_decay = value / 1000.0
        self.visualization.decay = self.visualization.base_decay
        self.settings_changed.emit()
    
    def on_beat_decay_changed(self, state):
        self.visualization.beat_decay = state == Qt.CheckState.Checked.value
        self.settings_changed.emit()
    
    def on_dither_changed(self, state):
        self.visualization.dither_enabled = state == Qt.CheckState.Checked.value
        self.dither_slider.setEnabled(self.visualization.dither_enabled)
        self.settings_changed.emit()
    
    def on_dither_amount_changed(self, value):
        self.visualization.dither_amount = value / 1000.0
        self.settings_changed.emit()
    
    def on_effect_changed(self):
        self.visualization.effect_nebula = self.nebula_check.isChecked()
        self.visualization.effect_solar = self.solar_check.isChecked()
        self.visualization.effect_dots = self.dots_check.isChecked()
        self.visualization.effect_grid = self.grid_check.isChecked()
        self.visualization.effect_border = self.border_check.isChecked()
        self.settings_changed.emit()
    
    def on_auto_change_changed(self, state):
        self.visualization.auto_change = state == Qt.CheckState.Checked.value
        self.duration_slider.setEnabled(self.visualization.auto_change)
        self.settings_changed.emit()
    
    def on_duration_changed(self, value):
        self.visualization.warp_duration = value
        self.settings_changed.emit()
    
    def randomize_all(self):
        self.visualization.wave_mode = random.randint(0, self.visualization.num_wave_modes - 1)
        self.visualization.palette_index = random.randint(0, len(self.visualization.palettes) - 1)
        self.visualization.apply_warp_mode(random.randint(0, self.visualization.num_warp_modes - 1), instant=True)
        
        self.visualization.effect_nebula = random.choice([True, False])
        self.visualization.effect_solar = random.choice([True, False])
        self.visualization.effect_dots = random.choice([True, False])
        self.visualization.effect_grid = random.choice([True, False, False, False])
        self.visualization.effect_border = random.choice([True, False, False, False])
        
        self.load_current_settings()
        self.settings_changed.emit()
    
    def reset_to_defaults(self):
        self.visualization.wave_mode = 0
        self.visualization.palette_index = 0
        self.visualization.apply_warp_mode(0, instant=True)
        
        self.visualization.instant_warp = True
        
        self.visualization.base_decay = 0.985
        self.visualization.decay = 0.985
        self.visualization.beat_decay = True
        
        self.visualization.dither_enabled = True
        self.visualization.dither_amount = 0.008
        
        self.visualization.effect_nebula = True
        self.visualization.effect_solar = False
        self.visualization.effect_dots = False
        self.visualization.effect_grid = False
        self.visualization.effect_border = False
        
        self.visualization.auto_change = True
        self.visualization.warp_duration = 600
        
        self.load_current_settings()
        self.settings_changed.emit()


class GeissVisualization(QOpenGLWidget):
    
    NAME = "Geiss"
    double_clicked = Signal()
    
    def __init__(self, audio_analyzer, parent=None):
        super().__init__(parent)
        
        self.audio_analyzer = audio_analyzer
        self.is_playing = False
        self.time = 0.0
        
        self.fbo1 = None
        self.fbo2 = None
        self.current_fbo = 0
        
        self.warp_mode = 0
        self.num_warp_modes = 15
        self.warp_timer = 0
        self.warp_duration = 600
        self.auto_change = True
        
        self.zoom = 1.02
        self.rotation = 0.005
        self.drift_x = 0.0
        self.drift_y = 0.0
        
        self.target_zoom = 1.02
        self.target_rotation = 0.005
        self.target_drift_x = 0.0
        self.target_drift_y = 0.0
        
        self.next_warp_ready = False
        self.next_zoom = 1.02
        self.next_rotation = 0.005
        self.next_drift_x = 0.0
        self.next_drift_y = 0.0
        self.next_warp_mode = 0
        
        self.instant_warp = True
        
        self.dither_enabled = True
        self.dither_amount = 0.008
        self.dither_texture = None
        self.dither_offset = 0.0
        
        self.color_phase = 0.0
        self.palette_index = 0
        
        self.palettes = [
            [(0.2, 0.4, 0.95), (0.55, 0.2, 0.95), (0.95, 0.2, 0.75), (0.3, 0.55, 0.95)],
            [(0.95, 0.4, 0.1), (0.95, 0.75, 0.2), (0.95, 0.2, 0.1), (0.95, 0.55, 0.3)],
            [(0.1, 0.85, 0.65), (0.2, 0.55, 0.95), (0.3, 0.95, 0.85), (0.1, 0.65, 0.85)],
            [(0.95, 0.2, 0.55), (0.2, 0.95, 0.95), (0.95, 0.95, 0.3), (0.75, 0.3, 0.95)],
            [(0.3, 0.95, 0.5), (0.5, 0.3, 0.95), (0.2, 0.75, 0.95), (0.4, 0.95, 0.65)],
            [(0.55, 0.2, 0.75), (0.95, 0.5, 0.2), (0.95, 0.3, 0.5), (0.75, 0.4, 0.95)],
            [(0.1, 0.3, 0.85), (0.5, 0.1, 0.75), (0.2, 0.65, 0.95), (0.4, 0.2, 0.95)],
            [(0.85, 0.1, 0.3), (0.55, 0.1, 0.85), (0.3, 0.2, 0.95), (0.95, 0.2, 0.5)],
        ]
        
        self.wave_mode = 0
        self.num_wave_modes = 8
        
        self.effect_solar = False
        self.effect_grid = False
        self.effect_dots = False
        self.effect_border = False
        self.effect_nebula = True
        
        self.decay = 0.985
        self.base_decay = 0.985
        self.beat_decay = True
        
        self.smoothed_waveform = np.zeros(512)
        self.smoothed_bass = 0.0
        self.smoothed_mid = 0.0
        self.smoothed_treble = 0.0
        
        self.update_counter = 0
        self.audio_update_interval = 3
        
        self.beat_history = []
        self.last_beat_time = 0
        
        self.bg_hue = 0.0
        
        self.load_settings()
        
        self.prepare_next_warp()
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(33)
    
    def show_settings_dialog(self, parent=None):
        dialog = GeissSettingsDialog(self, parent)
        dialog.exec()
        self.save_settings()
    
    def load_settings(self):
        settings = QSettings("MyMusicPlayer", "GeissVisualization")
        
        self.palette_index = settings.value("palette_index", 0, type=int)
        if self.palette_index >= len(self.palettes):
            self.palette_index = 0
        
        self.wave_mode = settings.value("wave_mode", 0, type=int)
        if self.wave_mode >= self.num_wave_modes:
            self.wave_mode = 0
        
        self.warp_mode = settings.value("warp_mode", 0, type=int)
        if self.warp_mode >= self.num_warp_modes:
            self.warp_mode = 0
        
        self.instant_warp = settings.value("instant_warp", True, type=bool)
        
        self.effect_solar = settings.value("effect_solar", False, type=bool)
        self.effect_grid = settings.value("effect_grid", False, type=bool)
        self.effect_dots = settings.value("effect_dots", False, type=bool)
        self.effect_border = settings.value("effect_border", False, type=bool)
        self.effect_nebula = settings.value("effect_nebula", True, type=bool)
        
        self.base_decay = settings.value("base_decay", 0.985, type=float)
        self.decay = self.base_decay
        
        self.beat_decay = settings.value("beat_decay", True, type=bool)
        
        self.dither_enabled = settings.value("dither_enabled", True, type=bool)
        self.dither_amount = settings.value("dither_amount", 0.008, type=float)
        
        self.auto_change = settings.value("auto_change", True, type=bool)
        self.warp_duration = settings.value("warp_duration", 600, type=int)
        
        self.apply_warp_mode(self.warp_mode, instant=True)
    
    def save_settings(self):
        settings = QSettings("MyMusicPlayer", "GeissVisualization")
        
        settings.setValue("palette_index", self.palette_index)
        settings.setValue("wave_mode", self.wave_mode)
        settings.setValue("warp_mode", self.warp_mode)
        
        settings.setValue("instant_warp", self.instant_warp)
        
        settings.setValue("effect_solar", self.effect_solar)
        settings.setValue("effect_grid", self.effect_grid)
        settings.setValue("effect_dots", self.effect_dots)
        settings.setValue("effect_border", self.effect_border)
        settings.setValue("effect_nebula", self.effect_nebula)
        
        settings.setValue("base_decay", self.base_decay)
        settings.setValue("beat_decay", self.beat_decay)
        
        settings.setValue("dither_enabled", self.dither_enabled)
        settings.setValue("dither_amount", self.dither_amount)
        
        settings.setValue("auto_change", self.auto_change)
        settings.setValue("warp_duration", self.warp_duration)
    
    def get_warp_params(self, mode):
        if mode == 0:
            return (1.01 + random.random() * 0.015, 
                    0.002 + random.random() * 0.004, 
                    0.0, 0.0)
        elif mode == 1:
            return (1.01 + random.random() * 0.01, 
                    -0.002 - random.random() * 0.004, 
                    0.0, 0.0)
        elif mode == 2:
            return (1.015 + random.random() * 0.01, 
                    0.0, 
                    (random.random() - 0.5) * 0.006, 
                    (random.random() - 0.5) * 0.006)
        elif mode == 3:
            return (0.985 - random.random() * 0.01, 
                    0.006 + random.random() * 0.006, 
                    0.0, 0.0)
        elif mode == 4:
            return (1.02 + random.random() * 0.01, 
                    0.001, 
                    0.003, 0.0)
        elif mode == 5:
            return (1.015, 
                    (random.random() - 0.5) * 0.01, 
                    0.0, 0.002)
        elif mode == 6:
            return (1.008, 0.008, 0.0, 0.0)
        elif mode == 7:
            return (1.025, -0.005, -0.002, 0.001)
        elif mode == 8:
            return (1.01, 0.0, 0.004, 0.0)
        elif mode == 9:
            return (1.01, 0.0, 0.0, 0.004)
        elif mode == 10:
            return (0.99, 0.003, 0.0, 0.0)
        elif mode == 11:
            return (1.02, 0.01, 0.002, 0.002)
        elif mode == 12:
            return (1.015, -0.008, -0.001, 0.001)
        elif mode == 13:
            return (1.005, 0.012, 0.0, 0.0)
        else:
            return (1.03, 0.0, 0.0, 0.0)
    
    def prepare_next_warp(self):
        self.next_warp_mode = random.randint(0, self.num_warp_modes - 1)
        params = self.get_warp_params(self.next_warp_mode)
        self.next_zoom, self.next_rotation, self.next_drift_x, self.next_drift_y = params
        self.next_warp_ready = True
    
    def apply_warp_mode(self, mode, instant=False):
        self.warp_mode = mode
        params = self.get_warp_params(mode)
        
        if instant or self.instant_warp:
            self.zoom, self.rotation, self.drift_x, self.drift_y = params
            self.target_zoom, self.target_rotation, self.target_drift_x, self.target_drift_y = params
        else:
            self.target_zoom, self.target_rotation, self.target_drift_x, self.target_drift_y = params
    
    def switch_to_next_warp(self):
        if self.next_warp_ready:
            self.warp_mode = self.next_warp_mode
            
            if self.instant_warp:
                self.zoom = self.next_zoom
                self.rotation = self.next_rotation
                self.drift_x = self.next_drift_x
                self.drift_y = self.next_drift_y
            
            self.target_zoom = self.next_zoom
            self.target_rotation = self.next_rotation
            self.target_drift_x = self.next_drift_x
            self.target_drift_y = self.next_drift_y
            
            self.next_warp_ready = False
            
            self.prepare_next_warp()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            settings_action = menu.addAction("Visualization Settings...")
            action = menu.exec(event.globalPosition().toPoint())
            if action == settings_action:
                self.show_settings_dialog(self.window())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.double_clicked.emit()
        event.accept()
    
    def set_playing(self, playing: bool):
        self.is_playing = playing
    
    def select_new_warp(self):
        self.switch_to_next_warp()
    
    def animate(self):
        self.time += 0.033
        self.color_phase += 0.008
        self.bg_hue += 0.001
        self.dither_offset += 0.1
        
        self.update_counter += 1
        
        if self.update_counter >= self.audio_update_interval:
            self.update_counter = 0
            self.update_audio_data()
        
        if self.is_playing and self.auto_change:
            self.warp_timer += 1
            if self.warp_timer >= self.warp_duration:
                self.warp_timer = 0
                self.select_new_warp()
                if random.random() < 0.4:
                    self.wave_mode = random.randint(0, self.num_wave_modes - 1)
                if random.random() < 0.2:
                    self.palette_index = (self.palette_index + 1) % len(self.palettes)
                if random.random() < 0.1:
                    self.effect_solar = not self.effect_solar
                if random.random() < 0.05:
                    self.effect_dots = not self.effect_dots
        
        if self.is_playing:
            if not self.instant_warp:
                lerp = 0.03
                self.zoom += (self.target_zoom - self.zoom) * lerp
                self.rotation += (self.target_rotation - self.rotation) * lerp
                self.drift_x += (self.target_drift_x - self.drift_x) * lerp
                self.drift_y += (self.target_drift_y - self.drift_y) * lerp
            
            bass_influence = self.smoothed_bass * 0.005
            self.zoom = self.target_zoom + bass_influence
        
        self.update()
    
    def update_audio_data(self):
        waveform = self.audio_analyzer.get_waveform()
        bass, mid, treble, beat = self.audio_analyzer.get_levels()
        
        smooth = 0.7
        self.smoothed_waveform = self.smoothed_waveform * smooth + waveform * (1 - smooth)
        self.smoothed_bass = self.smoothed_bass * smooth + bass * (1 - smooth)
        self.smoothed_mid = self.smoothed_mid * smooth + mid * (1 - smooth)
        self.smoothed_treble = self.smoothed_treble * smooth + treble * (1 - smooth)
        
        if beat and self.is_playing:
            current_time = self.time
            if current_time - self.last_beat_time > 0.3:
                self.last_beat_time = current_time
                if self.beat_decay:
                    self.decay = max(0.975, self.decay - 0.01)
                if self.auto_change and self.next_warp_ready and random.random() < 0.15:
                    self.warp_timer = self.warp_duration
        
        if self.decay < self.base_decay:
            self.decay += 0.0005
    
    def initializeGL(self):
        GL.glEnable(GL.GL_BLEND)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glEnable(GL.GL_POINT_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
        GL.glHint(GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        
        self.init_fbos()
        self.init_dither_texture()
    
    def init_dither_texture(self):
        size = 256
        noise = np.random.rand(size, size).astype(np.float32)
        noise = (noise - 0.5) * 2.0
        
        self.dither_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.dither_texture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_R32F, size, size, 0, 
                        GL.GL_RED, GL.GL_FLOAT, noise)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
    
    def init_fbos(self):
        w = max(self.width(), 320)
        h = max(self.height(), 240)
        
        fmt = QOpenGLFramebufferObjectFormat()
        fmt.setInternalTextureFormat(GL.GL_RGBA8)
        
        self.fbo1 = QOpenGLFramebufferObject(w, h, fmt)
        self.fbo2 = QOpenGLFramebufferObject(w, h, fmt)
        
        self.fbo1.bind()
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.fbo1.release()
        
        self.fbo2.bind()
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.fbo2.release()
    
    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)
        self.init_fbos()
    
    def paintGL(self):
        if self.fbo1 is None or self.fbo2 is None:
            return
        
        source_fbo = self.fbo1 if self.current_fbo == 0 else self.fbo2
        dest_fbo = self.fbo2 if self.current_fbo == 0 else self.fbo1
        
        dest_fbo.bind()
        GL.glViewport(0, 0, dest_fbo.width(), dest_fbo.height())
        
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-1, 1, -1, 1, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        
        self.draw_background()
        self.draw_warped_feedback(source_fbo)
        
        if self.dither_enabled:
            self.draw_dither_effect()
        
        self.draw_waveform_with_glow()
        
        if self.effect_solar:
            self.draw_solar_effect()
        if self.effect_dots:
            self.draw_dots_effect()
        if self.effect_nebula:
            self.draw_nebula_particles()
        if self.effect_grid:
            self.draw_grid_effect()
        if self.effect_border:
            self.draw_border_effect()
        
        dest_fbo.release()
        
        GL.glViewport(0, 0, self.width(), self.height())
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-1, 1, -1, 1, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, dest_fbo.texture())
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        
        GL.glColor4f(1.0, 1.0, 1.0, 1.0)
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(0, 0); GL.glVertex2f(-1, -1)
        GL.glTexCoord2f(1, 0); GL.glVertex2f(1, -1)
        GL.glTexCoord2f(1, 1); GL.glVertex2f(1, 1)
        GL.glTexCoord2f(0, 1); GL.glVertex2f(-1, 1)
        GL.glEnd()
        
        GL.glDisable(GL.GL_TEXTURE_2D)
        
        self.current_fbo = 1 - self.current_fbo
    
    def draw_background(self):
        hue = self.bg_hue % 1.0
        r, g, b = self.hsv_to_rgb(hue, 0.4, 0.02 + self.smoothed_bass * 0.015)
        
        GL.glBegin(GL.GL_QUADS)
        GL.glColor4f(r, g, b, 1.0)
        GL.glVertex2f(-1, -1)
        GL.glVertex2f(1, -1)
        
        r2, g2, b2 = self.hsv_to_rgb((hue + 0.1) % 1.0, 0.4, 0.015)
        GL.glColor4f(r2, g2, b2, 1.0)
        GL.glVertex2f(1, 1)
        GL.glVertex2f(-1, 1)
        GL.glEnd()
    
    def hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            return v, v, v
        
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        
        if i == 0: return v, t, p
        if i == 1: return q, v, p
        if i == 2: return p, v, t
        if i == 3: return p, q, v
        if i == 4: return t, p, v
        if i == 5: return v, p, q
        return v, v, v
    
    def draw_dither_effect(self):
        if self.dither_texture is None:
            return
        
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.dither_texture)
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        
        offset_x = (self.dither_offset * 0.1) % 1.0
        offset_y = (self.dither_offset * 0.073) % 1.0
        
        scale = 4.0
        
        dither_strength = self.dither_amount * (0.8 + self.smoothed_mid * 0.4)
        
        GL.glColor4f(dither_strength, dither_strength, dither_strength, 1.0)
        
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(offset_x, offset_y)
        GL.glVertex2f(-1, -1)
        GL.glTexCoord2f(offset_x + scale, offset_y)
        GL.glVertex2f(1, -1)
        GL.glTexCoord2f(offset_x + scale, offset_y + scale)
        GL.glVertex2f(1, 1)
        GL.glTexCoord2f(offset_x, offset_y + scale)
        GL.glVertex2f(-1, 1)
        GL.glEnd()
        
        GL.glDisable(GL.GL_TEXTURE_2D)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    
    def draw_warped_feedback(self, source_fbo):
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, source_fbo.texture())
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        
        tint_hue = (self.color_phase * 0.1) % 1.0
        tr, tg, tb = self.hsv_to_rgb(tint_hue, 0.07, 1.0)
        
        fade = self.decay
        GL.glColor4f(fade * tr, fade * tg, fade * tb, 1.0)
        
        inv_zoom = 1.0 / self.zoom
        half = 0.5
        
        cos_r = cos(self.rotation)
        sin_r = sin(self.rotation)
        
        corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        tex_coords = []
        
        for vx, vy in corners:
            cx = vx * inv_zoom
            cy = vy * inv_zoom
            
            rx = cx * cos_r - cy * sin_r
            ry = cx * sin_r + cy * cos_r
            
            tx = (rx + 1.0) * half + self.drift_x
            ty = (ry + 1.0) * half + self.drift_y
            
            tex_coords.append((tx, ty))
        
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(*tex_coords[0]); GL.glVertex2f(-1, -1)
        GL.glTexCoord2f(*tex_coords[1]); GL.glVertex2f(1, -1)
        GL.glTexCoord2f(*tex_coords[2]); GL.glVertex2f(1, 1)
        GL.glTexCoord2f(*tex_coords[3]); GL.glVertex2f(-1, 1)
        GL.glEnd()
        
        GL.glDisable(GL.GL_TEXTURE_2D)
    
    def get_color(self, t, brightness_boost=1.0):
        palette = self.palettes[self.palette_index]
        t = (t + self.color_phase) % 1.0
        
        idx = t * (len(palette) - 1)
        i = int(idx)
        f = idx - i
        
        if i >= len(palette) - 1:
            c = palette[-1]
        else:
            c1 = palette[i]
            c2 = palette[i + 1]
            c = (
                c1[0] + (c2[0] - c1[0]) * f,
                c1[1] + (c2[1] - c1[1]) * f,
                c1[2] + (c2[2] - c1[2]) * f
            )
        
        return (
            min(1.0, c[0] * brightness_boost),
            min(1.0, c[1] * brightness_boost),
            min(1.0, c[2] * brightness_boost)
        )
    
    def draw_waveform_with_glow(self):
        waveform = self.smoothed_waveform
        
        if not self.is_playing:
            waveform = np.sin(np.linspace(0, 4 * pi, len(waveform)) + self.time) * 0.15
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        
        self.draw_waveform_pass(waveform, line_width_mult=3.5, alpha=0.1, brightness=0.5)
        self.draw_waveform_pass(waveform, line_width_mult=2.0, alpha=0.2, brightness=0.7)
        self.draw_waveform_pass(waveform, line_width_mult=1.0, alpha=0.8, brightness=1.0)
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    
    def draw_waveform_pass(self, waveform, line_width_mult=1.0, alpha=1.0, brightness=1.0):
        num_points = len(waveform)
        base_brightness = (0.6 + self.smoothed_bass * 0.4) * brightness
        base_line_width = 2.5 + self.smoothed_bass * 2.5
        
        GL.glLineWidth(base_line_width * line_width_mult)
        
        if self.wave_mode == 0:
            GL.glBegin(GL.GL_LINE_STRIP)
            for i in range(num_points):
                t = i / (num_points - 1)
                x = (t * 2.0 - 1.0) * 0.9
                y = waveform[i] * 0.8
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y)
            GL.glEnd()
        
        elif self.wave_mode == 1:
            GL.glBegin(GL.GL_LINE_LOOP)
            for i in range(num_points):
                t = i / num_points
                angle = t * 2 * pi
                radius = 0.3 + waveform[i] * 0.4
                x = cos(angle) * radius
                y = sin(angle) * radius
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y)
            GL.glEnd()
        
        elif self.wave_mode == 2:
            GL.glBegin(GL.GL_LINE_STRIP)
            for i in range(num_points):
                t = i / (num_points - 1)
                angle = t * 4 * pi + self.time * 0.3
                radius = 0.1 + t * 0.5 + waveform[i] * 0.3
                x = cos(angle) * radius
                y = sin(angle) * radius
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y)
            GL.glEnd()
        
        elif self.wave_mode == 3:
            half = num_points // 2
            GL.glBegin(GL.GL_LINES)
            for i in range(half):
                t = i / half
                x = (t * 2.0 - 1.0) * 0.9
                y1 = waveform[i] * 0.7
                y2 = waveform[i + half] * 0.7
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y1)
                GL.glVertex2f(x, y2)
            GL.glEnd()
        
        elif self.wave_mode == 4:
            GL.glBegin(GL.GL_LINE_STRIP)
            for i in range(num_points):
                t = i / (num_points - 1)
                x = (t * 2.0 - 1.0) * 0.9
                y = waveform[i] * 0.8
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y)
            GL.glEnd()
            
            GL.glBegin(GL.GL_LINE_STRIP)
            for i in range(num_points):
                t = i / (num_points - 1)
                x = (t * 2.0 - 1.0) * 0.9
                y = -waveform[num_points - 1 - i] * 0.6
                
                color = self.get_color(1 - t, base_brightness * 0.6)
                GL.glColor4f(color[0], color[1], color[2], alpha * 0.5)
                GL.glVertex2f(x, y)
            GL.glEnd()
        
        elif self.wave_mode == 5:
            GL.glBegin(GL.GL_LINE_STRIP)
            for i in range(num_points):
                t = i / (num_points - 1)
                y = (t * 2.0 - 1.0) * 0.9
                x = waveform[i] * 0.8
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y)
            GL.glEnd()
        
        elif self.wave_mode == 6:
            GL.glPointSize((3.5 + self.smoothed_bass * 3.5) * line_width_mult)
            GL.glBegin(GL.GL_POINTS)
            step = max(1, num_points // 96)
            for i in range(0, num_points, step):
                t = i / (num_points - 1)
                x = (t * 2.0 - 1.0) * 0.9
                y = waveform[i] * 0.8
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                GL.glVertex2f(x, y)
            GL.glEnd()
        
        elif self.wave_mode == 7:
            bar_values = self.audio_analyzer.get_bar_values()
            num_bars = min(48, len(bar_values))
            bar_width = 1.8 / num_bars
            
            for i in range(num_bars):
                t = i / num_bars
                x = -0.9 + i * bar_width
                height = bar_values[i] * 0.7
                
                color = self.get_color(t, base_brightness)
                GL.glColor4f(color[0], color[1], color[2], alpha)
                
                GL.glLineWidth((base_line_width * 0.5) * line_width_mult)
                GL.glBegin(GL.GL_LINES)
                GL.glVertex2f(x + bar_width * 0.4, -0.6)
                GL.glVertex2f(x + bar_width * 0.4, -0.6 + height)
                GL.glEnd()
        
        GL.glLineWidth(1.0)
        GL.glPointSize(1.0)
    
    def draw_solar_effect(self):
        if self.smoothed_bass < 0.2:
            return
        
        intensity = (self.smoothed_bass - 0.2) * 1.3
        num_rays = 12
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        GL.glLineWidth(2.0)
        GL.glBegin(GL.GL_LINES)
        
        for i in range(num_rays):
            angle = (i / num_rays) * 2 * pi + self.time * 0.2
            length = 0.12 + intensity * 0.35 + random.random() * 0.08
            
            color = self.get_color(i / num_rays, 1.0)
            GL.glColor4f(color[0], color[1], color[2], intensity * 0.5)
            
            GL.glVertex2f(0, 0)
            GL.glVertex2f(cos(angle) * length, sin(angle) * length)
        
        GL.glEnd()
        GL.glLineWidth(1.0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    
    def draw_nebula_particles(self):
        num_particles = int(12 + self.smoothed_mid * 15)
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        GL.glPointSize(2.5)
        GL.glBegin(GL.GL_POINTS)
        
        random.seed(int(self.time * 2))
        
        for i in range(num_particles):
            base_angle = random.random() * 2 * pi
            base_radius = 0.2 + random.random() * 0.7
            drift = sin(self.time * 0.5 + i) * 0.1
            
            x = cos(base_angle) * (base_radius + drift)
            y = sin(base_angle) * (base_radius + drift)
            
            color = self.get_color(random.random(), 0.7)
            GL.glColor4f(color[0], color[1], color[2], 0.15 + self.smoothed_mid * 0.15)
            GL.glVertex2f(x, y)
        
        GL.glEnd()
        GL.glPointSize(1.0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        random.seed()
    
    def draw_dots_effect(self):
        num_dots = int(25 + self.smoothed_mid * 30)
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        GL.glPointSize(2.0)
        GL.glBegin(GL.GL_POINTS)
        
        for i in range(num_dots):
            angle = random.random() * 2 * pi
            radius = 0.2 + random.random() * 0.6
            x = cos(angle) * radius
            y = sin(angle) * radius
            
            color = self.get_color(random.random(), 0.85)
            GL.glColor4f(color[0], color[1], color[2], 0.25 + self.smoothed_mid * 0.25)
            GL.glVertex2f(x, y)
        
        GL.glEnd()
        GL.glPointSize(1.0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    
    def draw_grid_effect(self):
        GL.glLineWidth(1.0)
        color = self.get_color(self.time * 0.05 % 1.0, 0.25)
        GL.glColor4f(color[0], color[1], color[2], 0.12)
        
        GL.glBegin(GL.GL_LINES)
        
        for i in range(-4, 5):
            x = i * 0.2
            GL.glVertex2f(x, -1)
            GL.glVertex2f(x, 1)
            GL.glVertex2f(-1, x)
            GL.glVertex2f(1, x)
        
        GL.glEnd()
    
    def draw_border_effect(self):
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        GL.glLineWidth(2.5)
        color = self.get_color(self.time * 0.1 % 1.0, 0.85)
        GL.glColor4f(color[0], color[1], color[2], 0.35)
        
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(-0.95, -0.95)
        GL.glVertex2f(0.95, -0.95)
        GL.glVertex2f(0.95, 0.95)
        GL.glVertex2f(-0.95, 0.95)
        GL.glEnd()
        
        GL.glLineWidth(1.0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    
    def cleanup(self):
        self.animation_timer.stop()
        self.save_settings()
        
        if self.dither_texture is not None:
            GL.glDeleteTextures([self.dither_texture])
            self.dither_texture = None
        
        self.fbo1 = None
        self.fbo2 = None