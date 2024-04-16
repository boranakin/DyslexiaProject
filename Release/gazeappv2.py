from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
import sys, time, subprocess, datetime, numpy as np
from datetime import datetime

class CalibrationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())  # Same size as the parent
        self.dots = [
            (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9),
            (0.5, 0.1), (0.5, 0.9), (0.5, 0.5)
        ]
        self.current_dot = 0
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.next_button = QPushButton("Next", self)
        self.next_button.clicked.connect(self.nextDot)
        self.next_button.setGeometry(self.width() - 100, self.height() - 50, 80, 30)
        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        self.parent.hideUI()  # Hide other UI elements

    def closeEvent(self, event):
        super().closeEvent(event)
        self.parent.showUI()  # Restore UI elements

    def nextDot(self):
        if self.current_dot > 0:
            self.parent.stopRecording()
        if self.current_dot < len(self.dots):
            self.parent.startCalibrationRecording(self.current_dot)
            self.current_dot += 1
            if self.current_dot == len(self.dots):
                self.next_button.setText("Finish")
        else:
            self.close()

        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setPen(QPen(QColor(255, 0, 0), 10))
        dot_x = int(self.width() * self.dots[self.current_dot - 1][0])
        dot_y = int(self.height() * self.dots[self.current_dot - 1][1])
        qp.drawPoint(QPoint(dot_x, dot_y))


def normalize_gaze_to_screen(gaze_point, screen_width, screen_height):
    x, y = gaze_point

    # Adjust the scale factor if values exceed [-1, 1]
    x_scale = max(abs(x), 1)
    y_scale = max(abs(y), 1)

    # Normalize x and y to screen coordinates, adjusting for any over-bound values
    screen_x = int(((x / x_scale) + 1) / 2 * screen_width)
    screen_y = int((1 - (y / y_scale)) / 2 * screen_height)

    return screen_x, screen_y

# Convert string timestamps to datetime objects and calculate dwell times
def calculate_dwell_times(gaze_data):
    dwell_data = []
    last_point = None
    last_timestamp = None
    accumulated_time = 0

    for line in gaze_data:
        timestamp_str, _, gaze_str = line.partition('] Gaze point: ')
        timestamp = datetime.strptime(timestamp_str.strip('['), "%Y-%m-%d %H:%M:%S.%f")
        gaze_point = tuple(float(val) for val in gaze_str.strip('[]').split(', '))

        if last_point is not None:
            time_diff = (timestamp - last_timestamp).total_seconds()
            distance = ((gaze_point[0] - last_point[0]) ** 2 + (gaze_point[1] - last_point[1]) ** 2) ** 0.5
            # Check if the gaze is still within a fixation (this threshold may need to be adjusted)
            if distance < 0.1 and time_diff < 1:
                accumulated_time += time_diff
            else:
                # The fixation has ended; save the accumulated dwell time for the last point
                dwell_data.append((last_timestamp, last_point[0], last_point[1], accumulated_time))
                accumulated_time = 0  # Reset for the next fixation

        last_point = gaze_point
        last_timestamp = timestamp

    # Don't forget to add the last fixation's dwell time
    if accumulated_time > 0:
        dwell_data.append((last_timestamp, last_point[0], last_point[1], accumulated_time))

    return dwell_data

## NEWWWW
def parse_word_hit_counts(file_path):
    word_hit_data = []
    with open(file_path, 'r') as file:
        for line in file:
            # Assuming the file format is consistent with your example
            parts = line.strip().split(' - ')
            identifier, count_str = parts[0], parts[1]
            timestamps_str = parts[3] if len(parts) > 3 else ""
            # Extracting coordinates from the identifier
            coords = tuple(map(float, identifier.split('-')))
            count = int(count_str.split(': ')[1])
            timestamps = timestamps_str.split(', ')
            word_hit_data.append({
                'coords': coords,
                'count': count,
                'timestamps': timestamps
            })
    return word_hit_data

# Example usage
gaze_data_example = [
    "[2024-03-25 12:59:56.961] Gaze point: [-0.615992, 0.437235]",
    # ... all your other gaze data lines ...
]
dwell_data = calculate_dwell_times(gaze_data_example)

class Overlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttributes()

    def setAttributes(self):
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

class HeatmapOverlay(Overlay):
    def __init__(self, gaze_points, word_hit_data, parent=None):
        super().__init__(parent)
        self.gaze_points = gaze_points
        self.word_hit_data = word_hit_data
        # Dynamically adjust the number of bins based on the screen size
        self.bins = max(min(parent.width(), parent.height()) // 100, 10)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Drawing the heatmap based on gaze points
        gaze_points_xy = [(point[0], point[1]) for point in self.gaze_points]
        heatmap, xedges, yedges = np.histogram2d(*zip(*gaze_points_xy), bins=(self.bins, self.bins))
        heatmap /= np.max(heatmap)  # Normalize

        for i in range(len(xedges)-1):
            for j in range(len(yedges)-1):
                intensity = heatmap[i, j]
                color = QColor(255, 0, 0, int(255 * intensity))
                qp.setBrush(color)
                qp.setPen(Qt.NoPen)
                qp.drawRect(QRect(int(xedges[i]), int(yedges[j]), int(xedges[i+1] - xedges[i]), int(yedges[j+1] - yedges[j])))

        # Ensure the text is visible by setting a contrasting color
        qp.setPen(QColor(0, 0, 0))  # Black color  # White color for visibility
        font = QFont('Arial', 10)  # Larger font size for visibility
        qp.setFont(font)

        # Debug: Draw a fixed piece of text to ensure drawing works
        qp.drawText(10, 20, "Test Timestamp")

        for word_data in self.word_hit_data:
            if word_data['count'] > 1:
                # Make sure coordinates are correctly mapped
                x, y = self.adjust_coordinates(word_data['coords'])
                timestamp_summary = self.generate_timestamp_summary(word_data['timestamps'])
                qp.drawText(x, y, timestamp_summary)

    def adjust_coordinates(self, coords):
        screen_x, screen_y = coords
        return screen_x, screen_y  # Return adjusted coordinates

    def generate_timestamp_summary(self, timestamps):
        # Logic to generate a summary string from timestamps
        return f"Count: {len(timestamps)}"

class GazeOverlay(Overlay):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gaze_x, self.gaze_y = 0, 0
        # Calculate the base circle radius dynamically based on the parent size
        # The factor (e.g., 0.06 for 6%) determines the size of the pointer relative to the window
        self.update_base_circle_radius()

    def update_base_circle_radius(self):
        # Dynamically update the base circle radius based on the current window size
        self.base_circle_radius = min(self.parent().width(), self.parent().height()) * 0.03

    def paintEvent(self, event):
        self.update_base_circle_radius()  # Ensure the base radius is updated to reflect any window resizing
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setBrush(QColor(255, 165, 0, 128))  # Semi-transparent orange
        qp.setPen(Qt.NoPen)
        # Ensure x, y, and base_circle_radius are treated as integers
        x = int(self.gaze_x - self.base_circle_radius)
        y = int(self.gaze_y - self.base_circle_radius)
        diameter = int(2 * self.base_circle_radius)  # Diameter needs to be an integer as well
        qp.drawEllipse(x, y, diameter, diameter)

    def update_gaze_position(self, x, y):
        self.gaze_x, self.gaze_y = x, y
        self.update()  # Trigger a repaint with the updated position


#hit count format: typesetting, 2, (2024-03-02 16:39:30, 2024-03-02 16:40:30)

class GazeDataProcessor(QThread):
    update_gaze_signal = pyqtSignal(datetime, int, int)

    def __init__(self, gaze_data, screen_width, screen_height, word_labels):
        super().__init__()
        self.gaze_data = gaze_data
        self.screen_width = screen_width
        self.screen_height = screen_height
        # word_labels now contains tuples of (identifier, QLabel object, word text)
        self.word_labels = word_labels
        # Initialize with tuples of (identifier, word text)
        self.word_hits = {(label[0], label[2]): {'count': 0, 'timestamps': []} for label in word_labels}

    def run(self):
        for line in self.gaze_data:
            timestamp_str, gaze_str = line.split('] Gaze point: ')
            timestamp = datetime.strptime(timestamp_str[1:], "%Y-%m-%d %H:%M:%S.%f")
            gaze_point = [float(val) for val in gaze_str.strip()[1:-1].split(',')]
            screen_x, screen_y = normalize_gaze_to_screen(gaze_point, self.screen_width, self.screen_height)

            for identifier, label_obj, word in self.word_labels:
                if label_obj.geometry().contains(screen_x, screen_y):
                    key = (identifier, word)
                    # Ensure the word hit entry includes screen coordinates
                    if key not in self.word_hits:
                        self.word_hits[key] = {'count': 0, 'timestamps': [], 'coords': (screen_x, screen_y)}
                    else:
                        self.word_hits[key]['coords'] = (screen_x, screen_y)  # Always update to the latest coordinates
                    self.word_hits[key]['count'] += 1
                    self.word_hits[key]['timestamps'].append(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"))

            self.update_gaze_signal.emit(timestamp, screen_x, screen_y)
            time.sleep(0.02)
            
    def write_hit_counts_to_file(self, filename='word_hit_counts.txt'):
        with open(filename, 'w') as file:
            for (identifier, word), data in self.word_hits.items():
                timestamps_str = ', '.join(data['timestamps'])
                # Assume each word hit data now includes the last known screen coordinates
                # It might require you to update the self.word_hits[key] structure elsewhere to include these coordinates.
                # For example, self.word_hits[key] could be updated to include 'coords': (screen_x, screen_y) when the hit is registered
                if 'coords' in data:
                    coords = data['coords']  # This would be a tuple like (screen_x, screen_y)
                    file.write(f"{identifier} - {word}: {data['count']} - Coords: {coords[0]}, {coords[1]} - Timestamps: {timestamps_str}\n")
                else:
                    file.write(f"{identifier} - {word}: {data['count']} - Timestamps: {timestamps_str}\n")


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
        # General recording to a default file, not specific to calibration
        default_filename = 'gazeData.txt'
        open(default_filename, 'w').close()  # Ensures the file is empty before starting to record
        executable_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/Tobii_api_test1"
        window_id = str(self.winId().__int__())  # Convert window handle to string
        # Now include the default filename in the command
        cmd = [executable_path, window_id, default_filename]
        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Starting general recording with command: {cmd}")  # Optional: Debugging output

    def startCalibrationRecording(self, dot_id):
        # Calibration recording to a specific file based on the dot ID
        filename = f'gazeData_{dot_id}.txt'
        open(filename, 'w').close()  # Ensures the file is empty before starting to record
        executable_path = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/Tobii_api_test1"
        window_id = str(self.winId().__int__())
        # Include the specific filename for this dot in the command
        cmd = [executable_path, window_id, filename]
        self.recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Starting calibration recording for dot {dot_id} with command: {cmd}")

    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process = None
            print("Recording stopped.")  # Optional: Confirmation message for stopping the recording

    def showHeatmapOnText(self):
        gaze_points = []
        with open('gazeData.txt', 'r') as file:
            for line in file:
                if 'Gaze point:' in line:
                    _, gaze_str = line.split('] Gaze point: ')
                    gaze_point = [float(val) for val in gaze_str.strip()[1:-1].split(',')]
                    # Normalize gaze points for the screen dimensions
                    screen_x, screen_y = normalize_gaze_to_screen(gaze_point, self.width(), self.height())
                    gaze_points.append((screen_x, screen_y))

        # Debugging: Print the number of parsed gaze points
        print(f"Number of parsed gaze points: {len(gaze_points)}")
        word_hit_file_path = "C:\\Users\\Nazli\\Desktop\\DyslexiaProject-main\\Release\\word_hit_counts.txt"
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
        gaze_data = []
        with open('gazeData.txt', 'r') as file:
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

app = QApplication(sys.argv)
main_window = GazeVisualizer(app.desktop().screenGeometry().width(), app.desktop().screenGeometry().height())
main_window.showFullScreen()
sys.exit(app.exec_())