from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLineEdit, QLabel, QTableWidget,
    QTableWidgetItem, QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView


class FileListWidget(QListWidget):
    """Custom QListWidget with Finder-style shift-click range selection."""
    
    def __init__(self):
        super().__init__()
        self.last_clicked_index = -1
        self.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
    
    def mousePressEvent(self, event):
        """Handle mouse click with shift-click range selection support."""
        index = self.row(self.itemAt(event.pos()))
        
        if index == -1:
            # Clicked on empty space
            super().mousePressEvent(event)
            return
        
        item = self.item(index)
        
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Shift-click: select range between last clicked and current
            if self.last_clicked_index >= 0:
                start = min(self.last_clicked_index, index)
                end = max(self.last_clicked_index, index)
                
                # Select all items in range
                for i in range(start, end + 1):
                    self.item(i).setSelected(True)
            else:
                # No previous selection, just select this item
                item.setSelected(True)
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Cmd/Ctrl-click: toggle selection (standard multi-select)
            item.setSelected(not item.isSelected())
        else:
            # Regular click: select only this item
            self.clearSelection()
            item.setSelected(True)
        
        self.last_clicked_index = index


class MainUI(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
        main_layout.setSpacing(5)  # Minimal spacing

        # --- TOP BAR ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)  # No margins
        top_bar.setSpacing(5)  # Minimal spacing

        self.btn_folder = QPushButton("Open Folder")
        self.btn_folder.setMaximumHeight(28)
        self.mz_input = QLineEdit("172.1332")
        self.mz_input.setMaximumHeight(28)
        self.run_btn = QPushButton("Run")
        self.run_btn.setMaximumHeight(28)
        self.status_label = QLabel("Ready")

        top_bar.addWidget(self.btn_folder)
        top_bar.addWidget(QLabel("m/z:"))
        top_bar.addWidget(self.mz_input)
        top_bar.addWidget(self.run_btn)
        top_bar.addWidget(self.status_label)

        # Create container for top bar with strict height
        top_bar_widget = QWidget()
        top_bar_widget.setLayout(top_bar)
        top_bar_widget.setMaximumHeight(38)
        main_layout.addWidget(top_bar_widget, 0)  # Don't expand vertically

        # --- MAIN SPLIT (LEFT / RIGHT) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # -------- LEFT PANEL --------
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(0, 0, 0, 0)  # No margins
        left_panel.setSpacing(3)  # Minimal spacing

        self.file_list = FileListWidget()
        left_panel.addWidget(QLabel("Files (select one or more)"))
        left_panel.addWidget(self.file_list)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)

        # -------- RIGHT PANEL --------
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)  # No margins
        right_panel.setSpacing(3)  # Minimal spacing

        # Tabs for different plots - take most of the space
        self.plot_tabs = QTabWidget()
        right_panel.addWidget(self.plot_tabs, 1)  # Stretch to fill space
        
        # Tab 1: TIC
        self.browser_tic = QWebEngineView()
        self.plot_tabs.addTab(self.browser_tic, "TIC")
        
        # Tab 2: EIC
        self.browser_eic = QWebEngineView()
        self.plot_tabs.addTab(self.browser_eic, "EIC")
        
        # Tab 3: Area Comparison
        self.browser_areas = QWebEngineView()
        self.plot_tabs.addTab(self.browser_areas, "Peak Areas")

        # Table peaks - compact at bottom
        self.peak_table = QTableWidget()
        self.peak_table.setColumnCount(3)
        self.peak_table.setHorizontalHeaderLabels(["File", "RT", "Area"])
        self.peak_table.setMaximumHeight(150)  # Fixed small height
        
        right_panel.addWidget(self.peak_table, 0)  # Don't stretch

        right_widget = QWidget()
        right_widget.setLayout(right_panel)

        # Add to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.setSizes([300, 1000])

        main_layout.addWidget(splitter)