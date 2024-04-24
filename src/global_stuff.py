""" 
global parameters, global variables
and functions for saving and loading settings to/from INI file
"""

from typing import ClassVar, Tuple
from functools import cache

from PySide6.QtCore import Qt, QObject, Signal, QSettings, QPoint
from PySide6.QtGui import QColor, QIcon, QPixmap, QPen, QBrush, QPainter, QTransform
from PySide6.QtWidgets import QApplication

from constants import *

# --------------------------------------------------------------------------------------------
class GlobalParameters(QObject):
    """ GlobalParameters class as single instance, with signals to notify about parameter changes
    - members: KeepFocusOnSlider, KeepOnePosForAllModels, StayOnPosOnFillModel, StopAnnoyingGlowSignal, PlottersGranularity 
    - signals: sigGranularity, sigKeepFocusOnSlider"""
    sigGranularity: ClassVar[Signal] = Signal(int)
    sigKeepFocusOnSlider: ClassVar[Signal] = Signal(bool)

    __instance:ClassVar['GlobalParameters | None'] = None

    _KeepFocusOnSlider = True
    _KeepOnePosForAllModels = True
    _StayOnPosOnFillModel = True
    _StopAnnoyingGlowSignal = False
    _plottersGranularity = 2

    def __new__(cls, *args, **kwargs):
    # single instance
        if not cls.__instance:
            cls.__instance = super().__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings_GLobalParams_to_INI = QSettings(APP_NAME + '.ini', QSettings.IniFormat)

        self.settings_DocksUI_to_registry = QSettings(ORG_NAME, APP_NAME) # , format=QSettings.NativeFormat)
        """UI settings (sizes and positions) saved to platform independent (ex. registry)"""
        self.loadFromINI()

    @property
    def KeepFocusOnSlider(self) -> bool:
        """ '<i>Keep</i>' Focus On Slider when switching between models ..."""
        return self._KeepFocusOnSlider
    @KeepFocusOnSlider.setter
    def KeepFocusOnSlider(self, v:bool):
        self._KeepFocusOnSlider = v
        self.sigKeepFocusOnSlider.emit(v)


    @property
    def plottersGranularity(self) -> int:
        """ Plotters will plot data from mask<b>[&nbsp;:&nbsp;:&nbsp;{self.plottersGranularity}]</b> """
        return self._plottersGranularity
    @plottersGranularity.setter
    def plottersGranularity(self, i:int):
        self._plottersGranularity = i
        GlobalParameters.plottersGranularity.__doc__ = f" Plotters will plot data from mask<b>[&nbsp;:&nbsp;:&nbsp;{i}]</b> "
        self.sigGranularity.emit(i)
    
    
    @property
    def KeepOnePosForAllModels(self) -> bool:
        """ Keep the slider Pos\n when switching between models """
        return self._KeepOnePosForAllModels
    @KeepOnePosForAllModels.setter
    def KeepOnePosForAllModels(self, v:bool):
        self._KeepOnePosForAllModels = v


    @property
    def StayOnPosOnFillModel(self) -> bool:
        """ '<i>False</i>' => go to the last index """
        return self._StayOnPosOnFillModel
    @StayOnPosOnFillModel.setter
    def StayOnPosOnFillModel(self, v:bool):
        self._StayOnPosOnFillModel = v


    @property
    def StopAnnoyingGlowSignal(self) -> bool:
        """ Stop annoying GLOW signal 😄 """
        return self._StopAnnoyingGlowSignal
    @StopAnnoyingGlowSignal.setter
    def StopAnnoyingGlowSignal(self, v:bool):
        self._StopAnnoyingGlowSignal = v


    def loadFromINI(self):
        self._KeepFocusOnSlider = bool(self.settings_GLobalParams_to_INI.value('KeepFocusOnSlider', self._KeepFocusOnSlider, bool))
        self._KeepOnePosForAllModels = bool(self.settings_GLobalParams_to_INI.value('KeepOnePosForAllModels', self._KeepOnePosForAllModels, bool))
        self._StayOnPosOnFillModel = bool(self.settings_GLobalParams_to_INI.value('StayOnPosOnFillModel', self._StayOnPosOnFillModel, bool))
        self._StopAnnoyingGlowSignal = bool(self.settings_GLobalParams_to_INI.value('StopAnnoyingGlowSignal', self._StopAnnoyingGlowSignal, bool))
        self._plottersGranularity = int(self.settings_GLobalParams_to_INI.value('PlottersGranularity', self._plottersGranularity, int))
        self.plottersGranularity = min(max(self.plottersGranularity, min(CHOICES_LISTS.GRANULARITY)), max(CHOICES_LISTS.GRANULARITY))
    
    def saveToINI(self):
        self.settings_GLobalParams_to_INI.setValue('KeepFocusOnSlider', self._KeepFocusOnSlider)
        self.settings_GLobalParams_to_INI.setValue('KeepOnePosForAllModels', self.KeepOnePosForAllModels)
        self.settings_GLobalParams_to_INI.setValue('StayOnPosOnFillModel', self.StayOnPosOnFillModel)
        self.settings_GLobalParams_to_INI.setValue('StopAnnoyingGlowSignal', self.StopAnnoyingGlowSignal)
        self.settings_GLobalParams_to_INI.setValue('PlottersGranularity', self.plottersGranularity)
        self.settings_GLobalParams_to_INI.sync() 
# end class GlobalParameters

# --------------------------------------------------------------------------------------------
# region global variables
globalParameters = GlobalParameters()

gApp:QApplication = QApplication.instance()
if gApp is None:
    # if it does not exist then a QApplication is created
    gApp = QApplication()
gApp.setStyle("Fusion")

LOCK_ICO = QIcon('images/lock-32.ico')
NOLOCK_ICO = QIcon('images/unlock-32.ico')
# endregion global variables

# --------------------------------------------------------------------------------------------
# region Color Constants & Utils

# QColor.__hash__ = lambda self: self.blue() + self.green() * 0x100 + self.red() * 0x10000 
QColor.__hash__ =  lambda self: (self.red() << 16)  + (self.green() << 8 ) + self.blue() # type: ignore
# for @cache on combineColors(),  yeah, right, it's a bit faster with cache :D

QColor.rgbTuple = lambda s: (s.red(), s.green(), s.blue())
# for passing to stylesheet rgb(%d, %d, %d ...

@cache
def combineColors(c1:QColor, c2:QColor):
    """ returns a 'combined' color from 2 colors"""
    c3 = QColor()
    # convention : black == QColor() => Transparent, so :
    black = QColor()
    if c1 == black :
        c1 = c2
    if c2 == black :
        c2 = c1
    c3.setRed(int(((c1.red() + c2.red()) / 2)))
    c3.setGreen(int(((c1.green() + c2.green()) / 2)))
    c3.setBlue(int(((c1.blue() + c2.blue()) / 2)))
    return c3


def backgroundColorContrast(color:QColor):
    """ returns a contrasting color for the given background color """
    if (color.red() * 0.299 + color.green() * 0.587 + color.blue()*0.114) > 186 : 
        return MxCOLORS.PLOTTER_DARK_BACKGROUND
    else:
        return QColor('white')


class MxCOLORS:
    TBL_HEADER_GRAY = QColor(230, 230, 230)         # #e6e6e6
    TBL_INNER_BORDER_GRAY = QColor(210, 210, 210)   # #d2d2d2
    TBL_OUTER_BORDER_GRAY = QColor(185, 185, 185)   # #b9b9b9
    PLOTTER_DARK_BACKGROUND = QColor(150, 140, 140) # #b9b9b9

    BIAS = QColor(0xe2dcd0)

    W1_Row0 = QColor(0xdd5555) # #dd5555
    W1_Row1 = QColor(0xff8822) # #ff8822   
    W1_Col0 = QColor(0x57bef1) # #57bef1  
    W1_Col1 = QColor(0xadd276) # #add276 
    W1_00 = combineColors(W1_Row0, W1_Col0)
    W1_01 = combineColors(W1_Row0, W1_Col1)
    W1_10 = combineColors(W1_Row1, W1_Col0)
    W1_11 = combineColors(W1_Row1, W1_Col1)
    A1_0 = combineColors(W1_Col0, QColor('white'))
    A1_1 = combineColors(W1_Col1, QColor('white'))
    Z2 = QColor('hotpink')
    W2_0 = combineColors(A1_0, Z2)
    W2_1 = combineColors(A1_1, Z2)
    W2_Col = combineColors(W2_0, W2_1)
    Y = combineColors(Z2, QColor('white'))

    LOSS_HEADER_COLOR = QColor(0xffe600) # #ffe600
    LOSS_COST_COLOR = QColor(0xb9a80e) # #b9a80e

    
    
    # finding the right colors for the 4 quadruplet
    X00_COLOR = QColor(0xfa687b) # #fa687b
    X01_COLOR = QColor(0x3bad53) # #3bad53
    X10_COLOR = QColor(0x39a2db) # #39a2db
    X11_COLOR = QColor(0xd829d0) # #d829d0

    
    LST_COLOR_X00_X11 = [X00_COLOR, X01_COLOR, X10_COLOR, X11_COLOR]

    @staticmethod
    def get_color_for_value(value:float):
        """ for visualizing the loss progress Red(0) to Yellow(60) To Green(120) """
        # Ensure the value is within the valid range [0, 1]
        value = max(0, min(1, value))

        # Map the value to the hue in the range [0, 120]
        hue = 120 * (1 - value)

        # Create a QColor with the calculated hue and (saturation, value) set to (100, 255)
        color = QColor()
        color.setHsv(int(hue), 100, 255)

        return color
# endregion Color Constants & Utils

def _createPixmapUpDown() -> Tuple[QPixmap, QPixmap]:
    pixmap = QPixmap(66, 22)
    pixmap.fill(Qt.transparent)

    # Create a QPainter to draw on QPixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Set the pen color and width
    pen = QPen(MxCOLORS.W1_Col1)
    pen.setWidthF(2.8)
    painter.setPen(pen)

    # Set the brush color
    brush = QBrush(MxCOLORS.W1_Col0)
    painter.setBrush(brush)

    # Draw a triangle
    polyLineDot = [QPoint(1, 3), QPoint(33, 19), QPoint(65, 3)]
    painter.drawPolygon(polyLineDot)

    pen = QPen(MxCOLORS.W1_Col1)
    pen.setWidthF(2.8)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)

    polyLineDot = [QPoint(20, 7), QPoint(33, 13), QPoint(33, 13), QPoint(46, 7)]
    painter.drawLines(polyLineDot)

    polyLineDot = [QPoint(32, 7), QPoint(34, 7) ]
    painter.drawLine(*polyLineDot)

    # End the QPainter
    painter.end()

    pixmapDown = pixmap
    pixmapUp = pixmap.transformed(QTransform().scale(1, -1))

    return pixmapDown, pixmapUp

gPixmapDown, gPixmapUp = _createPixmapUpDown()
