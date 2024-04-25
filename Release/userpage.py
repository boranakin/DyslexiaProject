# userpage.py

import os
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import QPoint, Qt

from ui_styles import get_button_style, get_exit_button_style, get_label_style

class UserPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())  # Match the parent size
        self.parent = parent  # This will reference the GazeVisualizer instance
        self.initUI()
        self.update_user_list()  # Populate the user list on initialization

    def initUI(self):
        self.setWindowTitle('User Management')
        main_layout = QVBoxLayout()  # Main layout for the widget
        
        button_height = int(self.parent.screen_height * 0.06 * self.parent.dpi_scale_factor)

        # Top layout for title and exit button
        top_layout = QHBoxLayout()
        self.user_list_label = QLabel("List of Users:", self)
        font_family, font_size, _ = get_label_style(self.parent.screen_height)
        self.user_list_label.setFont(QFont(font_family, font_size))
        top_layout.addWidget(self.user_list_label, alignment=Qt.AlignLeft)
        
        top_layout.addStretch()  # Spacer

        exit_button_size = int(self.parent.screen_height * 0.05 * self.parent.dpi_scale_factor)
        self.exit_button = QPushButton('X', self)
        self.exit_button.setFixedSize(exit_button_size, exit_button_size)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setStyleSheet(get_exit_button_style(exit_button_size))
        top_layout.addWidget(self.exit_button, alignment=Qt.AlignRight)

        main_layout.addLayout(top_layout)

        self.user_list_widget = QListWidget(self)
        self.user_list_widget.setMaximumHeight(int(self.parent.screen_height * 0.3))
        self.user_list_widget.setMaximumWidth(int(self.parent.screen_width * 0.3))
        main_layout.addWidget(self.user_list_widget)

        spacer_item = QVBoxLayout()
        spacer_item.addStretch(1)
        main_layout.addLayout(spacer_item)

        # Bottom layout for adding new user and selecting a user
        bottom_layout = QHBoxLayout()

        self.new_user_input = QLineEdit("Enter new user name", self)
        self.new_user_input.setFont(QFont(font_family, font_size))
        self.new_user_input.setFixedWidth(int(self.parent.screen_width * 0.3))
        bottom_layout.addWidget(self.new_user_input, alignment=Qt.AlignLeft)

        self.add_user_button = QPushButton("Add User", self)
        self.add_user_button.clicked.connect(self.add_user)
        self.add_user_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.add_user_button.setStyleSheet(get_button_style(button_height))
        bottom_layout.addWidget(self.add_user_button, alignment=Qt.AlignLeft)

        # New Select User button
        self.select_user_button = QPushButton("Select User", self)
        self.select_user_button.clicked.connect(self.user_selected)
        self.select_user_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.select_user_button.setStyleSheet(get_button_style(button_height))
        bottom_layout.addWidget(self.select_user_button, alignment=Qt.AlignLeft)

        # Delete User button setup
        self.delete_user_button = QPushButton("Delete User", self)
        self.delete_user_button.clicked.connect(self.delete_user)
        self.delete_user_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.delete_user_button.setStyleSheet(get_button_style(button_height))
        bottom_layout.addWidget(self.delete_user_button, alignment=Qt.AlignLeft)

        main_layout.addLayout(bottom_layout)
        main_layout.addSpacing(int(self.parent.screen_height * 0.1))

        self.setLayout(main_layout)

    def user_selected(self):
        selected_item = self.user_list_widget.currentItem()
        if selected_item:
            selected_user = selected_item.text()
            self.parent.setCurrentUser(selected_user)  # This should update current_user_directory as well
            print(f"User selected: {selected_user}")
        else:
            print("No user selected.")

    def add_user(self):
        user_name = self.new_user_input.text().strip()
        if user_name:
            self.parent.setCurrentUser(user_name)  # Set and create user directory
            self.update_user_list()  # Refresh the user list
        else:
            print("Please enter a valid user name.")

    def delete_user(self):
        selected_item = self.user_list_widget.currentItem()
        if selected_item:
            selected_user = selected_item.text()
            user_folder = os.path.join("C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", f"{selected_user}_data")
            try:
                # Attempt to delete the user directory
                os.rmdir(user_folder)  # Note: os.rmdir only removes empty directories
                print(f"Deleted user directory: {user_folder}")
            except OSError as e:
                print(f"Error deleting user directory: {e}")
            self.update_user_list()
        else:
            print("No user selected to delete.")

    def update_user_list(self):
        self.user_list_widget.clear()  # Clear existing entries
        data_directory = "C:/Users/borana/Documents/GitHub/DyslexiaProject/Release/data"
        font_family, _, _ = get_label_style(self.parent.screen_height)  # Use same font family as the rest of UI
        large_font = QFont(font_family, 14)  # Set larger font size; adjust size as needed

        for folder_name in os.listdir(data_directory):
            if folder_name.endswith('_data'):
                # Extract user name from folder name
                user_name = folder_name[:-5]  # Assuming '_data' is 5 characters long
                item = QListWidgetItem(user_name)  # Create new item with user name
                item.setFont(large_font)  # Set the font for this item
                self.user_list_widget.addItem(item)  # Add to the list widget

        print("User list updated.")

    def showEvent(self, event):
        super().showEvent(event)
        self.parent.hideUI()  # Hide non-essential UI elements

    def closeEvent(self, event):
        super().closeEvent(event)
        self.parent.showUI()  # Restore UI elements after calibration
