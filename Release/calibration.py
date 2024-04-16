# calibration.py

from PyQt5.QtWidgets import QWidget, QPushButton
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import QPoint

class CalibrationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())  # Match the parent size
        self.dots = [
            (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9),
            (0.5, 0.1), (0.5, 0.9), (0.5, 0.5)
        ]
        self.current_dot = 0
        self.parent = parent
        self.initUI()
        self.current_position = None  # Store current dot position

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
        #self.parent.resetCalibration()  # Reset calibration if necessary

    def nextDot(self):
        if self.current_dot > 0:
            self.parent.stopRecording()
        if self.current_dot < len(self.dots):
            self.parent.startCalibrationRecording(self.current_dot)
            self.updateCurrentPosition()
            self.current_dot += 1
            if self.current_dot == len(self.dots):
                self.next_button.setText("Finish")
        else:
            self.close()

    def updateCurrentPosition(self):
        # Calculate the position once when updating to a new dot
        dot_x = int(self.width() * self.dots[self.current_dot][0])
        dot_y = int(self.height() * self.dots[self.current_dot][1])
        self.current_position = QPoint(dot_x, dot_y)
        self.update()  # Redraw with the new dot

    def paintEvent(self, event):
        if self.current_position:
            qp = QPainter(self)
            qp.setPen(QPen(QColor(255, 0, 0), 10))
            qp.drawPoint(self.current_position)
