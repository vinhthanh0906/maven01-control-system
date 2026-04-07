'''
- Building Linear Compass 
'''
import math
import time 
from collections import deque


from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QSizePolicy, QProgressBar
)

class LinearCompass(QWidget):
    def __init__(self, parent =None):
        super().__init__()
        self.width = 160 
        self.height = 120 
        
        #set frame
        self.frame_width = self.width + 100
        self.frame_height = self.height + 200 
        
    def direction_line(self, length, gap_length):
        #Normal line 
        self.length = 0.5 * self.width
        # self.color = white
        self.main_direction_line = 0.75 * self.width

    def set_attitude(self, roll, pitch):
        self._roll = roll
        self._pitch = pitch 
        self.update()
        
    def directionUpdate(self):
        self._ro
        
        
    
    #Direction letter 
    def character__and_widget(self):
        pass 
    
        
    
