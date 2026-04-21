import sys, os
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QTableWidgetItem
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from ui import MainUI
from ms_engine import extract_tic, extract_eic, pick_peaks, integrate_peaks, clear_cache


class OrbitrapApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Orbitrap Mass Spectrometry Analyzer")
        self.resize(1800, 1000)

        self.ui = MainUI()
        self.setCentralWidget(self.ui)

        # Set default folder to qc-mzml-files
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.folder = os.path.join(script_dir, "qc-mzml-files")
        
        # Load files from default folder
        self.load_folder_files()

        # --- connections ---
        self.ui.btn_folder.clicked.connect(self.open_folder)
        self.ui.run_btn.clicked.connect(self.run_analysis)

    def open_folder(self):
        self.folder = QFileDialog.getExistingDirectory(self, "Select folder")
        self.load_folder_files()

    def load_folder_files(self):
        """Load .mzML files from the current folder into the file list."""
        self.ui.file_list.clear()
        
        if not self.folder or not os.path.isdir(self.folder):
            self.ui.status_label.setText("Error: Folder not found")
            return

        for f in os.listdir(self.folder):
            if f.endswith(".mzML") and "QC_mapp" in f:
                self.ui.file_list.addItem(f)

    def run_analysis(self):
        clear_cache()  # Clear cache to start fresh
        
        if not self.folder:
            self.ui.status_label.setText("Error: No folder selected")
            print("No folder selected")
            return

        # Get selected files
        selected_items = self.ui.file_list.selectedItems()
        if not selected_items:
            self.ui.status_label.setText("Error: No files selected")
            print("No files selected. Please select one or more files (Cmd+click on macOS).")
            return
        
        files = [item.text() for item in selected_items]
        print(f"Processing {len(files)} selected file(s): {files}")
        self.ui.status_label.setText(f"Processing {len(files)} files...")

        # Parse multiple m/z values from input (comma-separated)
        mz_input = self.ui.mz_input.text().strip()
        try:
            mz_values = [float(m.strip()) for m in mz_input.split(',')]
            print(f"m/z values: {mz_values}")
        except ValueError as e:
            self.ui.status_label.setText(f"Error: Invalid m/z values")
            print(f"Error parsing m/z values: {e}")
            return

        try:
            # --- TIC PLOT ---
            self.ui.status_label.setText("Generating TIC plot...")
            print("Generating TIC plot...")
            fig_tic = go.Figure()
            for file in files:
                path = os.path.join(self.folder, file)
                print(f"  Processing TIC for {file}...")
                rt, inten = extract_tic(path)
                print(f"    Got {len(rt)} data points, max: {inten.max():.2e}")
                fig_tic.add_trace(go.Scatter(x=rt, y=inten, name=file, mode='lines'))
            
            fig_tic.update_layout(
                title="Total Ion Chromatography (TIC)",
                xaxis_title="Retention Time (min)",
                yaxis_title="Intensity",
                template="plotly_white",
                hovermode="x unified",
                yaxis=dict(exponentformat="e")
            )
            
            html_tic = fig_tic.to_html(include_plotlyjs='cdn')
            self.ui.browser_tic.setHtml(html_tic)
            print("TIC plot complete")

            # --- EIC PLOT ---
            self.ui.status_label.setText("Generating EIC plot...")
            print("Generating EIC plot...")
            fig_eic = go.Figure()
            eic_count = 0
            for mz in mz_values:
                for file in files:
                    path = os.path.join(self.folder, file)
                    print(f"  Processing EIC for {file} (m/z={mz})...")
                    rt, inten = extract_eic(path, mz)
                    print(f"    Got {len(rt)} data points, max: {inten.max():.2e}")
                    fig_eic.add_trace(go.Scatter(x=rt, y=inten, name=f"{file} (m/z={mz})", mode='lines'))
                    eic_count += 1
                    
                    # Add peak markers
                    peaks = pick_peaks(rt, inten)
                    print(f"    Found {len(peaks)} peaks")
                    if len(peaks) > 0:
                        fig_eic.add_trace(go.Scatter(
                            x=rt[peaks],
                            y=inten[peaks],
                            mode="markers",
                            name=f"{file} peaks (m/z={mz})",
                            marker=dict(size=8, color='red')
                        ))
            
            fig_eic.update_layout(
                title="Extracted Ion Chromatography (EIC)",
                xaxis_title="Retention Time (min)",
                yaxis_title="Intensity",
                template="plotly_white",
                hovermode="x unified",
                yaxis=dict(exponentformat="e")
            )
            
            html_eic = fig_eic.to_html(include_plotlyjs='cdn')
            self.ui.browser_eic.setHtml(html_eic)
            print("EIC plot complete")

            # --- AREA COMPARISON PLOT ---
            self.ui.status_label.setText("Generating area plot...")
            print("Generating area comparison plot...")
            # Collect area data per m/z per file
            area_data = {}  # {mz: {file: total_area}}
            
            self.ui.peak_table.setRowCount(0)
            
            for mz in mz_values:
                area_data[mz] = {}
                for file in files:
                    path = os.path.join(self.folder, file)
                    print(f"  Processing peaks for {file} (m/z={mz})...")
                    rt, inten = extract_eic(path, mz)
                    peaks = pick_peaks(rt, inten)
                    results = integrate_peaks(rt, inten, peaks)
                    print(f"    Found {len(results)} peaks to integrate")
                    
                    # Total area for this m/z in this file
                    total_area = sum([r['area'] for r in results])
                    area_data[mz][file] = total_area
                    print(f"    Total area: {total_area:.2e}")
                    
                    # Fill table with individual peaks
                    for r in results:
                        row = self.ui.peak_table.rowCount()
                        self.ui.peak_table.insertRow(row)
                        
                        self.ui.peak_table.setItem(row, 0, QTableWidgetItem(f"{file} (m/z={mz})"))
                        self.ui.peak_table.setItem(row, 1, QTableWidgetItem(f"{r['rt']:.2f}"))
                        self.ui.peak_table.setItem(row, 2, QTableWidgetItem(f"{r['area']:.2e}"))
            
            # Create area comparison plot
            fig_areas = go.Figure()
            
            for mz in mz_values:
                files_sorted = sorted(files)
                areas = [area_data[mz].get(file, 0) for file in files_sorted]
                print(f"  m/z {mz}: areas = {[f'{a:.2e}' for a in areas]}")
                fig_areas.add_trace(go.Bar(
                    x=files_sorted,
                    y=areas,
                    name=f"m/z {mz}"
                ))
            
            fig_areas.update_layout(
                title="Peak Areas Comparison Across Files",
                xaxis_title="File",
                yaxis_title="Total Peak Area",
                barmode="group",
                template="plotly_white",
                hovermode="x unified",
                xaxis_tickangle=-45,
                yaxis=dict(exponentformat="e")
            )
            
            html_areas = fig_areas.to_html(include_plotlyjs='cdn')
            self.ui.browser_areas.setHtml(html_areas)
            print("Areas plot complete")
            
            self.ui.status_label.setText(f"✓ Complete! {len(files)} files, {len(mz_values)} m/z values")
            print("Analysis finished successfully!")
            clear_cache()  # Free up memory after analysis
            
        except Exception as e:
            self.ui.status_label.setText(f"Error: {type(e).__name__}")
            print(f"Error during analysis: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            clear_cache()  # Free up memory even on error


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = OrbitrapApp()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)