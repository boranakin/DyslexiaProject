from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
import sys, time, subprocess, datetime, numpy as np
from datetime import datetime

def normalize_gaze_to_screen(gaze_point, screen_width, screen_height):
    y_offset = 180  # Adjust this value as needed to correct the offset
    x, y = gaze_point
    screen_x = int((x + 1) / 2 * screen_width)
    screen_y = int((1 - y) / 2 * screen_height) + y_offset  # Subtract the offset here
    return screen_x, screen_y

class Overlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttributes()

    def setAttributes(self):
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

class HeatmapOverlay(Overlay):
    def __init__(self, gaze_points, parent=None):
        super().__init__(parent)
        self.gaze_points = gaze_points

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Assuming self.gaze_points is a list of tuples like [(x, y, timestamp), ...]
        # Extract just the x and y coordinates for the heatmap
        gaze_points_xy = [(point[0], point[1]) for point in self.gaze_points]

        # Generate the heatmap based on the x and y coordinates
        heatmap, xedges, yedges = np.histogram2d(*zip(*gaze_points_xy), bins=(50, 50))
        heatmap /= np.max(heatmap)  # Normalize

        # Draw the heatmap rectangles
        for i in range(len(xedges)-1):
            for j in range(len(yedges)-1):
                intensity = heatmap[i, j]
                color = QColor(255, 0, 0, int(255 * intensity))  # Map intensity to opacity
                qp.setBrush(color)
                qp.setPen(Qt.NoPen)  # No border
                # Draw rectangle
                qp.drawRect(QRect(int(xedges[i]), int(yedges[j]), int(xedges[i+1] - xedges[i]), int(yedges[j+1] - yedges[j])))

class GazeOverlay(Overlay):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gaze_x, self.gaze_y, self.circle_radius = 0, 0, 20

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setBrush(QColor(255, 165, 0, 128))
        qp.setPen(Qt.NoPen)
        qp.drawEllipse(self.gaze_x - self.circle_radius, self.gaze_y - self.circle_radius, 2 * self.circle_radius, 2 * self.circle_radius)

    def update_gaze_position(self, x, y):
        self.gaze_x, self.gaze_y = x, y
        self.update()

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

            # Iterate over word labels
            for identifier, label_obj, word in self.word_labels:
                if label_obj.geometry().contains(screen_x, screen_y):
                    key = (identifier, word)
                    self.word_hits[key]['count'] += 1
                    self.word_hits[key]['timestamps'].append(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"))

            self.update_gaze_signal.emit(timestamp, screen_x, screen_y)
            time.sleep(0.01)  # Adjust as needed

    def write_hit_counts_to_file(self, filename='word_hit_counts.txt'):
        with open(filename, 'w') as file:
            for (identifier, word), data in self.word_hits.items():
                timestamps_str = ', '.join(data['timestamps'])
                # Write both the identifier and word text
                file.write(f"{identifier} - {word}: {data['count']} - Timestamps: {timestamps_str}\n")


class GazeVisualizer(QMainWindow):
    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.screen_width, self.screen_height = screen_width, screen_height
        self.setupUI()

    def setupUI(self):
        self.setGeometry(100, 100, self.screen_width, self.screen_height)
        self.setWindowTitle('Gaze Tracker')
        self.setupLabels()
        self.setupButtons()
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.setGeometry(0, 0, self.screen_width, self.screen_height)

    def setupLabels(self):
        text = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."
        self.words = text.split()
        font = QFont('Calibri', 30)
        x, y = self.screen_width // 4, self.screen_height // 4
        line_height = QFontMetrics(font).height()
        self.labels = []  # This will now store tuples of (identifier, QLabel object, word text)
        line_number = 1
        word_index = 1

        for word in self.words:
            word_width = QFontMetrics(font).width(word)
            if x + word_width > self.screen_width - self.screen_width // 3:
                x = self.screen_width // 3
                y += line_height + 10
                line_number += 1
                word_index = 1  # Reset word index for the new line
            identifier = f"{line_number}-{word_index}"
            label = QLabel(word, self)
            label.setFont(font)
            label.resize(word_width, line_height)
            label.move(x, y)
            label.show()
            self.labels.append((identifier, label, word))  # Store identifier, QLabel, and word text
            x += word_width + 10
            word_index += 1


    def setupButtons(self):
        # Create a central widget and set a vertical layout on it
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create a horizontal layout for the buttons
        button_layout = QHBoxLayout()

        # Define your button functionalities and names
        functions = [
            (self.startPlayback, 'Playback'),
            (self.startRecording, 'Record'),
            (self.stopPlayback, 'Stop Playback'),
            (self.showHeatmapOnText, 'Project Heatmap'),
            (self.stopRecording, 'Stop Recording')
        ]

        # Create and add buttons to the horizontal layout
        for func, name in functions:
            button = QPushButton(name)
            button.clicked.connect(func)
            button.setFixedSize(230, 60)  # Set button size to 200x50 pixels
            #button.setStyleSheet("QPushButton { font-size: 22pt; background-color: #FEB046; border-radius: 15px;  }")  # Set button stylesheet for larger font size
            button.setStyleSheet("""
                QPushButton {
                    font-size: 18pt;
                    color: #FFFFFF;
                    border-radius: 15px;
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FF973C, stop:1 #FF973C);
                    padding: 5px;
                    border: 4px solid #DBDBDB;
                }
                QPushButton:hover {
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0, x2:1, y2:0,
                        stop:0 #7e57c2, stop:1 #9575cd);
                }
                QPushButton:pressed {
                    background-color: qlineargradient(
                        spread:pad, x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4a148c, stop:1 #6a1b9a);
                }
            """)
            button_layout.addWidget(button)

         # Add fixed spacing to main layout before adding buttons to move them higher up
        main_layout.addSpacing(1000)  # Adjust the value to control the height above the buttons

        # Add the horizontal layout with buttons to the main layout
        main_layout.addLayout(button_layout)

        # Optional: Adjust spacing and margins if needed
        main_layout.setSpacing(10)  # Set spacing between widgets
        main_layout.setContentsMargins(10, 10, 10, 30)  # Set margins of the layout
        button_layout.setSpacing(10)  # Set spacing between buttons

        # Simplified "Exit" button with a minimal stylesheet
        exit_button = QPushButton('X')
        exit_button.setFixedSize(50, 50)  # Smaller size for a minimalistic button
        exit_button.clicked.connect(self.close)  # Connects to the window's close function
        exit_button.setStyleSheet("""
            QPushButton {
                font-size: 18pt;
                color: #FFFFFF;
                border: 2px solid #555;
                background-color: #333;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #777;
            }
        """)
        button_layout.addWidget(exit_button)

    def startRecording(self):
        open('gazeData.txt', 'w').close()
        self.recording_process = subprocess.Popen(["C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/Tobii_api_test1", str(self.winId().__int__())])

    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()

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

        if len(gaze_points) > 0:
            self.heatmap_overlay = HeatmapOverlay(gaze_points, self)
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
