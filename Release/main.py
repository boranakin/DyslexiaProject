# main.py
from PyQt5.QtWidgets import QApplication
import sys
from ui_components import GazeVisualizer

def main():
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    main_window = GazeVisualizer(screen.size().width(), screen.size().height())
    main_window.showFullScreen()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

#user verileri icin tree veri yapisi; hit countlar da userda tutulsun
#saat tarih şeklinde recording session     
#metni büyütme daha yukarı ve aşağı genisleme   TMM
#toggle buttons
#installer