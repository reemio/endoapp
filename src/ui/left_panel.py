
# FILE: src/ui/left_panel.py
# Restored QComboBoxes, restored Conclusion/Recommendation combo pattern,
# and ensured no extra boxing around sections.

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QPushButton,
    QListView,
    QStyledItemDelegate,
    QDateEdit,
    QSpinBox,
    QScrollArea, 
    QSizePolicy,
    QStyleOptionViewItem
)
from PySide6.QtCore import Qt, Signal, QDate, QSize, QRect, QPoint
from PySide6.QtGui import QTextCursor, QTextBlockFormat, QIcon, QPainter
import logging
import re 
import time 

class AutoNumberTextEdit(QTextEdit):
    """TEXT EDIT WITH AUTO-NUMBERING FROM FIRST LINE AND ON ENTER KEY."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auto_numbering = True
        self.textChanged.connect(self.handle_text_changed_for_first_line)

    def keyPressEvent(self, event):
        if self.auto_numbering and (event.key() in (Qt.Key_Return, Qt.Key_Enter)):
            cursor = self.textCursor()
            current_block_text = cursor.block().text().strip()
            if re.fullmatch(r"\d+\.\s*", current_block_text):
                cursor.insertBlock()
                return
            cursor.insertBlock()
            next_num = 1
            previous_block = cursor.block().previous()
            if previous_block.isValid():
                prev_text = previous_block.text().strip()
                match = re.match(r"^(\d+)\.", prev_text)
                if match:
                    try:
                        next_num = int(match.group(1)) + 1
                    except ValueError:
                        pass
            cursor.insertText(f"{next_num}. ")
            return
        super().keyPressEvent(event)

    def handle_text_changed_for_first_line(self):
        if not self.auto_numbering:
            return
        try:
            self.textChanged.disconnect(self.handle_text_changed_for_first_line)
        except RuntimeError:
            pass
        cursor_pos = self.textCursor().position()
        current_text = self.toPlainText()
        lines = current_text.split('\n', 1)
        first_line_content = lines[0].strip()
        if first_line_content and not re.match(r"^\d+\.\s", first_line_content):
            original_first_line_text = lines[0]
            new_first_line = f"1. {original_first_line_text}"
            if len(lines) > 1:
                new_text = new_first_line + '\n' + lines[1]
            else:
                new_text = new_first_line
            self.setPlainText(new_text)
            if cursor_pos <= len(original_first_line_text):
                new_pos = min(cursor_pos + 3, len(new_text))
                c = self.textCursor()
                c.setPosition(new_pos)
                self.setTextCursor(c)
        self.textChanged.connect(self.handle_text_changed_for_first_line)


class NoScrollComboBox(QComboBox):
    """ComboBox that ignores mouse wheel unless popup is open."""

    def wheelEvent(self, event):
        view = self.view()
        if view and view.isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class AgeSpinBox(QSpinBox):
    """Spin box that shows blank when no age is set."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(-1, 150)
        self.setSpecialValueText("")
        self.setValue(-1)

    def textFromValue(self, value):
        if value < 0:
            return ""
        return super().textFromValue(value)

    def valueFromText(self, text):
        text = text.strip()
        if not text:
            return self.minimum()
        return super().valueFromText(text)

    def wheelEvent(self, event):
        event.ignore()


class NoScrollDateEdit(QDateEdit):
    def wheelEvent(self, event):
        event.ignore()


class ComboItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.delete_icon = QIcon("icons/x.png")
        self.icon_size = QSize(14, 14)
        self.icon_padding = 6

    def paint(self, painter, option, index):
        painter.save()
        text_rect = QRect(option.rect)
        text_rect.setRight(text_rect.right() - (self.icon_size.width() + self.icon_padding))
        text_option = QStyleOptionViewItem(option)
        text_option.rect = text_rect
        super().paint(painter, text_option, index)

        icon_rect = QRect(
            option.rect.right() - self.icon_size.width() - self.icon_padding // 2,
            option.rect.center().y() - self.icon_size.height() // 2,
            self.icon_size.width(),
            self.icon_size.height()
        )
        self.delete_icon.paint(painter, icon_rect, Qt.AlignCenter)
        painter.restore()


class ComboListView(QListView):
    delete_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.icon_area_width = 24

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            rect = self.visualRect(index)
            if event.pos().x() >= rect.right() - self.icon_area_width:
                self.delete_clicked.emit(index.row())
                return
        super().mousePressEvent(event)


class LeftPanel(QWidget):
    data_changed = Signal(dict)
    generate_report_requested = Signal() # Signal for when generate report is clicked
    refinement_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.combo_delete_map = {}
        self.setupUI()
        if hasattr(self, 'setup_auto_apply_connections'):
            self.setup_auto_apply_connections() 
        else:
            logging.warning("LeftPanel: setup_auto_apply_connections method not found.")

    def set_database(self, db_manager):
        self.db = db_manager
        if hasattr(self, 'load_dropdown_history'):
            self.load_dropdown_history()
        else:
            logging.warning("LeftPanel: load_dropdown_history method not found.")

    def setupUI(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0)
        outer_layout.setSpacing(0) 

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # Ensure vertical scrollbar is always on
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        main_content_widget = QWidget()
        # main_content_widget.setStyleSheet("background-color: white;") # Set background for content if needed
        
        content_layout = QVBoxLayout(main_content_widget) 
        content_layout.setSpacing(15) # Spacing between logical groups (Patient Info, Report Details)
        content_layout.setContentsMargins(15, 15, 15, 15) 

        # --- Patient Information Section ---
        patient_info_title = self.create_styled_section_title("Patient Information")
        content_layout.addWidget(patient_info_title)
        self.setup_patient_info_fields(content_layout) 

        # --- Report Details Section ---
        report_details_title = self.create_styled_section_title("Report Details")
        content_layout.addWidget(report_details_title) # Add title
        self.setup_report_details_fields(content_layout) # Add fields under this title
        
        content_layout.addSpacing(15) # Space before buttons
        self.setup_buttons_section(content_layout) 

        content_layout.addStretch(1) 

        scroll_area.setWidget(main_content_widget)
        outer_layout.addWidget(scroll_area)

    def create_styled_section_title(self, title_text):
        # Use HTML formatting instead of stylesheet - completely bypasses widget styling system
        html_title = f'''
        <div style="color: #007bff; font-weight: bold; font-size: 12pt; padding-bottom: 5px; margin-bottom: 10px;">
            {title_text}
        </div>
        '''
        title_label = QLabel()
        title_label.setText(html_title)
        title_label.setTextFormat(Qt.RichText)
        
        # Make absolutely sure no frame or background is applied
        title_label.setFrameStyle(0)  # No frame
        title_label.setAutoFillBackground(False)  # Don't fill background
        
        # Explicitly set to be transparent with no border
        title_label.setAttribute(Qt.WA_TranslucentBackground)
        title_label.setStyleSheet("background: transparent; border: none;")
        
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        return title_label

    def _add_field_row(self, target_layout, label_text, widget_to_add):
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10) # Spacing between label and widget
        
        # Use HTML formatting for the label
        html_label = f'''
        <span style="font-weight: bold; color: #333333;">{label_text}</span>
        '''
        
        label = QLabel()
        label.setText(html_label)
        label.setTextFormat(Qt.RichText)
        label.setMinimumWidth(110)
        
        # Remove any possible frame or background
        label.setFrameStyle(0)  # No frame
        label.setAutoFillBackground(False)  # Don't fill background
        label.setAttribute(Qt.WA_TranslucentBackground)
        label.setStyleSheet("background: transparent; border: none;")
        
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred) # Label fixed width, preferred height
        
        row_layout.addWidget(label)
        if isinstance(widget_to_add, list): # For Patient ID + Button
            for w in widget_to_add:
                if isinstance(w, QPushButton):
                    row_layout.addWidget(w)
                else:
                    row_layout.addWidget(w, 1) # Main widget takes stretch
        else:
            row_layout.addWidget(widget_to_add, 1) 
        target_layout.addLayout(row_layout)

    def _reset_combo(self, combo_widget):
        if not combo_widget:
            return
        combo_widget.setCurrentIndex(-1)
        if combo_widget.isEditable():
            combo_widget.setEditText("")

    def _register_combo_with_delete(self, combo_key, combo_widget, history_keys):
        if not hasattr(self, "combo_delete_map"):
            self.combo_delete_map = {}
        self.combo_delete_map[combo_key] = {
            "combo": combo_widget,
            "history_keys": history_keys if isinstance(history_keys, (list, tuple)) else [history_keys],
        }
        self._enable_inline_delete(combo_key, combo_widget)

    def _enable_inline_delete(self, combo_key, combo_widget):
        list_view = ComboListView(combo_widget)
        list_view.delete_clicked.connect(lambda row, key=combo_key: self.handle_delete_from_popup(key, row))
        combo_widget.setView(list_view)
        combo_widget.setItemDelegate(ComboItemDelegate(combo_widget))

    def handle_delete_from_popup(self, combo_key, row_index):
        mapping = getattr(self, "combo_delete_map", {}).get(combo_key)
        if not mapping:
            return
        combo = mapping.get("combo")
        if not combo or row_index < 0 or row_index >= combo.count():
            return
        value = combo.itemText(row_index).strip()
        combo.removeItem(row_index)
        if combo.currentIndex() == row_index:
            self._reset_combo(combo)
        if self.db and value:
            for field_name in mapping.get("history_keys", []):
                try:
                    self.db.delete_dropdown_entry(field_name, value)
                except Exception as e:
                    logging.warning(f"Failed to delete dropdown value '{value}' for {field_name}: {e}")

    def handle_delete_combo_value(self, combo_key):
        mapping = getattr(self, "combo_delete_map", {}).get(combo_key)
        if not mapping:
            return
        combo = mapping.get("combo")
        if not combo:
            return
        current_text = combo.currentText().strip()
        if not current_text:
            return
        # Remove from combo widget
        for idx in range(combo.count()):
            if combo.itemText(idx).strip() == current_text:
                combo.removeItem(idx)
                break
        self._reset_combo(combo)
        # Remove from history table
        if self.db:
            for field_name in mapping.get("history_keys", []):
                try:
                    self.db.delete_dropdown_entry(field_name, current_text)
                except Exception as e:
                    logging.warning(f"Failed to delete dropdown value '{current_text}' for {field_name}: {e}")

    def _populate_combo_with_history(self, combo_widget, history_items):
        """Insert history items at the top of the combo box, keeping order and avoiding duplicates."""
        if not combo_widget or not history_items:
            return
        current_text = combo_widget.currentText()
        existing_values = {combo_widget.itemText(i).strip() for i in range(combo_widget.count())}
        for item in reversed(history_items):
            if not item:
                continue
            normalized = item.strip()
            if not normalized or "\n" in normalized or normalized in existing_values:
                continue
            combo_widget.insertItem(0, item)
            existing_values.add(normalized)
        if current_text:
            combo_widget.setCurrentText(current_text)

    def _extract_history_entries(self, text):
        """Split multiline text into individual entries suitable for history storage."""
        if not text:
            return []
        entries = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = re.match(r"^\d+\.\s*(.*)", line)
            if match:
                line = match.group(1).strip()
            if line:
                entries.append(line)
        return entries

    def _apply_template_to_text_edit(self, text_edit, template_text):
        """Append the selected template into the current line without wiping previous entries."""
        if not text_edit or not template_text:
            return
        template_text = template_text.strip()
        if not template_text:
            return

        current_content = text_edit.toPlainText().strip()
        if not current_content:
            text_edit.setPlainText(template_text)
            return

        cursor = text_edit.textCursor()
        block_text = cursor.block().text()
        prefix_match = re.match(r"^(\d+\.\s*)(.*)", block_text)
        prefix = prefix_match.group(1) if prefix_match else ""

        cursor.beginEditBlock()
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(f"{prefix}{template_text}")
        cursor.endEditBlock()

    def setup_patient_info_fields(self, target_layout): 
        # Hospital (Restored to QComboBox)
        self.hospital_combo = NoScrollComboBox(); self.hospital_combo.setEditable(True); self.hospital_combo.setMinimumWidth(200)
        self.hospital_combo.setPlaceholderText("Select or type hospital...")
        self.hospital_combo.lineEdit().textEdited.connect(lambda text: self.hospital_combo.lineEdit().setText(text.upper()))
        self._reset_combo(self.hospital_combo)
        self._register_combo_with_delete("hospital_name", self.hospital_combo, "hospital_name")
        self._add_field_row(target_layout, "Hospital:", self.hospital_combo)

        # Report Title (Restored to QComboBox, as it had history items)
        self.report_title_combo = NoScrollComboBox(); self.report_title_combo.setEditable(True)
        self.report_title_combo.addItems([
            "ENDOSCOPY REPORT", "UPPER ENDOSCOPY REPORT", "COLONOSCOPY REPORT",
            "GASTROSCOPY REPORT", "SIGMOIDOSCOPY REPORT", "BRONCHOSCOPY REPORT"
        ])
        self._reset_combo(self.report_title_combo)
        self._register_combo_with_delete("report_title", self.report_title_combo, "report_title")
        self._add_field_row(target_layout, "Report Title:", self.report_title_combo)
        
        # Patient ID
        self.patient_id_edit = QLineEdit(); self.patient_id_edit.setPlaceholderText("0000/YY")
        self.generate_id_btn = QPushButton("Auto Generate")
        self.generate_id_btn.clicked.connect(self.generate_patient_id)
        self._add_field_row(target_layout, "Patient ID:", [self.patient_id_edit, self.generate_id_btn])
        
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Patient Full Name")
        self.name_edit.textEdited.connect(lambda text: self.name_edit.setText(text.upper()))
        self._add_field_row(target_layout, "Name:", self.name_edit)

        self.gender_combo = NoScrollComboBox(); self.gender_combo.addItems(["MALE", "FEMALE"])
        self._add_field_row(target_layout, "Gender:", self.gender_combo)
        
        self.age_spin = AgeSpinBox()
        self._add_field_row(target_layout, "Age:", self.age_spin)

        self.referring_doctor_combo = NoScrollComboBox(); self.referring_doctor_combo.setEditable(True) # Restored
        self.referring_doctor_combo.lineEdit().textEdited.connect(lambda text: self.referring_doctor_combo.lineEdit().setText(text.upper()))
        self._reset_combo(self.referring_doctor_combo)
        self._register_combo_with_delete("referring_doctor", self.referring_doctor_combo, "referring_doctor")
        self._add_field_row(target_layout, "Referring Doctor:", self.referring_doctor_combo)

        self.medication_combo = NoScrollComboBox(); self.medication_combo.setEditable(True) # Restored
        self.medication_combo.addItems(["Sedation + Local Spray", "Local Spray Only", "None"])
        self._reset_combo(self.medication_combo)
        self._register_combo_with_delete("medication", self.medication_combo, "medication")
        self._add_field_row(target_layout, "Medication:", self.medication_combo)
        
        self.indication_combo = NoScrollComboBox(); self.indication_combo.setEditable(True)
        self.indication_combo.addItems(["Screening", "Abdominal pain", "Dysphagia", "GERD symptoms", "Gastrointestinal bleeding", "Follow-up examination"])
        self._reset_combo(self.indication_combo)
        self._register_combo_with_delete("indication", self.indication_combo, "indication")
        self._add_field_row(target_layout, "Indication:", self.indication_combo)

        self.doctor_combo = NoScrollComboBox(); self.doctor_combo.setEditable(True) # Restored
        # Connect to text changed signal to convert to uppercase
        self.doctor_combo.lineEdit().textEdited.connect(lambda text: self.doctor_combo.lineEdit().setText(text.upper()))
        self.doctor_combo.lineEdit().setPlaceholderText("DOCTOR NAME (AUTO-CAPITALIZED)")
        self._reset_combo(self.doctor_combo)
        self._register_combo_with_delete("doctor", self.doctor_combo, "doctor")
        self._add_field_row(target_layout, "Doctor:", self.doctor_combo)

        self.designation_combo = NoScrollComboBox(); self.designation_combo.setEditable(True)
        # Convert default items to uppercase
        self.designation_combo.addItems(["SURGEON", "CONSULTANT SURGEON", "SPECIALIST", "RESIDENT"])
        # Connect to text changed signal to convert to uppercase
        self.designation_combo.lineEdit().textEdited.connect(lambda text: self.designation_combo.lineEdit().setText(text.upper()))
        self.designation_combo.lineEdit().setPlaceholderText("DESIGNATION (AUTO-CAPITALIZED)")
        self._reset_combo(self.designation_combo)
        self._register_combo_with_delete("designation", self.designation_combo, "designation")
        self._add_field_row(target_layout, "Designation:", self.designation_combo)
        
        self.date_edit = NoScrollDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self._add_field_row(target_layout, "Date:", self.date_edit)


    def setup_report_details_fields(self, target_layout):
        # Findings (Label then TextEdit)
        html_findings = '''
        <span style="font-weight: bold; color: #333333; margin-top: 5px; margin-bottom: 3px;">Findings:</span>
        '''
        findings_label = QLabel()
        findings_label.setText(html_findings)
        findings_label.setTextFormat(Qt.RichText)
        findings_label.setFrameStyle(0)
        findings_label.setAutoFillBackground(False)
        findings_label.setAttribute(Qt.WA_TranslucentBackground)
        findings_label.setStyleSheet("background: transparent; border: none;")
        findings_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        findings_header_layout = QHBoxLayout()
        findings_header_layout.addWidget(findings_label)
        findings_header_layout.addStretch()
        self.refine_with_ai_btn = QPushButton()
        self.refine_with_ai_btn.setCursor(Qt.PointingHandCursor)
        self.refine_with_ai_btn.setToolTip("Refine with AI")
        self.refine_with_ai_btn.setIcon(QIcon("icons/AI.png"))
        self.refine_with_ai_btn.setIconSize(QSize(28, 28))
        self.refine_with_ai_btn.setFixedSize(36, 36)
        self.refine_with_ai_btn.setStyleSheet(
            """
            QPushButton { border: none; background: transparent; border-radius: 6px; }
            QPushButton:hover { background-color: rgba(255,193,7,0.25); }
            QPushButton:pressed { background-color: rgba(255,193,7,0.4); }
            """
        )
        self.refine_with_ai_btn.clicked.connect(self._emit_refinement_request)
        findings_header_layout.addWidget(self.refine_with_ai_btn, 0, Qt.AlignRight)
        target_layout.addLayout(findings_header_layout)
        # Use regular QTextEdit for Findings (no auto-numbering)
        self.findings_text = QTextEdit()
        self.findings_text.setMinimumHeight(120)
        self.findings_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        target_layout.addWidget(self.findings_text)

        # Conclusions (Label, then ComboBox for templates, then TextEdit)
        conclusions_header_layout = QHBoxLayout()
        
        html_conclusions = '''
        <span style="font-weight: bold; color: #333333; margin-top: 5px;">Conclusions:</span>
        '''
        conclusions_label = QLabel()
        conclusions_label.setText(html_conclusions)
        conclusions_label.setTextFormat(Qt.RichText)
        
        # Remove any possible frame or background
        conclusions_label.setFrameStyle(0)  # No frame
        conclusions_label.setAutoFillBackground(False)  # Don't fill background
        conclusions_label.setAttribute(Qt.WA_TranslucentBackground)
        conclusions_label.setStyleSheet("background: transparent; border: none;")
        
        conclusions_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred) # Fixed width for label
        conclusions_header_layout.addWidget(conclusions_label)
        self.conclusions_combo = NoScrollComboBox(); self.conclusions_combo.setEditable(True); self.conclusions_combo.setMinimumWidth(250)
        self.conclusions_combo.setPlaceholderText("Select or type conclusion template...")
        self._reset_combo(self.conclusions_combo)
        self._register_combo_with_delete(
            "conclusions",
            self.conclusions_combo,
            ["conclusions_template", "conclusions_detail"]
        )
        conclusions_header_layout.addWidget(self.conclusions_combo, 1) # Combo takes stretch
        target_layout.addLayout(conclusions_header_layout)
        self.conclusions_text = AutoNumberTextEdit(); self.conclusions_text.setMinimumHeight(100); self.conclusions_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        target_layout.addWidget(self.conclusions_text)
        self.conclusions_combo.textActivated.connect(self.handle_conclusions_dropdown_selection)


        # Recommendations (Label, then ComboBox for templates, then TextEdit)
        recommendations_header_layout = QHBoxLayout()
        
        html_recommendations = '''
        <span style="font-weight: bold; color: #333333; margin-top: 5px;">Recommendations:</span>
        '''
        recommendations_label = QLabel()
        recommendations_label.setText(html_recommendations)
        recommendations_label.setTextFormat(Qt.RichText)
        
        # Remove any possible frame or background
        recommendations_label.setFrameStyle(0)  # No frame
        recommendations_label.setAutoFillBackground(False)  # Don't fill background
        recommendations_label.setAttribute(Qt.WA_TranslucentBackground)
        recommendations_label.setStyleSheet("background: transparent; border: none;")
        
        recommendations_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred) # Fixed width for label
        recommendations_header_layout.addWidget(recommendations_label)
        self.recommendations_combo = NoScrollComboBox(); self.recommendations_combo.setEditable(True); self.recommendations_combo.setMinimumWidth(250)
        self.recommendations_combo.setPlaceholderText("Select or type recommendation template...")
        self._reset_combo(self.recommendations_combo)
        self._register_combo_with_delete(
            "recommendations",
            self.recommendations_combo,
            ["recommendations_template", "recommendations_detail"]
        )
        recommendations_header_layout.addWidget(self.recommendations_combo, 1)
        target_layout.addLayout(recommendations_header_layout)
        self.recommendations_text = AutoNumberTextEdit(); self.recommendations_text.setMinimumHeight(100); self.recommendations_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        target_layout.addWidget(self.recommendations_text)
        self.recommendations_combo.textActivated.connect(self.handle_recommendations_dropdown_selection)
        
    def setup_buttons_section(self, layout_to_add_to): 
        # ... (same as previous full version) ...
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.save_btn = QPushButton("Save"); self.find_btn = QPushButton("Find Patient"); self.report_btn = QPushButton("Generate Report")
        for btn in [self.save_btn, self.find_btn, self.report_btn]:
            btn.setMinimumHeight(35); btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton { background-color: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px; font-size: 10pt; font-weight: bold; }
                QPushButton:hover { background-color: #0056b3; } QPushButton:pressed { background-color: #004085; }
            """)
            buttons_layout.addWidget(btn)
        buttons_layout.addStretch(1); layout_to_add_to.addLayout(buttons_layout)

        # Connect button signals
        # self.save_btn.clicked.connect(self.save_data) # Assuming a save_data method exists or will be created
        # self.find_btn.clicked.connect(self.find_patient) # Assuming a find_patient method exists or will be created
        self.report_btn.clicked.connect(self.generate_report_requested.emit)

    def setup_auto_apply_connections(self):
        # ... (same as previous full version, ensure all relevant widgets are covered) ...
        line_edits_to_connect = [self.patient_id_edit, self.name_edit] # Only actual QLineEdits for textChanged
        for le in line_edits_to_connect:
            if hasattr(le, 'textChanged'): le.textChanged.connect(self.handle_auto_apply)
        
        combos_to_connect = [self.hospital_combo, self.report_title_combo, self.gender_combo, 
                             self.referring_doctor_combo, self.medication_combo, self.indication_combo,
                             self.doctor_combo, self.designation_combo, 
                             self.conclusions_combo, self.recommendations_combo]
        for combo in combos_to_connect:
            if hasattr(combo, 'currentTextChanged'): combo.currentTextChanged.connect(self.handle_auto_apply)
        
        text_edits_to_connect = [self.findings_text, self.conclusions_text, self.recommendations_text]
        for te in text_edits_to_connect:
            if hasattr(te, 'textChanged'): te.textChanged.connect(self.handle_auto_apply)

        if hasattr(self, 'age_spin'): self.age_spin.valueChanged.connect(self.handle_auto_apply)
        if hasattr(self, 'date_edit'): self.date_edit.dateChanged.connect(self.handle_auto_apply)


    def handle_auto_apply(self):
        try:
            data = self.get_all_data(); self.data_changed.emit(data)
        except Exception as e: logging.error(f"LeftPanel Auto-apply failed: {e}")

    def handle_conclusions_dropdown_selection(self, text):
        # If user selects from dropdown, and the text area isn't already that, update text area.
        # Avoid clearing user's detailed text if they just re-selected the same template.
        self._apply_template_to_text_edit(self.conclusions_text, text)


    def handle_recommendations_dropdown_selection(self, text):
        self._apply_template_to_text_edit(self.recommendations_text, text)

    def _emit_refinement_request(self):
        try:
            payload = self.get_report_data()
        except Exception as exc:  # noqa: BLE001
            logging.error(f"LeftPanel: Failed to gather report data for AI refinement: {exc}")
            return
        self.refinement_requested.emit(payload)


    def save_dropdown_values_to_database(self):
        if not self.db: logging.warning("LeftPanel: DB not set, cannot save dropdown history."); return
        try:
            fields_to_save = {
                "hospital_name": self.hospital_combo.currentText(),
                "report_title": self.report_title_combo.currentText(),
                "referring_doctor": self.referring_doctor_combo.currentText(),
                "medication": self.medication_combo.currentText(),
                "doctor": self.doctor_combo.currentText(),
                "indication": self.indication_combo.currentText(),
                "designation": self.designation_combo.currentText(),
                "conclusions_template": self.conclusions_combo.currentText(), # Save template
                "recommendations_template": self.recommendations_combo.currentText(), # Save template
            }
            for field_name, value in fields_to_save.items():
                if value and value.strip(): 
                    self.db.update_dropdown_history(field_name, value.strip())
                    if field_name == "conclusions_template":
                        self._populate_combo_with_history(self.conclusions_combo, [value.strip()])
                    elif field_name == "recommendations_template":
                        self._populate_combo_with_history(self.recommendations_combo, [value.strip()])
            
            # Also save current detailed text area content to history under a different or same key
            conclusions_entries = self._extract_history_entries(self.conclusions_text.toPlainText())
            for entry in conclusions_entries:
                self.db.update_dropdown_history("conclusions_detail", entry)
            self._populate_combo_with_history(self.conclusions_combo, conclusions_entries)
            
            recommendations_entries = self._extract_history_entries(self.recommendations_text.toPlainText())
            for entry in recommendations_entries:
                self.db.update_dropdown_history("recommendations_detail", entry)
            self._populate_combo_with_history(self.recommendations_combo, recommendations_entries)

            logging.info("LeftPanel: Dropdown/field values (for history) saved to database")
        except Exception as e: logging.error(f"LeftPanel: Failed to save dropdown/field values: {e}")

    def load_dropdown_history(self):
        if not self.db: logging.warning("LeftPanel: DB not set, cannot load dropdown history."); return
        try:
            combo_widgets_for_history = {
                "hospital_name": self.hospital_combo, "report_title": self.report_title_combo,
                "referring_doctor": self.referring_doctor_combo, "medication": self.medication_combo,
                "doctor": self.doctor_combo, "indication": self.indication_combo,
                "designation": self.designation_combo, 
                "conclusions_template": self.conclusions_combo, # Load templates into combo
                "recommendations_template": self.recommendations_combo, # Load templates into combo
            }
            for field_name, combo_widget in combo_widgets_for_history.items():
                history_items = self.db.get_dropdown_history(field_name, 20)
                self._populate_combo_with_history(combo_widget, history_items)

            # Include detailed conclusions and recommendations text in dropdown history
            conclusions_detail_history = self.db.get_dropdown_history("conclusions_detail", 20)
            self._populate_combo_with_history(self.conclusions_combo, conclusions_detail_history)

            recommendations_detail_history = self.db.get_dropdown_history("recommendations_detail", 20)
            self._populate_combo_with_history(self.recommendations_combo, recommendations_detail_history)
            for combo in (self.referring_doctor_combo, self.indication_combo, self.doctor_combo):
                self._reset_combo(combo)
            logging.info("LeftPanel: Dropdown history loaded.")
        except Exception as e: logging.error(f"LeftPanel: Failed to load dropdown history: {e}")

    def get_all_data(self): return {"patient_info": self.get_patient_info(), "report_data": self.get_report_data()}
    
    def get_patient_info(self):
        # Note: Report Title and Indication are now part of Patient Info section visually,
        # so they are collected here. Ensure your data handling (saving, PDF generation)
        # expects them in this patient_info dictionary or adjusts accordingly.
        gender_text = (self.gender_combo.currentText() or "").upper()
        age_text = self.age_spin.text().strip()
        age_value = int(age_text) if age_text.isdigit() else None
        return {
            "hospital_name": self.hospital_combo.currentText().strip(),
            "report_title": self.report_title_combo.currentText(), # As per new layout
            "patient_id": self.patient_id_edit.text(),
            "name": self.name_edit.text().strip(),
            "gender": gender_text if gender_text in {"MALE", "FEMALE"} else "",
            "age": age_value,
            "referring_doctor": self.referring_doctor_combo.currentText().strip(),
            "medication": self.medication_combo.currentText(),
            "indication": self.indication_combo.currentText(), # As per new layout
            "doctor": self.doctor_combo.currentText().strip(),
            "designation": self.designation_combo.currentText(),
            "date": self.date_edit.date().toString("dd/MM/yyyy"), 
        }

    def get_report_data(self): # Now primarily findings, conclusions, recommendations
        return {
            "findings": self.findings_text.toPlainText(), 
            "conclusions": self.conclusions_text.toPlainText(),
            "recommendations": self.recommendations_text.toPlainText(),
        }

    def set_patient_info(self, data):
        if not data: return
        self.hospital_combo.setCurrentText((data.get("hospital_name", "") or "").upper())
        # Report Title and Indication are now part of this method
        self.report_title_combo.setCurrentText(data.get("report_title", "Endoscopy Report"))
        self.indication_combo.setCurrentText(data.get("indication", ""))

        self.patient_id_edit.setText(data.get("patient_id", ""))
        self.name_edit.setText((data.get("name", "") or "").upper())
        gender_value = (data.get("gender", "") or "MALE").upper()
        if gender_value not in {"MALE", "FEMALE"}:
            gender_value = "MALE"
        self.gender_combo.setCurrentText(gender_value)
        try:
            age_val = data.get("age", None)
            if age_val is None or age_val == "":
                self.age_spin.setValue(0)
            else:
                self.age_spin.setValue(int(age_val))
        except (ValueError, TypeError):
            self.age_spin.setValue(0)
        self.referring_doctor_combo.setCurrentText((data.get("referring_doctor", "") or "").upper())
        self.medication_combo.setCurrentText(data.get("medication", ""))
        self.doctor_combo.setCurrentText((data.get("doctor", "") or "").upper())
        self.designation_combo.setCurrentText(data.get("designation", ""))
        try:
            date_val = data.get("date", "") 
            q_date = QDate.fromString(date_val, "dd/MM/yyyy") 
            if not q_date.isValid(): q_date = QDate.fromString(date_val, "yyyy-MM-dd")
            self.date_edit.setDate(q_date if q_date.isValid() else QDate.currentDate())
        except: self.date_edit.setDate(QDate.currentDate())


    def set_report_data(self, data): 
        if not data: return
        # report_title and indication are now handled by set_patient_info
        self.findings_text.setPlainText(data.get("findings", ""))
        
        conclusions_text_val = data.get("conclusions", "")
        self.conclusions_text.setPlainText(conclusions_text_val)
        if self.conclusions_combo.findText(conclusions_text_val, Qt.MatchExactly) != -1:
            self.conclusions_combo.setCurrentText(conclusions_text_val)
        elif conclusions_text_val: # If not in combo, set combo to blank or a generic prompt
             self.conclusions_combo.setCurrentIndex(-1) # Clears selection
             self.conclusions_combo.setEditText("") # Clears editable text

        recommendations_text_val = data.get("recommendations", "")
        self.recommendations_text.setPlainText(recommendations_text_val)
        if self.recommendations_combo.findText(recommendations_text_val, Qt.MatchExactly) != -1:
            self.recommendations_combo.setCurrentText(recommendations_text_val)
        elif recommendations_text_val:
            self.recommendations_combo.setCurrentIndex(-1)
            self.recommendations_combo.setEditText("")


    def clear_all_fields(self):
        self.hospital_combo.setCurrentIndex(-1); self.hospital_combo.setEditText("")
        self.report_title_combo.setCurrentText("Endoscopy Report") # Default for this combo
        self.patient_id_edit.clear(); self.name_edit.clear()
        self.gender_combo.setCurrentIndex(0); self.age_spin.setValue(self.age_spin.minimum())
        self.referring_doctor_combo.setCurrentIndex(-1); self.referring_doctor_combo.setEditText("")
        self.medication_combo.setCurrentIndex(-1); self.medication_combo.setEditText("") # Or set to "None" if that's a default
        self.indication_combo.setCurrentIndex(-1); self.indication_combo.setEditText("")
        self.doctor_combo.setCurrentIndex(-1); self.doctor_combo.setEditText("")
        self.designation_combo.setCurrentIndex(-1); self.designation_combo.setEditText("") # Or set to a default if applicable
        self.date_edit.setDate(QDate.currentDate())
        
        self.findings_text.clear()
        self.conclusions_combo.setCurrentIndex(-1); self.conclusions_combo.setEditText("")
        self.conclusions_text.clear()
        self.recommendations_combo.setCurrentIndex(-1); self.recommendations_combo.setEditText("")
        self.recommendations_text.clear()

    def clear_report_fields(self): 
        # This method might need adjustment based on whether Report Title/Indication are considered "report fields"
        # For now, clearing text areas and their associated combos:
        self.findings_text.clear()
        self.conclusions_combo.setCurrentIndex(-1); self.conclusions_combo.setEditText("")
        self.conclusions_text.clear()
        self.recommendations_combo.setCurrentIndex(-1); self.recommendations_combo.setEditText("")
        self.recommendations_text.clear()

    def generate_patient_id(self):
        """Generate hospital-specific incremental patient ID in format 0001/25"""
        try:
            # Get the current hospital
            current_hospital = self.hospital_combo.currentText()
            
            # Find main window to access settings
            main_window = self.parent() 
            while main_window and not hasattr(main_window, 'settings'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'settings') and main_window.settings:
                # Generate hospital-specific ID
                new_id = main_window.settings.get_next_patient_id(hospital=current_hospital) 
                self.patient_id_edit.setText(new_id)
                logging.info(f"Generated hospital-specific ID: {new_id} for {current_hospital}")
            else: 
                # Fallback ID generation with correct format
                from datetime import datetime
                current_year = datetime.now().strftime("%y")
                fallback_id = f"0001/{current_year}"
                self.patient_id_edit.setText(fallback_id)
                logging.warning("LeftPanel: Could not access settings, using fallback ID.")
        except Exception as e:
            logging.error(f"LeftPanel: Failed to generate patient ID: {e}")
            # Generate a fallback ID in the correct format
            from datetime import datetime
            current_year = datetime.now().strftime("%y")
            fallback_id = f"0001/{current_year}"
            self.patient_id_edit.setText(fallback_id)
