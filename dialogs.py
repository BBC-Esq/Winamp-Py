from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSlider,
    QPushButton,
    QGroupBox,
    QTabWidget,
    QWidget,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
)


class LabeledSlider(QWidget):
    """A slider with a label showing its current value."""
    
    valueChanged = Signal(float)
    
    def __init__(self, label, min_val, max_val, default, decimals=2, parent=None):
        super().__init__(parent)
        
        self.min_val = min_val
        self.max_val = max_val
        self.decimals = decimals
        self.multiplier = 10 ** decimals
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label)
        self.label.setMinimumWidth(140)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_val * self.multiplier))
        self.slider.setMaximum(int(max_val * self.multiplier))
        self.slider.setValue(int(default * self.multiplier))
        self.slider.valueChanged.connect(self._on_slider_changed)
        
        self.value_label = QLabel(f"{default:.{decimals}f}")
        self.value_label.setMinimumWidth(50)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(self.label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
    
    def _on_slider_changed(self, value):
        float_value = value / self.multiplier
        self.value_label.setText(f"{float_value:.{self.decimals}f}")
        self.valueChanged.emit(float_value)
    
    def value(self):
        return self.slider.value() / self.multiplier
    
    def setValue(self, value):
        self.slider.setValue(int(value * self.multiplier))
        self.value_label.setText(f"{value:.{self.decimals}f}")


class VisualizationSettingsDialog(QDialog):
    """Settings dialog for visualization parameters."""
    
    settings_changed = Signal(dict)
    
    # Default values
    DEFAULTS = {
        # Decay/Trails
        'decay': 0.985,
        'beat_decay_enabled': True,
        'beat_decay_amount': 0.01,
        
        # Line appearance
        'line_width_base': 2.5,
        'line_width_bass_mult': 2.5,
        
        # Glow effect
        'glow_outer_width': 3.5,
        'glow_outer_alpha': 0.10,
        'glow_outer_brightness': 0.5,
        'glow_mid_width': 2.0,
        'glow_mid_alpha': 0.20,
        'glow_mid_brightness': 0.7,
        'glow_core_alpha': 0.80,
        'glow_core_brightness': 1.0,
        
        # Colors
        'color_speed': 0.008,
        'palette_index': 0,
        'color_tint_saturation': 0.07,
        
        # Background
        'bg_brightness': 0.02,
        'bg_bass_influence': 0.015,
        'bg_saturation': 0.4,
        
        # Brightness
        'base_brightness': 0.6,
        'bass_brightness_mult': 0.4,
        
        # Particles/Effects
        'nebula_enabled': True,
        'nebula_count_base': 12,
        'nebula_count_mult': 15,
        'nebula_alpha': 0.15,
        'nebula_brightness': 0.7,
        
        'dots_count_base': 25,
        'dots_count_mult': 30,
        'dots_alpha': 0.25,
        'dots_brightness': 0.85,
        
        'solar_intensity': 1.3,
        'solar_alpha': 0.5,
        
        # Timing
        'warp_duration': 600,
        'audio_smoothing': 0.7,
    }
    
    def __init__(self, current_settings=None, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Visualization Settings")
        self.setMinimumWidth(500)
        
        self.settings = dict(self.DEFAULTS)
        if current_settings:
            self.settings.update(current_settings)
        
        self.setup_ui()
        self.load_values()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # Trails Tab
        trails_tab = QWidget()
        trails_layout = QVBoxLayout(trails_tab)
        
        decay_group = QGroupBox("Trail Persistence")
        decay_layout = QVBoxLayout(decay_group)
        
        self.decay_slider = LabeledSlider("Decay Rate:", 0.95, 0.995, self.settings['decay'], decimals=3)
        self.decay_slider.valueChanged.connect(lambda v: self._update_setting('decay', v))
        decay_layout.addWidget(self.decay_slider)
        
        self.beat_decay_check = QCheckBox("Beat-reactive decay")
        self.beat_decay_check.stateChanged.connect(lambda s: self._update_setting('beat_decay_enabled', s == Qt.CheckState.Checked.value))
        decay_layout.addWidget(self.beat_decay_check)
        
        self.beat_decay_slider = LabeledSlider("Beat Decay Amount:", 0.005, 0.03, self.settings['beat_decay_amount'], decimals=3)
        self.beat_decay_slider.valueChanged.connect(lambda v: self._update_setting('beat_decay_amount', v))
        decay_layout.addWidget(self.beat_decay_slider)
        
        trails_layout.addWidget(decay_group)
        
        timing_group = QGroupBox("Timing")
        timing_layout = QVBoxLayout(timing_group)
        
        self.warp_duration_slider = LabeledSlider("Warp Duration (frames):", 200, 1200, self.settings['warp_duration'], decimals=0)
        self.warp_duration_slider.valueChanged.connect(lambda v: self._update_setting('warp_duration', int(v)))
        timing_layout.addWidget(self.warp_duration_slider)
        
        self.smoothing_slider = LabeledSlider("Audio Smoothing:", 0.3, 0.9, self.settings['audio_smoothing'], decimals=2)
        self.smoothing_slider.valueChanged.connect(lambda v: self._update_setting('audio_smoothing', v))
        timing_layout.addWidget(self.smoothing_slider)
        
        trails_layout.addWidget(timing_group)
        trails_layout.addStretch()
        
        tabs.addTab(trails_tab, "Trails")
        
        # Lines Tab
        lines_tab = QWidget()
        lines_layout = QVBoxLayout(lines_tab)
        
        width_group = QGroupBox("Line Width")
        width_layout = QVBoxLayout(width_group)
        
        self.line_width_slider = LabeledSlider("Base Width:", 1.0, 5.0, self.settings['line_width_base'], decimals=1)
        self.line_width_slider.valueChanged.connect(lambda v: self._update_setting('line_width_base', v))
        width_layout.addWidget(self.line_width_slider)
        
        self.line_bass_slider = LabeledSlider("Bass Multiplier:", 0.0, 5.0, self.settings['line_width_bass_mult'], decimals=1)
        self.line_bass_slider.valueChanged.connect(lambda v: self._update_setting('line_width_bass_mult', v))
        width_layout.addWidget(self.line_bass_slider)
        
        lines_layout.addWidget(width_group)
        
        glow_group = QGroupBox("Glow Effect")
        glow_layout = QVBoxLayout(glow_group)
        
        glow_layout.addWidget(QLabel("Outer Glow:"))
        self.glow_outer_width_slider = LabeledSlider("  Width Mult:", 1.0, 6.0, self.settings['glow_outer_width'], decimals=1)
        self.glow_outer_width_slider.valueChanged.connect(lambda v: self._update_setting('glow_outer_width', v))
        glow_layout.addWidget(self.glow_outer_width_slider)
        
        self.glow_outer_alpha_slider = LabeledSlider("  Alpha:", 0.0, 0.3, self.settings['glow_outer_alpha'], decimals=2)
        self.glow_outer_alpha_slider.valueChanged.connect(lambda v: self._update_setting('glow_outer_alpha', v))
        glow_layout.addWidget(self.glow_outer_alpha_slider)
        
        self.glow_outer_bright_slider = LabeledSlider("  Brightness:", 0.2, 1.0, self.settings['glow_outer_brightness'], decimals=2)
        self.glow_outer_bright_slider.valueChanged.connect(lambda v: self._update_setting('glow_outer_brightness', v))
        glow_layout.addWidget(self.glow_outer_bright_slider)
        
        glow_layout.addWidget(QLabel("Middle Glow:"))
        self.glow_mid_width_slider = LabeledSlider("  Width Mult:", 1.0, 4.0, self.settings['glow_mid_width'], decimals=1)
        self.glow_mid_width_slider.valueChanged.connect(lambda v: self._update_setting('glow_mid_width', v))
        glow_layout.addWidget(self.glow_mid_width_slider)
        
        self.glow_mid_alpha_slider = LabeledSlider("  Alpha:", 0.0, 0.5, self.settings['glow_mid_alpha'], decimals=2)
        self.glow_mid_alpha_slider.valueChanged.connect(lambda v: self._update_setting('glow_mid_alpha', v))
        glow_layout.addWidget(self.glow_mid_alpha_slider)
        
        self.glow_mid_bright_slider = LabeledSlider("  Brightness:", 0.3, 1.2, self.settings['glow_mid_brightness'], decimals=2)
        self.glow_mid_bright_slider.valueChanged.connect(lambda v: self._update_setting('glow_mid_brightness', v))
        glow_layout.addWidget(self.glow_mid_bright_slider)
        
        glow_layout.addWidget(QLabel("Core:"))
        self.glow_core_alpha_slider = LabeledSlider("  Alpha:", 0.3, 1.0, self.settings['glow_core_alpha'], decimals=2)
        self.glow_core_alpha_slider.valueChanged.connect(lambda v: self._update_setting('glow_core_alpha', v))
        glow_layout.addWidget(self.glow_core_alpha_slider)
        
        self.glow_core_bright_slider = LabeledSlider("  Brightness:", 0.5, 1.5, self.settings['glow_core_brightness'], decimals=2)
        self.glow_core_bright_slider.valueChanged.connect(lambda v: self._update_setting('glow_core_brightness', v))
        glow_layout.addWidget(self.glow_core_bright_slider)
        
        lines_layout.addWidget(glow_group)
        lines_layout.addStretch()
        
        tabs.addTab(lines_tab, "Lines & Glow")
        
        # Colors Tab
        colors_tab = QWidget()
        colors_layout = QVBoxLayout(colors_tab)
        
        palette_group = QGroupBox("Color Palette")
        palette_layout = QVBoxLayout(palette_group)
        
        palette_row = QHBoxLayout()
        palette_row.addWidget(QLabel("Palette:"))
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
        self.palette_combo.currentIndexChanged.connect(lambda i: self._update_setting('palette_index', i))
        palette_row.addWidget(self.palette_combo, 1)
        palette_layout.addLayout(palette_row)
        
        self.color_speed_slider = LabeledSlider("Color Cycle Speed:", 0.001, 0.02, self.settings['color_speed'], decimals=3)
        self.color_speed_slider.valueChanged.connect(lambda v: self._update_setting('color_speed', v))
        palette_layout.addWidget(self.color_speed_slider)
        
        self.tint_sat_slider = LabeledSlider("Trail Tint Saturation:", 0.0, 0.2, self.settings['color_tint_saturation'], decimals=2)
        self.tint_sat_slider.valueChanged.connect(lambda v: self._update_setting('color_tint_saturation', v))
        palette_layout.addWidget(self.tint_sat_slider)
        
        colors_layout.addWidget(palette_group)
        
        brightness_group = QGroupBox("Brightness")
        brightness_layout = QVBoxLayout(brightness_group)
        
        self.base_bright_slider = LabeledSlider("Base Brightness:", 0.3, 1.0, self.settings['base_brightness'], decimals=2)
        self.base_bright_slider.valueChanged.connect(lambda v: self._update_setting('base_brightness', v))
        brightness_layout.addWidget(self.base_bright_slider)
        
        self.bass_bright_slider = LabeledSlider("Bass Brightness Add:", 0.0, 0.8, self.settings['bass_brightness_mult'], decimals=2)
        self.bass_bright_slider.valueChanged.connect(lambda v: self._update_setting('bass_brightness_mult', v))
        brightness_layout.addWidget(self.bass_bright_slider)
        
        colors_layout.addWidget(brightness_group)
        
        bg_group = QGroupBox("Background")
        bg_layout = QVBoxLayout(bg_group)
        
        self.bg_bright_slider = LabeledSlider("Background Brightness:", 0.0, 0.08, self.settings['bg_brightness'], decimals=3)
        self.bg_bright_slider.valueChanged.connect(lambda v: self._update_setting('bg_brightness', v))
        bg_layout.addWidget(self.bg_bright_slider)
        
        self.bg_bass_slider = LabeledSlider("Bass Influence:", 0.0, 0.05, self.settings['bg_bass_influence'], decimals=3)
        self.bg_bass_slider.valueChanged.connect(lambda v: self._update_setting('bg_bass_influence', v))
        bg_layout.addWidget(self.bg_bass_slider)
        
        self.bg_sat_slider = LabeledSlider("Background Saturation:", 0.0, 0.8, self.settings['bg_saturation'], decimals=2)
        self.bg_sat_slider.valueChanged.connect(lambda v: self._update_setting('bg_saturation', v))
        bg_layout.addWidget(self.bg_sat_slider)
        
        colors_layout.addWidget(bg_group)
        colors_layout.addStretch()
        
        tabs.addTab(colors_tab, "Colors")
        
        # Effects Tab
        effects_tab = QWidget()
        effects_layout = QVBoxLayout(effects_tab)
        
        nebula_group = QGroupBox("Nebula Particles")
        nebula_layout = QVBoxLayout(nebula_group)
        
        self.nebula_check = QCheckBox("Enable Nebula Particles")
        self.nebula_check.stateChanged.connect(lambda s: self._update_setting('nebula_enabled', s == Qt.CheckState.Checked.value))
        nebula_layout.addWidget(self.nebula_check)
        
        self.nebula_count_slider = LabeledSlider("Base Count:", 5, 30, self.settings['nebula_count_base'], decimals=0)
        self.nebula_count_slider.valueChanged.connect(lambda v: self._update_setting('nebula_count_base', int(v)))
        nebula_layout.addWidget(self.nebula_count_slider)
        
        self.nebula_mult_slider = LabeledSlider("Audio Multiplier:", 5, 40, self.settings['nebula_count_mult'], decimals=0)
        self.nebula_mult_slider.valueChanged.connect(lambda v: self._update_setting('nebula_count_mult', int(v)))
        nebula_layout.addWidget(self.nebula_mult_slider)
        
        self.nebula_alpha_slider = LabeledSlider("Alpha:", 0.05, 0.4, self.settings['nebula_alpha'], decimals=2)
        self.nebula_alpha_slider.valueChanged.connect(lambda v: self._update_setting('nebula_alpha', v))
        nebula_layout.addWidget(self.nebula_alpha_slider)
        
        self.nebula_bright_slider = LabeledSlider("Brightness:", 0.3, 1.2, self.settings['nebula_brightness'], decimals=2)
        self.nebula_bright_slider.valueChanged.connect(lambda v: self._update_setting('nebula_brightness', v))
        nebula_layout.addWidget(self.nebula_bright_slider)
        
        effects_layout.addWidget(nebula_group)
        
        dots_group = QGroupBox("Random Dots")
        dots_layout = QVBoxLayout(dots_group)
        
        self.dots_count_slider = LabeledSlider("Base Count:", 10, 50, self.settings['dots_count_base'], decimals=0)
        self.dots_count_slider.valueChanged.connect(lambda v: self._update_setting('dots_count_base', int(v)))
        dots_layout.addWidget(self.dots_count_slider)
        
        self.dots_mult_slider = LabeledSlider("Audio Multiplier:", 10, 60, self.settings['dots_count_mult'], decimals=0)
        self.dots_mult_slider.valueChanged.connect(lambda v: self._update_setting('dots_count_mult', int(v)))
        dots_layout.addWidget(self.dots_mult_slider)
        
        self.dots_alpha_slider = LabeledSlider("Alpha:", 0.1, 0.5, self.settings['dots_alpha'], decimals=2)
        self.dots_alpha_slider.valueChanged.connect(lambda v: self._update_setting('dots_alpha', v))
        dots_layout.addWidget(self.dots_alpha_slider)
        
        self.dots_bright_slider = LabeledSlider("Brightness:", 0.5, 1.2, self.settings['dots_brightness'], decimals=2)
        self.dots_bright_slider.valueChanged.connect(lambda v: self._update_setting('dots_brightness', v))
        dots_layout.addWidget(self.dots_bright_slider)
        
        effects_layout.addWidget(dots_group)
        
        solar_group = QGroupBox("Solar Flare")
        solar_layout = QVBoxLayout(solar_group)
        
        self.solar_intensity_slider = LabeledSlider("Intensity:", 0.5, 2.5, self.settings['solar_intensity'], decimals=2)
        self.solar_intensity_slider.valueChanged.connect(lambda v: self._update_setting('solar_intensity', v))
        solar_layout.addWidget(self.solar_intensity_slider)
        
        self.solar_alpha_slider = LabeledSlider("Alpha:", 0.2, 0.8, self.settings['solar_alpha'], decimals=2)
        self.solar_alpha_slider.valueChanged.connect(lambda v: self._update_setting('solar_alpha', v))
        solar_layout.addWidget(self.solar_alpha_slider)
        
        effects_layout.addWidget(solar_group)
        effects_layout.addStretch()
        
        tabs.addTab(effects_tab, "Effects")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _update_setting(self, key, value):
        self.settings[key] = value
        self.settings_changed.emit(self.settings)
    
    def load_values(self):
        """Load current settings into UI widgets."""
        self.decay_slider.setValue(self.settings['decay'])
        self.beat_decay_check.setChecked(self.settings['beat_decay_enabled'])
        self.beat_decay_slider.setValue(self.settings['beat_decay_amount'])
        self.warp_duration_slider.setValue(self.settings['warp_duration'])
        self.smoothing_slider.setValue(self.settings['audio_smoothing'])
        
        self.line_width_slider.setValue(self.settings['line_width_base'])
        self.line_bass_slider.setValue(self.settings['line_width_bass_mult'])
        
        self.glow_outer_width_slider.setValue(self.settings['glow_outer_width'])
        self.glow_outer_alpha_slider.setValue(self.settings['glow_outer_alpha'])
        self.glow_outer_bright_slider.setValue(self.settings['glow_outer_brightness'])
        self.glow_mid_width_slider.setValue(self.settings['glow_mid_width'])
        self.glow_mid_alpha_slider.setValue(self.settings['glow_mid_alpha'])
        self.glow_mid_bright_slider.setValue(self.settings['glow_mid_brightness'])
        self.glow_core_alpha_slider.setValue(self.settings['glow_core_alpha'])
        self.glow_core_bright_slider.setValue(self.settings['glow_core_brightness'])
        
        self.palette_combo.setCurrentIndex(self.settings['palette_index'])
        self.color_speed_slider.setValue(self.settings['color_speed'])
        self.tint_sat_slider.setValue(self.settings['color_tint_saturation'])
        
        self.base_bright_slider.setValue(self.settings['base_brightness'])
        self.bass_bright_slider.setValue(self.settings['bass_brightness_mult'])
        
        self.bg_bright_slider.setValue(self.settings['bg_brightness'])
        self.bg_bass_slider.setValue(self.settings['bg_bass_influence'])
        self.bg_sat_slider.setValue(self.settings['bg_saturation'])
        
        self.nebula_check.setChecked(self.settings['nebula_enabled'])
        self.nebula_count_slider.setValue(self.settings['nebula_count_base'])
        self.nebula_mult_slider.setValue(self.settings['nebula_count_mult'])
        self.nebula_alpha_slider.setValue(self.settings['nebula_alpha'])
        self.nebula_bright_slider.setValue(self.settings['nebula_brightness'])
        
        self.dots_count_slider.setValue(self.settings['dots_count_base'])
        self.dots_mult_slider.setValue(self.settings['dots_count_mult'])
        self.dots_alpha_slider.setValue(self.settings['dots_alpha'])
        self.dots_bright_slider.setValue(self.settings['dots_brightness'])
        
        self.solar_intensity_slider.setValue(self.settings['solar_intensity'])
        self.solar_alpha_slider.setValue(self.settings['solar_alpha'])
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self.settings = dict(self.DEFAULTS)
        self.load_values()
        self.settings_changed.emit(self.settings)
    
    def get_settings(self):
        """Return the current settings dictionary."""
        return self.settings