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

'''prompt: Give me a list of some characteristics of a good coffee shop? answer in a paragraph.
Response:
Some characteristics of good coffee shops include:
 - Very good coffee, either freshly roasted locally or acquired from a quality roaster
 - High end coffee grinders, brewing machines, and a high quality espresso machine and well-trained baristas
 - Different coffee roast options (i.e. medium roast, dark roast) and brewing methods (i.e. drip coffee and pour-over) available
 - A variety of cafe fare, such as pastries and croissants, available for purchase to accompany coffee
 - Ample seating, with power outlets available by most seats."	
error: prompt compliance'''