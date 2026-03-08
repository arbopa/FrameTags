from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .directory_scanner import DirectoryScanner
from .exiftool_runner import ExifToolRunner
from .metadata_fields import FIELD_DEFS, FIELD_ORDER
from .metadata_mapper import MetadataMapper
from .metadata_reader import MetadataReader
from .metadata_writer import MetadataWriter
from .models import AppSettings, FileChangeSet, Preset
from .preset_manager import PresetManager
from .preview_engine import PreviewEngine
from .settings_manager import SettingsManager, decode_geometry, encode_geometry


class PreviewWorker(QObject):
    progress = Signal(str, int, int)
    finished = Signal(object, object, int)
    failed = Signal(str)

    def __init__(
        self,
        roots: list[Path],
        recurse: bool,
        selected_fields: dict[str, str],
        write_mode: str,
        exiftool_executable: str,
    ) -> None:
        super().__init__()
        self.roots = roots
        self.recurse = recurse
        self.selected_fields = selected_fields
        self.write_mode = write_mode
        self.exiftool_executable = exiftool_executable

    @Slot()
    def run(self) -> None:
        runner: ExifToolRunner | None = None
        try:
            scanner = DirectoryScanner()
            self.progress.emit("Scanning files", 0, 0)
            files = scanner.scan(self.roots, self.recurse)
            if not files:
                self.finished.emit([], [], 0)
                return

            runner = ExifToolRunner(executable=self.exiftool_executable)
            mapper = MetadataMapper()
            reader = MetadataReader(runner, mapper)
            engine = PreviewEngine(reader, mapper)

            def _on_progress(message: str, done: int, total: int) -> None:
                self.progress.emit(message, done, total)

            changes = engine.build_changes(
                files=files,
                selected_values=self.selected_fields,
                write_mode=self.write_mode,
                include_unchanged=False,
                progress_callback=_on_progress,
            )
            self.finished.emit(changes, engine.last_errors, len(files))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if runner is not None:
                runner.stop()


class ApplyWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(int, int)
    failed = Signal(str)

    def __init__(
        self,
        change_sets: list[FileChangeSet],
        raw_write_preference: str,
        exiftool_executable: str,
    ) -> None:
        super().__init__()
        self.change_sets = change_sets
        self.raw_write_preference = raw_write_preference
        self.exiftool_executable = exiftool_executable

    @Slot()
    def run(self) -> None:
        runner = ExifToolRunner(executable=self.exiftool_executable)
        mapper = MetadataMapper()
        writer = MetadataWriter(runner, mapper)
        try:
            changed_files, changed_actions = writer.apply(
                self.change_sets,
                self.raw_write_preference,
                progress_callback=lambda done, total: self.progress.emit(done, total),
            )
            self.finished.emit(changed_files, changed_actions)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            runner.stop()


class PreviewDialog(QDialog):
    apply_requested = Signal()

    def __init__(self, changes: list[FileChangeSet], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preview Changes")
        if parent is not None:
            parent_size = parent.size()
            self.resize(max(1050, parent_size.width() + 250), max(600, parent_size.height() - 40))
        else:
            self.resize(1150, 720)

        self.changes = changes
        self.applying_active = False

        layout = QVBoxLayout(self)
        self.summary_label = QLabel(self._summary_text())
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["File", "Existing Summary", "Proposed Summary", "Changed Fields"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(3, 95)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Review changes, then apply or cancel.")
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Metadata")
        self.apply_btn.clicked.connect(self.apply_requested.emit)
        button_row.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_btn)
        layout.addLayout(button_row)

        self._populate_table()

    def _summary_text(self) -> str:
        file_count = len(self.changes)
        action_count = sum(len(c.actions) for c in self.changes)
        return f"{file_count} files will be updated ({action_count} metadata changes)"

    @staticmethod
    def _field_display_label(field_key: str) -> str:
        special_labels = {
            "creator_email": "Email",
            "creator_website": "Website",
            "caption": "Caption",
            "keywords": "Keywords",
        }
        if field_key in special_labels:
            return special_labels[field_key]
        return FIELD_DEFS[field_key].label

    @staticmethod
    def _display_value(value: object) -> str:
        if value is None:
            return "-"
        if isinstance(value, list):
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            return ", ".join(cleaned) if cleaned else "-"
        text = str(value).strip()
        return text if text else "-"

    def _format_summary(self, actions, proposed: bool) -> str:
        parts: list[str] = []
        for action in actions:
            label = self._field_display_label(action.field)
            raw_value = action.to_value if proposed else action.from_value
            parts.append(f"{label}: {self._display_value(raw_value)}")
        return "; ".join(parts)

    def _populate_table(self) -> None:
        self.table.setRowCount(0)
        for change in self.changes:
            row = self.table.rowCount()
            self.table.insertRow(row)

            existing_summary = self._format_summary(change.actions, proposed=False)
            proposed_summary = self._format_summary(change.actions, proposed=True)

            file_item = QTableWidgetItem(Path(change.file_path).name)
            file_item.setToolTip(str(change.file_path))
            existing_item = QTableWidgetItem(existing_summary)
            existing_item.setToolTip(existing_summary)
            proposed_item = QTableWidgetItem(proposed_summary)
            proposed_item.setToolTip(proposed_summary)
            changed_item = QTableWidgetItem(str(change.changed_field_count))

            self.table.setItem(row, 0, file_item)
            self.table.setItem(row, 1, existing_item)
            self.table.setItem(row, 2, proposed_item)
            self.table.setItem(row, 3, changed_item)

        self.table.setSortingEnabled(True)

    def set_applying(self, running: bool) -> None:
        self.applying_active = running
        self.apply_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(not running)
        self.table.setEnabled(not running)
        if running:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Applying metadata...")
        else:
            self.progress_bar.setRange(0, 100)

    def reject(self) -> None:  # type: ignore[override]
        if self.applying_active:
            return
        super().reject()


class MainWindow(QMainWindow):
    def __init__(
        self,
        project_root: Path,
        exiftool_runner: ExifToolRunner,
        preset_manager: PresetManager,
        settings_manager: SettingsManager,
    ) -> None:
        super().__init__()
        self.setWindowTitle("FrameTags \u2014 Batch Metadata Editor")

        self.project_root = project_root
        self.exiftool_runner = exiftool_runner
        self.preset_manager = preset_manager
        self.settings_manager = settings_manager

        self.settings = self.settings_manager.load()
        self.current_changes: list[FileChangeSet] = []

        self.preview_thread: QThread | None = None
        self.preview_worker: PreviewWorker | None = None
        self.apply_thread: QThread | None = None
        self.apply_worker: ApplyWorker | None = None
        self.active_preview_dialog: PreviewDialog | None = None

        self.field_checks: dict[str, QCheckBox] = {}
        self.field_inputs: dict[str, QWidget] = {}

        self._build_ui()
        self._build_menu()
        self._load_presets()
        self._restore_settings()
        self._update_preview_enabled()

    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About FrameTags", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About FrameTags",
            "FrameTags\n"
            "Batch metadata editor for photographers\n"
            "Copyright (c) Cameratrician Studios",
        )
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        directory_box = self._build_directory_section()
        preset_box = self._build_preset_section()
        fields_box = self._build_fields_section()
        write_box = self._build_write_section()
        preview_box = self._build_preview_section()
        execution_box = self._build_execution_section()

        fields_box.setMaximumHeight(560)

        root_layout.addWidget(directory_box, 0)
        root_layout.addWidget(preset_box, 0)
        root_layout.addWidget(fields_box, 3)
        root_layout.addWidget(write_box, 0)
        root_layout.addWidget(preview_box, 0)
        root_layout.addWidget(execution_box, 0)

    def _build_directory_section(self) -> QWidget:
        box = QGroupBox("1. Directory Selection")
        layout = QVBoxLayout(box)

        self.dir_list = QListWidget()
        layout.addWidget(self.dir_list)

        row = QHBoxLayout()
        add_btn = QPushButton("Add Directory")
        add_btn.clicked.connect(self._add_directory)
        row.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected Directory")
        remove_btn.clicked.connect(self._remove_directory)
        row.addWidget(remove_btn)
        layout.addLayout(row)

        self.recurse_checkbox = QCheckBox("Process subdirectories")
        self.recurse_checkbox.setChecked(True)
        layout.addWidget(self.recurse_checkbox)

        return box

    def _build_preset_section(self) -> QWidget:
        box = QGroupBox("2. Preset Controls")
        layout = QHBoxLayout(box)

        self.preset_combo = QComboBox()
        layout.addWidget(self.preset_combo)

        load_btn = QPushButton("Load Preset")
        load_btn.clicked.connect(self._load_selected_preset)
        layout.addWidget(load_btn)

        save_btn = QPushButton("Save New Preset")
        save_btn.clicked.connect(self._save_new_preset)
        layout.addWidget(save_btn)

        update_btn = QPushButton("Update Preset")
        update_btn.clicked.connect(self._update_preset)
        layout.addWidget(update_btn)

        delete_btn = QPushButton("Delete Preset")
        delete_btn.clicked.connect(self._delete_preset)
        layout.addWidget(delete_btn)

        return box

    def _build_fields_section(self) -> QWidget:
        box = QGroupBox("3. Metadata Field Editor")
        grid = QGridLayout(box)

        row = 0
        for key in FIELD_ORDER:
            field_def = FIELD_DEFS[key]
            check = QCheckBox()
            check.toggled.connect(self._update_preview_enabled)
            label = QLabel(field_def.label)
            if field_def.multiline:
                input_widget = QPlainTextEdit()
                input_widget.setMaximumHeight(70)
            else:
                input_widget = QLineEdit()

            self.field_checks[key] = check
            self.field_inputs[key] = input_widget

            grid.addWidget(check, row, 0)
            grid.addWidget(label, row, 1)
            grid.addWidget(input_widget, row, 2)
            row += 1

        grid.setColumnStretch(2, 1)
        return box

    def _build_write_section(self) -> QWidget:
        box = QGroupBox("4. Write Behavior")
        layout = QVBoxLayout(box)

        self.write_overwrite = QRadioButton("Overwrite existing metadata")
        self.write_overwrite.setChecked(True)
        layout.addWidget(self.write_overwrite)

        self.write_if_empty = QRadioButton("Only write if empty")
        layout.addWidget(self.write_if_empty)

        self.append_keywords = QCheckBox("For Keywords: append instead of replace")
        self.append_keywords.setChecked(False)
        layout.addWidget(self.append_keywords)

        self.raw_sidecar = QCheckBox("For RAW files: prefer sidecar when possible")
        self.raw_sidecar.setChecked(True)
        layout.addWidget(self.raw_sidecar)

        return box

    def _build_preview_section(self) -> QWidget:
        box = QGroupBox("5. Preview")
        layout = QVBoxLayout(box)
        hint = QLabel("Preview results open in a separate window with Apply Metadata and Cancel.")
        layout.addWidget(hint)
        return box

    def _build_execution_section(self) -> QWidget:
        box = QGroupBox("6. Execution")
        layout = QVBoxLayout(box)

        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self._preview_changes)
        layout.addWidget(self.preview_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Select fields, then preview.")
        layout.addWidget(self.status_label)

        return box

    def _has_checked_fields(self) -> bool:
        return any(check.isChecked() for check in self.field_checks.values())

    def _update_preview_enabled(self) -> None:
        running_preview = self.preview_thread is not None and self.preview_thread.isRunning()
        self.preview_btn.setEnabled(self._has_checked_fields() and not running_preview)

    def _add_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select directory")
        if not folder:
            return
        existing = {self.dir_list.item(i).text() for i in range(self.dir_list.count())}
        if folder in existing:
            return
        self.dir_list.addItem(QListWidgetItem(folder))

    def _remove_directory(self) -> None:
        row = self.dir_list.currentRow()
        if row >= 0:
            self.dir_list.takeItem(row)

    def _selected_roots(self) -> list[Path]:
        roots: list[Path] = []
        for i in range(self.dir_list.count()):
            roots.append(Path(self.dir_list.item(i).text()))
        return roots

    def _selected_field_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key in FIELD_ORDER:
            if not self.field_checks[key].isChecked():
                continue
            widget = self.field_inputs[key]
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
            else:
                value = widget.toPlainText().strip()
            if value:
                values[key] = value
        return values

    def _validate_gps(self, selected_fields: dict[str, str]) -> bool:
        for field_key, min_val, max_val in (
            ("gps_latitude", -90.0, 90.0),
            ("gps_longitude", -180.0, 180.0),
        ):
            if field_key not in selected_fields:
                continue
            value = selected_fields[field_key]
            try:
                numeric = float(value)
            except ValueError:
                QMessageBox.warning(self, "Invalid GPS", f"{FIELD_DEFS[field_key].label} must be a decimal number.")
                return False
            if numeric < min_val or numeric > max_val:
                QMessageBox.warning(
                    self,
                    "Invalid GPS",
                    f"{FIELD_DEFS[field_key].label} must be between {min_val} and {max_val}.",
                )
                return False
        return True

    def _current_write_mode(self) -> str:
        if self.write_if_empty.isChecked():
            return "write_if_empty"
        if self.append_keywords.isChecked():
            return "append_keywords"
        return "overwrite"

    def _preview_changes(self) -> None:
        if self.preview_thread is not None and self.preview_thread.isRunning():
            return
        if not self._has_checked_fields():
            QMessageBox.information(self, "No Fields Selected", "Select at least one metadata field to apply.")
            return
        if not self.exiftool_runner.is_available():
            QMessageBox.critical(
                self,
                "ExifTool Missing",
                "ExifTool or PyExifTool is not available. Install dependencies and ensure ExifTool is available.",
            )
            return

        roots = self._selected_roots()
        if not roots:
            QMessageBox.warning(self, "No Directories", "Please add at least one directory.")
            return

        selected_fields = self._selected_field_values()
        if not selected_fields:
            QMessageBox.warning(self, "No Field Values", "Select at least one metadata field to apply.")
            return

        if not self._validate_gps(selected_fields):
            return

        self.current_changes = []
        self._update_preview_enabled()
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Starting preview worker...")

        self.preview_thread = QThread(self)
        self.preview_worker = PreviewWorker(
            roots=roots,
            recurse=self.recurse_checkbox.isChecked(),
            selected_fields=selected_fields,
            write_mode=self._current_write_mode(),
            exiftool_executable=self.exiftool_runner.executable,
        )
        self.preview_worker.moveToThread(self.preview_thread)

        self.preview_thread.started.connect(self.preview_worker.run)
        self.preview_worker.progress.connect(self._on_preview_progress)
        self.preview_worker.finished.connect(self._on_preview_finished)
        self.preview_worker.failed.connect(self._on_preview_failed)

        self.preview_worker.finished.connect(self.preview_thread.quit)
        self.preview_worker.failed.connect(self.preview_thread.quit)
        self.preview_thread.finished.connect(self._cleanup_preview_worker)

        self.preview_thread.start()

    @Slot(str, int, int)
    def _on_preview_progress(self, message: str, done: int, total: int) -> None:
        self.status_label.setText(f"{message}... ({done}/{total})" if total > 0 else f"{message}...")
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(done, total))
        else:
            self.progress_bar.setRange(0, 0)

    @Slot(object, object, int)
    def _on_preview_finished(self, changes_obj: object, errors_obj: object, scanned_total: int) -> None:
        changes = changes_obj if isinstance(changes_obj, list) else []
        errors = errors_obj if isinstance(errors_obj, list) else []

        self.current_changes = [c for c in changes if isinstance(c, FileChangeSet) and c.actions]

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        file_count = len(self.current_changes)
        action_count = sum(len(c.actions) for c in self.current_changes)
        error_count = len(errors)

        if scanned_total == 0:
            self.status_label.setText("No supported image files found.")
            return

        if error_count:
            self.status_label.setText(
                f"Preview ready: {file_count} file(s), {action_count} field updates, {error_count} read error(s)."
            )
            QMessageBox.warning(
                self,
                "Preview Warnings",
                f"Preview completed with {error_count} read error(s).",
            )
        else:
            self.status_label.setText(
                f"Preview ready: {file_count} file(s), {action_count} field updates."
            )

        if self.current_changes:
            self._open_preview_dialog()
        else:
            QMessageBox.information(self, "No Changes", "No files would be changed with current selections.")

    def _open_preview_dialog(self) -> None:
        dialog = PreviewDialog(self.current_changes, self)
        dialog.apply_requested.connect(self._apply_from_active_dialog)
        self.active_preview_dialog = dialog
        dialog.exec()
        self.active_preview_dialog = None

    def _apply_from_active_dialog(self) -> None:
        if self.active_preview_dialog is None:
            return
        self._apply_from_dialog(self.active_preview_dialog)

    def _apply_from_dialog(self, dialog: PreviewDialog) -> None:
        if self.apply_thread is not None and self.apply_thread.isRunning():
            return
        if not self.current_changes:
            QMessageBox.information(self, "No Preview", "Run preview first.")
            return

        dialog.set_applying(True)

        self.apply_thread = QThread(self)
        self.apply_worker = ApplyWorker(
            change_sets=self.current_changes,
            raw_write_preference=("prefer_sidecar" if self.raw_sidecar.isChecked() else "direct_when_supported"),
            exiftool_executable=self.exiftool_runner.executable,
        )
        self.apply_worker.moveToThread(self.apply_thread)

        self.apply_thread.started.connect(self.apply_worker.run)
        self.apply_worker.progress.connect(self._on_apply_progress)
        self.apply_worker.finished.connect(self._on_apply_finished)
        self.apply_worker.failed.connect(self._on_apply_failed)

        self.apply_worker.finished.connect(self.apply_thread.quit)
        self.apply_worker.failed.connect(self.apply_thread.quit)
        self.apply_thread.finished.connect(self._cleanup_apply_worker)

        self.apply_thread.start()

    @Slot(int, int)
    def _on_apply_progress(self, done: int, total: int) -> None:
        dialog = self.active_preview_dialog
        if dialog is None:
            return
        if total > 0:
            percent = int((done / total) * 100)
            dialog.progress_bar.setRange(0, total)
            dialog.progress_bar.setValue(done)
            dialog.status_label.setText(f"Applying metadata... {percent}%")
        else:
            dialog.progress_bar.setRange(0, 0)
            dialog.status_label.setText("Applying metadata...")

    @Slot(int, int)
    def _on_apply_finished(self, changed_files: int, changed_actions: int) -> None:
        dialog = self.active_preview_dialog
        if dialog is None:
            return

        dialog.set_applying(False)
        dialog.progress_bar.setRange(0, 100)
        dialog.progress_bar.setValue(100)
        dialog.status_label.setText(
            f"Apply complete: {changed_files} file(s), {changed_actions} field updates."
        )

        QMessageBox.information(
            self,
            "Completed",
            f"Metadata applied to {changed_files} files ({changed_actions} metadata changes).",
        )
        dialog.accept()

    @Slot(str)
    def _on_apply_failed(self, message: str) -> None:
        dialog = self.active_preview_dialog
        if dialog is not None:
            dialog.set_applying(False)
            dialog.progress_bar.setRange(0, 100)
            dialog.progress_bar.setValue(0)
            dialog.status_label.setText("Apply failed.")
        QMessageBox.critical(self, "Apply Failed", message)

    @Slot(str)
    def _on_preview_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preview failed.")
        QMessageBox.critical(self, "Preview Failed", message)

    @Slot()
    def _cleanup_preview_worker(self) -> None:
        if self.preview_worker is not None:
            self.preview_worker.deleteLater()
            self.preview_worker = None
        if self.preview_thread is not None:
            self.preview_thread.deleteLater()
            self.preview_thread = None
        self._update_preview_enabled()

    @Slot()
    def _cleanup_apply_worker(self) -> None:
        if self.apply_worker is not None:
            self.apply_worker.deleteLater()
            self.apply_worker = None
        if self.apply_thread is not None:
            self.apply_thread.deleteLater()
            self.apply_thread = None

    def _collect_preset_fields(self) -> dict[str, str]:
        values = self._selected_field_values()
        return {k: v for k, v in values.items() if v.strip()}

    def _load_presets(self) -> None:
        self.preset_combo.clear()
        self.preset_combo.addItem("")
        for preset in self.preset_manager.list_presets():
            self.preset_combo.addItem(preset.name)

    def _load_selected_preset(self) -> None:
        name = self.preset_combo.currentText().strip()
        if not name:
            return
        presets = {p.name: p for p in self.preset_manager.list_presets()}
        preset = presets.get(name)
        if not preset:
            return

        for key in FIELD_ORDER:
            self.field_checks[key].setChecked(False)
            widget = self.field_inputs[key]
            if isinstance(widget, QLineEdit):
                widget.setText("")
            else:
                widget.setPlainText("")

        for key, value in preset.fields.items():
            if key not in self.field_inputs:
                continue
            self.field_checks[key].setChecked(True)
            widget = self.field_inputs[key]
            if isinstance(widget, QLineEdit):
                widget.setText(value)
            else:
                widget.setPlainText(value)

        self._update_preview_enabled()

    def _save_new_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save New Preset", "Preset name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Preset name is required.")
            return

        fields = self._collect_preset_fields()
        if not fields:
            QMessageBox.warning(self, "No Values", "No non-empty selected fields to save.")
            return

        self.preset_manager.save_new(Preset(name=name, fields=fields))
        self._load_presets()
        self.preset_combo.setCurrentText(name)

    def _update_preset(self) -> None:
        name = self.preset_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Select Preset", "Select a preset to update.")
            return

        fields = self._collect_preset_fields()
        self.preset_manager.update(Preset(name=name, fields=fields))
        self._load_presets()
        self.preset_combo.setCurrentText(name)

    def _delete_preset(self) -> None:
        name = self.preset_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Select Preset", "Select a preset to delete.")
            return
        answer = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.preset_manager.delete(name)
        self._load_presets()

    def _restore_settings(self) -> None:
        settings = self.settings

        for path in settings.last_used_directories:
            if Path(path).exists():
                self.dir_list.addItem(path)

        self.recurse_checkbox.setChecked(settings.recurse)
        if settings.write_mode == "write_if_empty":
            self.write_if_empty.setChecked(True)
        else:
            self.write_overwrite.setChecked(True)

        self.append_keywords.setChecked(settings.write_mode == "append_keywords")
        self.raw_sidecar.setChecked(settings.raw_write_preference == "prefer_sidecar")
        self.preset_combo.setCurrentText(settings.last_selected_preset)

        if settings.window_geometry:
            try:
                self.restoreGeometry(decode_geometry(settings.window_geometry))
            except Exception:
                pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.preview_thread is not None and self.preview_thread.isRunning():
            self.preview_thread.quit()
            self.preview_thread.wait(2000)
        if self.apply_thread is not None and self.apply_thread.isRunning():
            self.apply_thread.quit()
            self.apply_thread.wait(2000)

        settings = AppSettings(
            last_selected_preset=self.preset_combo.currentText().strip(),
            last_used_directories=[
                self.dir_list.item(i).text() for i in range(self.dir_list.count())
            ],
            recurse=self.recurse_checkbox.isChecked(),
            write_mode=self._current_write_mode(),
            raw_write_preference=("prefer_sidecar" if self.raw_sidecar.isChecked() else "direct_when_supported"),
            window_geometry=encode_geometry(bytes(self.saveGeometry())),
        )
        self.settings_manager.save(settings)
        self.exiftool_runner.stop()
        super().closeEvent(event)
