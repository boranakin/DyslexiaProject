import os
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import QPoint, Qt

import numpy as np
import sklearn
import joblib
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline

from ui_styles import get_button_style, get_exit_button_style

class CalibrationScreen(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())  # Match the parent size
        self.dots = [
            (-0.6, -0.5), (0.6, -0.5), (-0.6, 0.5), (0.6, 0.5),
            (0.0, -0.5), (0.0, 0.5), (0.0, 0.0),
            (-0.6, 0.0), (0.6, 0.0),
            (-0.6, -0.25), (0.6, -0.25), (-0.6, 0.25), (0.6, 0.25),
            (-0.3, -0.25), (0.3, -0.25), (-0.3, 0.25), (0.3, 0.25)  # New dots added in the middle at 0.3 and -0.3
        ]

        self.current_dot = 0
        self.parent = parent  # This will reference the GazeVisualizer instance
        self.initUI()
        self.current_position = None  # Store current dot position

    def initUI(self):
        # Setup dimensions and positioning
        button_width = int(self.parent.screen_width * 0.07 * self.parent.dpi_scale_factor)
        button_height = int(self.parent.screen_height * 0.04 * self.parent.dpi_scale_factor)
        margin_right = int(self.parent.screen_width * 0.02)
        margin_bottom = int(self.parent.screen_height * 0.50)

        # Next Button
        self.next_button = QPushButton("Next", self)
        self.next_button.clicked.connect(self.nextDot)
        self.next_button.setGeometry(
            self.width() - button_width - margin_right, 
            self.height() - button_height - margin_bottom, 
            button_width, button_height
        )
        self.next_button.setStyleSheet(get_button_style(button_height))

        # Analyze Now Button
        self.analyze_button = QPushButton("Analyze", self)
        self.analyze_button.clicked.connect(self.analyzeCalibrationData)
        self.analyze_button.setGeometry(
            self.width() - button_width - margin_right, 
            self.height() - button_height - margin_bottom - button_height - 10,  # Adjust the vertical spacing
            button_width, button_height
        )
        self.analyze_button.setStyleSheet(get_button_style(button_height))

        # Exit Button
        exit_button_size = int(self.parent.screen_height * 0.05 * self.parent.dpi_scale_factor)
        self.exit_button = QPushButton('X', self)
        self.exit_button.setFixedSize(exit_button_size, exit_button_size)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setStyleSheet(get_exit_button_style(exit_button_size))
        self.exit_button.setGeometry(
            self.width() - exit_button_size - margin_right,  # Align to the right
            margin_right,  # Small top margin
            exit_button_size, 
            exit_button_size
        )

        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        self.parent.hideUICalibration()  # Hide non-essential UI elements

    def closeEvent(self, event):
        super().closeEvent(event)
        self.parent.showUICalibration()  # Restore UI elements after calibration

    def nextDot(self):
        if self.current_dot < len(self.dots):
            if self.current_dot > 0:
                self.parent.stopRecording()
            self.parent.startCalibrationRecording(self.current_dot)
            self.updateCurrentPosition()
            self.current_dot += 1
            if self.current_dot == len(self.dots):
                self.next_button.setText("Finish")
                self.next_button.clicked.disconnect()  # Disconnect the existing connection
                self.next_button.clicked.connect(self.finishCalibration)  # Connect a new method to handle finish
        else:
            self.update()  # Update UI if needed

    def finishCalibration(self):
        self.parent.stopRecording()
        self.analyzeCalibrationData()
        self.close()  # Close the calibration screen or transition to next part

    def updateCurrentPosition(self):
        # Calculate position based on the -1 to 1 system
        dot_x = int((self.dots[self.current_dot][0] + 1) / 2 * self.width())
        dot_y = int((1 - self.dots[self.current_dot][1]) / 2 * self.height())  # Inverting the Y-axis transformation
        self.current_position = QPoint(dot_x, dot_y)
        self.update()

    def paintEvent(self, event):
        if self.current_position:
            qp = QPainter(self)
            qp.setPen(QPen(QColor(140, 40, 160), 0))
            qp.setBrush(QColor(140, 40, 160))
            dot_radius = 10
            qp.drawEllipse(self.current_position, dot_radius, dot_radius)

        #results_path = f'C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/calibration_results.txt'
        #file_path = f'C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/gazeData_{index}.txt'

    def analyzeCalibrationData(self):
        results_path = 'C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/calibration_results.txt'
        measured_points = []
        expected_points = []
        try:
            with open(results_path, 'w') as result_file:
                result_file.write("Calibration Results:\n")
                result_file.write("Dot Index, Expected (X,Y), Measured (X,Y), Distance\n")
                for index, expected in enumerate(self.dots):
                    file_path = f'C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/gazeData_{index}.txt'
                    if os.path.exists(file_path):
                        gaze_points = self.read_gaze_data(file_path)
                        average_gaze_point = self.calculate_average_gaze_point(gaze_points, expected)
                        if average_gaze_point != (None, None):
                            measured_points.append(average_gaze_point)
                            expected_points.append(expected)
                            distance = self.calculate_distance(average_gaze_point, expected)
                            result_file.write(f"{index}, {expected}, {average_gaze_point}, {distance:.2f}\n")
                    else:
                        print(f"File not found: {file_path}")

            # Fit the polynomial regression model and preprocess gaze data
            if measured_points and expected_points:
                self.fit_polynomial_regression(np.array(measured_points), np.array(expected_points))
                print("Polynomial regression model computed and saved.")
                # Call preprocess data method after the model is saved
                original_file = 'C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/gazeData.txt'
                transformed_file = 'C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data/gazeData_calibrated.txt'
                self.preprocess_gaze_data(original_file, transformed_file)
        except Exception as e:
            print(f"Error during calibration data analysis: {e}")

    def fit_polynomial_regression(self, measured_points, expected_points, degree=2):
        model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
        model.fit(measured_points, expected_points)
        joblib.dump(model, 'polynomial_regression_model.pkl')  # Save the model to disk

    def read_gaze_data(self, file_path):
        gaze_points = []
        with open(file_path, 'r') as file:
            for line in file:
                if 'Gaze point:' in line:
                    _, coords = line.split('Gaze point:')
                    x, y = map(float, coords.strip(' []\n').split(','))
                    # Directly append the x and y values as they are read
                    gaze_points.append((x, y))
        return gaze_points

    def calculate_average_gaze_point(self, gaze_points, expected):
        # Filter gaze points based on the threshold before averaging
        threshold = 0.15
        filtered_points = [point for point in gaze_points if abs(point[0] - expected[0]) <= threshold and abs(point[1] - expected[1]) <= threshold]
        if not filtered_points:
            return (None, None)
        total_x = sum(x for x, _ in filtered_points)
        total_y = sum(y for _, y in filtered_points)
        count = len(filtered_points)
        return (total_x / count, total_y / count) if count > 0 else (None, None)

    def calculate_distance(self, measured, expected):
        if not measured or None in measured:  # Check if measured is None or contains None
            return float('inf')  # Return 'infinite' distance to indicate no valid measurement
        return ((measured[0] - expected[0])**2 + (measured[1] - expected[1])**2)**0.5

    def preprocess_gaze_data(self, original_file, transformed_file):
        model = joblib.load('polynomial_regression_model.pkl')  # Load the model from disk
        with open(original_file, 'r') as infile, open(transformed_file, 'w') as outfile:
            for line in infile:
                if 'Gaze point:' in line:
                    timestamp_part, gaze_part = line.split('Gaze point:')
                    x, y = map(float, gaze_part.strip(' []\n').split(','))
                    transformed = model.predict([[x, y]])[0]
                    outfile.write(f"{timestamp_part}Gaze point: [{transformed[0]}, {transformed[1]}]\n")


