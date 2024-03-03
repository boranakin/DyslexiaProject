from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QVBoxLayout, QDialog
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
import sys
import time
import subprocess
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

def normalize_gaze_to_screen(gaze_point, screen_width, screen_height):
    x, y = gaze_point
    screen_x = (x + 1) / 2 * screen_width
    screen_y = (1 - y) / 2 * screen_height
    return int(screen_x), int(screen_y)

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

                # Convert float values to integers
                x1 = int(xedges[i])
                y1 = int(yedges[j])
                x2 = int(xedges[i+1])
                y2 = int(yedges[j+1])
                width = x2 - x1
                height = y2 - y1

                rect = QRect(x1, y1, width, height)
                qp.drawRect(rect)


class GazeOverlay(QWidget):
    def __init__(self, parent=None):
        super(GazeOverlay, self).__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.gaze_x = 0
        self.gaze_y = 0
        self.circle_radius = 20

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 165, 0, 128))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.gaze_x - self.circle_radius, self.gaze_y - self.circle_radius, self.circle_radius * 2, self.circle_radius * 2)

    def update_gaze_position(self, x, y):
        self.gaze_x = x
        self.gaze_y = y
        self.update()

class GazeDataProcessor(QThread):
    update_gaze_signal = pyqtSignal(int, int)

    def __init__(self, gaze_data, screen_width, screen_height, word_labels, words):
        super().__init__()
        self.gaze_data = gaze_data
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.word_labels = word_labels
        self.words = words
        self.hit_counts = [0] * len(word_labels)
        self.hit_timestamps = [[] for _ in word_labels]
        
    def run(self):
        for line in self.gaze_data:
            if 'Gaze point:' in line:
                gaze_point = line.split('[')[1].split(']')[0]
                x, y = map(float, gaze_point.split(','))
                screen_x, screen_y = normalize_gaze_to_screen((x, y), self.screen_width, self.screen_height)
                self.update_gaze_signal.emit(screen_x, screen_y)
                self.check_gaze_hit(screen_x, screen_y)
                time.sleep(0.1)
        self.write_hit_counts_to_file()

    def check_gaze_hit(self, x, y):
        for index, label in enumerate(self.word_labels):
            if label.geometry().contains(x, y):
                self.hit_counts[index] += 1
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.hit_timestamps[index].append(current_time)

    def write_hit_counts_to_file(self):
        with open('word_hit_counts.txt', 'w') as file:
            for word, count, timestamps in zip(self.words, self.hit_counts, self.hit_timestamps):
                timestamps_str = ', '.join(timestamps)
                file.write(f"{word}: {count} - Timestamps: {timestamps_str}\n")

class GazeVisualizer(QMainWindow):
    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.initUI(screen_width, screen_height)
        self.recording_process = None

    def startRecording(self, calibration_mode=False):
        open('gazeData.txt', 'w').close()
        window_handle = self.winId()
        window_handle_int = int(window_handle.__int__())
        cpp_executable_path = "path/to/executable"
        self.recording_process = subprocess.Popen([cpp_executable_path, str(window_handle_int)])

    def stopRecording(self):
        if self.recording_process:
            self.recording_process.terminate()

    def createAndDisplayHeatmap(self, gaze_points):
        screen_gaze_points = [(x * self.width() / 2 + self.width() / 2, -y * self.height() / 2 + self.height() / 2) for x, y in gaze_points]
        heatmap, xedges, yedges = np.histogram2d([x for x, y in screen_gaze_points], [y for x, y in screen_gaze_points], bins=(50, 50))
        fig, ax = plt.subplots()
        cax = ax.imshow(heatmap.T, extent=[0, self.width(), 0, self.height()], origin='lower', cmap='hot', interpolation='nearest')
        fig.colorbar(cax)
        ax.set_title('Gaze Heatmap')
        ax.set_xlabel('Screen X')
        ax.set_ylabel('Screen Y')
        dialog = QDialog(self)
        dialog.setWindowTitle("Gaze Heatmap")
        layout = QVBoxLayout(dialog)
        canvas = FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)
        dialog.exec_()

    def showHeatmap(self):
        with open('gazeData.txt', 'r') as file:
            gaze_data = file.readlines()
        gaze_points = []
        for line in gaze_data:
            if 'Gaze point:' in line:
                gaze_point = line.split('[')[1].split(']')[0]
                x, y = map(float, gaze_point.split(','))
                gaze_points.append((x, y))
        self.createAndDisplayHeatmap(gaze_points)

    def showHeatmapOnText(self):
        with open('gazeData.txt', 'r') as file:
            gaze_data = file.readlines()
        gaze_points = []
        for line in gaze_data:
            if 'Gaze point:' in line:
                gaze_point = line.split('[')[1].split(']')[0]
                x, y = map(float, gaze_point.split(','))
                screen_x, screen_y = normalize_gaze_to_screen((x, y), self.width(), self.height())
                gaze_points.append((screen_x, screen_y))
        self.heatmap_overlay = HeatmapOverlay(gaze_points, self)
        self.heatmap_overlay.setGeometry(0, 0, self.width(), self.height())
        self.heatmap_overlay.show()

    def initUI(self, screen_width, screen_height):
        margin_horizontal = screen_width // 3
        margin_vertical = screen_height // 4
        self.text = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."
        self.words = self.text.split()
        font = QFont('Calibri', 22)
        fm = QFontMetrics(font)
        self.labels = []
        x = margin_horizontal
        y = margin_vertical
        line_height = fm.height()
        for word in self.words:
            word_width = fm.width(word)
            if x + word_width > screen_width - margin_horizontal:
                x = margin_horizontal
                y += line_height + 10
            label = QLabel(word, self)
            label.setFont(font)
            label.resize(word_width, line_height)
            label.move(x, y)
            label.show()
            self.labels.append(label)
            x += word_width + 10
        self.setGeometry(100, 100, screen_width, screen_height)
        self.setWindowTitle('Gaze Tracker')
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.setGeometry(0, 0, screen_width, screen_height)
        button_width = 150
        button_height = 50
        button_x = (screen_width - button_width * 2 - 20) // 2
        button_y = screen_height - button_height - 20

        self.playback_button = QPushButton('Playback', self)
        self.playback_button.clicked.connect(self.startPlayback)
        self.playback_button.setGeometry(button_x, button_y, button_width, button_height)
        self.playback_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        
        self.record_button = QPushButton('Record', self)
        self.record_button.setGeometry(button_x + button_width + 20, button_y, button_width, button_height)
        self.record_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.record_button.clicked.connect(self.startRecording)
        
        self.stop_button = QPushButton('Stop Playback', self)
        self.stop_button.setGeometry(button_x + button_width * 2 + 40, button_y, button_width, button_height)
        self.stop_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.stop_button.clicked.connect(self.stopPlayback)
        
        self.heatmap_on_text_button = QPushButton('Project Heatmap', self)
        self.heatmap_on_text_button.setGeometry(button_x + button_width * 3 + 60, button_y, button_width, button_height)
        self.heatmap_on_text_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.heatmap_on_text_button.clicked.connect(self.showHeatmapOnText)
        
        self.heatmap_button = QPushButton('Show Heatmap', self)
        self.heatmap_button.setGeometry(button_x + button_width * 4 + 80, button_y, button_width, button_height)
        self.heatmap_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.heatmap_button.clicked.connect(self.showHeatmap)
        
        self.stop_record_button = QPushButton('Stop Recording', self)
        self.stop_record_button.setGeometry(button_x + button_width * 5 + 100, button_y, button_width, button_height)
        self.stop_record_button.setStyleSheet("QPushButton { background-color: orange; font-size: 18px; }")
        self.stop_record_button.clicked.connect(self.stopRecording)

    def startPlayback(self):
        with open('gazeData.txt', 'r') as file:
            gaze_data = file.readlines()
        self.gaze_processor = GazeDataProcessor(gaze_data, self.width(), self.height(), self.labels, self.words)
        self.gaze_processor.update_gaze_signal.connect(self.gaze_overlay.update_gaze_position)
        self.gaze_processor.start()

    def stopPlayback(self):
        if self.gaze_processor and self.gaze_processor.isRunning():
            self.gaze_processor.terminate()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        color = QColor(255, 255, 255, 128)
        painter.setBrush(color)
        for label in self.labels:
            rect = label.geometry()
            painter.drawRect(rect)

app = QApplication(sys.argv)
screen_resolution = app.desktop().screenGeometry()
width, height = screen_resolution.width(), screen_resolution.height()
main_window = GazeVisualizer(width, height)
main_window.showFullScreen()
sys.exit(app.exec_())