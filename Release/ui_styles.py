# ui_styles.py
from config import app_config
import os

def get_button_style(button_height):
    return f"""
        QPushButton {{
            font-size: {int(button_height * 0.3)}pt;
            color: white;
            border-radius: {button_height // 2}px;
            background-color: qlineargradient(
                spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                stop:0 rgba(126, 87, 194, 1), stop:1 rgba(149, 117, 205, 1));
            border: 1px solid #DBDBDB;
            padding: 10px;
        }}
        QPushButton:hover {{
            background-color: qlineargradient(
                spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                stop:0 rgba(255, 151, 60, 1), stop:1 rgba(255, 193, 7, 1));
        }}
        QPushButton:pressed {{
            background-color: qlineargradient(
                spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                stop:0 rgba(221, 44, 0, 1), stop:1 rgba(255, 109, 0, 1));
        }}
    """

def get_exit_button_style(exit_button_size):
    return f"""
        QPushButton {{
            font-size: {int(exit_button_size * 0.4)}pt;
            color: #FFFFFF;
            border: 2px solid #555;
            background-color: #333;
            border-radius: {exit_button_size // 2}px;
        }}
        QPushButton:hover {{
            background-color: #555;
        }}
        QPushButton:pressed {{
            background-color: #777;
        }}
    """

def get_label_style(screen_height):
    # Base font size and scaling factor
    base_font_size = 12  # Base size for calculation

    # Adjust font size based on screen height
    font_scaling_factor = screen_height / 1080  # Assuming 1080p as base
    font_size = max(int(base_font_size * font_scaling_factor), 50)
    
    font_family = 'Calibri'
    line_spacing_factor = 1.5  # Adjust this factor to increase line spacing, 1.5 means 150% of line height
    
    return font_family, font_size, line_spacing_factor

def get_text_content(directory_path=None):
    default_text = "Lorem Ipsum is simply dummy text of the printing and typesetting industry..."
    if directory_path:
        text_file_path = os.path.join(directory_path, "custom_text.txt")
        if os.path.exists(text_file_path):
            try:
                with open(text_file_path, 'r') as file:
                    return file.read()
            except IOError as e:
                print(f"Unable to read the text file: {e}")
    return default_text

# Define the styles as dictionary entries for easy retrieval.
styles = {
    "default": """
        QMainWindow {
            background-color: #FFFFFF;  /* White background */
            color: #000000;  /* Black text */
        }
    """,
    "night_mode": """
        QMainWindow {
            background-color: #333333;  /* Dark gray background */
            color: #DDDDDD;  /* Light gray text */
        }
    """
}

def get_theme(mode):
    """Return the stylesheet for a given mode."""
    return styles.get(mode, styles["default"])  # Return default if mode key is not found.
