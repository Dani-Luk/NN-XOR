"""
This module contains classes for plotting data using PySide6 and pyqtgraph.

Classes:
- Singles_Plotter: A plot widget for displaying single series of data.
- Pairs_Plotter: A plot widget for displaying pairs of data.
- HalfPlanes_Plotter: A plot widget for displaying half-planes.


Functions:
- floatDockPatched: Removes a dock from a DockArea and places it in a new window.

"""

from typing import List, Callable
import numpy as np

from PySide6.QtCore import (Qt, QSize, Property, QByteArray, Signal, 
                            QPropertyAnimation, QSequentialAnimationGroup, QParallelAnimationGroup, QEasingCurve, 
                            QPointF, QLineF, QMarginsF
                            )
from PySide6.QtWidgets import ( QWidget,  QVBoxLayout, QLabel, QHBoxLayout, 
                               QPushButton, QGraphicsColorizeEffect, 
                               )
from PySide6.QtGui import QColor, QPainterPath, QFont, QTransform, QBrush

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock

from global_stuff import gApp, MxCOLORS, combineColors
from utilities import Line


pg.setConfigOption('foreground', pg.mkColor("black"))
pg.setConfigOptions(antialias=True)


def floatDockPatched(self, dock): 
    """Removes *dock* from this DockArea and places it in a new window. (patched with setWindowTitle)"""
    area = self.addTempArea()
    area.win.resize(dock.size())
    area.win.setWindowTitle(dock.label.text())
    area.moveDock(dock, 'top', None)

DockArea.floatDock = floatDockPatched
# end floatDockPatched

class Singles_Plotter(pg.PlotWidget):
    """
    A plot widget for displaying single series of data.

    Signals:
    - sigPosChanged: Emitted when the position of the vertical line is changed.
    - sigClickedPlotIndex: Emitted when a plot curve is clicked.

    Attributes:
    - __instances: A dictionary that stores instances of Singles_Plotter.
    - series: A list of numpy arrays representing the data series.
    - colors: A list of QColor objects representing the colors of the plot curves.
    - labels: A list of strings representing the labels of the plot curves.
    - plot_data: A list of PlotDataItem objects representing the plot curves.
    - maxLen: The maximum length of the data series.
    - name: The name of the plot widget.
    - granularity: The granularity of the plot data.
    - bLossLikeLegendBackground: A boolean indicating whether to use a loss-like legend background.
    - sigPosChangedFromHub: A signal for receiving position change signals from the hub.
    - HubSlotForPosChanged: A callable function for handling position change signals from the hub.
    - lstLinesTP: A list of InfiniteLine objects corresponding to turning points.
    - lstIntTP: A list of integers representing the positions of the turning points.
    - vLine: An InfiniteLine object representing the vertical line.
    - lblLegend: A QLabel object representing the legend label.
    - lytH: A QHBoxLayout object representing the layout for the legend.
    - curve_clicked: A boolean indicating whether a curve has been clicked.
    - selected_curve: The selected curve.
    - lstIndex2Show: A list of indices to show.

    Methods:
    - setGranularityFromSignal: Sets the granularity for all instances of Singles_Plotter.
    - __init__: Initializes the Singles_Plotter object.
    - __del__: Deletes the Singles_Plotter object.
    - setTurningPoints: Sets the turning points for the plot.
    - setGranularity: Sets the granularity of the plot data.
    - AddSeries: Adds a series of data to the plot.
    - updateSeries: Updates the plot data.
    - _AddRuler: Adds a vertical line to the plot.
    - _setPos: Sets the position of the vertical line.
    """

    sigPosChanged = Signal(float)
    sigClickedPlotIndex = Signal(int)
    """Emitted when a plot curve is clicked. The signal provides the index of the clicked curve."""
    __instances = {}

    @classmethod
    def setGranularityFromSignal(cls, i:int):
        """
        Sets the granularity for all instances of Singles_Plotter.

        Parameters:
        - i: The granularity value.
        """
        for item in Singles_Plotter.__instances.values():
            Singles_Plotter.setGranularity(item, i)
    
    def __init__(self, parent=None, name="", 
                 sigPosChangedFromHub: Signal | None=None, 
                 HubSlotForPosChanged: Callable[[int], None] | None=None, 
                 background_color:QColor|None = None,
                 granularity:int = 1,
                 bLossLikeLegendBackground = False,
                 **kargs):
        """
        Initializes the Singles_Plotter object.

        Parameters:
        - parent: The parent widget.
        - name: The name of the plot widget.
        - sigPosChangedFromHub: A signal for receiving position change signals from the hub.
        - HubSlotForPosChanged: A callable function for handling position change signals from the hub.
        - background_color: The background color of the plot widget.
        - granularity: The granularity of the plot data.
        - bLossLikeLegendBackground: A boolean indicating whether to use a loss-like legend background. (aka for visualizing the loss progress Red(0) to Yellow(60) To Green(120) )
        - **kargs: Additional keyword arguments.
        """
        super().__init__(parent=parent, background=background_color, **kargs)
        
        Singles_Plotter.__instances[id(self)] = self

        self.series = []
        self.colors = []
        self.labels = []
        self.plot_data = []
        self.maxLen = 0
        self.name = name
        self.granularity = granularity
        self.bLossLikeLegendBackground = bLossLikeLegendBackground
        self.sigPosChangedFromHub = sigPosChangedFromHub
        if sigPosChangedFromHub:
            self.sigPosChangedFromHub.connect(self._setPos)
        if HubSlotForPosChanged:
            self.sigPosChanged.connect(HubSlotForPosChanged)
        self.lstLinesTP:List[pg.InfiniteLine] = []
        self.lstIntTP = []
        self.vLine:pg.InfiniteLine | None = None

        lytV = QVBoxLayout()
        lytV.setContentsMargins(0,1,1,0)
        lytV.setSpacing(0)
        self.lblLegend = QLabel()
        if background_color is None :
            self.lblLegend.setStyleSheet("QLabel { background-color:white; }")
        else:
            self.lblLegend.setStyleSheet("QLabel { background-color:#%06x; }" % background_color.__hash__())
        lytV.addWidget(self.lblLegend, stretch=0, alignment= Qt.AlignRight|Qt.AlignTop)
        self.lytH = QHBoxLayout()
        self.lytH.setContentsMargins(0,2,2,0)
        self.lytH.setSpacing(5)
        self.lytH.addStretch(1)
        lytV.addLayout(self.lytH, stretch=0)
        lytV.addStretch(1)
        self.setLayout(lytV)
        self.setBackground(background_color)
        self._AddRuler()

        self.scene().sigMouseClicked.connect(self.mouse_clicked)    
        self.curve_clicked = True
        self.selected_curve = None
        self.lstIndex2Show = []

    def __del__(self) -> None:
        """
        Deletes the Singles_Plotter object.
        """
        del Pairs_Plotter.__instances[id(self)]


    def setTurningPoints(self, lstTurningPoints:List[int]):
        """
        Sets the turning points for the plot.

        ### Parameters:
        - lstTurningPoints: A list of integers representing the positions of the turning points as a pg.InfiniteLine.
        """
        i = 0
        while i < (min(len(self.lstLinesTP), len(lstTurningPoints))):
            line = self.lstLinesTP[i]
            pos = lstTurningPoints[i]
            line.setBounds([pos, pos])
            line.setPos(pos)
            line.show()
            line.label.setText("%d" % pos) # update the label, I dont know why label="{value:.0f}" didn't update itself?
            i += 1

        while i < (max(len(self.lstLinesTP), len(lstTurningPoints))):
            if i >= len(lstTurningPoints):
                self.lstLinesTP[i].hide()
            else :
                pos = lstTurningPoints[i]
                newLine = pg.InfiniteLine(pos, 
                                        pen=pg.mkPen(color='blue', width=1, style=Qt.DotLine), 
                                        movable=True,
                                        bounds=[pos, pos],
                                        hoverPen = pg.mkPen(color='g',width=2, cosmetic=True), 
                                        label="{value:.0f}", 
                                        labelOpts={"position":0.92, "movable":True, "color":QColor(75, 75, 220, 150) }, 
                                        )
                def _clickTurningLine(line:pg.InfiniteLine, ev):
                    ix = int(line.p[0])
                    ix = int(line.bounds()[0])
                    self._setPos(ix)
                    self._setLabels(ix)
                    self._emit(ix)
                newLine.sigClicked.connect(_clickTurningLine)

                self.lstLinesTP.append(newLine)
                self.addItem(newLine)
            i += 1
        
        self.lstIntTP = lstTurningPoints

        if self.vLine:
            # put the VLine on top of the TurningPoints
            self.removeItem(self.vLine)
            self.addItem(self.vLine)
    # end setTurningPoints

    def setGranularity(self, granularity:int):
        """
        Sets the granularity of the plot data.

        Parameters:
        - granularity: The granularity value.
        """
        self.granularity = granularity
        self.updateSeries(*self.series)

    
    def AddSeries(self, serie:np.ndarray, color:QColor=QColor('blue'), label=''):
        """
        Adds a series of data to the plot.

        Parameters:
        - serie: A numpy array representing the data series.
        - color: The color of the plot curve.
        - label: The label of the plot curve.
        """
        if self.series:
            assert len(self.series[0]) == len(serie), "the length of the series is not equal"
        else:
            self.maxLen = len(serie)
        self.maxLen = max(self.maxLen, len(serie))
        self.series.append(serie)
        self.colors.append(color)
        self.labels.append(label)
        x = [0]
        if serie.size > 1:
            x = np.linspace(0, serie.size - 1, 
                            serie.size // self.granularity + 1, 
                            endpoint=True, dtype=int) # with {0, serie.size-1} guaranteed 
        y = serie[x]        
        plt = self.plot(x=x, y=y, pen=pg.mkPen(color=color, width=1.8))
        self.plot_data.append(plt)
        plt.setCurveClickable(True)
        plt.sigClicked.connect(lambda x: self._curveClick(x))
        self.lstIndex2Show.append(len(self.lstIndex2Show))


    def updateSeries(self, *data):
        """
        Updates the plot data.

        Parameters:
        - data: The updated data series.
        """
        assert len(data) == len(self.series), "Nb series not match "
        sameLen = len(data[0])
        assert all(len(data[i]) == sameLen for i in range(len(data))), "the length of the series is not equal"
        self.maxLen = sameLen
        self.setUpdatesEnabled(False)
        for i in range(len(self.series)):
            try:
                self.series[i] = data[i]
                x = np.linspace(0, self.series[i].size - 1, 
                                self.series[i].size // self.granularity + 1, 
                                endpoint=True, dtype=int) # with {0, serie.size-1} guaranteed 
                y = self.series[i][x]
                self.plot_data[i].setData(x=x, y=y)
            except Exception as ex:
                print(ex) 
                pass
        self._setLabels(round(self.vLine.value()))
        self.setUpdatesEnabled(True)


    def _AddRuler(self):
        """
        Adds a vertical line movable to the plot for the current position.
        """
        self.vLine = pg.InfiniteLine(angle=90, pen = pg.mkPen(color='blue', width=1), hoverPen = pg.mkPen(color='r',width=2., cosmetic=True), 
                                     movable=True, label="{value:0.0f}", labelOpts={"position":0.05, "movable":True})
        def mouseDrag(line:pg.InfiniteLine):
            index = round(line.p[0])
            new_index = min(max(index, 0), self.maxLen - 1)
            if new_index == index:
                self._setLabels(index)
                self._emit(index)
            else:
                self._setPos(new_index)
                self._emit(new_index)
        self.vLine.sigDragged.connect(mouseDrag)
        self.addItem(self.vLine, ignoreBounds=True )


    def _setPos(self, pos:float):
        """
        Sets the position of the vertical line representing the current position.

        Parameters:
        - pos: The position value.
        """
        # self.vLine.setPos(pos)
        self.sigPosChanged.emit(round(pos))
        self.setUpdatesEnabled(False) # some issues if zoom <> 0 : leave traces of VLine/CurveArrow 
        self.vLine.setPos(pos)
        self._setLabels(pos)
        self.setUpdatesEnabled(True)


    def _setLabels(self, pos):
        """ set the legend label"""
        self.setUpdatesEnabled(False) # some issues if zoom <> 0 : leave traces of VLine/CurveArrow 
        strLegend = ""
        tplValues = ()
        for i in range(len(self.series)): 
            if i == 0 or i in self.lstIndex2Show : # For Loss plot : First Serie == Loss Avg, always visible
                val = "-"
                if pos < len(self.series[i]):
                    val = "%0.3f" % self.series[i][pos]
                    strLegend += f"<span style='font-size: %spt; font-weight:bold; color: #%06x;'> %s=" 
                    if self.bLossLikeLegendBackground:
                        strLegend += f"<span style='background-color:#%06x; color:#0000DD;'>{val}</span> \
                                    " % MxCOLORS.get_color_for_value(float(val)).__hash__()
                    else:
                        strLegend += f"{val}" 
                    strLegend += "</span>,"
                else:
                    strLegend += f"<span style='font-size: %spt; font-weight:bold; color: #%06x;'> %s={val},"

                tplValues += ("10" if self.selected_curve is self.plot_data[i] else "9", self.colors[i].__hash__(), self.labels[i], ) 
        strLegend = strLegend[:-1] # without the last ','
        self.lblLegend.setText(strLegend % tplValues)
        self.setUpdatesEnabled(True)        
    # end _setLabels

    def _emit(self, pos: int):
        if self.sigPosChangedFromHub:
            self.sigPosChangedFromHub.disconnect(self._setPos) 
        self.sigPosChanged.emit(pos)
        if self.sigPosChangedFromHub:       
            self.sigPosChangedFromHub.connect(self._setPos)


    def highlightPlot(self, ix:int):
        if ix >=0 and ix in self.lstIndex2Show:
            highlight_curve = self.plot_data[ix]
        else:
            highlight_curve = None

        self.blockSignals(True)
        self._curveClick(highlight_curve)
        # self.showPlots(self.lstIndex2Show)
        self.blockSignals(False)
        self.curve_clicked = True
        self._setLabels(round(self.vLine.value()))


    def showLossPlots(self, lst_ix:List[int], crt_ix:int):
        """ used only in Loss plots, having 5 lines. \n
        Showing lst_ix and highlight crt_ix. \n
        ix == 0 reserved for Avg Loss, always visible.
        """
        self.lstIndex2Show = lst_ix 
        for ix in range(1, 5):
            line_item = self.plot_data[ix]
            if ix in self.lstIndex2Show:
                line_item.setPen(self.default_pen(line_item))
            else:
                line_item.setPen(self.zero_pen(line_item))
        self.highlightPlot(crt_ix)


    def mouse_clicked(self, *args):
        # unselect if no curve clicked
        if self.curve_clicked == True :
            self.curve_clicked = False
        else:
            try:
                self.selected_curve.setPen(self.default_pen(self.selected_curve))
                self.sigClickedPlotIndex.emit(-1)
            except:
                pass
            self.selected_curve = None
        self._setLabels(round(self.vLine.value()))
    

    def _curveClick(self, curve):
        """ highlight the selected curve """
        self.selected_curve = curve
        self.curve_clicked = True

        # Modify the pen properties of the selected curve
        for ix in self.lstIndex2Show:
            line_item = self.plot_data[ix]
            if line_item == curve:
                pen = line_item.opts['pen']
                pen = pg.mkPen(pen)
                selected_pen = pg.mkPen(color=pen.color(), width=2.8)  
                line_item.setPen(selected_pen)
                self.sigClickedPlotIndex.emit(ix)
            else:
                line_item.setPen(self.default_pen(line_item))


    @staticmethod
    def default_pen(line_item):
        pen = line_item.opts['pen']
        pen = pg.mkPen(pen)
        default_pen = pg.mkPen(color=pen.color(), width=1.8)
        return default_pen        

    @staticmethod
    def zero_pen(line_item):
        pen = line_item.opts['pen']
        pen = pg.mkPen(pen)
        zero_pen = pg.mkPen(color=pen.color(), width=0.1)
        return zero_pen
# end Singles_Plotter

class Pairs_Plotter(pg.PlotWidget):
    """A custom plot widget for displaying pairs of data.

    This widget extends the `pg.PlotWidget` class and provides additional functionality
    for plotting pairs of data. It supports adding pairs of data, setting the granularity
    of the plot, updating the series, and displaying turning points.

    Signals:
        sigPosChanged: This signal is emitted when the position of the plot is changed.
            It provides the new position and the corresponding data values.

    Attributes:
        __instances (dict): A dictionary that stores instances of the `Pairs_Plotter` class.

    Args:
        parent (QWidget): The parent widget.
        sigPosChangedFromHub (Signal, optional): A signal for position changes from the hub.
        HubSlotForPosChanged (Callable, optional): A slot to call when the position is changed.
        background_color (QColor, optional): The background color of the plot.
        granularity (int, optional): The granularity of the plot.
        **kargs: Additional keyword arguments to pass to the base class constructor.
    """

    sigPosChanged = Signal(float, tuple)
    __instances = {}
    # https://stackoverflow.com/questions/1507566/how-and-when-to-appropriately-use-weakref-in-python
    # better : __instances = weakref.WeakValueDictionary() ?

    @classmethod
    def setGranularityFromSignal(cls, i:int):
        """Sets the granularity for all instances of `Pairs_Plotter`."""
        for item in Pairs_Plotter.__instances.values():
            Pairs_Plotter.setGranularity(item, i)

    # region __init__
    def __init__(self, parent=None,
                 sigPosChangedFromHub: Signal | None=None,
                 HubSlotForPosChanged: Callable[[int], None] | None=None, 
                 background_color:QColor|None = None,
                 granularity:int = 1,
                 **kargs):
        """
        Initialize the Plotters object.

        Args:
            parent (QWidget): The parent widget. Defaults to None.
            sigPosChangedFromHub (Signal | None): Signal of PositionChanged from Hub. Defaults to None.
            HubSlotForPosChanged (Callable[[int], None] | None): Slot to call when PositionChanged() is triggered. Defaults to None.
            background_color (QColor | None): The background color of the widget. Defaults to None.
            granularity (int): The granularity of the plot. Defaults to 1.
            **kargs: Additional keyword arguments.

        Returns:
            None
        """
        super().__init__(parent=parent, **kargs)
        
        Pairs_Plotter.__instances[id(self)] = self

        self.series:List[tuple] = [] # pairs => tuple of 2 np.ndarray
        self.plot_data:List[pg.PlotDataItem] = [] # list of PlotDataItem 
        self.arrows:List[pg.CurveArrow] = [] # list of CurveArrow = current position
        self.colors:List[QColor] = [] # list of colors for the lines
        self.labels:List[tuple] = [] # list of pairs values for each line
        self.labelsWdg:List[QLabel] = [] # list of QLabel (with 2 values) for each line
        self.labels_colors:List[tuple] = [] # list of pairs colors for each pair of the current point of the line
        self.turningPoints:List[pg.ScatterPlotItem] = [] # list of turning points(ScatterPlotItem)
        self.sigPosChangedFromHub = sigPosChangedFromHub # Signal of PositionChanged from Hub

        if sigPosChangedFromHub:
            self.sigPosChangedFromHub.connect(self._setPos_and_Labels)

        if HubSlotForPosChanged: # Slot to call when PositionChanged() HERE = only by clicking on TurningPoint ScatterPlotItem
            self.sigPosChanged.connect(HubSlotForPosChanged)            
        self.background_color = background_color
        self.granularity = granularity

        lytV = QVBoxLayout()
        lytV.setContentsMargins(0,0,0,0)
        lytV.setSpacing(0)
        self.lytH = QHBoxLayout()
        self.lytH.setContentsMargins(0,2,2,0)
        self.lytH.setSpacing(5)
        self.lytH.addStretch(1)
        lytV.addLayout(self.lytH, stretch=0)
        lytV.addStretch(1)
        
        self.setBackground(self.background_color)
        if self.background_color is None :
            self.background_color = QColor('white')

        self.setLayout(lytV)
    #endregion __init__
    
    def __del__(self) -> None:
        del Pairs_Plotter.__instances[id(self)] 
       


    def setGranularity(self, granularity:int):
        self.granularity = granularity
        self.updateSeries(*self.series)


    def AddPairs(self, 
                 pairs_serie:tuple, 
                 line_color:QColor=MxCOLORS.W1_Col0, 
                 labels_text:tuple=('x1', 'y1'), 
                 labels_colors:tuple=(MxCOLORS.W1_00, MxCOLORS.W1_10) 
                 ):
        """
        Add pairs of data to the plot.

        Args:
            pairs_serie (tuple): A tuple containing two series of data.
            line_color (QColor, optional): The color of the line plot. Defaults to MxCOLORS.W1_Col0.
            labels_text (tuple, optional): A tuple containing the labels for the x and y axes. Defaults to ('x1', 'y1').
            labels_colors (tuple, optional): A tuple containing the colors for the labels. Defaults to (MxCOLORS.W1_00, MxCOLORS.W1_10).
        """
        pLen = len(pairs_serie[0])
        assert len(pairs_serie[0]) == len(pairs_serie[1]), "the length of the series is not equal"
        if self.series:
            assert len(self.series[0][0]) == pLen, "the length of the series is not equal"
        self.series.append(pairs_serie)
        # with {0, serie.size-1} guaranteed 
        pos_mask = np.linspace(0, pLen-1, pLen // self.granularity + 1, endpoint=True, dtype=int) 
        x = pairs_serie[0][pos_mask]
        y = pairs_serie[1][pos_mask]
        plt = self.plot(x=x, y=y, pen=pg.mkPen(color=line_color, width=1.8))
        self.plot_data.append(plt)

        def _tip(x, y, data):
            s = f"{labels_text[0]} : %0.3f <br>{labels_text[1]} : %0.3f <br>Pos : %d<br>" % (x, y, data)
            return s
        scatter = pg.ScatterPlotItem(symbol='star', size=10, brush=pg.mkBrush(64, 113, 242, 255), tip=_tip, 
                                     hoverable=True, 
                                     hoverSymbol='x', hoverSize=12, hoverBrush=pg.mkColor('g'))
        def _clickTurningPoint(*args):
            ix = args[1][0].data()
            self._setPos_and_Labels(ix)
            self._emit(ix) # emit the signal with the TP position
        scatter.sigClicked.connect(_clickTurningPoint)

        self.turningPoints.append(scatter)
        self.addItem(scatter)

        a = pg.CurveArrow(plt) # mark the current position on this line
        a.setStyle(headLen=15, tailLen=10, pen=line_color.darker(160), brush=line_color.darker(120))
        self.addItem(a)
        self.arrows.append(a)

        self.colors.append(line_color)
        self.labels.append(labels_text)
        self.labels_colors.append(labels_colors)
        self.colors += list(labels_colors)
        qLbl = QLabel(self)
        self.labelsWdg.append(qLbl)
        qLbl.setStyleSheet("QLabel { border: 1px solid #%06x; background-color: #%06x; }"
                           % (line_color.__hash__(), self.background_color.__hash__())
                           )
        self.lytH.addWidget(qLbl, stretch=0, alignment= Qt.AlignRight)
    # end AddPairs

    def updateSeries(self, *data):
        assert len(data) == len(self.series), "Nb series not match "
        sameLen = len(data[0][0])
        assert all((len(data[i][0]) == sameLen and len(data[i][1]) == sameLen) for i in range(len(data))), "the length of the series is not equal"
        for i in range(len(self.series)):
            self.series[i] = (data[i][0], data[i][1])
            # x = self.series[i][0][::self.granularity]
            # y = self.series[i][1][::self.granularity]
            pos_mask = np.linspace(0, sameLen - 1, sameLen // self.granularity + 1, endpoint=True, dtype=int)
                # with {0, serie.size-1} guaranteed 
                # Number of samples to generate + 1, secure min 1
            x = self.series[i][0][pos_mask]
            y = self.series[i][1][pos_mask]
            self.plot_data[i].setData(x=x, y=y)
        

    def setTurningPoints(self, lstTurningPoints:List[int]):
        assert len(self.plot_data) == len(self.series)
        for i in range(len(self.series)): # len(self.plot_data) == len(self.series)
            self.turningPoints[i].clear()
            self.turningPoints[i].setData(x=self.series[i][0][lstTurningPoints], 
                                          y=self.series[i][1][lstTurningPoints], 
                                          data=lstTurningPoints
                                          )

    def _setPos_and_Labels(self, pos:float):
        """ set the current position arrows on all lines and the labels """
        self.setUpdatesEnabled(False) # some issues if zoom <> 0  leave traces of VLine/CurveArrow
        for i in range(len(self.series)):
            if pos < len(self.series[i][0]):
                self.arrows[i].setPos((pos)/(len(self.series[i][0])))
                self.arrows[i].setVisible(True)
                val0 = "%0.3f" % self.series[i][0][pos]
                val1 = "%0.3f" % self.series[i][1][pos]
            else:
                self.arrows[i].setVisible(False)
                val0 = val1 = "-"
            strLegend = "<span style='font-size: 9pt; font-weight:bold;'>"
            tplValues = ()  
            qLabel:QLabel = self.labelsWdg[i]
            strLegend += f"<span style='color: #%06x';> %s={val0},</span> "
            tplValues += (self.labels_colors[i][0].__hash__(), ) + (self.labels[i][0], ) 
            strLegend += f"<span style='color: #%06x'> %s={val1}</span>"
            tplValues += (self.labels_colors[i][1].__hash__(), ) + (self.labels[i][1], )
            qLabel.setText(strLegend % tplValues)
        self.setUpdatesEnabled(True)


    def _emit(self, pos: int):
        # called when a TurningPoint (ScatterPlotItem is clicked
        if self.sigPosChangedFromHub:
            self.sigPosChangedFromHub.disconnect(self._setPos_and_Labels) 
        self.sigPosChanged.emit(pos, (self.series[0][0][pos], 
                                      self.series[0][1][pos], 
                                      self.series[1][0][pos], 
                                      self.series[1][1][pos])
                                      )
        if self.sigPosChangedFromHub:       
            self.sigPosChangedFromHub.connect(self._setPos_and_Labels)
# end Pairs_Plotter           

class HalfPlanes_Plotter(pg.PlotWidget):
    """
    A custom plot widget for visualizing half-planes of a line and  intersections with a given rectangle(QMargins).

    Args:
        parent (QWidget): The parent widget.
        x00_ValX_ValY (np.ndarray): A 4  by 4 matrix containing the 0-3 , X(calculated) and Y(True) associated.
        background_color (QColor | None): The background color of the plot widget. Defaults to None.
        **kargs: Additional keyword arguments to be passed to the base class constructor.

    Attributes:
        colors (list): A list to store the colors of the lines added to the plot.
        lstInfiniteLines (list): A list with the lines that separate the plane in 2 half-planes.
        lstPolygons (list): A list to store the polygons formed by the Lines and Rectangle(QMargins).
        quadrilateral_plotter (pg.PlotDataItem): quadrilateral transformed 'square' corresponding to [00, 01, 11 10]
        quadr_scatter (pg.ScatterPlotItem): The the vertices of the quadrilateral

    Methods:
        setData_Quadrilateral(x00_ValX_ValY: np.ndarray): Sets the data for the quadrilateral plot.
        AddLine(line: Line, margins: QMarginsF, color: QColor, polygon1BrushStyle: Qt.BrushStyle, polygon2BrushStyle: Qt.BrushStyle): 
        Adds a line to the plot widget.
    """
    def __init__(self, parent=None, x00_ValX_ValY = np.array([[0, 0, 0, 0], 
                                           [0, 1, 1, 1], 
                                           [1, 0, 1, 1], 
                                           [1, 1, 0, 0]]), # first 2 columns are the 0-3 values, 3rd column is the calculated value 
                                                            # and 4th column is the expected value
                 background_color: QColor | None = None,
                 **kargs):
        super().__init__(parent=parent, background=background_color, **kargs)
        
        # Initialize attributes
        self.colors = []
        self.lstPolygons = []
        self.lstInfiniteLines = [] # keep it separately to raise up after AddLine
        self.quadrilateral_plotter = None # quadrilateral transformed 'square' corresponding to [00, 01, 11 10]
        self.quadr_scatter = None # the vertices of the quadrilateral
        
        # Set plot properties
        self.setAspectLocked(True)
        self.setBackground(None) # Transparent
        self.setContentsMargins(0, 0, 0, 0)

        # Add vertical and horizontal lines
        vLine = pg.InfiniteLine(angle=90, pen = pg.mkPen(color='gray'), movable=False)
        vLine.setPos(0)
        self.addItem(vLine)
        hLine = pg.InfiniteLine(angle=0, pen = pg.mkPen(color='gray'), movable=False)
        hLine.setPos(0)
        self.addItem(hLine)        

        # real square [00, 01, 11 10]
        _ltr = self.plot(x=[0, 0, 1, 1], y=[0, 1, 1, 0], pen=pg.mkPen(color=QColor('lightslategray')))  # left top right edges
        _b = self.plot(x=[0, 1], y=[0, 0], pen=pg.mkPen(color=QColor('gray')))  # bottom edge

        brush = pg.mkBrush(color=QColor('gray'))
        brush.setStyle(Qt.DiagCrossPattern)
        brush.setStyle(Qt.Dense1Pattern)
        _fill = pg.FillBetweenItem(_ltr, _b, brush=brush)  # Gray fill the real square [00, 01, 11 10]
        self.addItem(_fill)

        # quadrilateral transformed 'square' corresponding to [00, 01, 11 10]
        # here just initialize, will be updated by setData_Quadrilateral
        self.quadrilateral_plotter = self.plot(x=[0], y=[0], pen=pg.mkPen(color=QColor('gray'), width=1.5, style=Qt.DotLine))  
        
        def _tip(x, y, data):
            return f"%0.3f ^ %0.3f = %s" % (x, y, data) # (x, y, data) = (p[0], p[1], p[2])
        # the vertices of the quadrilateral, on hover : show the real values of calculus and the expected result of the vertex
        self.quadr_scatter = pg.ScatterPlotItem(size=20, tip=_tip, pxMode=True, hoverable=True, hoverSize=28 )
        self.addItem(self.quadr_scatter)

        self.setData_Quadrilateral(x00_ValX_ValY)
        self._nb = 0
        self._avg = 0
    # end __init__
    
    def setData_Quadrilateral(self, x00_ValX_ValY:np.ndarray):
        """ Sets the data for the quadrilateral transformed 'square' corresponding to [00, 01, 11 10]"""
        def getSymbol(val:int) -> QPainterPath:
            symbol = QPainterPath()
            font = QFont()
            font.setPointSize(10)
            symbol.addText(0, 0, font, str(int(val)))
            symbol.moveTo(-10 + (np.random.randint(-2, 5)), -20 + (np.random.randint(-2, 5)))
            # slightly random offset to increase visibility if points exactly overlaps AND for seeing that a refresh it's made

            rect = symbol.boundingRect() 
            # To properly obey the position and size, custom symbols should be centered at (0,0) and width and height of 1.0
            scale = min(1. / rect.width(), 1. / rect.height())
            transform = QTransform()
            transform.scale(scale, scale)
            transform.translate(-rect.x() - rect.width() / 2.,  -rect.y() - rect.height() / 2. )
            return transform.map(symbol)
        # end getSymbol 
        
        x = x00_ValX_ValY[[0, 1, 3, 2, 0], 0] # mask to complete(close) the polygon 
        y = x00_ValX_ValY[[0, 1, 3, 2, 0], 1]
        self.quadrilateral_plotter.setData(x=x, y=y)

        self.quadr_scatter.setData(
                        x = x00_ValX_ValY[:, 0], 
                        y = x00_ValX_ValY[:, 1],
                        data = [f"{x00_ValX_ValY[i, 3]:0.3f}"
                                + "\n" + str(i//2) + " ^ " + str(i%2) 
                                + " = " + str(int(x00_ValX_ValY[i, 2])) for i in range(4)],
                        symbol = [getSymbol(val) for val in x00_ValX_ValY[:, 2]],  
                        pen = MxCOLORS.LST_COLOR_X00_X11,
                        brush = MxCOLORS.LST_COLOR_X00_X11,
                        )
    # end setData_Quadrilateral

    def AddLine(self, line:Line, margins: QMarginsF, 
                color=QColor("cyan"), 
                polygon1BrushStyle=Qt.SolidPattern, 
                polygon2BrushStyle=Qt.SolidPattern) :
        """ Add a line to the plotter, who cut the plan in 2 half-planes, 
        and show the intersection with the quadrilateral, by filling the half-planes with the corresponding brush style.
        First the intersection points are calculated, then the polygons are drawn, and finally the line and the intersection points are drawn
        """

        if round(line.a, 3)  == round(line.b, 3) == 0 :
            # there is no line
            return
        
        self.colors.append(color)
        lstPlotsForLine = []
        lstIntersectionsPoints, polygon1, polygon2 = line.PolygonsClockwiseLine(margins)
        match len(lstIntersectionsPoints):
            case 0 | 1:
                distMax = 0 
                pLineMax = QPointF(0,0)
                for p in polygon1:
                    dist, pLine = line.distFromPoint(p)
                    if dist > distMax:
                        distMax = dist
                        pLineMax = pLine
                left = min(pLineMax.x(), min(p.x() for p in polygon1))
                top = max(pLineMax.y(), max(p.y() for p in polygon1))
                right = max(pLineMax.x(), max(p.x() for p in polygon1))
                bottom = min(pLineMax.y(), min(p.y() for p in polygon1))
                margins = QMarginsF(int(0-left), int(top-2), int(right-2), int(0-bottom)) + 1.5 # :D
            case 2:
                pass
            case _: 
                raise Exception("Intersection points > 2 ?! ")

        # add 0.5 for better visibility :)
        lstIntersectionsPoints, polygon1, polygon2 = line.PolygonsClockwiseLine(margins + 0.5)

        arr = np.array([(p.x(), p.y()) for p in lstIntersectionsPoints]).T

        linePlot:pg.PlotDataItem = self.plot(arr[0], arr[1], pen=pg.mkPen(color=color, width=2)) 

        pos = lstIntersectionsPoints[0]
        qLine4Angle = QLineF(lstIntersectionsPoints[0], lstIntersectionsPoints[1])
        angle = 180 - qLine4Angle.angle()
        infLine = pg.InfiniteLine(pos=pos, 
                                  angle=angle, 
                                  pen = pg.mkPen(color=color, width=1.8), 
                                  hoverPen = pg.mkPen(color=color.darker(120), width=2.2), 
                                  movable=True, 
                                  label=f"%0.2f•𝒙%+0.2f•𝒚%+0.2f=0" % (line.a, line.b, line.c), 
                                  labelOpts={"position":0.05, "movable":True, "color":"blue" }
                                  )
        def _sigDragged(*args):
            # movable = True, only for getting hover
            infLine.setPos(pos)

        def _sigClicked(*args):
            f = infLine.label.textItem.font()
            f.setBold(True)
            infLine.label.setFont(f)

        # connect the signals
        infLine.sigClicked.connect(_sigClicked)
        infLine.sigDragged.connect(_sigDragged)

        infLine._nEnter = 0 # to keep track of the number of hoverEvent

        def _hoverEvent(ev):
            """ changing the style of the line definition label when hover, for visibility"""
            if ev.isEnter() :
                infLine._nEnter += 1
                fff = infLine.label.textItem.font()
                fff.setPointSizeF(10.5)
                infLine.label.textItem.setFont(fff)
                infLine.label.textItem.setHtml(
                    "<div style='font-size: larger; font-weight: normal; background:rgba(%d, %d, %d, 80);'>" % QColor('white').rgbTuple()
                    + f"%0.2f•𝒙%+0.2f•𝒚%+0.2f=0" % (line.a, line.b, line.c)
                    + "</div>"
                    ) 
                infLine.label.fill = pg.mkBrush(255, 255, 255, 170)
                infLine.label.border = pg.mkPen(color)
            if ev.isExit():
                infLine._nEnter -= 1
                if infLine._nEnter == 0:
                    fff = infLine.label.textItem.font()
                    fff.setPointSizeF(9.5)
                    infLine.label.textItem.setFont(fff)
                    infLine.label.textItem.setHtml(
                        "<div style='font-weight: normal; background:rgba(%d, %d, %d, 70);'>" % QColor('white').rgbTuple()
                        + f"%0.2f•𝒙%+0.2f•𝒚%+0.2f=0" % (line.a, line.b, line.c)
                        + "</div>") 
                    infLine.label.fill = pg.mkBrush(255, 255, 255, 30)
                    infLine.label.border = pg.mkPen(None)

        def _InfLine_hoverEvent(ev):
            # print(type(ev)) but inaccesible <class 'pyqtgraph.GraphicsScene.mouseEvents.HoverEvent'>
            pg.InfiniteLine.hoverEvent(infLine, ev)
            _hoverEvent(ev)
        
        # wrapping the events
        infLine.hoverEvent = _InfLine_hoverEvent
        infLine.label.hoverEvent = _hoverEvent
        
        self.addItem(infLine)            
        self.lstInfiniteLines.append(infLine)

        lstPlotsForLine.append(linePlot)
        # polygon 1
        color1 = color.lighter(120)
        arr = np.array([(p.x(), p.y()) for p in polygon1]).T
        polPlot = self.plot(arr[0], arr[1], pen=pg.mkPen(color=color, width=1.5))  
        lstPlotsForLine.append(polPlot)
        # Fill line - polygon 1
        brush:QBrush = pg.mkBrush(*color1.rgbTuple(), 150)
            # brush.setStyle(Qt.Dense2Pattern)
        fillPlot = pg.FillBetweenItem(linePlot, polPlot, brush = brush)  
        self.addItem(fillPlot)
        lstPlotsForLine.append(fillPlot)

        brush:QBrush = pg.mkBrush(color)
        brush.setStyle(polygon1BrushStyle)
        fillPlot = pg.FillBetweenItem(linePlot, polPlot, brush = brush)  
        
        self.addItem(fillPlot)
        lstPlotsForLine.append(fillPlot)

        # polygon 2
        color2 = color.darker(100)
        arr = np.array([(p.x(), p.y()) for p in polygon2]).T
        polPlot = self.plot(arr[0], arr[1], pen=pg.mkPen(color=color, width=1.5))  
        lstPlotsForLine.append(polPlot)
        # Fill line - polygon 2
        brush:QBrush = pg.mkBrush(color2.red(), color2.green(), color2.blue(), 150)
            # brush.setStyle(Qt.Dense7Pattern)
        fillPlot = pg.FillBetweenItem(linePlot, polPlot, brush = brush) 
        
        self.addItem(fillPlot)
        lstPlotsForLine.append(fillPlot)
        
        brush:QBrush = pg.mkBrush(color)
        brush.setStyle(polygon2BrushStyle)
        fillPlot = pg.FillBetweenItem(linePlot, polPlot, brush = brush)  
        
        self.addItem(fillPlot)
        lstPlotsForLine.append(fillPlot)        

        self.lstPolygons.append(lstPlotsForLine)

        # raise up infiniteLines
        for infLine in self.lstInfiniteLines:
            self.removeItem(infLine)
            self.addItem(infLine)
    # end AddLine

    def RemoveAllLines(self):
        # remove all lines and polygons
        while self.lstPolygons:
            lPlots = self.lstPolygons.pop(0)
            for pl_item in lPlots:
                self.removeItem(pl_item)

        while self.lstInfiniteLines:
            lPlot = self.lstInfiniteLines.pop(0)
            self.removeItem(lPlot)

# end class HalfPlanes_Plotter


class Dock_Colored(Dock):
    """
    A colored dock widget that supports glowing animation.

    Attributes:
        __SCALE_STEP (float): The scale step used for zooming.
        __instances (dict): A dictionary to keep track of instances of Dock_Colored.

    Methods:
        ClassGlow(cls, lstGlowColors: List[QColor]): Call the glow method to all instances of Dock_Colored.
        __init__(self, name, plotter, area, size, widget, hideTitle, autoOrientation, label, color, sig_extern_glow, **kargs): Initializes a Dock_Colored instance.
        wrap_updateStyleDock(f): Wraps the updateStyleDock method to update the widget area's style sheet.
        wrap_updateStyle_DockLabel(f): Wraps the updateStyle_DockLabel method to update the label's style sheet.
        getScale(self) -> float: Returns the current scale value.
        setScale(self, sc: float): Sets the scale value and updates the view's scale accordingly.
        __del__(self): Destructor method to remove the instance from the __instances dictionary.
        Glow(self, color: QColor): Applies the glow effect to the dock widget IF the color matches his own list of colors.

    """

    __SCALE_STEP = 0.995
    __instances = {}

    @classmethod
    def classGlow(cls, lstGlowColors: List[QColor]):
        """
        Call the glow effect with a list of Colors to all instances of Dock_Colored
        Each instance will decide if it will apply the glow effect or not, based on its own colors list.

        Args:
            lstGlowColors (List[QColor]): A list of colors to apply the glow effect.

        """
        for item in Dock_Colored.__instances.values():
            for color in lstGlowColors:
                Dock_Colored.__glow(item, color)
    # end ClassGlow

    def __init__(self, name, plotter: Singles_Plotter | Pairs_Plotter | HalfPlanes_Plotter,
                 area=None, size=(450, 200), widget=None, hideTitle=False, autoOrientation=True, label=None,
                 color: QColor = MxCOLORS.TBL_HEADER_GRAY,
                 sig_extern_glow: Signal | None = None,
                 **kargs):
        """
        Initializes a Dock_Colored instance.

        Args:
            name: The name of the dock widget.
            plotter: The plotter instance to be added to the dock widget.
            area: The area where the dock widget will be placed.
            size: The size of the dock widget.
            widget: The widget to be added to the dock widget.
            hideTitle: Whether to hide the title of the dock widget.
            autoOrientation: Whether to automatically orient the dock widget.
            label: The label of the dock widget.
            color: The color of the dock widget.
            sig_extern_glow: An external signal for the glow effect.
            **kargs: Additional keyword arguments.
        """
 
        super().__init__(name, area, size, widget, hideTitle, autoOrientation, label, **kargs)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        Dock_Colored.__instances[id(self)] = self

        self._name = ''.join(name.split())
        self.color = color
        if plotter:
            self.plotter = plotter
            self.addWidget(plotter,0,0)
            self.view= plotter.getViewBox()
        
        def wrap_updateStyleDock(f):
            def inner():
                f()
                self.widgetArea.setStyleSheet("""QWidget{
                        border: 1px solid #%06x ;
                        }""" % ( self.color.__hash__())
                        )
            return inner

        def wrap_updateStyle_DockLabel(f):
            def inner():
                f()
                if self.label.orientation == 'horizontal':
                    self.label.setStyleSheet("""DockLabel {
                                       background-color: '#%06x';
                                       border-top-right-radius: 7px;
                                       border-top-left-radius: 7px;
                                       }""" % self.color.__hash__())
                else:
                    self.label.setStyleSheet("""DockLabel {
                                       background-color: '#%06x';
                                       border-top-left-radius: 7px;
                                       border-bottom-left-radius: 7px;
                                       }""" % self.color.__hash__())
            return inner
        self.updateStyle = wrap_updateStyleDock(self.updateStyle)
        self.label.updateStyle = wrap_updateStyle_DockLabel(self.label.updateStyle)

        # if sig_extern_glow:
        #     sig_extern_glow.connect(self.Glow)
        
        self._dummy:float = 0
  
        animUp = QPropertyAnimation(self, QByteArray('scale')) #, self)
        animUp.setStartValue(1)
        animUp.setEndValue(3)
        animUp.setDuration(150)       
        animUp.setEasingCurve(QEasingCurve.InCubic)           

        self.animDown = QPropertyAnimation(self, QByteArray('scale')) #, self)
        self.animDown.setStartValue(-4)
        self.animDown.setEndValue(-1)
        self.animDown.setDuration(150)       
        self.animDown.setEasingCurve(QEasingCurve.OutInCubic)           
        seqGrowAnim = QSequentialAnimationGroup(self)
        seqGrowAnim.addAnimation(animUp)
        seqGrowAnim.addAnimation(self.animDown)

        self.efect = QGraphicsColorizeEffect ()
        self.efect.setColor(QColor('fuchsia'))
        # self.label.setGraphicsEffect(efect)

        animUpGlow = QPropertyAnimation(self.efect, b"strength")#, dock_tittle)  
        animUpGlow.setStartValue(0)
        animUpGlow.setEndValue(1)
        animUpGlow.setDuration(200)       
        animUpGlow.setEasingCurve(QEasingCurve.InOutCubic)

        animDownGlow = QPropertyAnimation(self.efect, b"strength")#, dock_tittle )
        animDownGlow.setStartValue(1)
        animDownGlow.setEndValue(0)
        animDownGlow.setDuration(300)    

        seqGlowAnim = QSequentialAnimationGroup(self)
        seqGlowAnim.addAnimation(animUpGlow)
        seqGlowAnim.addAnimation(animDownGlow)

        self.grpAnimation = QParallelAnimationGroup(self)
        self.grpAnimation.addAnimation(seqGrowAnim)
        self.grpAnimation.addAnimation(seqGlowAnim)
        
        # self.label.sigClicked.connect(self.take_screenshot)
        self.setMinimumSize(QSize(300, 140))
    # end __init__
        

    def getScale(self) -> float:
        return self._dummy

    def setScale(self, sc:float):
        self._dummy = sc
        if sc > 0 :
            self.view.scaleBy((self.__SCALE_STEP, self.__SCALE_STEP))
        else:
            self.view.scaleBy(( 1 / self.__SCALE_STEP, 1 / self.__SCALE_STEP))

    scale = Property(float, getScale, setScale)
        # NOTE: Dock_Colored.scale2 = Property(float, getScale2, setScale2) or other dynamically ... not works 'cause :
        # https://stackoverflow.com/questions/22116670/how-to-dynamically-create-q-properties


    def __del__(self) -> None:
        del Dock_Colored.__instances[id(self)] # needed ?
        return


    def __glow(self, color:QColor):
        """ Apply the glow effect to the dock widget IF the color matches his own list of colors."""
        if not self.plotter: return
        
        lst_colors = [self.color] + self.plotter.colors
        if color in lst_colors:
            # start the animation
            self.label.setGraphicsEffect(self.efect)
            self.grpAnimation.stop()
            self.grpAnimation.start()
# end Dock_Colored    

# region TEST 
    # SVG print HTML screenshot Image resize etc
    # def take_screenshot(self):
    #     p = self.grab()
    #     # p.save('Dock_Colored_' + str(self.label.text()) + '.bmp' , 'BMP', quality=100)
    #     self.wdgImage = Dock_Colored.WDG_label_image(pOrig=p)
    #     self.wdgImage.show()
# endregion TEST 

# region main
if __name__ == "__main__":
    
    from slider import SliderEdit
    
    epoch_size = 200

    x = np.sin(np.linspace(0, 2*np.pi, epoch_size)) 
    y = np.cos(np.linspace(0, 6*np.pi, epoch_size))
    
    z = np.sin(np.linspace(0, 6*np.pi, epoch_size)) 
    w = np.cos(np.linspace(0, 16*np.pi, epoch_size))

    slider = SliderEdit()
    slider.setMinimum(0)
    
    gr = 5

    slider.setMaximum(len(x)-1)

    wdgSinglesPlot = Singles_Plotter(sigPosChangedFromHub=slider.valueChanged, 
                                     HubSlotForPosChanged=slider.setValue, 
                                     granularity=gr, 
                                     name="sgl")
    txtW2="""<span style=\" font-size:9pt; \">W</span>
                                <span style=\" font-size:11pt; vertical-align:super;\">|2|</span>"""
    wdgSinglesPlot.AddSeries(x, MxCOLORS.W1_00, txtW2+'1[1,0]')
    wdgSinglesPlot.AddSeries(y, MxCOLORS.W1_01, 'w1[1,1]')
    
    wdgSinglesPlot.updateSeries(z, w)

    wdgPairesPlotter = Pairs_Plotter(sigPosChangedFromHub=slider.valueChanged, HubSlotForPosChanged=slider.setValue, granularity=gr)

    wdgPairesPlotter.AddPairs(pairs_serie=(x, y), labels_colors=(MxCOLORS.W1_00, MxCOLORS.W1_01), 
                              line_color=MxCOLORS.W1_Col0, 
                              labels_text=(txtW2 + '1[0,0]', 'w1[0,1]') )
    wdgPairesPlotter.AddPairs(pairs_serie=(z, w), labels_colors=(MxCOLORS.W1_10, MxCOLORS.W1_11), 
                              line_color=MxCOLORS.W1_Col1, 
                              labels_text=('w1[1,0]', 'w1[1,1]') )

    my_generator = np.random.default_rng()
    lstTurningPoints = list(my_generator.integers(0, epoch_size, my_generator.integers(1, max(min(7, epoch_size), 2 ))))
    print(lstTurningPoints)
    wdgPairesPlotter.setTurningPoints(lstTurningPoints)
    wdgSinglesPlot.setTurningPoints(lstTurningPoints)
    slider.setTurningPoints(lstTurningPoints, [ str(x) for x in lstTurningPoints])

    dockArea = DockArea()

    pyQTdockUp = Dock('main', hideTitle=True)
    dockChild = Dock_Colored(name="Pairs", plotter=wdgPairesPlotter, color=MxCOLORS.W1_Col1)


    plotPlane = HalfPlanes_Plotter()
    
    def update_Planes(pos:int):
        plotPlane.setUpdatesEnabled(False)
        plotPlane.RemoveAllLines()
        a, b, c = x[pos], y[pos], z[pos]
        line = Line(a, b, c)
        plotPlane.AddLine(line, QMarginsF(1,2,2,1), MxCOLORS.W1_Col0, Qt.HorPattern, Qt.VerPattern)
        a, b, c = z[pos], w[pos], x[pos]
        line = Line(a, b, c)
        plotPlane.AddLine(line, QMarginsF(2,1,1,2), MxCOLORS.W1_Col1, Qt.FDiagPattern, Qt.BDiagPattern)
        gen = np.random.default_rng()
        zero = lambda : (gen.random() - 0.5) / 2
        unu = lambda : (gen.random() / 4 ) + 1
        arr = np.array([[zero(), zero(), 0, zero()], [zero(), unu(), 1, unu()], [unu(), zero(), 1, unu()], [unu(), unu(), 0, zero()]])
        plotPlane.setData_Quadrilateral(x00_ValX_ValY=arr)
        plotPlane.setUpdatesEnabled(True)

    slider.valueChanged.connect(update_Planes)

    line = Line(0.1, 1, -3)
    plotPlane.AddLine(line, QMarginsF(1,2,2,1), MxCOLORS.W1_Col0, Qt.HorPattern, Qt.VerPattern)
    line = Line(1, 2, -0.8)
    plotPlane.AddLine(line, QMarginsF(2,1,1,2), MxCOLORS.W1_Col1, Qt.FDiagPattern, Qt.BDiagPattern)
    dockPlane = Dock_Colored(name="Half Planes", plotter=plotPlane, color=combineColors(MxCOLORS.W1_Col0, MxCOLORS.W1_Col1))

    dockArea.addDock(dockPlane)
    dockArea.addDock(pyQTdockUp)
    dockArea.addDock(dockChild)

    btnGranularityTP = QPushButton("Granularity / Generating list TP")
    btnGranularityTP.setCheckable(True)
    btnGranularityTP.setChecked(True)
    btnGranularityTP.state = {}
    
    def _toggledTP(checked:bool):
        sv = slider.value()
        wdgSinglesPlot._setPos(0)
        wdgPairesPlotter._setPos_and_Labels(0)
        if checked:
            wdgSinglesPlot.setGranularity(1)
            wdgPairesPlotter.setGranularity(1)
        else:
            wdgSinglesPlot.setGranularity(10)
            wdgPairesPlotter.setGranularity(10)
        wdgSinglesPlot._setPos(sv)
        wdgPairesPlotter._setPos_and_Labels(sv)
        
        lstTurningPoints = list(my_generator.integers(0, epoch_size, my_generator.integers(1, max(min(7, epoch_size), 2 ))))
        print(lstTurningPoints)
        if 0 not in lstTurningPoints:
            lstTurningPoints.insert(0, 0)
        if epoch_size-1 not in lstTurningPoints:
            lstTurningPoints.append(epoch_size-1)
        wdgPairesPlotter.setTurningPoints(lstTurningPoints)
        wdgSinglesPlot.setTurningPoints(lstTurningPoints)
        slider.setTurningPoints(lstTurningPoints, [ str(x) for x in lstTurningPoints])


    btnGranularityTP.toggled.connect(_toggledTP)

    btnOvertaking = QPushButton("overtaking")
    def _clickOvertaking(*args):
        nInt = int(2 * np.random.random_sample() * slider.maximum() + 2)
        slider.setValue(nInt)
        slider._valueChanged(nInt)
    btnOvertaking.clicked.connect(_clickOvertaking)

    dock1 = Dock_Colored(name="Single ...", plotter=wdgSinglesPlot, color=MxCOLORS.W1_Row0)
    if (lyt := QVBoxLayout()):
        lyt.addWidget(dock1)
        lyt.addWidget(slider)
        lyt.addWidget(btnOvertaking)
        lyt.addWidget(btnGranularityTP)
    
    wdgMain = QWidget()
    wdgMain.setLayout(lyt)

    pyQTdockUp.addWidget(wdgMain)

    winMain = QWidget()
    l = QVBoxLayout()
    l.setContentsMargins(0,0,0,0)
    l.addWidget(dockArea)
    l.setSpacing(0)
    winMain.setWindowTitle("Test")
    winMain.setLayout(l)

    winMain.resize(600, 800)
 
    winMain.show()
    gApp.exec()
# endregion main
