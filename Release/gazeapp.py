from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QTextEdit, QVBoxLayout, QDialog
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
import sys
import time
import subprocess  # Import subprocess module
import datetime  # Import datetime module
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

class HeatmapOverlay(QWidget):
    def __init__(self, gaze_points, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.gaze_points = gaze_points
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Generate the heatmap matrix based on gaze points
        heatmap, xedges, yedges = np.histogram2d([x for x, y in self.gaze_points], [y for x, y in self.gaze_points], bins=(50, 50))

        # Normalize the heatmap for display purposes
        heatmap = heatmap / np.max(heatmap)

        # Map the heatmap values to colors and draw rectangles
        for i in range(len(xedges)-1):
            for j in range(len(yedges)-1):
                intensity = heatmap[i, j]
                color = QColor(255, 0, 0, int(255 * intensity))  # Red with variable opacity
                qp.setBrush(color)
                qp.setPen(Qt.NoPen)
                rect = QRect(xedges[i], yedges[j], xedges[i+1] - xedges[i], yedges[j+1] - yedges[j])
                qp.drawRect(rect)

def normalize_gaze_to_screen(gaze_point, screen_width, screen_height):
    x, y = gaze_point

    # Calculate the proportional position on the screen
    screen_x = (x + 1) / 2 * screen_width
    screen_y = (1 - y) / 2 * screen_height

    # Optionally, you can clamp to screen bounds
    #screen_x = max(0, min(screen_width, screen_x))
    #screen_y = max(0, min(screen_height, screen_y))

    return int(screen_x), int(screen_y)


# Custom widget for displaying gaze points
class GazeOverlay(QWidget):
    def __init__(self, parent=None):
        super(GazeOverlay, self).__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.gaze_x = 0
        self.gaze_y = 0
        self.circle_radius = 20  # Set the radius of the circle here
        self.y_axis_offset = 0  # Adjust this value to pull down the circle

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 165, 0, 128))  # Semi-transparent orange
        painter.setPen(Qt.NoPen)
        # Draw a circle with the specified radius
        painter.drawEllipse(self.gaze_x - self.circle_radius, self.gaze_y - self.circle_radius, self.circle_radius * 2, self.circle_radius * 2)

    def update_gaze_position(self, x, y):
        self.gaze_x = x
        self.gaze_y = y + self.y_axis_offset  # Apply the Y-axis offset here
        self.update()


# Thread class for processing gaze data
class GazeDataProcessor(QThread):
    update_gaze_signal = pyqtSignal(int, int)

    def __init__(self, gaze_data, screen_width, screen_height, word_labels, words):
        super().__init__()
        self.gaze_data = gaze_data
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.word_labels = word_labels
        self.words = words
        self.hit_counts = [0] * len(word_labels)  # Initialize hit counts for each word
        self.hit_timestamps = [[] for _ in word_labels]  # Initialize timestamps for each word
        
    def run(self):
        for line in self.gaze_data:
            if 'Gaze point:' in line:
                gaze_point = line.split('[')[1].split(']')[0]
                x, y = map(float, gaze_point.split(','))
                screen_x, screen_y = normalize_gaze_to_screen((x, y), self.screen_width, self.screen_height)
                # Adjust the y-coordinate by a fixed offset (e.g., 50 pixels)
                screen_y += 0 # Adjust this value as needed to correct the offset

                # Emit the signal with the adjusted gaze position
                self.update_gaze_signal.emit(screen_x, screen_y)

                # Check if gaze hits any word box
                self.check_gaze_hit(screen_x, screen_y)

                # Sleep to control the update rate
                time.sleep(0.1)

        # Write hit counts to file after processing all data
        self.write_hit_counts_to_file()

    def check_gaze_hit(self, x, y):
        for index, label in enumerate(self.word_labels):
            if label.geometry().contains(x, y):
                self.hit_counts[index] += 1
                # Record the timestamp of the hit
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.hit_timestamps[index].append(current_time)

    def write_hit_counts_to_file(self):
        with open('word_hit_counts.txt', 'w') as file:
            for word, count, timestamps in zip(self.words, self.hit_counts, self.hit_timestamps):
                timestamps_str = ', '.join(timestamps)
                file.write(f"{word}: {count} - Timestamps: {timestamps_str}\n")

    # In GazeVisualizer, modify startPlayback method to pass labels to GazeDataProcessor
    def startPlayback(self):
        # Read gaze data from file
        with open('gazeData.txt', 'r') as file:
            gaze_data = file.readlines()

        # Initialize and start the gaze data processor with word labels
        self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels)
        self.gaze_processor.update_gaze_signal.connect(self.gaze_overlay.update_gaze_position)
        self.gaze_processor.start()


# Main window class
class GazeVisualizer(QMainWindow):
    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.initUI(screen_width, screen_height)
        self.recording_process = None  # Initialize a variable to store the subprocess

    def startRecording(self, calibration_mode=False):
        # Clear the gazeData.txt file before starting a new recording
        open('gazeData.txt', 'w').close()

        # Retrieve the window handle
        #window_handle = int(self.winId())
        window_handle = self.winId()
        window_handle_int = int(window_handle.__int__())
        # Path to the compiled C++ executable
        cpp_executable_path = "C:/Users/borana/Desktop/ENS491/Tobii Kihleksi/TobiiProject/Release/Tobii_api_test1.exe"
        
        # Start the C++ executable as a subprocess with window handle as argument
        self.recording_process = subprocess.Popen([cpp_executable_path, str(window_handle_int)])

    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()  # Terminate the subprocess

    def createAndDisplayHeatmap(self, gaze_points):
        # Convert gaze points to screen coordinates
        screen_gaze_points = [(x * self.width() / 2 + self.width() / 2, -y * self.height() / 2 + self.height() / 2) for x, y in gaze_points]

        # Create a 2D histogram of gaze points
        heatmap, xedges, yedges = np.histogram2d([x for x, y in screen_gaze_points], [y for x, y in screen_gaze_points], bins=(50, 50))

        # Create a figure for the heatmap
        fig, ax = plt.subplots()
        cax = ax.imshow(heatmap.T, extent=[0, self.width(), 0, self.height()], origin='lower', cmap='hot', interpolation='nearest')
        fig.colorbar(cax)
        ax.set_title('Gaze Heatmap')
        ax.set_xlabel('Screen X')
        ax.set_ylabel('Screen Y')

        # Display the heatmap in a separate window
        dialog = QDialog(self)
        dialog.setWindowTitle("Gaze Heatmap")
        layout = QVBoxLayout(dialog)
        canvas = FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)
        dialog.exec_()

    def showHeatmap(self):
        # Read gaze data from file
        with open('gazeData.txt', 'r') as file:
            gaze_data = file.readlines()

        # Process gaze data to extract x, y coordinates
        gaze_points = []
        for line in gaze_data:
            if 'Gaze point:' in line:
                gaze_point = line.split('[')[1].split(']')[0]
                x, y = map(float, gaze_point.split(','))
                gaze_points.append((x, y))

        # Call a function to create and display the heatmap
        self.createAndDisplayHeatmap(gaze_points)

    def showHeatmapOnText(self):
        # Process gaze data to extract x, y coordinates
        gaze_points = []
        for line in self.gaze_data:
            if 'Gaze point:' in line:
                gaze_point = line.split('[')[1].split(']')[0]
                x, y = map(float, gaze_point.split(','))
                # Convert to screen coordinates
                screen_x, screen_y = normalize_gaze_to_screen((x, y), self.width(), self.height())
                gaze_points.append((screen_x, screen_y))

        # Create and display the heatmap overlay
        self.heatmap_overlay = HeatmapOverlay(gaze_points, self)
        self.heatmap_overlay.setGeometry(0, 0, self.width(), self.height())
        self.heatmap_overlay.show()

    def initUI(self, screen_width, screen_height):

        margin_horizontal = screen_width // 3
        margin_vertical = screen_height // 4
        
        self.text ="Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."
        self.words = self.text.split()

        # Set font for the labels
        font = QFont('Calibri', 22)
        fm = QFontMetrics(font)
        self.labels = []

        # x, y = 10, 40 Starting position for the first word
        x = margin_horizontal
        y = margin_vertical
        line_height = fm.height()

        for word in self.words:
            word_width = fm.width(word)

            # Check if the word exceeds the screen width
            if x + word_width > screen_width - margin_horizontal:
            #if x + word_width > screen_width:
                #x = 10  Reset X position
                x = margin_horizontal
                y += line_height + 10  # Move to the next line

            label = QLabel(word, self)
            label.setFont(font)
            label.resize(word_width, line_height)
            label.move(x, y)
            label.show()
            self.labels.append(label)

            x += word_width + 10  # Space between words

        self.setGeometry(100, 100, screen_width, screen_height)
        self.setWindowTitle('Gaze Tracker')

        # Set up the gaze overlay
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.setGeometry(0, 0, screen_width, screen_height)

        # Button dimensions and positions
        button_width = 150
        button_height = 50
        button_x = (screen_width - button_width * 2 - 20) // 2
        button_y = screen_height - button_height - 20

        # Playback button
        self.playback_button = QPushButton('Playback', self)
        self.playback_button.clicked.connect(self.startPlayback)
        self.playback_button.setGeometry(button_x, button_y, button_width, button_height)
        self.playback_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")

        # Record button
        self.record_button = QPushButton('Record', self)
        self.record_button.setGeometry(button_x + button_width + 20, button_y, button_width, button_height)
        self.record_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.record_button.clicked.connect(self.startRecording)
        
        # Stop Playback button
        self.stop_button = QPushButton('Stop Playback', self)
        self.stop_button.setGeometry(button_x + button_width * 2 + 40, button_y, button_width, button_height)
        self.stop_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.stop_button.clicked.connect(self.stopPlayback)

        #On-Text Heatmap button
        self.heatmap_button = QPushButton('Show Heatmap on Text', self)
        self.heatmap_button.setGeometry(button_x + button_width * 4 + 80, button_y, button_width, button_height)
        self.heatmap_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.heatmap_button.clicked.connect(self.showHeatmapOnText)

        # Heatmap button
        self.heatmap_button = QPushButton('Show Heatmap', self)
        self.heatmap_button.setGeometry(button_x + button_width * 4 + 80, button_y, button_width, button_height)
        self.heatmap_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.heatmap_button.clicked.connect(self.showHeatmap)

        # Stop Recording button
        self.stop_record_button = QPushButton('Stop Recording', self)
        self.stop_record_button.setGeometry(button_x + button_width * 3 + 60, button_y, button_width, button_height)
        self.stop_record_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.stop_record_button.clicked.connect(self.stopRecording)
        
        
    def startPlayback(self):
        # Read gaze data from file
        with open('gazeData.txt', 'r') as file:
            gaze_data = file.readlines()
        # Initialize and start the gaze data processor with word labels
        self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels, self.words)
        self.gaze_processor.update_gaze_signal.connect(self.gaze_overlay.update_gaze_position)
        self.gaze_processor.start()
        
    def stopPlayback(self):
        if self.gaze_processor and self.gaze_processor.isRunning():
            self.gaze_processor.terminate()  # Terminate the gaze data processor thread

    def paintEvent(self, event):
        painter = QPainter(self)
        #painter.setPen(QColor(0, 0, 0))
        painter.setPen(Qt.NoPen)  # No border for the rectangles

        # Draw semi-transparent rectangles
        color = QColor(255, 255, 255, 128)  # Semi-transparent white
        painter.setBrush(color)

        for label in self.labels:
            rect = label.geometry()
            painter.drawRect(rect)  # Draw rectangle around each word

# Read gaze data from file
with open('gazeData.txt', 'r') as file:
    gaze_data = file.readlines()

# Initialize the application
app = QApplication(sys.argv)
screen_resolution = app.desktop().screenGeometry()
width, height = screen_resolution.width(), screen_resolution.height()

# Create and display the main window
main_window = GazeVisualizer(width, height)
main_window.showFullScreen()
sys.exit(app.exec_())
