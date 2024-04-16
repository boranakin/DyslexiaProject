from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
import sys, time, subprocess, datetime, numpy as np
from datetime import datetime

def normalize_gaze_to_screen(gaze_point, screen_width, screen_height):
    x, y = gaze_point

    # Adjust the scale factor if values exceed [-1, 1]
    x_scale = max(abs(x), 1)
    y_scale = max(abs(y), 1)

    # Normalize x and y to screen coordinates, adjusting for any over-bound values
    screen_x = int(((x / x_scale) + 1) / 2 * screen_width)
    screen_y = int((1 - (y / y_scale)) / 2 * screen_height)

    return screen_x, screen_y

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