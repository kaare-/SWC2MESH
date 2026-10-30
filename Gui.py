# Gui.py

import sys
import os
from PyQt5 import QtCore, QtWidgets
import processing  # Your processing module
from multiprocessing import cpu_count

class Worker(QtCore.QObject):
    progress = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    def __init__(self, swc_directory, output_directory, target_reduction, tube_sides,
                 enable_cleaning, smoothing_iterations, smoothing_pass_band, num_processes):
        super().__init__()
        self.swc_directory = swc_directory
        self.output_directory = output_directory
        self.target_reduction = target_reduction
        self.tube_sides = tube_sides
        self.enable_cleaning = enable_cleaning
        self.smoothing_iterations = smoothing_iterations
        self.smoothing_pass_band = smoothing_pass_band
        self.num_processes = num_processes

    @QtCore.pyqtSlot()
    def run(self):
        try:
            messages = processing.process_swc_files(
                self.swc_directory,
                self.output_directory,
                self.target_reduction,
                self.tube_sides,
                self.enable_cleaning,
                self.smoothing_iterations,
                self.smoothing_pass_band,
                self.num_processes
            )
            for message in messages:
                self.progress.emit(message)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class SWCConverterApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SWC to STL Converter')

        # Layouts
        main_layout = QtWidgets.QVBoxLayout()
        form_layout = QtWidgets.QFormLayout()

        # Input fields
        self.swc_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.target_reduction_edit = QtWidgets.QLineEdit('0.5')
        self.tube_sides_edit = QtWidgets.QLineEdit('8')
        self.num_processes_edit = QtWidgets.QLineEdit(str(max(1, cpu_count() - 1)))

        # Checkbox for cleaning
        self.cleaning_checkbox = QtWidgets.QCheckBox("Enable Mesh Cleaning")
        self.cleaning_checkbox.setChecked(True)  # Default to enabled

        # Smoothing parameters
        self.smoothing_iterations_edit = QtWidgets.QLineEdit('3')
        self.smoothing_pass_band_edit = QtWidgets.QLineEdit('0.1')

        # Browse buttons
        swc_browse_button = QtWidgets.QPushButton('Browse')
        output_browse_button = QtWidgets.QPushButton('Browse')

        swc_browse_button.clicked.connect(self.browse_swc_directory)
        output_browse_button.clicked.connect(self.browse_output_directory)

        # Add widgets to form layout
        form_layout.addRow('SWC Directory:', self.swc_dir_edit)
        form_layout.addRow('', swc_browse_button)
        form_layout.addRow('Output Directory:', self.output_dir_edit)
        form_layout.addRow('', output_browse_button)
        form_layout.addRow('Target Reduction (0.0 - 1.0):', self.target_reduction_edit)
        form_layout.addRow('Tube Sides:', self.tube_sides_edit)
        form_layout.addRow('Number of Processes:', self.num_processes_edit)
        form_layout.addRow(self.cleaning_checkbox)
        form_layout.addRow('Smoothing Iterations:', self.smoothing_iterations_edit)
        form_layout.addRow('Smoothing Pass Band:', self.smoothing_pass_band_edit)

        # Start button
        self.start_button = QtWidgets.QPushButton('Start Processing')
        self.start_button.clicked.connect(self.start_processing)

        # Log text box
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)

        # Add widgets to main layout
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(QtWidgets.QLabel('Processing Log:'))
        main_layout.addWidget(self.log_text)

        self.setLayout(main_layout)

    def browse_swc_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select SWC Directory')
        if directory:
            self.swc_dir_edit.setText(directory)

    def browse_output_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        if directory:
            self.output_dir_edit.setText(directory)

    def start_processing(self):
        swc_directory = self.swc_dir_edit.text()
        output_directory = self.output_dir_edit.text()
        try:
            target_reduction = float(self.target_reduction_edit.text())
            tube_sides = int(self.tube_sides_edit.text())
            num_processes = int(self.num_processes_edit.text())
            enable_cleaning = self.cleaning_checkbox.isChecked()
            smoothing_iterations = int(self.smoothing_iterations_edit.text())
            smoothing_pass_band = float(self.smoothing_pass_band_edit.text())
        except ValueError:
            QtWidgets.QMessageBox.critical(self, 'Error', 'Please enter valid values for parameters.')
            return

        if not swc_directory or not output_directory:
            QtWidgets.QMessageBox.critical(self, 'Error', 'Please select input and output directories.')
            return

        if not os.path.exists(swc_directory):
            QtWidgets.QMessageBox.critical(self, 'Error', 'Input directory does not exist.')
            return

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        # Disable the Start button
        self.start_button.setEnabled(False)
        self.log_text.clear()

        # Create a QThread object
        self.thread = QtCore.QThread()
        # Create a worker object
        self.worker = Worker(swc_directory, output_directory, target_reduction, tube_sides,
                             enable_cleaning, smoothing_iterations, smoothing_pass_band, num_processes)
        # Move the worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.progress.connect(self.update_log)
        self.worker.error.connect(self.on_processing_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Start the thread
        self.thread.start()

    @QtCore.pyqtSlot()
    def on_processing_finished(self):
        self.start_button.setEnabled(True)
        QtWidgets.QMessageBox.information(
            self,
            'Processing Complete',
            'Batch processing has completed.\nCheck the output directory for results and the log file.'
        )

    @QtCore.pyqtSlot(str)
    def on_processing_error(self, error_message):
        self.start_button.setEnabled(True)
        QtWidgets.QMessageBox.critical(self, 'Processing Error', error_message)

    @QtCore.pyqtSlot(str)
    def update_log(self, message):
        self.log_text.append(message)
        self.log_text.ensureCursorVisible()

def main():
    # Set the multiprocessing start method
    import multiprocessing
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn', force=True)

    app = QtWidgets.QApplication(sys.argv)
    window = SWCConverterApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
