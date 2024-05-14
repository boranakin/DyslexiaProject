import os, shutil
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QListWidget, QListWidgetItem, QTextEdit
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from ui_styles import get_button_style, get_exit_button_style, get_label_style

from config import app_config

class UserPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())
        self.parent = parent
        #self.selected_user_folder = None
        self.initUI()
        self.update_user_list()

    def initUI(self):
        self.setWindowTitle('User and Session Management')
        main_layout = QVBoxLayout()
        button_height = int(self.parent.screen_height * 0.06 * self.parent.dpi_scale_factor)

        # Top layout for title and exit button
        top_layout = QHBoxLayout()
        self.user_list_label = QLabel("List of Users and Sessions:", self)
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

        # User and Session list widgets
        self.user_list_widget = QListWidget(self)
        self.user_list_widget.setMaximumHeight(int(self.parent.screen_height * 0.3))
        main_layout.addWidget(self.user_list_widget)

        self.session_list_widget = QListWidget(self)
        self.session_list_widget.setMaximumHeight(int(self.parent.screen_height * 0.3))
        main_layout.addWidget(self.session_list_widget)

        # Input field for new usernames/sessions
        self.new_user_input = QLineEdit("Enter Username", self)
        self.new_user_input.setFont(QFont(font_family, font_size))
        main_layout.addWidget(self.new_user_input)

        # Text input field for custom reading text
        self.text_input = QTextEdit(self)
        self.text_input.setPlaceholderText("Enter custom reading text here...")
        self.text_input.setMaximumHeight(100)
        main_layout.addWidget(self.text_input)

        # Save Text Button
        self.save_text_button = QPushButton("Save Text", self)
        self.save_text_button.clicked.connect(self.save_custom_text)
        self.save_text_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.save_text_button.setStyleSheet(get_button_style(button_height))
        main_layout.addWidget(self.save_text_button)

        # First and second rows of management buttons
        self.setupManagementButtons(main_layout, font_family, font_size, button_height)

        self.setLayout(main_layout)

    def setupManagementButtons(self, main_layout, font_family, font_size, button_height):
        # First row of management buttons
        first_row_layout = QHBoxLayout()
        self.add_user_button = QPushButton("Kullanıcı Oluştur", self)
        self.add_user_button.clicked.connect(self.add_user)
        self.add_user_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.add_user_button.setStyleSheet(get_button_style(button_height))
        first_row_layout.addWidget(self.add_user_button)

        self.create_session_button = QPushButton("Create Session", self)
        self.create_session_button.clicked.connect(self.create_session)
        self.create_session_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.create_session_button.setStyleSheet(get_button_style(button_height))
        first_row_layout.addWidget(self.create_session_button)

        self.select_session_button = QPushButton("Select Session", self)
        self.select_session_button.clicked.connect(self.session_selected)
        self.select_session_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.select_session_button.setStyleSheet(get_button_style(button_height))
        first_row_layout.addWidget(self.select_session_button)
        
        main_layout.addLayout(first_row_layout)

        # Second row of management buttons
        second_row_layout = QHBoxLayout()
        self.delete_session_button = QPushButton("Delete Session", self)
        self.delete_session_button.clicked.connect(self.delete_session)
        self.delete_session_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.delete_session_button.setStyleSheet(get_button_style(button_height))
        second_row_layout.addWidget(self.delete_session_button)

        self.delete_user_button = QPushButton("Delete User", self)
        self.delete_user_button.clicked.connect(self.delete_user)
        self.delete_user_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.delete_user_button.setStyleSheet(get_button_style(button_height))
        second_row_layout.addWidget(self.delete_user_button)

        self.select_user_button = QPushButton("Select User", self)
        self.select_user_button.clicked.connect(self.user_selected)
        self.select_user_button.setFixedSize(int(self.parent.screen_width * 0.15), button_height)
        self.select_user_button.setStyleSheet(get_button_style(button_height))
        second_row_layout.addWidget(self.select_user_button)
        
        main_layout.addLayout(second_row_layout)

    def save_custom_text(self):
        if app_config.session_directory:  # Use AppConfig to get the session directory
            text = self.text_input.toPlainText()
            if len(text) > 1000:
                print("Text is too long, please limit to 1000 characters.")
                return
            text_file_path = os.path.join(app_config.session_directory, "custom_text.txt")
            with open(text_file_path, 'w') as file:
                file.write(text)
            print(f"Text saved to {text_file_path}")
        else:
            print("No session selected. Please select a session to save the text.")

    def delete_user(self):
        selected_item = self.user_list_widget.currentItem()
        if selected_item:
            user_name = selected_item.text()
            user_folder = os.path.join("/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", f"{user_name}_data")
            try:
                shutil.rmtree(user_folder)
                print(f"Deleted user directory: {user_folder}")
                self.update_user_list()  # Refresh the list after deletion
                self.update_session_list()
            except OSError as e:
                print(f"Error deleting user directory: {e}")
        else:
            print("No user selected to delete.")

    def delete_session(self):
        selected_user = self.user_list_widget.currentItem()
        selected_session = self.session_list_widget.currentItem()
        if selected_user and selected_session:
            session_folder = os.path.join("/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", selected_user.text() + "_data", selected_session.text())
            try:
                # Remove the session directory and its contents
                os.rmdir(session_folder)
                print(f"Deleted session directory: {session_folder}")
                self.update_session_list(os.path.join("/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", selected_user.text() + "_data"))
            except OSError as e:
                print("Error deleting session directory:", e)
        else:
            print("No session selected for deletion.")

    def update_user_list(self):
        self.user_list_widget.clear()
        data_directory = "/Users/borana/Documents/GitHub/DyslexiaProject/Release/data"
        font_family, _, _ = get_label_style(self.parent.screen_height)  # Assuming get_label_style is adequate
        custom_font = QFont(font_family, 20)  # You can adjust the size here as needed
        
        for folder_name in os.listdir(data_directory):
            if folder_name.endswith('_data'):
                user_name = folder_name[:-5]  # Strip '_data' to get the user name
                item = QListWidgetItem(user_name)
                item.setFont(custom_font)  # Apply the custom font to the item
                self.user_list_widget.addItem(item)
        print("User list updated.")

    def update_session_list(self):
        if self.selected_user_folder:
            self.session_list_widget.clear()
            sessions = os.listdir(self.selected_user_folder)
            font_family, _, _ = get_label_style(self.parent.screen_height)
            custom_font = QFont(font_family, 20)  # Same font size as the user list for consistency
            
            for session in sessions:
                item = QListWidgetItem(session)
                item.setFont(custom_font)  # Apply the custom font to the item
                self.session_list_widget.addItem(item)
            print("Session list updated for", os.path.basename(self.selected_user_folder))

    def user_selected(self):
        selected_item = self.user_list_widget.currentItem()
        if selected_item:
            self.selected_user_folder = os.path.join("/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", selected_item.text() + "_data")
            self.update_session_list()
            print(f"User selected: {selected_item.text()}")
        else:
            print("No user selected.")

    def create_session(self):
        if self.selected_user_folder:
            timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M")
            session_folder = os.path.join(self.selected_user_folder, timestamp)
            os.makedirs(session_folder, exist_ok=True)
            self.update_session_list()
            print(f"Session created: {session_folder}")
        else:
            print("No user selected for creating a session.")

    def session_selected(self):
        selected_item = self.session_list_widget.currentItem()
        if selected_item:
            selected_session_folder = os.path.join(self.selected_user_folder, selected_item.text())
            app_config.session_directory = selected_session_folder
            print(f"Session selected: {selected_session_folder}")
        else:
            print("No session selected.")

    def add_user(self):
        user_name = self.new_user_input.text().strip()
        if user_name:
            user_folder = os.path.join("/Users/borana/Documents/GitHub/DyslexiaProject/Release/data", user_name + "_data")
            os.makedirs(user_folder, exist_ok=True)
            self.update_user_list()
            print(f"User added: {user_name}")

    def showEvent(self, event):
        super().showEvent(event)
        self.parent.hideUI()  # Hide non-essential UI elements

    def closeEvent(self, event):
        super().closeEvent(event)
        self.parent.updateTextDisplay()  # Refresh the display in GazeVisualizer
        self.parent.showUI()  # Restore UI elements after calibration
