import sys, time, os
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import matplotlib.pyplot as plt

def normalize_gaze_to_screen(gaze_point, screen_width, screen_height):
    x, y = gaze_point
    x_scale = max(abs(x), 1)
    y_scale = max(abs(y), 1)
    screen_x = int(((x / x_scale) + 1) / 2 * screen_width)
    screen_y = int((1 - (y / y_scale)) / 2 * screen_height)
    return screen_x, screen_y

def parse_word_hit_counts(file_path):
    word_hit_data = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.strip().split(' - ')
            identifier, count_str = parts[0], parts[1]
            timestamps_str = parts[3] if len(parts) > 3 else ""
            coords = tuple(map(float, identifier.split('-')))
            count = int(count_str.split(': ')[1])
            timestamps = timestamps_str.split(', ')
            word_hit_data.append({'coords': coords, 'count': count, 'timestamps': timestamps})
    return word_hit_data

class GazeDataProcessor(QThread):
    update_gaze_signal = pyqtSignal(datetime, int, int)

    def __init__(self, gaze_data, screen_width, screen_height, word_labels, user_directory=None):
        super().__init__()
        self.gaze_data = gaze_data
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.word_labels = word_labels
        self.user_directory = user_directory
        self.word_hits = {label[0]: {'count': 0, 'timestamps': [], 'coords': None} for label in word_labels}
        self.label_geometries = self._compute_label_geometries()

    def _compute_label_geometries(self):
        geometries = {}
        for identifier, label_obj, word in self.word_labels:
            geometries[identifier] = label_obj.geometry()
        return geometries

    def run(self):
        for line in self.gaze_data:
            timestamp_str, gaze_str = line.split('] Gaze point: ')
            timestamp = datetime.strptime(timestamp_str[1:], "%Y-%m-%d %H:%M:%S.%f")
            gaze_point = [float(val) for val in gaze_str.strip()[1:-1].split(',')]
            screen_x, screen_y = normalize_gaze_to_screen(gaze_point, self.screen_width, self.screen_height)

            for identifier, geometry in self.label_geometries.items():
                if geometry.contains(screen_x, screen_y):
                    if self.word_hits[identifier]['coords'] is None:
                        self.word_hits[identifier]['coords'] = (geometry.x(), geometry.y())
                    self.word_hits[identifier]['count'] += 1
                    self.word_hits[identifier]['timestamps'].append(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"))

            self.update_gaze_signal.emit(timestamp, screen_x, screen_y)
            time.sleep(0.02)

    def write_hit_counts_to_file(self, filename='word_hit_counts.txt'):
        if not self.user_directory:
            print("User directory not set. Cannot write hit counts.")
            return
        file_path = os.path.join(self.user_directory, filename)
        with open(file_path, 'w') as file:
            for key, data in self.word_hits.items():
                coords_str = f" - Coords: {data['coords'][0]}, {data['coords'][1]}" if data['coords'] else ""
                timestamps_str = ', '.join(data['timestamps'])
                file.write(f"{key}: {data['count']}{coords_str} - Timestamps: {timestamps_str}\n")
