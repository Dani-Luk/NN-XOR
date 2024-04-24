
from typing import List
from dataclasses import dataclass
import numpy as np

from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import (QAction, QIntValidator, QKeyEvent, QMouseEvent, 
                           QEnterEvent, QFontMetrics, QWheelEvent, QShowEvent, 
                            )
from PySide6.QtWidgets import (QStyle, QToolTip, QWidget, QVBoxLayout,
                               QSlider, QLabel, QLineEdit, QMenu, 
                               )

from global_stuff import *
from utilities import *
from core import *


@dataclass(init=False)
class TurningPointLabel(QLabel):
    """A custom QLabel subclass for representing a turning point label.
    
    This class inherits from QLabel and provides additional functionality for handling mouse events and displaying tooltips.
    
    Attributes with @dataclass :
        val (int): The value associated with the turning point label.
        txtToolTip (str): The tooltip text to be displayed when the mouse hovers over the label.
    """    
    val: int
    txtToolTip: str
    
    def __init__(self, parent: 'SliderEdit') -> None:
        super().__init__(text="", parent=parent)
        self.leaveEvent() # setStyleSheet to normal
        
    def mousePressEvent(self, ev: QMouseEvent) -> None:
        self.parent().setValue(self.val)

    def enterEvent(self, event: QEnterEvent) -> None:
        """setStyleSheet to hover and show the ToolTip"""
        self.setStyleSheet("""QLabel 
                        { 
                        background-color: rgba(0, 255, 0, 0.5);
                        border: 1px solid rgba(0, 255, 0, 0.2);
                        }"""
                                            )
        self.setCursor(Qt.PointingHandCursor)
        strTT = self.txtToolTip
        if not strTT : return
        qtt = QToolTip()
        fm = QFontMetrics(qtt.font())
        hfont = fm.height()
        countReturns = strTT.count('<br>') + 1
        try:
            qtt.showText(self.parent().mapToGlobal(self.pos()) - QPoint(2, 23 + hfont * countReturns ), strTT ) 
        except :
            pass
    # end enterEvent
    
    def leaveEvent(self, *args) -> None:
        """setStyleSheet to normal"""
        self.setStyleSheet("""QLabel 
                        { 
                        background-color:rgba(0,70,255,0.5);
                        border-left: 1px solid rgba(255,255,255,0.4);
                        border-right: 1px solid rgba(185,185,200,0.4); 
                        }"""
                           )        


class SliderEdit(QSlider):
    """A custom QSlider subclass for representing a slider with additional functionality.

    Methods:
        setRightClickMenu(self, menu: QMenu): Sets the right-click context menu for the slider.
        setTurningPoints(self, newLstTurningPoints: List[int], newLstTurningPointsDiffs: List[str]): Sets the list of turning points and their tooltips.
        setPos2NearTP(self, bForward: bool): Sets the position to the nearest turning point.
        getVirtualValue(self) -> int: Returns the value of the slider that could be greater than the maximum.
    """
    __HANDLE_WIDTH = 40
 
    def __init__(self, parent = None) -> None:
        super().__init__(orientation=Qt.Orientation.Horizontal, parent=parent)
        
        self.setStyleSheet("""
            QSlider::groove:horizontal {
            border: 1px solid #ababab; 
            border-radius: 2px;
            height: 4px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */
            margin: 2px 0;
            background: #d3d3d3;
            }
            QSlider::handle:horizontal:focus {
                background-color: #dcd0ff; 
                /* background-color: rgba(220, 208, 255, 205); */
                /* border: 1px solid #999999; */
                border: 1px solid #0026ff; 
                border-radius: 4px;
                width: %dpx;
                margin-top: -8px;
                margin-bottom: -8px;
            }        
            QSlider::handle:horizontal:!focus {
                background-color: #dcd0ff; 
                border: 1px solid #999999;
                border-radius: 4px;
                width: %dpx;
                margin-top: -8px;
                margin-bottom: -8px;
            }        
            QSlider::sub-page:horizontal {
            background: #6666cc;
            border: 1px solid #00477e;
            border-radius: 2px;
            height: 4px;
            margin: 2px 0;
            }
            """ % (self.__HANDLE_WIDTH, self.__HANDLE_WIDTH))

        self.setMinimumHeight(20)
        self.setSingleStep(1)
        self.setPageStep(10)

        self.menu:QMenu | None = None
        self.lstLabelsTP:List[TurningPointLabel] = [] #list of Labels TurningPoints
        self.lstIntTP = [] # list of Pos(int) of TurningPoints
        self.lstTurningPointsDiffs = [] # list of diffs

        self.label = QLabel(self) # label for the current value
        lbl = self.label
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        self.setMouseTracking(True)
        lbl.setAlignment(Qt.AlignHCenter)
        lbl.setToolTip("Press a digit/F2 or DblClick to edit \n" 
                       "Alt/Shift + arrows/wheel: +/- 10 \n" 
                       "Alt+Shift + arrows/wheel: +/-100 \n" 
                       "Ctrl + arrows/wheel: next/previous TP \n" 
                       "Right click for menu"
                       )
        
        lbl.setFixedWidth(self.__HANDLE_WIDTH - 2)
        #region lbl DblClick    
        def lblDblClick(*args):
            """ edit the current value"""
            wdg_edit = QWidget(self)
            wdg_edit.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup | Qt.NoDropShadowWindowHint ) #type:ignore
            wdg_edit.resize(self.label.size()) 

            edt = QLineEdit(wdg_edit)
            f = edt.font()
            f.setBold(True)
            edt.setFont(f)
            edt.setValidator(QIntValidator(bottom=self.minimum(), top=self.maximum()))
            edt.resize(self.label.size()) 
            edt.setText(str(self.value()))
            edt.selectAll()
            edt.setObjectName('edt')
            edt.setStyleSheet("QLineEdit#edt { color: blue; border: 0px solid blue; }")
            edt.setAlignment(Qt.AlignCenter)
            edt.setMinimumSize(QSize(10,10))
            edt.focusOutEvent = lambda *args : self.setValue(int(edt.text()))
            def _keyPressEvent(ev: QKeyEvent):
                if ev.key() in (Qt.Key_Tab, Qt.Key_Enter, Qt.Key_Return):
                    wdg_edit.close()
                elif ev.key() == Qt.Key_Escape:
                    edt.setText(str(self.value()))
                return QLineEdit.keyPressEvent(edt, ev)  
            edt.keyPressEvent = _keyPressEvent
            edt.setFocus()

            pTopLeft = lbl.mapToGlobal(QPoint(0,0))
            wdg_edit.move(pTopLeft) # + self.label.pos() ) 
            wdg_edit.show()
            wdg_edit.activateWindow()
        # endregion lbl DblClick
        lbl.mouseDoubleClickEvent = lblDblClick

        def _mousePressEvent(event: QMouseEvent) -> None:
            # show context menu on right click, if provided
            if event.button() == Qt.RightButton:
                if self.menu:
                    self.menu.popup(self.mapToGlobal(self.label.geometry().bottomLeft()  + QPoint(-2, +3)))
                    event.accept()
                    return
            return QLabel.mousePressEvent(lbl, event)
        lbl.mousePressEvent = _mousePressEvent

        self.valueChanged.connect(self._valueChanged)

        self.lblMax = QLabel(self) # label for the maximum value. It turn to red if the value is greater than the maximum
        self.lblMax.setFont(self.label.font())
        self.lblMax.setAlignment(self.label.alignment())
        self.lblMax.mousePressEvent = lambda _: self.setValue(self.maximum()) # reset to maximum
    # end __init__
    
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._valueChanged(self.value())
    
    def setRightClickMenu(self, menu: QMenu):
        self.menu = menu
        self.menu.setStyleSheet("""
                            QMenu {background-color: rgb(220, 208, 255); 
                            }
                            QMenu::item{
                            background-color:  rgb(220, 208, 255); 
                            }
                            QMenu::item:selected{
                            background-color:  rgb(196, 176, 255); 
                            color: #000;
                            }"""
                               )        

    def setTurningPoints(self, newLstTurningPoints:List[int], newLstTurningPointsDiffs:List[str]):
        """ set the list of TurningPoints(QLabel) their list of diffs for ToolTip \n
        and reposition the TurningPoints on the Slider"""
        self.lstTurningPointsDiffs = newLstTurningPointsDiffs
        len_newLstTurningPoints = len(newLstTurningPoints)

        # reuse TP QLabels if possible
        while len(self.lstLabelsTP) < len_newLstTurningPoints:
            self.lstLabelsTP.append(TurningPointLabel(self))
        
        for i in range(len_newLstTurningPoints, len(self.lstLabelsTP)):
            self.lstLabelsTP[i].hide() # hide the unused TP QLabels
        
        for i in range(len_newLstTurningPoints):
            tp = self.lstLabelsTP[i]
            tp.txtToolTip = newLstTurningPointsDiffs[i]
            tp.val = newLstTurningPoints[i]
            tp.setFixedSize(4, self.height())
            x = QStyle.sliderPositionFromValue(self.minimum(), 
                                               self.maximum(),
                                               tp.val, 
                                               self.width() - self.__HANDLE_WIDTH - 2 * 2 )
            tp.move(x + self.__HANDLE_WIDTH//2, 0)
            tp.show()
            tp.lower()
        self.lstIntTP = newLstTurningPoints
        self.lblMax.lower()
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """ wheelEvent for the SliderEdit \n
        Ctrl + wheel : next/previous TP \n
        Alt/Shift + wheel : +/- 10 \n
        Alt+Shift + wheel : +/-100 \n
        wheel : +/- 1 \n"""

        if event.modifiers() & Qt.ControlModifier:
                self.setPos2NearTP(event.angleDelta().x() + event.angleDelta().y() > 0)
        elif event.modifiers() & Qt.AltModifier and event.modifiers() & Qt.ShiftModifier :  # type: ignore
            if event.angleDelta().x() + event.angleDelta().y() > 0 :
                self.setValue(self.value() + 100 )
            else:
                self.setValue(self.value() - 100)
        elif event.modifiers() & Qt.AltModifier or event.modifiers() & Qt.ShiftModifier :  # type: ignore
            if event.angleDelta().x() + event.angleDelta().y() > 0 :
                self.setValue(self.value() + 10 )
            else:
                self.setValue(self.value() - 10)
        else:
            if event.angleDelta().x() + event.angleDelta().y() > 0 :
                self.setValue(self.value() + 1 )
            else:
                self.setValue(self.value() - 1)            

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """ process the keyPressEvent for Edit, Next TP, +/- 1, 10, 100"""
        if event.key() in (Qt.Key_F2, Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space):
            self.label.mouseDoubleClickEvent(None)
        elif event.key() in range(Qt.Key_0, Qt.Key_9 + 1):
            self.label.mouseDoubleClickEvent(None)
            gApp.processEvents() # to allow the editor to be created
            gApp.sendEvent(gApp.focusWidget(), event) # to send the key to the editor
        elif event.key() in (Qt.Key_Up, Qt.Key_Right, Qt.Key_Down, Qt.Key_Left ):
            if event.modifiers() & Qt.ControlModifier:
                self.setPos2NearTP(event.key() in (Qt.Key_Up, Qt.Key_Right))
                return
            mult = 1 if event.key() in (Qt.Key_Up, Qt.Key_Right) else -1
            if event.modifiers() & Qt.AltModifier or event.modifiers() & Qt.ShiftModifier : 
                mult = mult * 10
            if event.modifiers() & Qt.AltModifier and event.modifiers() & Qt.ShiftModifier : 
                mult = mult * 10
            self.setValue(self.value() + mult)            
        else:
            return super().keyPressEvent(event)

    def setPos2NearTP(self, bForward:bool):
        """ set the Slider to the nearest TurningPoint Forward or Backward including [0 & maximum] positions"""
        if bForward :
            self.setValue(min( [self.maximum()] + [p for p in self.lstIntTP if p > self.value()] ))
        else:
            self.setValue(max( [0] + [p for p in self.lstIntTP if p < self.value()] ))

    def getVirtualValue(self) -> int:
        """ return the value of the Slider that could be greater than the maximum"""
        return int(self.label.text() or 0)
    
    def setMaximum(self, arg__1: int) -> None:
        """ set the maximum and reposition the TurningPoints on the Slider"""
        super().setMaximum(arg__1)
        self.setTurningPoints(self.lstIntTP, self.lstTurningPointsDiffs)

    def _valueChanged(self, newVal:int):
        """ update the label and the position of the label and the lblMax value and transparency"""
        self.label.setText(str(newVal))
        if newVal > self.maximum():
            self.label.setStyleSheet("QLabel { color:red; background-color: #dcd0ff; }")
        else:
            self.label.setStyleSheet("QLabel { color:black; background-color: rgba(220, 208, 255, 0.7); }")
        y = (self.height() - self.label.height())//2 
        dx = QStyle.sliderPositionFromValue(self.minimum(), self.maximum(),
                                            newVal, self.width() - self.__HANDLE_WIDTH - 2 * 2 )
        self.label.move(dx + 3, y)
        self.__setup_lblMax()
        if globalParameters._KeepFocusOnSlider == True:
            self.setFocus()

    def __setup_lblMax(self):
        """ set the lblMax value and transparency(function by distance from current position to maximum)"""
        self.lblMax.setText(str(self.maximum()))
        self.lblMax.resize(self.label.size()+ QSize(0, 4))
        self.lblMax.move(self.width()-self.lblMax.width(), self.label.pos().y()-2)
        vMaxSecure1 = max(self.maximum(), 1)
        self.lblMax.setStyleSheet("""QLabel 
                                  { color:rgba(0,0,0,%0.3f); 
                                   background-color:rgba(235,235,235,%0.3f); 
                                   border: 1px solid rgba(153,153,153,%0.3f); 
                                   border-radius: 4px;
                                   margin-top: 0px;
                                   margin-bottom: 0px;                                  
                                   }"""
                                  % ((1 - (self.value() / vMaxSecure1)**6, 
                                      min(0.5, 1 - (self.value() / vMaxSecure1)**3),  
                                      min(0.5, 1 - (self.value() / vMaxSecure1)**3), ) 
                                      )
                                    )
        self.lblMax.lower()
        
    def resizeEvent(self, event) -> None:
        """ reposition the labels and the lblMax
        and reposition the TurningPoints on the Slider"""
        super().resizeEvent(event)
        self._valueChanged(self.value())
        self.setTurningPoints(self.lstIntTP, self.lstTurningPointsDiffs)
        self.__setup_lblMax()                                  


if __name__ == "__main__":
    
    lstAct = []
    for i in range (5):
        act = QAction()
        f = lambda checked, val=i: print(i, val)
        act.triggered.connect(lambda checked : f(checked, i))
        act.setText(f"Action {i+1:02d} ")
        lstAct.append(act)

    menu = QMenu()
    menu.addActions(lstAct)

    max_size = 4000

    wdgSlider = SliderEdit()
    wdgSlider.setRightClickMenu(menu)
    wdgSlider.setMinimum(0)
    wdgSlider.setMaximum(max_size - 1)

    my_generator = np.random.default_rng()
    lstTurningPoints = list(my_generator.integers(0, max_size, my_generator.integers(3, 7)))
    lstTurningPoints = [0] + sorted(list(my_generator.integers(1, max_size - 1, my_generator.integers(3, 7)))) + [max_size - 1]
    lstToolTip = list(map(lambda s : f"<b> TP = {s} </b>", lstTurningPoints))
    wdgSlider.setTurningPoints(lstTurningPoints, lstToolTip)    
    
    ly = QVBoxLayout()
    ly.setContentsMargins(2, 20, 2, 20)
    ly.addWidget(wdgSlider)

    winMain = QWidget()
    winMain.setStyleSheet("background-color: #e3feff;")
    winMain.setLayout(ly)
    winMain.resize(600, 300)
    winMain.show()
   
    gApp.exec()
   