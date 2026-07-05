
from pathlib import Path
import os
import subprocess
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFileDialog, QProgressBar, QMessageBox,
    QLineEdit, QFrame
)

try:
    from licitasuite.engine.pipeline import Pipeline
except Exception:
    Pipeline = None


APP_NAME = "LicitaSuite 6.1 Professional"
APP_SUBTITLE = "Gerador de Atas de Registro de Preços"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_zip = None
        self.setWindowTitle(f"{APP_NAME} — {APP_SUBTITLE}")
        self.setMinimumSize(980, 720)

        icon_path = Path("assets") / "LicitaSuite.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_menu()
        self._build_ui()
        self._apply_style()

    def _build_menu(self):
        menu_file = self.menuBar().addMenu("Arquivo")

        act_open_zip = QAction("Abrir Processo ZIP", self)
        act_open_zip.triggered.connect(self.select_zip)
        menu_file.addAction(act_open_zip)

        act_open_output = QAction("Abrir pasta das atas", self)
        act_open_output.triggered.connect(self.open_output_folder)
        menu_file.addAction(act_open_output)

        menu_file.addSeparator()

        act_exit = QAction("Sair", self)
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        menu_tools = self.menuBar().addMenu("Ferramentas")

        act_output = QAction("Abrir pasta Output", self)
        act_output.triggered.connect(lambda: self.open_folder(Path("output")))
        menu_tools.addAction(act_output)

        act_temp = QAction("Limpar pasta Temp", self)
        act_temp.triggered.connect(lambda: self.clear_folder(Path("temp")))
        menu_tools.addAction(act_temp)

        act_logs = QAction("Limpar Logs", self)
        act_logs.triggered.connect(lambda: self.clear_folder(Path("logs")))
        menu_tools.addAction(act_logs)

        menu_help = self.menuBar().addMenu("Ajuda")

        act_manual = QAction("Manual", self)
        act_manual.triggered.connect(self.show_manual_hint)
        menu_help.addAction(act_manual)

        act_about = QAction("Sobre", self)
        act_about.triggered.connect(self.show_about)
        menu_help.addAction(act_about)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)

        root.addWidget(self._header())
        root.addWidget(self._process_card())

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.btn_generate = QPushButton("⚙️  GERAR ATAS")
        self.btn_generate.setObjectName("primaryButton")
        self.btn_generate.setMinimumHeight(44)
        self.btn_generate.setMinimumWidth(240)
        self.btn_generate.clicked.connect(self.generate_atas)
        action_row.addWidget(self.btn_generate)
        action_row.addStretch()
        root.addLayout(action_row)

        log_label = QLabel("PROCESSAMENTO")
        log_label.setObjectName("sectionTitle")
        root.addWidget(log_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("As mensagens do processamento aparecerão aqui.")
        self.log.setObjectName("logBox")
        root.addWidget(self.log, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        root.addWidget(self.progress)

        footer = QLabel("LicitaSuite 6.1 Professional • Engine LTS • © 2026")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

    def _header(self):
        frame = QFrame()
        frame.setObjectName("header")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel(APP_NAME)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return frame

    def _process_card(self):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        label = QLabel("📂 Processo (.ZIP)")
        label.setObjectName("fieldLabel")
        layout.addWidget(label)

        row = QHBoxLayout()
        self.zip_input = QLineEdit()
        self.zip_input.setReadOnly(True)
        self.zip_input.setPlaceholderText("Selecione o arquivo ZIP do processo...")
        self.zip_input.setMinimumHeight(36)

        self.btn_select = QPushButton("Procurar")
        self.btn_select.setMinimumHeight(36)
        self.btn_select.clicked.connect(self.select_zip)

        row.addWidget(self.zip_input, 1)
        row.addWidget(self.btn_select)
        layout.addLayout(row)
        return frame

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #f4f6f9; font-family: Segoe UI, Arial; font-size: 10pt; }
            QMenuBar { background: #ffffff; border-bottom: 1px solid #d9e1ec; padding: 4px; }
            QMenuBar::item { padding: 6px 10px; background: transparent; }
            QMenuBar::item:selected { background: #eaf1fb; border-radius: 4px; }
            QMenu { background: #ffffff; border: 1px solid #d9e1ec; }
            QMenu::item { padding: 6px 22px; }
            QMenu::item:selected { background: #eaf1fb; }
            QFrame#header { background: #ffffff; border: 1px solid #d9e1ec; border-radius: 12px; }
            QLabel#title { color: #1f5494; font-size: 20pt; font-weight: 700; }
            QLabel#subtitle { color: #334155; font-size: 12pt; font-weight: 500; }
            QFrame#card { background: #ffffff; border: 1px solid #d9e1ec; border-radius: 12px; }
            QLabel#fieldLabel { color: #1f2937; font-weight: 600; }
            QLabel#sectionTitle { color: #1f5494; font-weight: 700; letter-spacing: 1px; }
            QLineEdit { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 6px 10px; }
            QPushButton { background: #eef4fb; color: #1f2937; border: 1px solid #c7d7ea; border-radius: 8px; padding: 8px 14px; font-weight: 600; }
            QPushButton:hover { background: #dceafe; }
            QPushButton#primaryButton { background: #1f5494; color: white; border: 1px solid #1f5494; border-radius: 10px; font-size: 11pt; font-weight: 700; }
            QPushButton#primaryButton:hover { background: #174273; }
            QTextEdit#logBox { background: #ffffff; color: #0f172a; border: 1px solid #d9e1ec; border-radius: 12px; padding: 10px; font-family: Consolas, Segoe UI, monospace; font-size: 10pt; }
            QProgressBar { background: #e5e7eb; border: 1px solid #cbd5e1; border-radius: 8px; height: 20px; text-align: center; font-weight: 600; }
            QProgressBar::chunk { background: #1f5494; border-radius: 8px; }
            QLabel#footer { color: #64748b; font-size: 9pt; }
        """)

    def select_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar ZIP do processo", "", "Arquivos ZIP (*.zip)")
        if path:
            self.selected_zip = Path(path)
            self.zip_input.setText(str(self.selected_zip))
            self.append_log(f"✓ ZIP selecionado: {self.selected_zip}")

    def generate_atas(self):
        if not self.selected_zip:
            QMessageBox.warning(self, "LicitaSuite", "Selecione primeiro o ZIP do processo.")
            return

        self.progress.setValue(5)
        self.log.clear()
        self.append_log("✓ Iniciando processamento...")
        self.append_log(f"✓ ZIP selecionado: {self.selected_zip}")
        QApplication.processEvents()

        try:
            if Pipeline is None:
                raise RuntimeError("Pipeline do LicitaSuite não foi carregado.")

            self.progress.setValue(15)
            self.append_log("✓ Carregando motor do LicitaSuite...")
            QApplication.processEvents()

            pipeline = Pipeline()
            self.progress.setValue(25)
            self.append_log("✓ Executando geração das atas...")
            QApplication.processEvents()

            self._run_pipeline(pipeline)

            self.progress.setValue(100)
            self.append_log("")
            self.append_log("✔ Processo concluído com sucesso.")
            self.append_log("✓ As atas foram geradas na pasta output.")

            answer = QMessageBox.question(
                self,
                "Processo concluído",
                "✔ Processo concluído com sucesso.\n\nDeseja abrir a pasta de destino?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                self.open_output_folder()

        except Exception as exc:
            self.progress.setValue(0)
            self.append_log("")
            self.append_log("✗ Erro durante o processamento.")
            self.append_log(str(exc))
            self.append_log(traceback.format_exc())
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro:\n\n{exc}")

    def _run_pipeline(self, pipeline):
        zip_path = str(self.selected_zip)
        if hasattr(pipeline, "run"):
            return pipeline.run(zip_path)
        if hasattr(pipeline, "execute"):
            return pipeline.execute(zip_path)
        if hasattr(pipeline, "process"):
            return pipeline.process(zip_path)
        raise RuntimeError("Não encontrei método run/execute/process no Pipeline.")

    def append_log(self, message):
        self.log.append(message)
        self.log.ensureCursorVisible()

    def open_output_folder(self):
        for folder in [Path("output") / "atas_geradas", Path("output")]:
            if folder.exists():
                self.open_folder(folder)
                return
        QMessageBox.information(self, "LicitaSuite", "A pasta output ainda não foi criada.")

    def open_folder(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder.resolve()))
        except Exception:
            subprocess.Popen(["explorer", str(folder.resolve())])

    def clear_folder(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        for item in folder.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil
                    shutil.rmtree(item)
            except Exception:
                pass
        QMessageBox.information(self, "LicitaSuite", f"Pasta limpa:\n{folder}")

    def show_manual_hint(self):
        manual = Path("docs")
        if manual.exists():
            self.open_folder(manual)
        else:
            QMessageBox.information(self, "Manual", "A pasta docs não foi localizada.")

    def show_about(self):
        QMessageBox.information(
            self,
            "Sobre o LicitaSuite",
            "LicitaSuite 6.1 Professional\n\n"
            "Gerador de Atas de Registro de Preços\n\n"
            "Versão: 6.1 Professional LTS\n"
            "Engine: LicitaSuite Engine\n\n"
            "Projeto: Januaria Marilia Campos de Medeiros\n"
            "Assistência técnica: OpenAI ChatGPT\n\n"
            "© 2026"
        )


def create_app():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app, window


def run():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


def start_app():
    run()
