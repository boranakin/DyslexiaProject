# overlays.py
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QRect

import numpy as np

class Overlay(QWidget):
    """ Basic overlay that can be transparent to mouse events and other interactions. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttributes()

    def setAttributes(self):
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

class HeatmapOverlay(Overlay):
    """ Displays a heatmap based on gaze points. """
    def __init__(self, gaze_points, word_hit_data, parent=None):
        super().__init__(parent)
        self.gaze_points = gaze_points
        self.word_hit_data = word_hit_data
        self.bins = max(min(parent.width(), parent.height()) // 100, 10)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        gaze_points_xy = [(point[0], point[1]) for point in self.gaze_points]
        heatmap, xedges, yedges = np.histogram2d(*zip(*gaze_points_xy), bins=(self.bins, self.bins))
        heatmap /= np.max(heatmap)

        for i in range(len(xedges)-1):
            for j in range(len(yedges)-1):
                intensity = heatmap[i, j]
                color = QColor(255, 0, 0, int(255 * intensity))
                qp.setBrush(color)
                qp.setPen(Qt.NoPen)
                qp.drawRect(QRect(int(xedges[i]), int(yedges[j]), int(xedges[i+1] - xedges[i]), int(yedges[j+1] - yedges[j])))

        qp.setPen(QColor(0, 0, 0))
        font = QFont('Arial', 10)
        qp.setFont(font)
        qp.drawText(10, 20, "Test Timestamp")

class GazeOverlay(Overlay):
    """ Displays an overlay of the current gaze position. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gaze_x, self.gaze_y = 0, 0
        self.update_base_circle_radius()

    def update_base_circle_radius(self):
        self.base_circle_radius = min(self.parent().width(), self.parent().height()) * 0.03

    def paintEvent(self, event):
        self.update_base_circle_radius()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setBrush(QColor(255, 165, 0, 128))
        qp.setPen(Qt.NoPen)
        x = int(self.gaze_x - self.base_circle_radius)
        y = int(self.gaze_y - self.base_circle_radius)
        diameter = int(2 * self.base_circle_radius)
        qp.drawEllipse(x, y, diameter, diameter)

    def update_gaze_position(self, x, y):
        self.gaze_x, self.gaze_y = x, y
        self.update()

#hit count format: typesetting, 2, (2024-03-02 16:39:30, 2024-03-02 16:40:30)