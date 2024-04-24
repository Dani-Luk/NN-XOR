# main.py 
"""
XOR Main Windows
"""

import os
from random import randint
from functools import partial
from typing import Any, List, Union
from operator import __add__

from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea

from PySide6.QtCore import (QEasingCurve, QEvent, QFileInfo, 
                            QModelIndex, QItemSelection, QKeyCombination, QObject, QPropertyAnimation,
                            QPoint, QRect, QSettings, QSize, Qt, QTimer
                            )
from PySide6.QtGui import ( QAction, QFontMetrics, QKeyEvent, QKeySequence, QColor, QPainter,
                           QMouseEvent, QPaintEvent, QResizeEvent, QCloseEvent
                           )
from PySide6.QtWidgets import (QAbstractItemView, QDockWidget,
                               QFileDialog, QLabel, QMainWindow,
                               QMenu, QMessageBox, QStyle,
                               QVBoxLayout, QWidget, 
                               )

from global_stuff import gApp, globalParameters, MxCOLORS, combineColors, NBSP, MAX_LEN_FILENAME_JSON, MODELS_DIR, APP_NAME
from custom_widgets import FadingMessageBox

from delegates import MxQTableView, TableView_sigCurrentChanged
from models import XOR_model, XOR_Slice
from control_panel import ControlPanel
from panels import (GraphPanel, SliderPanel, WxPanel, panel_W1_HalfPlanes,
                    panel_W2_HalfPlanes, z1a1z2Panel)
from plotters import (Dock_Colored, HalfPlanes_Plotter, Pairs_Plotter,
                      Singles_Plotter)
from tabs import TabDragEdit

# TODO : test Linux :D

class Dock_VLeftLabel_Resizable(QDockWidget):
    """A dock with a vertical label on the left side, resizable and detachable by double click on the label."""
    _minHeight = 180
    def __init__(
                self,
                parent: "MainWindowXOR", 
                childWidget: QWidget,
                title: str = "0 ^ 0 = ...",
                background_color: QColor = QColor('gray'),
                color:QColor = QColor('red'),
                font_weight : str = 'bold'
                ) -> None:
        
        QDockWidget.__init__(self, title, parent, flags=Qt.WindowStaysOnTopHint)
        self.setFeatures(QDockWidget.DockWidgetVerticalTitleBar | QDockWidget.DockWidgetFloatable )
        self._parent = parent
        self._childWidget = childWidget
        self.strChildName = 'aaazzz'
        childWidget.setObjectName(self.strChildName)
        childWidget.setStyleSheet(" QWidget#%s { border: 2px solid #%06x; margin: 0px;}" % (self.strChildName, background_color.__hash__()))
        
        self._title = title
        self.background_color = background_color
        self.dockedHeight = self._minHeight 
        self.floatingHeight = self._minHeight
        self.neverDettached = True # we dont have any positions to restore, so put it exactly below

        self.lblDock = QLabel("1     ") # with some spaces to be able to rotate
        self.lblDock.resize(29, 100)
        self.lblDock.setStyleSheet("""QLabel { background-color: #%06x;
                                    color: #%06x;
                                    font-weight: %s;
                                    border: 1px solid #%06x; 
                                    border: 1px solid white; 
                                    border-width : 2px 0px 2px 2px;
                                    border-top-left-radius: 8px;
                                    border-bottom-left-radius: 8px;
                                }""" % (background_color.__hash__(), color.__hash__(), font_weight, background_color.__hash__()))
        self.lblDock.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter )

        def _lblDock_paintEvent(event:QPaintEvent):
            """Paint the label rotated 90 degrees counter clockwise."""
            painter = QPainter(self.lblDock)
            fm: QFontMetrics = painter.fontMetrics()
            strX = self._title
            textSize = fm.size(Qt.TextSingleLine, strX, 0)
            r = QRect(0,0, textSize.width(), textSize.height())
            painter.translate(r.center())
            painter.rotate(-90)
            painter.translate(-(event.rect().height() + textSize.width()) / 2 + textSize.height() / 2 , 
                                - textSize.width() / 2 + (event.rect().width() - textSize.height()) / 2 + 2)
            painter.drawText(r, strX , Qt.AlignCenter)
        
        self.lblDock.paintEvent = _lblDock_paintEvent            
        
        def _lblDock_mouseDoubleClickEvent(event: QMouseEvent):
            # event for attach / detach the dock
            if not self.isFloating():
                # is docked, so detach it
                self._parent.setUpdatesEnabled(False)
                self.dockedHeight = self.height()
                self.setVisible(False)
                self.setFloating(True)
                gApp.processEvents() # to consume the resize event ...
                self._parent.resize(self._parent.width(), self._parent.height() - self.dockedHeight - 4)
                if self.neverDettached:
                    # when the first time detached, deploy it exactly below
                    self.neverDettached = False
                    self.floatingHeight = self.dockedHeight 
                    self.move(self._parent.geometry().bottomLeft() + QPoint(0, 3))
                self._parent.setUpdatesEnabled(True)
                self.setUpdatesEnabled(True)
                self._parent.expand_az() # some animation
            else:
                # is floating, so attach it
                self.floatingHeight = self.height()
                self._parent.setUpdatesEnabled(False)
                self.setVisible(False)
                self.setFloating(False)
                self._parent.setUpdatesEnabled(True)
                self.setUpdatesEnabled(True)
                self._parent.expand_az() # some animation
        # end _lblDock_mouseDoubleClickEvent
        self.lblDock.mouseDoubleClickEvent = _lblDock_mouseDoubleClickEvent
        self.lblDock.move(5, 0)

        self.setTitleBarWidget(self.lblDock)

        childWidget.setParent(self)
        childWidget.setMinimumHeight(0)
        self._childWidget.move(self.lblDock.width() - 4 , 2)
    # end __init__
    
    def setTitle(self, title:str):
        self._title = title
        self.lblDock.repaint()
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.isFloating():
            self.floatingHeight = self.height()
        self._childWidget.resize(event.size() - QSize(self.lblDock.width() + 3, 4))
# end class Dock_VLeftLabel_Resizable    

class MainWindowXOR(QMainWindow):
    def __init__(self, ) -> None:
        
        super().__init__()
        # now, we have a UI support for displaying the progress bar
        XOR_model.wdgMainWindow = self

        self.installEventFilter(self) # be the first, 'cause there are another filter in Tabs control
        import os
        modelsPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..' , MODELS_DIR))
        if not os.path.exists(modelsPath):
            os.makedirs(modelsPath)

        self._lastUsedDirectory = modelsPath
        self.settings = QSettings()

        self.setup_data_and_UI()

        self.wdgCtrlPanel.tabGlobalParam.sig_Load_UI_Requested.connect(self.readSettings_UI)
        self.wdgCtrlPanel.tabGlobalParam.sig_Save_UI_Requested.connect(self.writeSettings_UI)

        self.matrixPanel._x00_Table.setCurrentIndex(self.matrixPanel._x_model.createIndex(0, 0))
        QTimer.singleShot(100, lambda: self.matrixPanel.btnExpand.toggle())

        if globalParameters._KeepFocusOnSlider:
            QTimer.singleShot(1, self.pSlider.slider.setFocus)
        
        globalParameters.sigKeepFocusOnSlider.connect( lambda v : self.pSlider.slider.setFocus() if v else None)
    # end __init__

    def closeEvent(self, event: QCloseEvent) -> None:
        # close the docks also
        self.topDock.close()
        for dock in self.dock_plotters_Graph_Matrix_CtrlPanel.docks.values():
            try:
                dock.close()
            except:
                pass
        
        self.bottomDock.close()
        for dock in self.wdgz1a1z2.dockArea.docks.values():
            try:
                dock.close()        
            except:
                pass
        return super().closeEvent(event)
    # end closeEvent

    def constructTopDock(self) -> QDockWidget:
        self.tabModels = TabDragEdit(self, self.createNewModel, self.mXORmodel, menu = self.menu)
        self.tabModels.sigModelChanged.connect(self.setCrtModel)

        topLayout_Tab_and_Plotters = QVBoxLayout()
        topLayout_Tab_and_Plotters.setContentsMargins(2, 1, 2, 2)
        topLayout_Tab_and_Plotters.setSpacing(2)
        topLayout_Tab_and_Plotters.addWidget(self.tabModels, stretch=0, alignment=Qt.AlignTop)

        self.graphPanel = GraphPanel()
        self.matrixPanel = WxPanel(self.mXORmodel)

        mArr = self.mXORmodel.xor_array

        # region W1 Rows
        txtW1 = """<span style=\" font-size:9pt; \">W</span>
                                <span style=\" font-size:11pt; vertical-align:super;\">|1|</span>"""

        self.plotter_W1_Row0 = Singles_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, 
                                               name="W1 R0", 
                                               HubSlotForPosChanged=self.pSlider.SetPos)
        data_W1_00 = mArr.w1[..., 0, 0]
        data_W1_01 = mArr.w1[..., 0, 1]
        self.plotter_W1_Row0.AddSeries(data_W1_00, MxCOLORS.W1_00, txtW1 + '[0,0]')
        self.plotter_W1_Row0.AddSeries(data_W1_01, MxCOLORS.W1_01, txtW1 + '[0,1]')
        dock_W1_Row0 = Dock_Colored("W1 Row 0", size=(800,400), 
                                    color=MxCOLORS.W1_Row0, 
                                    plotter=self.plotter_W1_Row0)
                                    # sig_extern_glow=self.matrixPanel.W1_Table.sigGlow) # actually, the sig_extern_glow is obsolete

        self.plotter_W1_Row1 = Singles_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, 
                                               name="W1 R1", 
                                               HubSlotForPosChanged=self.pSlider.SetPos)
        data_W1_10 = mArr.w1[:, 1, 0]
        data_W1_11 = mArr.w1[:, 1, 1]
        self.plotter_W1_Row1.AddSeries(data_W1_10, MxCOLORS.W1_10, txtW1 + '[1,0]')
        self.plotter_W1_Row1.AddSeries(data_W1_11, MxCOLORS.W1_11, txtW1 + '[1,1]')
        dock_W1_Row1 = Dock_Colored("W1 Row 1", size=(800,400), 
                                    color=MxCOLORS.W1_Row1, 
                                    plotter=self.plotter_W1_Row1)
                                    # sig_extern_glow=self.matrixPanel.W1_Table.sigGlow)
        # endregion W1 Rows

        # region W1 Cols
        w1_R0C0 = mArr.w1[ :, 0, 0]
        w1_R1C0 = mArr.w1[ :, 1, 0]
        w1_biasC0 = mArr.w1[ :, 2, 0]

        self.plotter_W1_Col0 = Singles_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, name = 'W1 C0')
        self.plotter_W1_Col0.sigPosChanged.connect(self.pSlider.SetPos)
        self.plotter_W1_Col0.AddSeries(w1_R0C0, MxCOLORS.W1_00, txtW1 + '[0,0]')
        self.plotter_W1_Col0.AddSeries(w1_R1C0, MxCOLORS.W1_10, txtW1 + '[1,0]')
        self.plotter_W1_Col0.AddSeries(w1_biasC0, MxCOLORS.BIAS.darker(120), 'b' + chr(0x2081) + '[0]')

        self.dock_W1_Col0 = Dock_Colored(name="W1 Col 0", 
                                         color=MxCOLORS.W1_Col0, 
                                         plotter=self.plotter_W1_Col0)


        w1_R0C1 = mArr.w1[ :, 0, 1]
        w1_R1C1 = mArr.w1[ :, 1, 1]
        w1_biasC1 = mArr.w1[ :, 2, 1]

        self.plotter_W1_Col1 = Singles_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, name = 'W1 C1')
        self.plotter_W1_Col1.sigPosChanged.connect(self.pSlider.SetPos)
        self.plotter_W1_Col1.AddSeries(w1_R0C1, MxCOLORS.W1_01, txtW1 + '[0,1]')
        self.plotter_W1_Col1.AddSeries(w1_R1C1, MxCOLORS.W1_11, txtW1 + '[1,1]')
        self.plotter_W1_Col1.AddSeries(w1_biasC1, MxCOLORS.BIAS.darker(120), 'b' + chr(0x2081) + '[1]')

        self.dock_W1_Col1 = Dock_Colored("W1 Col 1",color=MxCOLORS.W1_Col1, plotter=self.plotter_W1_Col1)

        # endregion W1 Cols

        # region W1 Pairs
        self.plotterPairs_W1_Rows = Pairs_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, 
                                                  HubSlotForPosChanged=self.pSlider.SetPos )

        self.plotterPairs_W1_Rows.AddPairs(
                            pairs_serie=(mArr.w1[:, 0, 0], mArr.w1[:, 0, 1]),
                            line_color=MxCOLORS.W1_Row0, 
                            labels_colors=(MxCOLORS.W1_00, MxCOLORS.W1_01),
                            labels_text=(txtW1 + '[0,0]', txtW1 + '[0,1]')
                            )

        self.plotterPairs_W1_Rows.AddPairs(
                            pairs_serie=(mArr.w1[:, 1, 0], mArr.w1[:, 1, 1]),
                            line_color=MxCOLORS.W1_Row1, 
                            labels_colors=(MxCOLORS.W1_10, MxCOLORS.W1_11),
                            labels_text=(txtW1 + '[1,0]', txtW1 + '[1,1]')
                            )

        dock_Pairs_W1_Rows = Dock_Colored("W1 Rows", 
                            color = combineColors(MxCOLORS. W1_Row0, MxCOLORS.W1_Row1), 
                            plotter=self.plotterPairs_W1_Rows)

        self.plotterPairs_W1_Cols = Pairs_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, 
                                                  HubSlotForPosChanged=self.pSlider.SetPos )

        self.plotterPairs_W1_Cols.AddPairs(
                            pairs_serie=(mArr.w1[:, 0, 0], mArr.w1[:, 1, 0]),
                            line_color=MxCOLORS.W1_Col0, 
                            labels_colors=(MxCOLORS.W1_00, MxCOLORS.W1_10),
                            labels_text=(txtW1 + '[0,0]', txtW1 + '[1,0]')
                            )

        self.plotterPairs_W1_Cols.AddPairs(
                            pairs_serie=(mArr.w1[:, 0, 1], mArr.w1[:, 1, 1]),
                            line_color=MxCOLORS.W1_Col1, 
                            labels_colors=(MxCOLORS.W1_01, MxCOLORS.W1_11),
                            labels_text=(txtW1 + '[0,1]', txtW1 + '[1,1]')
                            )

        self.dock_Pairs_W1_Cols = Dock_Colored("W1 Columns", 
                            color = combineColors(MxCOLORS. W1_Col0, MxCOLORS.W1_Col1), 
                            plotter=self.plotterPairs_W1_Cols)
        # endregion W1 Pairs

        def _W1_selectionModel_selectionChanged(selected: QItemSelection,  deselected :QItemSelection ):
            # deselect all highlights line from plotters
            self.plotter_W1_Row0.highlightPlot(-1)
            self.plotter_W1_Row1.highlightPlot(-1)
            self.plotter_W1_Col0.highlightPlot(-1)
            self.plotter_W1_Col1.highlightPlot(-1)
            if len(selected.indexes()) == 1 :
                # deselect _W1_b1_Table 
                self.matrixPanel.W1_b1_Table.setCurrentIndex(QModelIndex())
                mIx:QModelIndex = selected.indexes()[0] # get just the fist one
                row, column = mIx.row(), mIx.column()
                match (row, column):
                    case (0, 0):
                        self.plotter_W1_Row0.highlightPlot(0)
                        self.plotter_W1_Col0.highlightPlot(0)
                    case (0, 1):
                        self.plotter_W1_Row0.highlightPlot(1)
                        self.plotter_W1_Col1.highlightPlot(0)
                    case (1, 0):
                        self.plotter_W1_Row1.highlightPlot(0)
                        self.plotter_W1_Col0.highlightPlot(1)
                    case (1, 1):
                        self.plotter_W1_Row1.highlightPlot(1)
                        self.plotter_W1_Col1.highlightPlot(1)
            return
        # end _W1_selectionModel_selectionChanged
        self.matrixPanel.W1_Table.selectionModel().selectionChanged.connect( _W1_selectionModel_selectionChanged)

        def _W1_b1_selectionModel_selectionChanged(selected: QItemSelection,  deselected :QItemSelection ):
            # deselect all highlights from plotters
            self.plotter_W1_Col0.highlightPlot(-1)
            self.plotter_W1_Col1.highlightPlot(-1)
            if len(selected.indexes()) == 1 :
                # deselect _W1_Table 
                self.matrixPanel.W1_Table.setCurrentIndex(QModelIndex())
                mIx:QModelIndex = selected.indexes()[0]
                column = mIx.column()
                match column:
                    case 0:
                        self.plotter_W1_Col0.highlightPlot(2)
                    case 1:
                        self.plotter_W1_Col1.highlightPlot(2)
            return
        # end _W1_b1_selectionModel_selectionChanged
        self.matrixPanel.W1_b1_Table.selectionModel().selectionChanged.connect( _W1_b1_selectionModel_selectionChanged)

        # region loss
        self.plotter_loss = Singles_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, 
                                            HubSlotForPosChanged=self.pSlider.SetPos,
                                            bLossLikeLegendBackground=True
                                    )
        self.plotter_loss.AddSeries(mArr.lossAvg[:, 0, 0], MxCOLORS.LOSS_COST_COLOR, 'Cost(loss):')
        self.plotter_loss.AddSeries(mArr.lossPerX[:, 0, 0], MxCOLORS.X00_COLOR, NBSP + ' 0^0')
        self.plotter_loss.AddSeries(mArr.lossPerX[:, 1, 0], MxCOLORS.X01_COLOR, NBSP + ' 0^1')
        self.plotter_loss.AddSeries(mArr.lossPerX[:, 2, 0], MxCOLORS.X10_COLOR, NBSP + ' 1^0')
        self.plotter_loss.AddSeries(mArr.lossPerX[:, 3, 0], MxCOLORS.X11_COLOR, NBSP + ' 1^1')

        self.matrixPanel._Z1_Table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        lstHubTables:List[Union[MxQTableView, TableView_sigCurrentChanged]] = [
            self.matrixPanel._x00_Table, 
            self.matrixPanel._Z1_Table, 
            self.matrixPanel._A1_Table, 
            self.matrixPanel._Z2_Table, 
            self.matrixPanel._y00_Table, 
            self.matrixPanel._lossPerX_table] # the tables that are connected to the hub to synchronize the current row

        def hub_XZAY_CurrentChange(row:int, objEmitter: Any):
            for tbl in lstHubTables:
                if tbl is not objEmitter:
                    try: 
                        tbl.sigCurrentChanged.disconnect()
                    except:
                        pass
                    if row == -1:
                        if tbl is not self.matrixPanel._lossPerX_table:
                            tbl.setCurrentIndex(QModelIndex())    
                        else:
                            self.plotter_loss.highlightPlot(-1)
                    else:
                        if tbl is not self.matrixPanel._lossPerX_table:
                            if tbl is not self.matrixPanel._x00_Table:
                                tbl.selectRow(row)
                            else:
                                self.matrixPanel._x00_Table.setSelectionBehavior(QAbstractItemView.SelectRows)
                                tbl.selectRow(row)
                                self.matrixPanel._x00_Table.setSelectionBehavior(QAbstractItemView.SelectItems)
                        else:
                            self.plotter_loss.highlightPlot(row + 1)

                    tbl.sigCurrentChanged.connect(hub_XZAY_CurrentChange) # reconnect to the Hub
                elif tbl is self.matrixPanel._lossPerX_table: # and tbl is the Emitter 
                    # matrixPanel._lossPerX_table dont receive from others, so doit himself
                    self.plotter_loss.highlightPlot(row + 1)
            # end for tbl in lstHubTables
            
            # set the operation index for the graph, the matrixPanel and the z1a1z2Panel
            self.graphPanel.operationIndex = row
            self.graphPanel.Set_XOR_item(self.pSlider.slider.getVirtualValue(), self.mXORmodel.getCrtSlice())
            self.matrixPanel.setSelectedOperation(row)
            self.wdgz1a1z2.setSelectedOperation(row) 
            strTitle = ' ^ '.join(f'{row:02b}') + ' = ' + str(self.mXORmodel.getCrtSlice().yParam[row][0])
            self.bottomDock.setTitle(strTitle)
        # end def hub_XZAY_CurrentChange

        for tbl in lstHubTables:    
            tbl.sigCurrentChanged.connect(hub_XZAY_CurrentChange)
        
        # when _lossPerX_table.sigSelectionChanged => show the corresponding loss/x(x==operation) plots 
        self.matrixPanel._lossPerX_table.sigSelectionChanged.connect(
            lambda lst_ix:  self.plotter_loss.showLossPlots(
                list(map(partial(__add__, 1), lst_ix)), 
                self.matrixPanel._y00_Table.currentIndex().row() + 1) # select the corresponding row in the y00_Table (result and y_true)
            )
        self.plotter_loss.showLossPlots([], -1) # initial state, show only the average loss

        def _plotter_loss_sigClickedPlotIndex(ix:int):
            # when the user click a plot, select the corresponding row in the _lossPerX_table
            if ix == -1:
                self.matrixPanel._lossAvg_Table.setCurrentIndex(QModelIndex()) # unselect all
                self.matrixPanel._lossPerX_table.setCurrentIndex(QModelIndex())
            elif ix == 0:
                self.matrixPanel._lossAvg_Table.selectRow(0)
                self.matrixPanel._lossPerX_table.setCurrentIndex(QModelIndex())
            else:
                self.matrixPanel._lossAvg_Table.setCurrentIndex(QModelIndex())
                hub_XZAY_CurrentChange(ix - 1, None)
            return
        # end _plotter_loss_sigClickedPlotIndex 
        self.plotter_loss.sigClickedPlotIndex.connect(_plotter_loss_sigClickedPlotIndex)

        self.dock_loss = Dock_Colored("Loss", 
                                      color=MxCOLORS.LOSS_HEADER_COLOR, 
                                      plotter=self.plotter_loss, )
                                #   sig_extern_glow=self.matrixPanel._lossAvg_Table.sigGlow) # actually, the sig_extern_glow is obsolete
        # endregion Loss

        # region W2
        txtW2 = """<span style=\" font-size:9pt; \">W</span>
                                <span style=\" font-size:11pt; vertical-align:super;\">|2|</span>"""
        
        self.plotter_W2_pairs = Pairs_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged)
        self.plotter_W2_pairs.AddPairs(
                            pairs_serie=(mArr.w2[:, 0, 0], mArr.w2[:, 1, 0]),
                            line_color=combineColors(MxCOLORS.W2_0, MxCOLORS.W2_1),
                            labels_colors=(MxCOLORS.W2_0, MxCOLORS.W2_1),
                            labels_text=(txtW2 + '[0]', txtW2 + '[1]')
                            )
        self.dock_W2_pairs = Dock_Colored("W2 pairs", 
                                          color=MxCOLORS.W2_Col, 
                                          plotter=self.plotter_W2_pairs, )
                                        #   sig_extern_glow=self.matrixPanel.W2_Table.sigGlow)
        self.dock_W2_pairs.setStretch(10, 10)

        self.plotter_W2_singles = Singles_Plotter(sigPosChangedFromHub=self.pSlider.sigSliceChanged, name='w2')
        self.plotter_W2_singles.AddSeries(
                            serie=mArr.w2[:, 0, 0], 
                            color=MxCOLORS.W2_0,
                            label=txtW2 + '[0]'
                            )
        self.plotter_W2_singles.AddSeries(
                            serie=mArr.w2[:, 1, 0], 
                            color=MxCOLORS.W2_1,
                            label=txtW2 + '[1]'
                            )
        self.plotter_W2_singles.AddSeries(
                            serie=mArr.w2[:, 2, 0], 
                            color=MxCOLORS.BIAS.darker(120),
                            label='b' + chr(0x2082) 
                            )


        self.plotter_W2_singles.sigPosChanged.connect(self.pSlider.SetPos)
        self.dock_W2_singles = Dock_Colored("W2 singles", 
                                            color=MxCOLORS.W2_Col, 
                                            plotter=self.plotter_W2_singles, )
                                            # sig_extern_glow=self.matrixPanel.W2_Table.sigGlow)
        self.dock_W2_singles.setStretch(10, 10)
        # endregion W2

        def _W2_selectionModel_selectionChanged(selected: QItemSelection,  deselected :QItemSelection ):
            # deselect 
            self.plotter_W2_singles.highlightPlot(-1)
            if len(selected.indexes()) == 1 :
                self.matrixPanel.W2_b2_Table.setCurrentIndex(QModelIndex())
                mIx:QModelIndex = selected.indexes()[0]
                row = mIx.row()
                self.plotter_W2_singles.highlightPlot(row)
            return
        self.matrixPanel.W2_Table.selectionModel().selectionChanged.connect( _W2_selectionModel_selectionChanged)

        def _W2_b2_selectionModel_selectionChanged(selected: QItemSelection,  deselected :QItemSelection ):
            # deselect all
            self.plotter_W2_singles.highlightPlot(-1)
            if len(selected.indexes()) == 1 :
                self.matrixPanel.W2_Table.setCurrentIndex(QModelIndex())
                self.plotter_W2_singles.highlightPlot(2)
            return
        self.matrixPanel.W2_b2_Table.selectionModel().selectionChanged.connect( _W2_b2_selectionModel_selectionChanged)

        # region Control Panel
        self.wdgCtrlPanel = ControlPanel()
        self.wdgCtrlPanel.setXORModel(self.mXORmodel)
        self.dock_CtrlPanel = Dock('Control Panel', widget=self.wdgCtrlPanel, autoOrientation=False)
        self.dock_CtrlPanel.sizeHint = lambda : QSize(410, 293)
        self.dock_CtrlPanel.setMinimumSize(QSize(410, 293))
        self.dock_CtrlPanel.setOrientation(o='horizontal')
        self.dock_CtrlPanel.setStretch(10, 30)
        # endregion Control Panel

        # region Graph 
        dock_Graph = Dock('Graph', hideTitle=True)
        dock_Graph.addWidget(self.graphPanel)
        # endregion Graph
        
        # region Half Planes
        plotPlane = HalfPlanes_Plotter()
        self.dock_W1_HalfPlanes = panel_W1_HalfPlanes("W1: two classifications / one transformation", 
                                                      plotter=plotPlane, 
                                                      color=combineColors(MxCOLORS.W1_Col0, MxCOLORS.W1_Col1),
                                                      # sig_extern_glow=self.matrixPanel.W1_Table.sigGlow, 
                                                      )

        plotPlane = HalfPlanes_Plotter()
        self.dock_W2_HalfPlanes = panel_W2_HalfPlanes("W2: one classification", plotter=plotPlane, 
                                                        color=MxCOLORS.W2_0, 
                                                        # sig_extern_glow=self.matrixPanel.W2_Table.sigGlow, 
                                                        )
        # end region Half Planes

        # region Matrix
        self.dock_Matrix = Dock("Matrix", hideTitle=True) 
        def wrap_updateStyleDock(f):
            def inner():
                f()
                self.dock_Matrix.widgetArea.setStyleSheet("""
                        Dock > QWidget {
                            border: 0px solid #0000ff;
                        }""") # No more border, thx
            return inner
        
        self.dock_Matrix.updateStyle = wrap_updateStyleDock(self.dock_Matrix.updateStyle)
        
        def _updateStyleDock(s:Dock):
                Dock.updateStyle(s)
                s.widgetArea.setStyleSheet("""
                        Dock > QWidget {
                            border-bottom: 1px solid rgba(200, 200, 200, 100);
                        }""") 

        # dock_Graph.updateStyle = lambda: _updateStyleDock(dock_Graph) # same as :
        dock_Graph.updateStyle = partial(_updateStyleDock, dock_Graph)

        self.dock_Matrix.addWidget(self.matrixPanel)
        # endregion Matrix

        # region arrange docks
        self.dock_plotters_Graph_Matrix_CtrlPanel = DockArea()
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_Matrix)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(dock_Graph, 'top', self.dock_Matrix)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_W2_HalfPlanes, 'right', dock_Graph)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_W2_singles, 'right', self.dock_W2_HalfPlanes)

        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_W1_Col1, 'top', dock_Graph)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_W1_Col0, 'top', self.dock_W1_Col1)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_Pairs_W1_Cols, 'top', self.dock_W1_Col0)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(dock_W1_Row1, 'left', self.dock_W1_Col1)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(dock_W1_Row0, 'left', self.dock_W1_Col0)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(dock_Pairs_W1_Rows, 'left', self.dock_Pairs_W1_Cols)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_W1_HalfPlanes, 'top', self.dock_W2_HalfPlanes)

        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_W2_pairs, 'top', self.dock_W2_singles)
        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_CtrlPanel, 'top', self.dock_W2_pairs)

        self.dock_plotters_Graph_Matrix_CtrlPanel.addDock(self.dock_loss, 'right', self.dock_Matrix)
        self.dock_loss.setStretch(30, 5)
        self.dock_Matrix.setStretch(22, 5)

        topLayout_Tab_and_Plotters.addWidget(self.dock_plotters_Graph_Matrix_CtrlPanel, stretch=1)
        # endregion arrange docks

        def _btnExpand_toggled(checked:bool):
 
            if checked :
                self.expand_az()
            else:
                self.collapse_az()

        self.matrixPanel.btnExpand.toggled.connect(_btnExpand_toggled)

        wdg_top_Tab_and_Plotters = QWidget()
        wdg_top_Tab_and_Plotters.setLayout(topLayout_Tab_and_Plotters)

        dockTop = QDockWidget("", self)
        dockTop.setTitleBarWidget(QWidget())
        dockTop.setContextMenuPolicy(Qt.PreventContextMenu)
        dockTop.setFeatures(QDockWidget.NoDockWidgetFeatures)

        dockTop.setWidget(wdg_top_Tab_and_Plotters)

        return dockTop
    # end constructTopDock method
    
    def constructCentralWidget(self) -> QWidget:
        # actually, the central widget is the slider panel
        lyCentral = QVBoxLayout() 
        lyCentral.setContentsMargins(2, 1, 1, 1)
        lyCentral.setSpacing(0)
        self.pSlider = SliderPanel()
        
        lyCentral.addWidget(self.pSlider, stretch=0)
        wdgCentral = QWidget()
        wdgCentral.setLayout(lyCentral)
        wdgCentral.setFixedHeight(25)

        return wdgCentral
    # end constructCentralWidget method

    def setup_UI(self):
        self.setUpdatesEnabled(False)
        self.setWindowTitle("An " + APP_NAME)

        wdgCentral = self.constructCentralWidget()
        self.setCentralWidget(wdgCentral)

        self.topDock = self.constructTopDock()
        self.topDock.setObjectName("topDock")

        self.addDockWidget(Qt.TopDockWidgetArea, self.topDock, Qt.Orientation.Vertical)


        self.wdgz1a1z2 = z1a1z2Panel(self.pSlider.sigSliceChanged, self.pSlider.SetPos, parent=self)
        self.bottomDock = Dock_VLeftLabel_Resizable(title="0 ^ 0 = 1", parent=self, childWidget=self.wdgz1a1z2,
                                                    background_color=QColor('blue').lighter(170), 
                                                    color=QColor('red'), 
                                                    font_weight='bold')
        self.bottomDock.setObjectName("bottomDock")
        self.bottomDock.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottomDock)

        self.resizeDocks([self.bottomDock], [self.bottomDock.dockedHeight - 50 ],  Qt.Vertical )

        self.bottomDock.hide()
        self.setUpdatesEnabled(True)
    # end setup_UI method

    def setup_data_and_UI(self):
        # initialise objects, bind connections, menu and then call the setup_UI
        tpIni = XOR_Slice(3) # for reproducibility
        self.mXORmodel = XOR_model(tpIni)

        self.mXORmodel.sigModelChanged.connect(self.RefreshCurrentModel)

    # region Menu
        menu = QMenu(self)
        menu.setStyleSheet("""
                        QMenu {background-color: #bde9e2;
                        }
                        QMenu::item{
                        background-color: #bde9e2;
                        }
                        QMenu::item:selected{
                        background-color:  #9dd9d2;
                        color: #000;
                        }"""
                            )

        action = QAction("&New model", self)
        action.setShortcut(QKeySequence.New)
        def _actionNewModel():
            _newModelName = self.tabModels.getNextName()
            _newXorModel = self.createNewModel()
            _newXorModel.modelName = _newModelName
            self.tabModels.addTabAndEdit(_newModelName, data=_newXorModel)
        action.triggered.connect(_actionNewModel)
        menu.addAction(action)

        action = QAction('&Duplicate model', self)
        action.setShortcut(QKeyCombination(Qt.ControlModifier, Qt.Key_D))
        def _duplicateModel():
            _newModelName = self.tabModels.getNextName(self.mXORmodel.modelName + " bis")
            _newXorModel = self.mXORmodel.clone()
            _newXorModel.modelName = _newModelName
            self.tabModels.addTabAndEdit(_newModelName, ix=self.tabModels.currentIndex() + 1, data=_newXorModel)
        action.triggered.connect(_duplicateModel)
        menu.addAction(action)
        
        action = QAction('&Open JSON', self)
        action.setShortcut(QKeySequence.Open)
        action.triggered.connect(self.loadModel)
        menu.addAction(action)

        menu.addSeparator()

        action = QAction('&Save JSON', self)
        action.setShortcut(QKeySequence.Save)
        action.triggered.connect(self.saveModel)
        menu.addAction(action)

        action = QAction('Save &As...', self)
        action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        action.triggered.connect(partial(self.saveModel, bSaveAs=True))
        menu.addAction(action)

        menu.addSeparator()
        action = QAction('Print as HTML/PDF', self)
        def _print():
            msgPrint = FadingMessageBox("Print", "Not implemented ... 😁", 1700, self, QMessageBox.Information)
            msgPrint.show()
        action.triggered.connect(_print)
        menu.addAction(action)

        menu.addSeparator()
        action = QAction('&Help', self)
        action.setShortcut(QKeySequence("F1"))

        def _showReadMeFile():
            import webbrowser
            # Specify the path to your HTML file
            file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..' , "README.html"))

            # Open the file in the default web browser
            # trying to open it in a new tab if possible
            webbrowser.open_new('file://' + os.path.realpath(file_path))
 
        action.triggered.connect(_showReadMeFile)
        menu.addAction(action)

        menu.addSeparator()
        action = QAction('A&bout', self)
        def _about():
            # msgAbout = FadingMessageBox("About", "<p style='font-size:15px'> What about? 😄 </p", 
            #                             2400, self, QMessageBox.Question)
            htmlText = """<p style='font-size:15px; font-style: italic; text-align: right;'> 
                        \"I'm a joker, I'm a smoker, I'm a midnight toker ...\" <br>
                        <a href='https://www.youtube.com/watch?v=dV3AziKTBUo'> Steve Miller Band - The Joker</a> &nbsp; &nbsp; 
                        </p>"""
            msgAbout = FadingMessageBox("About", htmlText, 3380, self, QMessageBox.Information) # 3:38 is the duration of the song :D
            msgAbout.show() # how many can you open ? :D
        action.triggered.connect(_about)
        menu.addAction(action)

        self.menu = menu
    # endregion Menu        
        
        # app.processEvents()
        self.setup_UI()

        self.pSlider.setData(self.mXORmodel.count() - 1, [0],
                              self.mXORmodel.lstTurningPointsDiff, 
                              0 if globalParameters.StayOnPosOnFillModel else self.mXORmodel.count() - 1
                              )
        self.pSlider.setWhatToCallToGetCrtSlice(self.mXORmodel.getCrtSlice)

        def _setSliderValue(ix:int):
            self.pSlider.slider.setValue(ix)

        self.wdgCtrlPanel.sigTPChanged.connect(_setSliderValue)

        self.mXORmodel.getCrtTPModel().sigTPSeedChanged.connect(self.refreshWxPanelFromTPSeedChanged, Qt.UniqueConnection )

        self.matrixPanel.w1b1w2b2_Signal.connect(
            lambda *args : self.graphPanel.Set_XOR_item(self.pSlider.slider.getVirtualValue(), self.mXORmodel.getCrtSlice()))
        
        def refreshHalfPlanes():
            item = self.mXORmodel.getCrtSlice()
            self.dock_W1_HalfPlanes.update_Planes(item)
            self.dock_W2_HalfPlanes.update_Planes(item)
       
        self.matrixPanel.w1b1w2b2_Signal.connect(refreshHalfPlanes)

        self.wdgz1a1z2.SetModel(self.mXORmodel)
        self.wdgz1a1z2.setSelectedOperation(0)

        def _x_selectionChanged(selected: QItemSelection, deselected: QItemSelection):
            # show/hide the values of the nodes in the graph
            if selected.count() > 0:
                self.graphPanel.showNodesValues = True
            else:
                self.graphPanel.showNodesValues = False
            self.graphPanel.Set_XOR_item(self.pSlider.slider.getVirtualValue(), self.mXORmodel.getCrtSlice())
            self.matrixPanel._x_Table.repaint()
        self.matrixPanel._x_Table.selectionChanged =_x_selectionChanged

        def _connector_clicked():
            # reverse the selection
            if len(self.matrixPanel._x_Table.selectedIndexes()) > 0:
                self.matrixPanel._x_Table.clearSelection()
            else: 
                self.matrixPanel._x_Table.selectRow(0)
        self.matrixPanel._connector.clicked.connect(_connector_clicked)

        self.pSlider.sigSliceChanged.connect(self.Set_XOR_item)

        rightMenuSlider = QMenu()
        action = QAction("New model from &here", self)
        def _actionNewModelFromHere():
            _newModelName = self.tabModels.getNextName(
                        self.mXORmodel.modelName + f" from {self.mXORmodel.getCrtSlice().index}"
                        )
            _newXorModel = self.createNewModel(bFromCurrentTP=True)
            _newXorModel.modelName = _newModelName
            _newXorModel.maskParamLocks = self.mXORmodel.maskParamLocks
            self.tabModels.addTabAndEdit(_newModelName, ix=self.tabModels.currentIndex() + 1 ,data=_newXorModel)
        action.triggered.connect(_actionNewModelFromHere)
        rightMenuSlider.addAction(action)

        action = QAction("&Before Delete", self)
        action.triggered.connect(lambda : self.mXORmodel.deleteBefore(self.mXORmodel.getPos()))
        rightMenuSlider.addAction(action)

        action = QAction("Delete &After", self)
        def _deleteAfter():
            self.mXORmodel.deleteAfterPos(self.mXORmodel.getPos())
        action.triggered.connect(_deleteAfter)
        rightMenuSlider.addAction(action)

        self.pSlider.slider.setRightClickMenu(rightMenuSlider)


        def _setStretch():
            self.dock_W1_HalfPlanes.setStretch(650, self.dock_Pairs_W1_Cols.height() + 4 + self.dock_W1_Col0.height())
            self.dock_W2_HalfPlanes.setStretch(650, self.dock_W1_Col1.height() + self.dock_Matrix.height())
            self.dock_CtrlPanel.setStretch(650, self.dock_Pairs_W1_Cols.height() + 6 + self.dock_W1_Col0.height())
            self.dock_W2_pairs.setStretch(650, (self.dock_W1_Col1.height() + self.dock_Matrix.height() + 2) / 2)
            self.dock_W2_singles.setStretch(650, (self.dock_W1_Col1.height() + self.dock_Matrix.height() + 2) / 2)
            self.dock_loss.setStretch(self.dock_W2_singles.width() + 3, 200)
            self.dock_Matrix.setStretch(1800 - self.dock_W2_singles.width() - 3, 200)

        QTimer.singleShot(0, _setStretch) # after is actually shown
    # end setup_data_and_UI method

    def createNewModel(self, bFromCurrentTP:bool = False) -> XOR_model:
        if bFromCurrentTP:
            tp = self.mXORmodel.getCrtSlice().clone()
        else:
            tp = XOR_Slice(randint(1, 65535))
        newModel = XOR_model(tp)
        # self.mXORmodel = newModel
        return newModel

    def refreshWxPanelFromTPSeedChanged(self):
        self.matrixPanel.Set_XOR_item(self.mXORmodel.getCrtSlice().index, self.mXORmodel.getCrtSlice()) 

    def setCrtModel(self, model:XOR_model):
        print('MainWindow setCrtModel', id(model))
        if self.mXORmodel is model:
            print('same model, Tab moved, do nothing')
            return
        newPos = self.pSlider.slider.getVirtualValue() if globalParameters.KeepOnePosForAllModels else model.getPos()
        self.mXORmodel = model
        # rebinding the connections
        bRes = self.mXORmodel.sigModelChanged.connect(self.RefreshCurrentModel, Qt.UniqueConnection)
        
        self.mXORmodel.getCrtTPModel().sigTPSeedChanged.connect(self.refreshWxPanelFromTPSeedChanged, Qt.UniqueConnection )

        self.mXORmodel.setPos(newPos)

        self.RefreshCurrentModel(newPos)


    def RefreshCurrentModel(self, pos:int):
        # resetting the data for plotters, CtrlPanel, matrixPanel, z1a1z2Panel
        self.wdgCtrlPanel.setXORModel(self.mXORmodel)

        xorArray = self.mXORmodel.xor_array
        tp_list = self.mXORmodel.lstTurningPoints
        tp_indexes_list = [ix.index for ix in tp_list]
        self.pSlider.slider.setTurningPoints(tp_indexes_list, self.mXORmodel.lstTurningPointsDiff)
        self.pSlider.slider.setMaximum(self.mXORmodel.count() - 1)
        self.pSlider.setWhatToCallToGetCrtSlice(self.mXORmodel.getCrtSlice)
        self.matrixPanel.setModel(self.mXORmodel)

        self.plotter_W1_Row0.updateSeries(xorArray.w1[:, 0, 0], xorArray.w1[:, 0, 1])
        self.plotter_W1_Row0.setTurningPoints(tp_indexes_list)

        self.plotter_W1_Row1.updateSeries(xorArray.w1[:, 1, 0], xorArray.w1[:, 1, 1])
        self.plotter_W1_Row1.setTurningPoints(tp_indexes_list)

        self.plotterPairs_W1_Rows.updateSeries(
            (xorArray.w1[:, 0, 0], xorArray.w1[:, 0, 1]), 
            (xorArray.w1[:, 1, 0], xorArray.w1[:, 1, 1])
            )
        self.plotterPairs_W1_Rows.setTurningPoints(tp_indexes_list)

        self.plotter_W1_Col0.updateSeries(xorArray.w1[:, 0, 0], xorArray.w1[:, 1, 0], xorArray.w1[:, 2, 0])
        self.plotter_W1_Col0.setTurningPoints(tp_indexes_list)

        self.plotter_W1_Col1.updateSeries(xorArray.w1[:, 0, 1], xorArray.w1[:, 1, 1], xorArray.w1[:, 2, 1])
        self.plotter_W1_Col1.setTurningPoints(tp_indexes_list)

        self.plotterPairs_W1_Cols.updateSeries(
            (xorArray.w1[:, 0, 0], 
            xorArray.w1[:, 1, 0]
            ), 
            (xorArray.w1[:, 0, 1],
            xorArray.w1[:, 1, 1]
            )
            )
        self.plotterPairs_W1_Cols.setTurningPoints(tp_indexes_list)

        self.plotter_loss.updateSeries(xorArray.lossAvg[:, 0, 0], 
                                xorArray.lossPerX[:, 0, 0],
                                xorArray.lossPerX[:, 1, 0],
                                xorArray.lossPerX[:, 2, 0],
                                xorArray.lossPerX[:, 3, 0],
                                )

        self.plotter_loss.setTurningPoints(tp_indexes_list)

        self.plotter_W2_singles.updateSeries(xorArray.w2[:, 0, 0], xorArray.w2[:, 1, 0], xorArray.w2[:, 2, 0], )
        self.plotter_W2_singles.setTurningPoints(tp_indexes_list)

        self.plotter_W2_pairs.updateSeries((xorArray.w2[:, 0, 0], xorArray.w2[:, 1, 0]))
        self.plotter_W2_pairs.setTurningPoints(tp_indexes_list)
        self.wdgz1a1z2.SetModel(self.mXORmodel)

        self.pSlider.slider.setValue(pos)
        # force trigger to update the labels
        self.pSlider.slider._valueChanged(pos)
        self.pSlider.ValueChanged(pos) # emit the signal to update the crt position in the plotters
        
        self.repaint()
        return
    # end RefreshCurrentModel method

    def Set_XOR_item(self, i:int, item:XOR_Slice):
        self.mXORmodel.setPos(i) 
        self.wdgCtrlPanel.RefreshCboAndTabFromXORmodel()
        self.matrixPanel.Set_XOR_item(i, item) 


    def expand_az(self):
        """expand the z-a Dock panel, docked or not"""
        # expand means -> it's not visible, so set min size, make it visible and anim to size
        if self.bottomDock.isFloating():
            self.bottomDock._childWidget.setStyleSheet(" QWidget#%s { border: 3px solid #%06x; margin: 1px; }" 
                    % (self.bottomDock.strChildName, self.bottomDock.background_color.__hash__()))
            # anim the weight of the dock
            anim = QPropertyAnimation(self.bottomDock, b'size', self) 
            anim.setStartValue(QSize(self.bottomDock.width(), 22)) # say it min==22, label paint issue
            anim.setEndValue(QSize(self.bottomDock.width(), self.bottomDock.floatingHeight))
            anim.setDuration(300)       
            anim.setEasingCurve(QEasingCurve.OutQuad)          
            self.bottomDock.resize(self.bottomDock.width(), 22)
            self.bottomDock.setVisible(True)
            self.bottomDock.setUpdatesEnabled(True)
            anim.start()            
        else:
            # if the bottomDock is docked
            self.bottomDock._childWidget.setStyleSheet(
                " QWidget#%s { border: 2px solid #%06x; margin: 0px;}"  
                % (self.bottomDock.strChildName, self.bottomDock.background_color.__hash__()))
            # lock the height of the top dock
            self.setUpdatesEnabled(False)
            self.topDock.setFixedHeight(self.topDock.height())
            self.bottomDock.setVisible(True)

            # anim the weight of the MainWindow => Δ bottomDock.height()
            anim = QPropertyAnimation(self, b'size', self)  
            anim.setStartValue(QSize(self.width(), self.height() + 22 + 3)) # +3 for separator
            anim.setEndValue(QSize(self.width(), self.height() +  self.bottomDock.dockedHeight - 22))
            anim.setDuration(300)       
            anim.setEasingCurve(QEasingCurve.OutQuad)          
            self.setUpdatesEnabled(True)            
            anim.start()            

            # unlock the height of the top dock
            def _anim_expand_finished():
                self.topDock.setMaximumSize(5000, 5000)
                self.topDock.setMinimumSize(10, 10)
            anim.finished.connect(_anim_expand_finished)


    def collapse_az(self):
        """ collapse the z-a Dock panel, docked or not"""
        # collapse => it's visible 
        if self.bottomDock.isFloating():
            # save the height 
            _tmp_height = self.bottomDock.floatingHeight
            anim = QPropertyAnimation(self.bottomDock, b'size', self) 
            anim.setStartValue(self.bottomDock.size())
            anim.setEndValue(QSize(self.bottomDock.width(), 22)) # say it min==22, label paint issue
            anim.setDuration(300)       
            anim.setEasingCurve(QEasingCurve.OutQuad)          
            anim.start()   
            def _finished():
                self.bottomDock.setVisible(False)
                self.bottomDock.floatingHeight = _tmp_height 
            anim.finished.connect(_finished)
        else:
            # save the height 
            self.bottomDock.dockedHeight = self.bottomDock.height()
            
            # lock the height of the top dock
            self.topDock.setFixedHeight(self.topDock.height())

            self.setUpdatesEnabled(False)

            # anim the weight of the MainWindow => Δ bottomDock.height()
            anim = QPropertyAnimation(self, b'size', self) 
            anim.setStartValue(self.size()) 
            anim.setEndValue(QSize(self.width(), self.height() - self.bottomDock.dockedHeight + 22))
            anim.setDuration(300)       
            anim.setEasingCurve(QEasingCurve.OutQuad)          
            self.setUpdatesEnabled(True)            
            anim.start()            
            # unlock the height of the top dock and hide the bottom dock
            def _anim_collapse_finished():
                self.topDock.setMaximumSize(5000, 5000)
                self.topDock.setMinimumSize(0,0)
                self.setUpdatesEnabled(False)    
                self.bottomDock.setVisible(False)
                tmpHeight = self.height() - self.bottomDock.height() - 3 - 1
                QTimer.singleShot(0, lambda : (self.resize(self.width(), tmpHeight), self.setUpdatesEnabled(True)))

            anim.finished.connect(_anim_collapse_finished)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self and event.type() == QEvent.KeyPress:
            ev:QKeyEvent = event
            if ev.keyCombination() in (QKeyCombination(Qt.ControlModifier, Qt.Key_Return), 
                                       QKeyCombination(Qt.ControlModifier | Qt.KeypadModifier, Qt.Key_Enter)
                                       ):
                self.pSlider.setFocus()
                return True
            if ev.keyCombination() in (QKeyCombination(Qt.ControlModifier, Qt.Key_QuoteLeft), 
                                       QKeyCombination(Qt.ShiftModifier | Qt.ControlModifier, Qt.Key_AsciiTilde)
                                       ):
                # I had no other idea
                # 'T' (toggle) is much too far from Ctrl
                # but '~' seen as bitwise inverter aka toggling, not so bad, I think :D
                self.matrixPanel.btnExpand.toggle()
                return True
        return super().eventFilter(watched, event)

    def loadModel(self):
            """
            Opens a file dialog to select a JSON model file and loads the model.

            Returns:
                None
            """
            fileDialog = QFileDialog(parent=self, 
                                     caption='Open json model', 
                                     directory=self._lastUsedDirectory, 
                                     filter='JSON model (*.json)')
            fileDialog.setModal(True)
            fileDialog.show()
            def _loadFromJson(fileSelected:str):
                if not fileSelected.strip() :
                    return
                self._lastUsedDirectory = fileDialog.directory().absolutePath()
                fileDialog.close()
                try :
                    newModel = XOR_model.LoadFromJson(fileSelected)
                except Exception as e:
                    QMessageBox(QMessageBox.Critical, "Error", f"Error: {e}", QMessageBox.StandardButton.Ok, self).show()
                    return
                if newModel:
                    fileInfo = QFileInfo(fileSelected)
                    self.tabModels.addTabAndEdit(name=fileInfo.completeBaseName(), data=newModel, bEdit=False)
            fileDialog.fileSelected.connect(_loadFromJson)
            return
        

    def saveModel(self, bSaveAs: bool = False) -> bool:
        """
        Saves the XOR model to a JSON file.

        Args:
            bSaveAs (bool, optional): Indicates whether to save the model with a new name. Defaults to False.

        Returns:
            bool: True if the model is successfully saved, False otherwise.
        """
        crtXorModel = self.mXORmodel
        if crtXorModel.lastSavedFileInfo is None:
            newFileName = self._lastUsedDirectory + "/" + crtXorModel.modelName + '.json'
        else:
            newFileName = crtXorModel.lastSavedFileInfo.absolutePath() + "/" + crtXorModel.modelName + '.json'

        if ( crtXorModel.lastSavedFileInfo is None 
            or crtXorModel.lastSavedFileInfo.absoluteFilePath() != newFileName
            or bSaveAs
            ):
            # check exist and confirm first save
            newFileName = QFileDialog.getSaveFileName(parent=self, 
                                                      caption="Save as..", 
                                                      dir=newFileName, 
                                                      filter='JSON model (*.json)' )[0]
           
            if newFileName == "":
                # was cancel it
                return False
            
            fileInfo = QFileInfo(newFileName)
            if len(fileInfo.completeBaseName()) > MAX_LEN_FILENAME_JSON :
                QMessageBox(QMessageBox.Critical, "File name length exceeded", 
                            "File name length exceeds 50.\nTruncated but NOT saved!",
                            QMessageBox.StandardButton.Ok,
                            self
                            ).show()
                self.mXORmodel.modelName = fileInfo.completeBaseName()[:MAX_LEN_FILENAME_JSON]
                # anyway keep the name attempt and signal the change
                self.mXORmodel.sigModelNameChanged.emit(self.mXORmodel.modelName)
                return False

        fileInfo = QFileInfo(newFileName)
        sRet = self.mXORmodel.SaveToJson(fileInfo)

        if sRet == "":
            msgBox = FadingMessageBox(
                    "Saved", 
                    f"Model saved as: <span style='color: blue; font:bold;'> {fileInfo.fileName()} </span> \
                    <br> (in <a href='{fileInfo.absolutePath()}'> {fileInfo.absolutePath()}</a>)", 
                    delay=1500, 
                    parent=self)
            msgBox.show()
            return True
        else:
            # some error
            msgBox = FadingMessageBox(
                    "Saving Error", 
                    f"Error: <span style='color: blue; font:bold;'> {sRet} </span> \
                    <br> (when saving as : {fileInfo.absoluteFilePath()})", 
                    delay=3000, 
                    parent=self, icon=QMessageBox.Warning)
            msgBox.show()
            return False


    def writeSettings_UI(self):
        """
        Writes the UI settings to the registry.

        This method saves the state and geometry of the main window, as well as the settings of various dock widgets.
        The saved settings are stored in the registry using globalParameters.settings_DocksUI_to_registry.

        Raises:
            Exception: If an error occurs while writing the settings to the registry.

        Returns:
            None
        """
        try:
            state_data = self.saveState()
            globalParameters.settings_DocksUI_to_registry.setValue("MainWindow_state", state_data)
            globalParameters.settings_DocksUI_to_registry.setValue("MainWindow_geometry", self.saveGeometry())

            globalParameters.settings_DocksUI_to_registry.setValue("BottomDock_floatingHeight", self.bottomDock.floatingHeight)
            globalParameters.settings_DocksUI_to_registry.setValue("BottomDock_dockedHeight", self.bottomDock.dockedHeight)
            globalParameters.settings_DocksUI_to_registry.setValue("BottomDock_isFloating", int(self.bottomDock.isFloating()))
            globalParameters.settings_DocksUI_to_registry.setValue("BottomDock_isVisible", int(self.bottomDock.isVisible()))

            topPanels = self.dock_plotters_Graph_Matrix_CtrlPanel.saveState()
            bottomPanels = self.wdgz1a1z2.dockArea.saveState()
            globalParameters.settings_DocksUI_to_registry.setValue("topPanels", topPanels)
            globalParameters.settings_DocksUI_to_registry.setValue("bottomPanels", bottomPanels)
        except Exception as e:
            print("Exception in writeSettings_UI", e)
            FadingMessageBox("Error", "Error in writeSettings_UI\n" + str(e), 2500, self, QMessageBox.Critical).show()
        else:
            FadingMessageBox("Saved", "UI settings saved, Ok.", 1500, self).show()
    # end writeSettings_UI

    def readSettings_UI(self):
        """
        Reads and restores the UI settings from the registry.

        This method retrieves the saved UI settings from the registry and restores the state of various UI elements,
        such as dock panels, window geometry, and visibility of the bottom dock.

        Returns:
            None
        """

        # tmp_state_data = self.saveState()
        # tmp_geometry = self.saveGeometry()
        # tmp_topPanels = dict(self.dock_plotters_Graph_Matrix_CtrlPanel.saveState())
        # tmp_bottomPanels = dict(self.wdgz1a1z2.dockArea.saveState())
        # doesn't work, still have some exceptions from DockArea.restoreState ... 

        topPanels = globalParameters.settings_DocksUI_to_registry.value("topPanels", self.dock_plotters_Graph_Matrix_CtrlPanel.saveState())
        bottomPanels = globalParameters.settings_DocksUI_to_registry.value("bottomPanels", self.wdgz1a1z2.dockArea.saveState())

        # some exceptions from DockArea.restoreState ... to investigate maybe later :D
        try:
            self.dock_plotters_Graph_Matrix_CtrlPanel.restoreState(topPanels)
        except Exception as e:
            print("Exception in readSettings_UI dock_plotters_Graph_Matrix_CtrlPanel.restoreState", e)
            pass

        try:
            self.wdgz1a1z2.dockArea.restoreState(bottomPanels)
        except Exception as e:
            print("Exception in readSettings_UI wdgz1a1z2.dockArea.restoreState", e)
            pass

        self.setUpdatesEnabled(False)
        try:
            self.restoreGeometry(globalParameters.settings_DocksUI_to_registry.value("MainWindow_geometry", self.saveGeometry()))
        except Exception as e:
            print("Exception in readSettings_UI restoreGeometry", e)
            pass
        state_data = globalParameters.settings_DocksUI_to_registry.value("MainWindow_state", self.saveState())

        try:
            self.restoreState(state_data) # type: ignore
        except Exception as e:
            print("Exception in readSettings_UI restoreState", e)
            pass

        bottomDock_isFloating = int(globalParameters.settings_DocksUI_to_registry.value(
                "BottomDock_isFloating", int(self.bottomDock.isFloating()))) # type: ignore
        bottomDock_isVisible = int(globalParameters.settings_DocksUI_to_registry.value(
                "BottomDock_isVisible", int(self.bottomDock.isVisible()))) # type: ignore

        gApp.processEvents()
        self.setUpdatesEnabled(True)

        self.bottomDock.floatingHeight = int(globalParameters.settings_DocksUI_to_registry.value(
                "BottomDock_floatingHeight", self.bottomDock.floatingHeight))  # type: ignore
        self.bottomDock.dockedHeight = int(globalParameters.settings_DocksUI_to_registry.value(
                "BottomDock_dockedHeight", self.bottomDock.dockedHeight))  # type: ignore

        if bottomDock_isVisible:
            if bottomDock_isFloating:
                self.bottomDock.setVisible(False)
                self.expand_az()
            else:
                # Visible and docked
                self.collapse_az()
                QTimer.singleShot(500, self.expand_az)

        self.repaint()

        self.matrixPanel.btnExpand.blockSignals(True)
        self.matrixPanel.btnExpand.setChecked(bool(bottomDock_isVisible))
        self.matrixPanel.btnExpand.blockSignals(False)
        self.matrixPanel._btnExpand_toggled(bool(bottomDock_isVisible)) # no signal emitted

        # doesn't work, still have some exceptions from DockArea.restoreState ... 
        # except Exception as e:
            # print("Exception in readSettings_UI", e)
            # self.setUpdatesEnabled(False)
            # self.dock_plotters_Graph_Matrix_CtrlPanel.restoreState(tmp_topPanels)
            # self.wdgz1a1z2.dockArea.restoreState(tmp_bottomPanels)
            # self.restoreGeometry(tmp_geometry) 
            # self.restoreState(tmp_state_data)
    
    # end readSettings_UI


if __name__ == "__main__":

    wnd = MainWindowXOR()
    
    wnd.setStyleSheet("""
            QMainWindow::separator {
                    width: 4px; /* when vertical */
                    height: 4px; /* when horizontal */  
                      }
            QMainWindow::separator:hover { 
                      background: #0078d4; }                     
                      """)

    gApp.setWindowIcon(gApp.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)) # think it's a good one
    wnd.show()
    # and now we can get the right geometry...

    scrn = wnd.screen()
    # scrn = app.primaryScreen()

    screenGeometry =  scrn.availableGeometry()
    wnd.resize(1800, screenGeometry.height() - 250)
    x = (screenGeometry.width() - wnd.width()) // 2
    wnd.move(screenGeometry.x() + x, 5)

    globalParameters.sigGranularity.connect(Pairs_Plotter.setGranularityFromSignal)
    globalParameters.sigGranularity.connect(Singles_Plotter.setGranularityFromSignal)

    globalParameters.plottersGranularity = globalParameters.plottersGranularity
    # aka globalParameters.SignalGranularity.emit(globalParameters.plottersGranularity)

    gApp.exec()
   


