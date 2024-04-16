# ui_components.py
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
import sys, subprocess, os
from datetime import datetime
from overlays import GazeOverlay, HeatmapOverlay
from data_handling import normalize_gaze_to_screen, parse_word_hit_counts, GazeDataProcessor
from calibration import CalibrationScreen

class GazeVisualizer(QMainWindow):
    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.screen_width, self.screen_height = screen_width, screen_height
        self.dwell_data = None
        self.setupUI()

    def setupUI(self):
        self.setGeometry(100, 100, self.screen_width, self.screen_height)
        self.setWindowTitle('Gaze Tracker')
        logical_dpi_x = QApplication.screens()[0].logicalDotsPerInchX()
        self.dpi_scale_factor = logical_dpi_x / 96
        self.setupLabels()
        self.setupButtons()
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.setGeometry(0, 0, self.screen_width, self.screen_height)

    def hideUI(self):
        # Hide elements like labels and other buttons
        for label in self.labels:
            label[1].hide()  # Assuming label[1] is the QLabel object
        self.gaze_overlay.hide()

    def showUI(self):
        # Show all previously hidden elements
        for label in self.labels:
            label[1].show()
        self.gaze_overlay.show()

    def setupLabels(self):
        text = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop..."

        # Base font size and scaling factor
        base_font_size = 12  # Base size for calculation
        screen_height = self.screen_height  # Use the screen height for scaling
        
        # Adjust font size based on screen height
        font_scaling_factor = screen_height / 1080  # Assuming 1080p as base
        # Adjust font size based on DPI scale factor
        font_size = max(int(base_font_size * self.dpi_scale_factor), 50)

        font = QFont('Calibri', font_size)
        fm = QFontMetrics(font)
        line_height = fm.height()

        words = text.split()
        max_line_width = self.screen_width * 0.8  # Use 80% of screen width for text

        x_start = self.screen_width * 0.1  # Start 10% from the left
        y_start = self.screen_height * 0.2  # Start 30% from the top, adjust as needed
        x, y = x_start, y_start

        self.labels = []  # This will store tuples of (identifier, QLabel object, word text)
        line_spacing_factor = 1.5  # Adjust this factor to increase line spacing, 1.5 means 150% of line height

        for word in words:
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

        # Center the text block vertically if it doesn't fill the screen

        total_text_height = y + line_height - y_start
        if total_text_height < self.screen_height * 0.6:  # If text block is smaller than 60% of screen height
            extra_space = (self.screen_height * 0.6 - total_text_height) / 2
            total_text_height += 2 * extra_space  # Adjust total height based on extra space added
            for identifier, label, word in self.labels:
                label.move(label.x(), int(label.y() + extra_space))

        # Store the total text height as an attribute for later use
        self.total_text_height = total_text_height + y_start  # Add y_start to include the initial offset

    def setupButtons(self):
        # Calculate dynamic sizes and spacing based on screen dimensions
        button_width = int(self.screen_width * 0.15 * self.dpi_scale_factor)
        button_height = int(self.screen_height * 0.07 * self.dpi_scale_factor)
        exit_button_size = int(self.screen_height * 0.08 * self.dpi_scale_factor)
        layout_spacing = int(self.screen_width * 0.01)  # 1% of screen width for spacing between elements

        # Central widget setup for overall layout management
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(layout_spacing)
        main_layout.setContentsMargins(layout_spacing, layout_spacing, layout_spacing, layout_spacing)

        spacer_height = int(max(self.screen_height * 0.05, self.total_text_height + self.screen_height * 0.05 - self.screen_height * 0.5))
        spacer = QSpacerItem(20, spacer_height, QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer)

        button_layout = QHBoxLayout()
        functions = [
            (self.startPlayback, 'Playback'),
            (self.startRecording, 'Record'),
            (self.stopPlayback, 'Stop Playback'),
            (self.showHeatmapOnText, 'Project Heatmap'),
            (self.stopRecording, 'Stop Recording'),
            (self.startCalibration, 'Calibrate')
        ]

        for func, name in functions:
            button = QPushButton(name)
            button.clicked.connect(func)
            button.setFixedSize(button_width, button_height)  # Keep dynamic sizing
            # Apply the dynamic visual styling with gradient effects here
            button.setStyleSheet(f"""
                QPushButton {{
                    font-size: {int(button_height * 0.15)}pt;
                    color: white;
                    border-radius: {button_height // 2}px;
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                        stop:0 rgba(126, 87, 194, 1), stop:1 rgba(149, 117, 205, 1));
                    border: 1px solid #DBDBDB;
                    padding: 5px;
                }}
                QPushButton:hover {{
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                        stop:0 rgba(255, 151, 60, 1), stop:1 rgba(255, 193, 7, 1));
                }}
                QPushButton:pressed {{
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                        stop:0 rgba(221, 44, 0, 1), stop:1 rgba(255, 109, 0, 1));
                }}
            """)
            button_layout.addWidget(button)

        main_layout.addLayout(button_layout)

        # Your existing setup for the "Exit" button...

        # Customize the "Exit" button with dynamic styling and sizing
        exit_button = QPushButton('X')
        exit_button.setFixedSize(exit_button_size, exit_button_size)
        exit_button.clicked.connect(self.close)
        exit_button.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(exit_button_size * 0.4)}pt;
                color: #FFFFFF;
                border: 2px solid #555;
                background-color: #333;
                border-radius: {exit_button_size // 2}px;
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #777;
            }}
        """)

        # Layout for the exit button, positioned to be visually separated
        exit_layout = QHBoxLayout()
        exit_layout.addWidget(exit_button)
        exit_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)
        main_layout.addLayout(exit_layout)

    def startCalibration(self):
        self.calibration_screen = CalibrationScreen(self)
        self.calibration_screen.show()

    def startRecording(self):
        # Define the path to the folder and the filename
        folder_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data"
        filename = 'gazeData.txt'
        file_path = os.path.join(folder_path, filename)
        
        # Ensure the file is empty before starting to record
        open(file_path, 'w').close()

        # Define the path to the executable
        executable_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/cpp_exec/Tobii_api_test1"
        window_id = str(self.winId().__int__())  # Convert window handle to string

        # Include the full file path in the command
        cmd = [executable_path, window_id, file_path]
        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print(f"Starting general recording with command: {cmd}")  # Optional: Debugging output

    def startCalibrationRecording(self, dot_id):
        # Calibration recording to a specific file based on the dot ID
        folder_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data"
        filename2 = f'gazeData_{dot_id}.txt'
        file_path2 = os.path.join(folder_path, filename2) 
        open(file_path2, 'w').close()  # Ensures the file is empty before starting to record
        executable_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/cpp_exec/Tobii_api_test1"
        window_id = str(self.winId().__int__())
        # Include the specific filename for this dot in the command
        cmd = [executable_path, window_id, file_path2]
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

    # Update startPlayback function similarly to handle timestamp and gaze points
    def startPlayback(self):
        folder_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data"
        filename1 = 'gazeData.txt'
        file_path3 = os.path.join(folder_path, filename1)

        gaze_data = []
        with open(file_path3, 'r') as file:
            gaze_data = file.readlines()

        # Pass self.labels directly, as it contains the tuples of identifiers and QLabel objects
        self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels)
        self.gaze_processor.update_gaze_signal.connect(lambda ts, x, y: self.gaze_overlay.update_gaze_position(x, y))
        self.gaze_processor.start()


    def stopPlayback(self):
        if self.gaze_processor and self.gaze_processor.isRunning():
            self.gaze_processor.terminate()

    def closeEvent(self, event):
        # Check if gaze_processor exists and call write_hit_counts_to_file
        if hasattr(self, 'gaze_processor') and self.gaze_processor is not None:
            self.gaze_processor.write_hit_counts_to_file()
        super().closeEvent(event)
