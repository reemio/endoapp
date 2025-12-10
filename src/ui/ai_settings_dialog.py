from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QComboBox,
    QPushButton,
    QMessageBox,
)


RECOMMENDED_MODELS = [
    "gpt-4.1",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4o-mini",
    "o4-mini",
    "gpt-4.1-distill",
    "gpt-3.5-turbo",
]


class AISettingsDialog(QDialog):
    """Dialog for configuring AI refinement and OpenAI package behavior."""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("AI Assistant Settings")
        self.setMinimumWidth(420)
        self._existing_key = ""
        self._clear_api_key = False
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)

        # Provider selector (editable for future providers)
        self.provider_combo = QComboBox()
        self.provider_combo.setEditable(True)
        self.provider_combo.addItems(["openai"])
        form_layout.addRow("Provider", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.addItems(RECOMMENDED_MODELS)
        self.model_combo.setEditable(False)
        form_layout.addRow("Model", self.model_combo)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.05)
        self.temperature_spin.setDecimals(2)
        form_layout.addRow("Temperature", self.temperature_spin)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 32768)
        self.max_tokens_spin.setSingleStep(50)
        form_layout.addRow("Max tokens", self.max_tokens_spin)

        self.brevity_checkbox = QCheckBox("Keep recommendations brief (<20 words)")
        form_layout.addRow("", self.brevity_checkbox)

        self.auto_manage_checkbox = QCheckBox("Automatically manage OpenAI package")
        self.auto_manage_checkbox.toggled.connect(self._sync_package_controls)
        form_layout.addRow("", self.auto_manage_checkbox)

        self.auto_update_checkbox = QCheckBox("Auto-update to preferred version")
        form_layout.addRow("", self.auto_update_checkbox)

        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("e.g., 1.52.2")
        form_layout.addRow("Preferred version", self.version_edit)

        api_key_layout = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Paste new API key or leave blank")
        api_key_layout.addWidget(self.api_key_edit, 1)
        self.clear_key_btn = QPushButton("Clear")
        self.clear_key_btn.clicked.connect(self._handle_clear_api_key)
        api_key_layout.addWidget(self.clear_key_btn, 0)
        form_layout.addRow("Stored API key", api_key_layout)

        layout.addLayout(form_layout)

        note = QLabel(
            "Saving will refresh the AI assistant configuration.\n"
            "API keys are stored locally and masked in logs."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self):
        ai_settings = self.settings_manager.get("ai_refinement", default={}) or {}
        self.provider_combo.setCurrentText(ai_settings.get("provider", "openai"))
        stored_model = ai_settings.get("model", RECOMMENDED_MODELS[0])
        if stored_model not in RECOMMENDED_MODELS:
            stored_model = RECOMMENDED_MODELS[0]
            self.settings_manager.set("ai_refinement", "model", value=stored_model)
        index = max(RECOMMENDED_MODELS.index(stored_model), 0)
        self.model_combo.setCurrentIndex(index)
        self.temperature_spin.setValue(float(ai_settings.get("temperature", 0.2)))
        self.max_tokens_spin.setValue(int(ai_settings.get("max_tokens", 900)))
        self.brevity_checkbox.setChecked(bool(ai_settings.get("brevity_default", True)))
        self.auto_manage_checkbox.setChecked(bool(ai_settings.get("auto_manage_package", False)))
        self.auto_update_checkbox.setChecked(bool(ai_settings.get("auto_update_package", False)))
        self.version_edit.setText(ai_settings.get("preferred_version", ""))
        self._existing_key = ai_settings.get("stored_api_key", "")
        if self._existing_key:
            self.api_key_edit.setPlaceholderText("Existing key retained (leave blank to keep)")
        self._sync_package_controls()

    def _sync_package_controls(self):
        enabled = self.auto_manage_checkbox.isChecked()
        self.auto_update_checkbox.setEnabled(enabled)
        self.version_edit.setEnabled(enabled)

    def _handle_clear_api_key(self):
        self._clear_api_key = True
        self.api_key_edit.clear()
        self.api_key_edit.setPlaceholderText("API key will be removed")

    def _handle_accept(self):
        if not self.model_combo.currentText().strip():
            QMessageBox.warning(self, "Validation", "Model name cannot be empty.")
            return

        try:
            self._save_settings()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Settings Error", f"Failed to save settings:\n{exc}")
            return
        self.accept()

    def _save_settings(self):
        values = {
            "provider": self.provider_combo.currentText().strip() or "openai",
            "model": self.model_combo.currentText().strip(),
            "temperature": float(self.temperature_spin.value()),
            "max_tokens": int(self.max_tokens_spin.value()),
            "brevity_default": self.brevity_checkbox.isChecked(),
            "auto_manage_package": self.auto_manage_checkbox.isChecked(),
            "auto_update_package": self.auto_update_checkbox.isChecked(),
            "preferred_version": self.version_edit.text().strip(),
        }
        for key, value in values.items():
            self.settings_manager.set("ai_refinement", key, value=value)

        if self._clear_api_key:
            self.settings_manager.set("ai_refinement", "stored_api_key", value="")
        elif self.api_key_edit.text().strip():
            self.settings_manager.set(
                "ai_refinement",
                "stored_api_key",
                value=self.api_key_edit.text().strip(),
            )
