from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.services.ai_refinement_service import RefinementRequest, RefinementResponse


class RefinementWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, service, request, history):
        super().__init__()
        self._service = service
        self._request = request
        self._history = history

    def run(self):
        try:
            response = self._service.refine(self._request, self._history)
            self.completed.emit(response)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RefinementDialog(QDialog):
    refinement_applied = Signal(dict)

    def __init__(self, parent=None, service=None, initial_sections=None, patient_context=None, default_brevity=True):
        super().__init__(parent)
        self.setWindowTitle("AI Findings Refinement")
        self.resize(920, 700)
        self._service = service
        self._settings_store = QSettings("EndoappC", "AIRefinementDialog")
        self._patient_context = patient_context or {}
        self._initial_sections = initial_sections or {}
        self._history = []
        self._chat_entries: list[tuple[str, str]] = []
        self._last_response: RefinementResponse | None = None
        self._worker: RefinementWorker | None = None
        self._default_instruction = "Polish to a concise, professional report."
        self._build_ui(default_brevity)
        self._ready = self._update_environment_status()
        if self._ready:
            QTimer.singleShot(0, self.trigger_initial_refinement)
        else:
            self.status_label.setText("Resolve the issues below before refining.")

    def _build_ui(self, default_brevity):
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Preparing AI refinement…")
        layout.addWidget(self.status_label)
        self.connection_label = QLabel()
        self.connection_label.setWordWrap(True)
        layout.addWidget(self.connection_label)

        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter, 1)

        left_widget = QWidget()
        preview_column = QVBoxLayout(left_widget)
        preview_column.setContentsMargins(0, 0, 10, 0)
        preview_column.setSpacing(8)

        self.findings_box = self._create_section_box("Findings")
        self.conclusions_box = self._create_section_box("Conclusions")
        self.recommendations_box = self._create_section_box("Recommendations")

        preview_column.addWidget(self.findings_box, stretch=3)
        preview_column.addWidget(self.conclusions_box, stretch=2)
        preview_column.addWidget(self.recommendations_box, stretch=2)

        self.splitter.addWidget(left_widget)

        convo_group = QGroupBox("Discussion")
        convo_layout = QVBoxLayout(convo_group)
        self.splitter.addWidget(convo_group)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)
        self._restore_layout_state()

        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("Start chatting with the AI assistant…")
        self.transcript_view.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fb;
                border: 1px solid #dfe3eb;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
            }
            """
        )
        convo_layout.addWidget(self.transcript_view, 1)

        self.user_input = QTextEdit()
        self.user_input.setPlaceholderText("Describe tweaks (e.g. tone, emphasize biopsies, etc.)")
        self.user_input.setFixedHeight(80)
        self.user_input.setStyleSheet("font-size: 11pt;")
        convo_layout.addWidget(self.user_input)

        buttons_layout = QHBoxLayout()
        self.ask_button = QPushButton()
        self.ask_button.setIcon(QIcon("icons/send.png"))
        self.ask_button.setIconSize(QSize(26, 26))
        self.ask_button.setFixedSize(48, 48)
        self.ask_button.setCursor(Qt.PointingHandCursor)
        self.ask_button.setToolTip("Send instruction to AI")
        self.ask_button.setStyleSheet(
            """
            QPushButton { border: none; background: transparent; border-radius: 6px; }
            QPushButton:hover { background-color: rgba(255,193,7,0.25); }
            QPushButton:pressed { background-color: rgba(255,193,7,0.4); }
            """
        )
        self.ask_button.clicked.connect(self.trigger_follow_up)
        self.apply_button = QPushButton("Insert Into Report")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_refinement)
        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.ask_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.cancel_button)
        convo_layout.addLayout(buttons_layout)

    def _create_section_box(self, title: str) -> QGroupBox:
        group = QGroupBox(title.title())
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                color: #007bff;
                border: 1px solid #dfe3eb;
                border-radius: 6px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            """
        )
        box_layout = QVBoxLayout(group)
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setMinimumHeight(120)
        box_layout.addWidget(editor)
        setattr(self, f"{title.lower()}_editor", editor)
        return group

    def trigger_initial_refinement(self):
        if not self._ready:
            return
        self._append_transcript("system", "Starting AI refinement…")
        self._run_refinement("")

    def trigger_follow_up(self):
        if not self._ready:
            return
        instruction = self.user_input.toPlainText().strip() or self._default_instruction
        self.user_input.clear()
        self._append_transcript("user", instruction)
        self._run_refinement(instruction)

    def _run_refinement(self, instruction: str):
        if not self._service:
            self.status_label.setText("AI service unavailable. Configure provider in settings.")
            return
        if self._worker and self._worker.isRunning():
            return
        if not self._update_environment_status():
            self.status_label.setText("Cannot contact AI until issues are resolved.")
            return
        request = RefinementRequest(
            findings_draft=self._initial_sections.get("findings", ""),
            conclusions_draft=self._initial_sections.get("conclusions", ""),
            recommendations_draft=self._initial_sections.get("recommendations", ""),
            patient_context=self._patient_context,
            user_instruction=instruction or self._default_instruction,
            brevity_mode=True,
        )
        history_snapshot = list(self._history)
        self.status_label.setText("Waiting for AI response…")
        self.ask_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self._worker = RefinementWorker(self._service, request, history_snapshot)
        self._worker.completed.connect(self._on_worker_success)
        self._worker.failed.connect(self._on_worker_failure)
        self._worker.start()

    def _on_worker_success(self, response: RefinementResponse):
        self._last_response = response
        assistant_text = "\n".join(
            [
                "FINDINGS:",
                response.findings_text,
                "",
                "CONCLUSIONS:",
                "\n".join(response.conclusions),
                "",
                "RECOMMENDATIONS:",
                "\n".join(response.recommendations),
            ]
        ).strip()
        self._append_transcript("assistant", assistant_text)
        self._worker = None
        self.ask_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.status_label.setText(f"AI response ready ({response.model_used}).")
        self._update_section_text(response)

    def _on_worker_failure(self, message: str):
        self.status_label.setText(f"AI request failed: {message}")
        self._append_transcript("assistant", f"⚠️ {message}")
        self._worker = None
        self.ask_button.setEnabled(self._update_environment_status())

    def _append_transcript(self, speaker: str, text: str):
        clean = text.strip()
        self._chat_entries.append((speaker, clean))
        self._render_chat_entries()
        if speaker in {"user", "assistant"}:
            self._history.append({"role": speaker, "content": clean})

    def _render_chat_entries(self):
        bubbles = []
        font_family = "'Segoe Script', 'Comic Sans MS', cursive"
        for speaker, text in self._chat_entries:
            align = "right" if speaker == "user" else "left"
            text_color = "#0d6efd" if speaker == "user" else "#1f2933"
            bubble = f"""
                <div style="text-align:{align}; margin:6px 0;">
                    <span style="
                        display:inline-block;
                        color:{text_color};
                        padding:0;
                        max-width:75%;
                        font-size:11pt;
                        font-family:{font_family};
                        line-height:1.35;
                    ">
                        {text.replace('\n', '<br>')}
                    </span>
                </div>
            """
            bubbles.append(bubble)
        html = "<br>".join(bubbles) if bubbles else "<div style='color:#999;'>Start chatting with the AI assistant…</div>"
        self.transcript_view.setHtml(html)
        self.transcript_view.verticalScrollBar().setValue(self.transcript_view.verticalScrollBar().maximum())

    def _update_section_text(self, response: RefinementResponse):
        self.findings_editor.setPlainText(response.findings_text)
        self.conclusions_editor.setPlainText("\n".join(response.conclusions))
        self.recommendations_editor.setPlainText("\n".join(response.recommendations))

    def apply_refinement(self):
        if not self._last_response:
            return
        payload = {
            "findings": self._last_response.findings_text,
            "conclusions": "\n".join(self._last_response.conclusions),
            "recommendations": "\n".join(self._last_response.recommendations),
        }
        self.refinement_applied.emit(payload)
        self._save_layout_state()
        self.accept()

    def _update_environment_status(self) -> bool:
        if not self._service:
            self.connection_label.setText("⚠️ AI service unavailable. Reopen the report after restarting the app.")
            self.ask_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self._ready = False
            return False
        issues = self._service.get_environment_issues()
        if issues:
            self.connection_label.setText(
                "⚠️ " + " ".join(issues) + " Use File → Settings to resolve these items."
            )
            self.ask_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self._ready = False
            return False
        self.connection_label.setText("✅ Connected to AI provider. Ready for refinement.")
        self.ask_button.setEnabled(True)
        self._ready = True
        return True

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            try:
                self._worker.completed.disconnect(self._on_worker_success)
                self._worker.failed.disconnect(self._on_worker_failure)
            except TypeError:
                pass
            self._worker.terminate()
            self._worker.wait(300)
        self._save_layout_state()
        super().closeEvent(event)

    def _restore_layout_state(self):
        if not self._settings_store:
            return
        geometry = self._settings_store.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        splitter_state = self._settings_store.value("splitter")
        if splitter_state and hasattr(self, "splitter"):
            self.splitter.restoreState(splitter_state)

    def _save_layout_state(self):
        if not self._settings_store:
            return
        self._settings_store.setValue("geometry", self.saveGeometry())
        if hasattr(self, "splitter"):
            self._settings_store.setValue("splitter", self.splitter.saveState())
