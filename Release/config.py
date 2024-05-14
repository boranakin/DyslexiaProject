# config.py
class AppConfig:
    def __init__(self):
        self._session_directory = None

    @property
    def session_directory(self):
        return self._session_directory

    @session_directory.setter
    def session_directory(self, value):
        self._session_directory = value

# Singleton instance
app_config = AppConfig()
