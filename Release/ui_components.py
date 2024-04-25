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

class GazeVisualizer(QMainWindow):

    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.screen_width, self.screen_height = screen_width, screen_height
        self.is_night_mode = False  # Track whether night mode is active
        self.dwell_data = None
        self.other_buttons = []  # Store references to other buttons
        self.setupUI()
        self.current_user = None
        self.current_user_directory = None  # Ensure this attribute is initialized
    
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
        self.night_mode_button.hide()
        for label in self.labels:
            label[1].hide()
        self.gaze_overlay.hide()
        for button in self.other_buttons:
            button.hide()
        self.exit_button.hide()  # Also hide the exit button during calibration

    def showUI(self):
        # Restore all UI elements after calibration
        self.night_mode_button.show()
        for label in self.labels:
            label[1].show()
        self.gaze_overlay.show()
        for button in self.other_buttons:
            button.show()
        self.exit_button.show()  # Show the exit button again

    def setupLabels(self):
        text = get_text_content()
        
        font_family, font_size, line_spacing_factor = get_label_style(self.screen_height)
        font = QFont(font_family, font_size)
        fm = QFontMetrics(font)
        line_height = fm.height()

        max_line_width = self.screen_width * 0.8  # Use 80% of screen width for text
        x_start = self.screen_width * 0.1  # Start 10% from the left
        y_start = self.screen_height * 0.2  # Start 30% from the top, adjust as needed
        x, y = x_start, y_start

        self.labels = []  # This will store tuples of (identifier, QLabel object, word text)
        for word in text.split():
            word_width = fm.width(word + ' ')  # Include space in width calculation
            if x + word_width > self.screen_width - x_start:  # Check if the word exceeds the max line width
                x = x_start  # Reset x to start of line
                y += int(line_height * line_spacing_factor)  # Increase y by the line height with added spacing

            identifier = f"{y}-{x}"  # Using the starting position as a simple identifier
            label = QLabel(word, self)
            label.setFont(font)
            label.adjustSize()  # Adjust label size to fit text
            label.move(int(x), int(y))
            label.show()
            self.labels.append((identifier, label, word))  # Store identifier, QLabel, and word text

            x += word_width  # Move x for the next word

        # Adjust vertical position if necessary
        total_text_height = y + line_height - y_start
        if total_text_height < self.screen_height * 0.6:  # If text block is smaller than 60% of screen height
            extra_space = (self.screen_height * 0.6 - total_text_height) / 2
            total_text_height += 2 * extra_space  # Adjust total height based on extra space added
            for identifier, label, word in self.labels:
                label.move(label.x(), int(label.y() + extra_space))

        self.total_text_height = total_text_height + y_start  # Add y_start to include the initial offset

    def setupButtons(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout_spacing = int(self.screen_width * 0.01)  # Dynamic spacing based on screen width
        margins = layout_spacing  # Use the same dynamic spacing for margins

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(layout_spacing)
        main_layout.setContentsMargins(margins, margins, margins, margins)

        # Setup exit button
        exit_button_size = int(self.screen_height * 0.05 * self.dpi_scale_factor)
        self.exit_button = QPushButton('X', self)  # Make exit_button an attribute of the class
        self.exit_button.setFixedSize(exit_button_size, exit_button_size)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setStyleSheet(get_exit_button_style(exit_button_size))
        exit_layout = QHBoxLayout()
        exit_layout.addWidget(self.exit_button)
        exit_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)
        main_layout.addLayout(exit_layout)

        # Setup Night Mode Button
        # Make the button a third of the size of other buttons
        button_width = int(self.screen_width * 0.045 * self.dpi_scale_factor)  # 1/3 width of other buttons
        button_height = int(self.screen_height * 0.029 * self.dpi_scale_factor)  # 1/3 height of other buttons
        self.night_mode_button = QPushButton('Nightmode', self)
        self.night_mode_button.setFixedSize(button_width, button_height)
        self.night_mode_button.clicked.connect(self.toggle_night_mode)
        self.night_mode_button.setStyleSheet(get_button_style(button_height))

        # Align the night mode button to the top left corner
        # Calculate margins to position the button near the top left corner with some spacing
        top_margin = int(self.screen_height * 0.01)  # Smaller margin from the top edge
        right_margin = int(self.screen_width * 0.01)  # Smaller margin from the left edge

        night_mode_layout = QHBoxLayout()
        night_mode_layout.addWidget(self.night_mode_button)
        night_mode_layout.setContentsMargins(right_margin, top_margin, 0, 0)  # Set margins
        night_mode_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)  # Align to top left
        main_layout.addLayout(night_mode_layout)

        # Dynamic spacer to move buttons up
        spacer_proportion = 0.3  # Adjust this value to change the vertical position of the buttons
        spacer_height = int(self.screen_height * spacer_proportion)
        spacer = QSpacerItem(20, spacer_height, QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer)

        # Setup other buttons
        button_width = int(self.screen_width * 0.12 * self.dpi_scale_factor)
        button_height = int(self.screen_height * 0.06 * self.dpi_scale_factor)
        button_layout = QHBoxLayout()
        functions = [
            (self.startPlayback, 'Playback'),
            (self.startRecording, 'Record'),
            (self.stopPlayback, 'Stop Playback'),
            (self.showHeatmapOnText, 'Project Heatmap'),
            (self.stopRecording, 'Stop Recording'),
            (self.startCalibration, 'Calibrate'),
            (self.openUserPage, 'Users')  # Add this line for the Users button
        ]
        self.other_buttons = []  # Define a list to manage other buttons
        for func, name in functions:
            button = QPushButton(name, self)
            button.clicked.connect(func)
            button.setFixedSize(button_width, button_height)
            button.setStyleSheet(get_button_style(button_height))
            button_layout.addWidget(button)
            self.other_buttons.append(button)  # Add to the list for easy management

        main_layout.addLayout(button_layout)  # Add the layout containing all buttons
    
    def startCalibration(self):
        self.calibration_screen = CalibrationScreen(self)
        self.calibration_screen.show()

    def openUserPage(self):
        # This assumes you have a class `UserPage` defined elsewhere
        self.user_page = UserPage(self)
        self.user_page.show()

    def startRecording(self):
        if not self.current_user_directory:
            print("No user selected for recording.")
            return

        filename = 'gazeData.txt'
        file_path = os.path.join(self.current_user_directory, filename)
        
        # Ensure the file is empty before starting to record
        open(file_path, 'w').close()

        # Define the path to the executable
        executable_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/cpp_exec/Tobii_api_test1"
        window_id = str(self.winId().__int__())

        # Include the full file path in the command
        cmd = [executable_path, window_id, file_path]
        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Starting general recording with command: {cmd}")

    def startCalibrationRecording(self, dot_id):
        if not self.current_user_directory:
            print("No user selected for calibration recording.")
            return

        filename = f'gazeData_{dot_id}.txt'
        file_path = os.path.join(self.current_user_directory, filename)
        open(file_path, 'w').close()  # Ensures the file is empty before starting to record
        executable_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/cpp_exec/Tobii_api_test1"
        window_id = str(self.winId().__int__())
        cmd = [executable_path, window_id, file_path]
        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Starting calibration recording for dot {dot_id} with command: {cmd}")

    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process = None
            print("Recording stopped.")  # Optional: Confirmation message for stopping the recording

    def showHeatmapOnText(self):
        folder_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data"
        filename1 = 'gazeData.txt'
        file_path3 = os.path.join(folder_path, filename1)
        gaze_points = []
        with open(file_path3, 'r') as file:
            for line in file:
                if 'Gaze point:' in line:
                    _, gaze_str = line.split('] Gaze point: ')
                    gaze_point = [float(val) for val in gaze_str.strip()[1:-1].split(',')]
                    # Normalize gaze points for the screen dimensions
                    screen_x, screen_y = normalize_gaze_to_screen(gaze_point, self.width(), self.height())
                    gaze_points.append((screen_x, screen_y))

        # Debugging: Print the number of parsed gaze points
        print(f"Number of parsed gaze points: {len(gaze_points)}")
        word_hit_file_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/word_hit_counts.txt"
        word_hit_data = parse_word_hit_counts(word_hit_file_path)

        if len(gaze_points) > 0:
            #self.heatmap_overlay = HeatmapOverlay(gaze_points, self)
            self.heatmap_overlay = HeatmapOverlay(gaze_points, word_hit_data, self)
            self.heatmap_overlay.setGeometry(0, 0, self.width(), self.height())
            self.heatmap_overlay.show()
            self.heatmap_overlay.update()  # Explicitly request an update
        else:
            print("No gaze points parsed or heatmap overlay not properly set up.")

    def startPlayback(self):
        if not self.current_user_directory:
            print("No user selected for playback.")
            return

        filename = 'gazeData_calibrated.txt'
        file_path = os.path.join(self.current_user_directory, filename)

        if os.path.exists(file_path):
            gaze_data = []
            with open(file_path, 'r') as file:
                gaze_data = file.readlines()

            self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels)
            self.gaze_processor.update_gaze_signal.connect(lambda ts, x, y: self.gaze_overlay.update_gaze_position(x, y))
            self.gaze_processor.start()
        else:
            print("Calibrated gaze data file does not exist.")

    def stopPlayback(self):
        if self.gaze_processor and self.gaze_processor.isRunning():
            self.gaze_processor.terminate()

    def closeEvent(self, event):
        # Check if gaze_processor exists and call write_hit_counts_to_file
        if hasattr(self, 'gaze_processor') and self.gaze_processor is not None:
            self.gaze_processor.write_hit_counts_to_file()
        super().closeEvent(event)


    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process = None
            print("Recording stopped.")  # Optional: Confirmation message for stopping the recording

    def showHeatmapOnText(self):
        if not self.current_user_directory:
            print("No user selected to show heatmap.")
            return

        filename = 'gazeData.txt'
        file_path = os.path.join(self.current_user_directory, filename)
        gaze_points = []

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                for line in file:
                    if 'Gaze point:' in line:
                        _, gaze_str = line.split('] Gaze point: ')
                        gaze_point = [float(val) for val in gaze_str.strip()[1:-1].split(',')]
                        screen_x, screen_y = normalize_gaze_to_screen(gaze_point, self.width(), self.height())
                        gaze_points.append((screen_x, screen_y))

            print(f"Number of parsed gaze points: {len(gaze_points)}")  # Debugging: Print the number of parsed gaze points

            word_hit_file_path = os.path.join(self.current_user_directory, "word_hit_counts.txt")
            if os.path.exists(word_hit_file_path):
                word_hit_data = parse_word_hit_counts(word_hit_file_path)
                self.heatmap_overlay = HeatmapOverlay(gaze_points, word_hit_data, self)
                self.heatmap_overlay.setGeometry(0, 0, self.width(), self.height())
                self.heatmap_overlay.show()
                self.heatmap_overlay.update()  # Explicitly request an update
            else:
                print("Word hit counts file does not exist.")
        else:
            print("Gaze data file does not exist.")

    def startPlayback(self):
        if not self.current_user_directory:
            print("No user selected for playback.")
            return

        filename = 'gazeData_calibrated.txt'
        file_path = os.path.join(self.current_user_directory, filename)

        if os.path.exists(file_path):
            gaze_data = []
            with open(file_path, 'r') as file:
                gaze_data = file.readlines()

            self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels)
            self.gaze_processor.update_gaze_signal.connect(lambda ts, x, y: self.gaze_overlay.update_gaze_position(x, y))
            self.gaze_processor.start()
        else:
            print("Calibrated gaze data file does not exist.")

    def stopPlayback(self):
        if self.gaze_processor and self.gaze_processor.isRunning():
            self.gaze_processor.terminate()
    
    def setCurrentUser(self, user_name):
        self.current_user = user_name
        self.updateFilePaths()

    def updateFilePaths(self):
        if self.current_user:
            self.current_user_directory = os.path.join("C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", f"{self.current_user}_data")
            os.makedirs(self.current_user_directory, exist_ok=True)
            print(f"Data directory set to: {self.current_user_directory}")
        else:
            self.current_user_directory = None  # Reset to None if no user is set

    def closeEvent(self, event):
        # Check if gaze_processor exists and call write_hit_counts_to_file
        if hasattr(self, 'gaze_processor') and self.gaze_processor is not None:
            self.gaze_processor.write_hit_counts_to_file()
        super().closeEvent(event)
