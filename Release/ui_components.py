# ui_components.py

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
import sys, subprocess, os
from datetime import datetime
from overlays import GazeOverlay, HeatmapOverlay
from data_handling import normalize_gaze_to_screen, parse_word_hit_counts, GazeDataProcessor
from calibration import CalibrationScreen
from userpage import UserPage
from ui_styles import get_button_style, get_exit_button_style, get_label_style, get_text_content, get_theme 
from config import app_config
class GazeVisualizer(QMainWindow):

    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.screen_width, self.screen_height = screen_width, screen_height
        self.is_night_mode = False  # Track whether night mode is active
        self.dwell_data = None
        self.other_buttons = []  # Store references to other buttons
        self.setupUI()
        self.current_directory = None  # Initialize the directory attribute
        self.recording_process = None
        self.gaze_processor = None
    
    def toggle_night_mode(self):
        # Toggle the night mode state and update the stylesheet
        new_mode = "night_mode" if not self.is_night_mode else "default"
        self.setStyleSheet(get_theme(new_mode))
        self.is_night_mode = not self.is_night_mode

    def setupUI(self):
        self.setGeometry(100, 100, self.screen_width, self.screen_height)
        self.setWindowTitle('Gaze Tracker')
        logical_dpi_x = QApplication.screens()[0].logicalDotsPerInchX()
        self.dpi_scale_factor = logical_dpi_x / 96
        self.setStyleSheet(get_theme("default"))  # Start with the default theme
        self.setupLabels()
        self.setupButtons()
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.setGeometry(0, 0, self.screen_width, self.screen_height)

    def hideUI(self):
        # Hide all non-essential UI elements except 'Next' and 'Exit'
        #self.night_mode_button.hide()
        for label in self.labels:
            label[1].hide()
        self.gaze_overlay.hide()
        for button in self.other_buttons:
            button.hide()
        self.exit_button.hide()  # Also hide the exit button during calibration

    def showUI(self):
        # Restore all UI elements after calibration
        #self.night_mode_button.show()
        for label in self.labels:
            label[1].show()
        self.gaze_overlay.show()
        for button in self.other_buttons:
            button.show()
        self.exit_button.show()  # Show the exit button again

    def setupLabels(self, text=None):

        if text is None:
            text = get_text_content()

        font_family, font_size, line_spacing_factor = get_label_style(self.screen_height)
        font = QFont(font_family, font_size)
        fm = QFontMetrics(font)
        line_height = fm.height()

        max_line_width = self.screen_width * 0.8  # Use 80% of screen width for text
        x_start = self.screen_width * 0.1  # Start 10% from the left
        top_margin = self.screen_height * 0.08  # Adjust the top margin to increase distance from the top edge
        bottom_margin = self.screen_height * 0.15  # Adjust the bottom margin to increase distance from the bottom edge
        x, y = x_start, top_margin

        self.labels = []
        for word in text.split():
            word_width = fm.width(word + ' ')
            if x + word_width > self.screen_width - x_start:
                x = x_start
                y += int(line_height * line_spacing_factor)

            identifier = f"{y}-{x}"
            label = QLabel(word, self)
            label.setFont(font)
            label.adjustSize()
            label.setStyleSheet("background-color: rgba(225, 225, 225, 0.7);")  # Slightly darker shade of white as background
            label.move(int(x), int(y))
            label.show()
            self.labels.append((identifier, label, word))

            x += word_width

        # Adjust vertical position if necessary to ensure bottom margin
        total_text_height = y + line_height - top_margin
        if total_text_height < self.screen_height - bottom_margin:
            extra_space = (self.screen_height - bottom_margin - total_text_height) / 2
            total_text_height += 2 * extra_space
            for identifier, label, word in self.labels:
                label.move(label.x(), int(label.y() + extra_space))

        self.total_text_height = total_text_height + top_margin  # Include the adjusted initial offset


    def setupButtons(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        margins = int(self.screen_width * 0.03)  # Margin for general spacing

        # Setup Exit Button
        exit_button_size = int(self.screen_height * 0.05 * self.dpi_scale_factor)
        self.exit_button = QPushButton('X', self)
        self.exit_button.setFixedSize(exit_button_size, exit_button_size)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setStyleSheet(get_exit_button_style(exit_button_size))
        self.exit_button.move(self.width() - exit_button_size - margins, margins)  # Top right corner
        self.exit_button.setParent(central_widget)

        # Define button sizes and spacing for bottom row
        button_width = int(self.screen_width * 0.12 * self.dpi_scale_factor)
        button_height = int(self.screen_height * 0.06 * self.dpi_scale_factor)
        button_spacing = 10  # Spacing between buttons

        # List of functions with their respective button labels
        functions = [
            (self.toggleRecording, 'Record'),
            (self.togglePlayback, 'Playback'),
            (self.startCalibration, 'Calibrate'),
            (self.openUserPage, 'Users'),
            (self.toggle_night_mode, 'Nightmode')
        ]

        total_buttons_width = len(functions) * button_width + (len(functions) - 1) * button_spacing
        start_x = (self.width() - total_buttons_width) // 2  # Center the block of buttons

        # Place all functional buttons on the bottom row
        self.other_buttons = []  # List to manage other buttons
        x_position = start_x
        for func, name in functions:
            button = QPushButton(name, self)
            button.clicked.connect(func)
            button.setFixedSize(button_width, button_height)
            button.setStyleSheet(get_button_style(button_height))
            button.move(x_position, self.height() - button_height - margins)  # Position at bottom
            x_position += button_width + button_spacing
            button.setParent(central_widget)
            self.other_buttons.append(button)

        # Store references to specific buttons for later use
        self.record_button = self.other_buttons[0]
        self.playback_button = self.other_buttons[1]

    def startCalibration(self):
        self.calibration_screen = CalibrationScreen(self)
        self.calibration_screen.show()

    def openUserPage(self):
        # This assumes you have a class `UserPage` defined elsewhere
        self.user_page = UserPage(self)
        self.user_page.show()
    
    def toggleRecording(self):
        if self.recording_process:
            # Stop the recording if it is currently running
            self.recording_process.terminate()
            self.recording_process = None
            self.record_button.setText("Record")  # Update button text to reflect available action
            print("Recording stopped.")
        else:
            directory = app_config.session_directory
            if not directory:
                print("No directory selected for recording.")
                return
            
            filename = 'gazeData.txt'
            file_path = os.path.join(directory, filename)
            
            open(file_path, 'w').close()  # Ensure the file is empty before starting to record
            executable_path = "/Users/borana/Documents/GitHub/DyslexiaProject/Release/cpp_exec/Tobii_api_test1"
            window_id = str(self.winId().__int__())
            cmd = [executable_path, window_id, file_path]
            self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.record_button.setText("Stop Recording")  # Update button text to reflect available action
            print(f"Starting general recording with command: {cmd}")

    def togglePlayback(self):
        if self.gaze_processor and self.gaze_processor.isRunning():
            # Stop the playback if it is currently running
            self.gaze_processor.terminate()
            self.gaze_processor = None
            self.playback_button.setText("Playback")  # Update button text to reflect available action
            print("Playback stopped.")
        else:
            directory = app_config.session_directory
            if not directory:
                print("No directory selected for playback.")
                return

            filename = 'gazeData_calibrated.txt'
            file_path = os.path.join(directory, filename)

            if os.path.exists(file_path):
                gaze_data = []
                with open(file_path, 'r') as file:
                    gaze_data = file.readlines()

                self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels, directory)
                self.gaze_processor.update_gaze_signal.connect(lambda ts, x, y: self.gaze_overlay.update_gaze_position(x, y))
                self.gaze_processor.finished.connect(self.onPlaybackFinished)  # Connect the finished signal to the slot
                self.gaze_processor.start()
                self.playback_button.setText("Stop Playback")  # Update button text to reflect available action
                print("Playback started.")
            else:
                print("Calibrated gaze data file does not exist.")
    
    def onPlaybackFinished(self):
        self.gaze_processor = None
        self.playback_button.setText("Playback")
        print("Playback finished.")

    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process = None
            print("Recording stopped.")

    def startCalibrationRecording(self, dot_id, directory):
        if not directory:
            print("No directory selected for calibration recording.")
            return

        filename = f'gazeData_{dot_id}.txt'
        file_path = os.path.join(directory, filename)
        open(file_path, 'w').close()  # Ensure the file is empty before starting to record
        executable_path = "/Users/borana/Documents/GitHub/DyslexiaProject/Release/cpp_exec/Tobii_api_test1"
        window_id = str(self.winId().__int__())
        cmd = [executable_path, window_id, file_path]
        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Starting calibration recording for dot {dot_id} with command: {cmd}")

    def setDirectory(self, directory):
        """Set the current working directory for user/session data."""
        if os.path.exists(directory):
            app_config.session_directory = directory
            print(f"Data directory set to: {directory}")
        else:
            app_config.session_directory = None
            print("Invalid directory. Please check the path and try again.")

    def updateTextDisplay(self):
        # This method updates the text content on the display
        text = get_text_content(app_config.session_directory)
        self.setupLabels(text)  # Assuming setupLabels can take text as an argument

    def showHeatmapOnText(self):
        """Show heatmap based on the gaze data stored in the current directory."""
        directory = app_config.session_directory
        if not directory:
            print("No directory set. Please select a session or create a new one.")
            return

        filename = 'gazeData_calibrated.txt'
        file_path = os.path.join(directory, filename)

        if not os.path.exists(file_path):
            print("Gaze data file does not exist.")
            return

        gaze_points = []
        with open(file_path, 'r') as file:
            for line in file:
                if 'Gaze point:' in line:
                    _, gaze_str = line.split('] Gaze point: ')
                    gaze_point = [float(val) for val in gaze_str.strip()[1:-1].split(',')]
                    screen_x, screen_y = normalize_gaze_to_screen(gaze_point, self.width(), self.height())
                    gaze_points.append((screen_x, screen_y))

        print(f"Number of parsed gaze points: {len(gaze_points)}")

        word_hit_file_path = os.path.join(directory, "word_hit_counts.txt")
        if not os.path.exists(word_hit_file_path):
            print("Word hit counts file does not exist.")
            return

        word_hit_data = parse_word_hit_counts(word_hit_file_path)
        if gaze_points:
            self.heatmap_overlay = HeatmapOverlay(gaze_points, word_hit_data, self)
            self.heatmap_overlay.setGeometry(0, 0, self.width(), self.height())
            self.heatmap_overlay.show()
            self.heatmap_overlay.update()
        else:
            print("No gaze points parsed or heatmap overlay not properly set up.")

    def closeEvent(self, event):
        # Check if gaze_processor exists and call write_hit_counts_to_file
        if hasattr(self, 'gaze_processor') and self.gaze_processor is not None:
            self.gaze_processor.write_hit_counts_to_file()
        super().closeEvent(event)