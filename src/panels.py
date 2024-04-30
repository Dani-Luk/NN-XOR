# panels.py

from operator import __add__
from typing import List, Optional, Callable

import numpy as np
import pandas as pd

from pyqtgraph.dockarea.DockArea import DockArea
from PySide6.QtCore import (Qt, QTimer, Signal, QElapsedTimer, 
                            QModelIndex, QPersistentModelIndex,
                            QPoint, QRect, QSize, QMarginsF )
from PySide6.QtGui import (QColor, QFont, QMouseEvent, QPainter, QPaintEvent,
                           QPen, QResizeEvent)
from PySide6.QtWidgets import (QAbstractItemView, QDataWidgetMapper, QFrame,
                               QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QTableView, QVBoxLayout, QWidget)


from global_stuff import (globalParameters, 
                          MxCOLORS, backgroundColorContrast, combineColors, 
                          gPixmapDown, gPixmapUp
                          )
from custom_widgets import ToolTip_CommitOnChange_ComboBox
from core import FunctionsListsByType
from delegates import MxQTableView, TableView_sigCurrentChanged, IntDelegate
from graph import Graph
from models import (XOR_model, XOR_Slice, XOR_array_model,
                    MatrixWithMaskAndColoredHeaderModel,
                    X00_Model, Y00_Model,
                     )
from plotters import (Dock_Colored, HalfPlanes_Plotter, Pairs_Plotter, Singles_Plotter)
from slider import SliderEdit
from utilities import Line


class WxPanel(QFrame):
    """ Weights Matrix Panel """
    w1b1w2b2_Signal = Signal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, str, str) 
    """ arguments=('w1', 'b1', 'w2', 'b2', activation1, activation2) """

    # TODO: refactoring W1_b1_Table and W2_b2_Table tables to be included in tables W1 and W2
    # this comes from the original design when I thought b1 and b2 were always fixed, not changed by the backprop algorithm, mea culpa

    def __init__(self, xorModel: XOR_model, parent: QWidget | None = None, f: Qt.WindowFlags = Qt.WindowType.Widget ) -> None:
        super().__init__(parent, f)

        self.mapper = QDataWidgetMapper(self)
        self.xorModel = xorModel
        self.mapper.setModel(self.xorModel.getCrtTPModel())

        self.crtXOR_Slice = self.xorModel.getCrtSlice()
        self.details_index = 0 # current displayed operation: 0 = 0^0, ..., 3 = 1^1

        lyt = QHBoxLayout()
        lyt.setSpacing(3)
        lyt.setContentsMargins(0, 0, 0, 0)

    # region X + bias(+1)
        self._x_data = pd.DataFrame([['...', '...']],  index=["X"], columns=['x'+chr(0x2080), 'x'+chr(0x2081)])
        self._x_model = MatrixWithMaskAndColoredHeaderModel(
            data=self._x_data, 
            mask=pd.DataFrame([[False, False]]),
            blockLock=pd.DataFrame(np.full((1,2), ([True]))),
            flags=Qt.ItemFlag.ItemIsEnabled  | Qt.ItemFlag.ItemIsSelectable, 
            hHeaderColors=[MxCOLORS.W1_Row0, MxCOLORS.W1_Row1],
            vHeaderColors=[QColor('blue').lighter(180)],
            mxExplicitColors=QColor('blue').lighter(160)
            )
        self._x_Table = MxQTableView()
        self._x_Table.setObjectName("_x_Table")
        self._x_Table.setStyleSheet(
            """MxQTableView#_x_Table {
            border: 1px solid #%06x; 
            } 
            MxQTableView#_x_Table::item:selected:!active { 
                border: 1px solid cyan;
                color: blue;    
            } 
            MxQTableView#_x_Table::item:selected:active { 
                border: 1px solid cyan;
            }                   
            """ % (QColor('blue').lighter(160).__hash__())
            ) 
        
        self._x_Table.setSelectionMode(QAbstractItemView.MultiSelection)
        self._x_Table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._x_Table.bKeepSelectedThicked = True

        # change the color of the x0 x1 columns to red (signifying the current operation)
        def _wrap_data_foreground(f):
            def _inner(index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
                if role == Qt.ItemDataRole.ForegroundRole and index.column() <=1 :
                    return QColor("red")
                return f(index , role)
            return _inner
        self._x_model.data = _wrap_data_foreground(self._x_model.data)
        self._x_Table.setModel(self._x_model)
        self._x_Table.setFixedWidth(72)
        self._x_Table.verticalHeader().setVisible(False)
        self._x_Table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._x_Table.setColumnWidth(0, 35)
        self._x_Table.setColumnWidth(1, 35)

        _b_data = pd.DataFrame([['(+1)']], columns=['(bias)'])
        _b_model = MatrixWithMaskAndColoredHeaderModel(
            data=_b_data, 
            mask=pd.DataFrame([[True]]),
            blockLock=pd.DataFrame([[True]]),
            flags=Qt.ItemFlag.ItemIsEnabled,
            hHeaderColors=[MxCOLORS.BIAS],
            vHeaderColors=[MxCOLORS.BIAS.lighter(120)]
            )
        self._b1_Table = MxQTableView()
        self._b1_Table.setObjectName('_b1_Table')
        self._b1_Table.setStyleSheet(""" MxQTableView#_b1_Table 
                                     { 
                                    border: 1px solid #b9b9b9;
                                    border-left-style:none;
                                     }
                                     """)
        self._b1_Table.setModel(_b_model)  
        self._b1_Table.setFixedWidth(45)
        self._b1_Table.verticalHeader().setVisible(False)
        self._b1_Table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._b1_Table.setColumnWidth(0, 45)

        self._x00_val = np.array([0, 1, 1, 0], dtype=np.bool_)
        self._x00_pc = np.array([25] * 4, dtype=np.int32)
        self._x00_model = X00_Model(self._x00_val, self._x00_pc )
        self._x00_model.set_yTrue_xPercents_Hits(yTrue = self._x00_val, 
                                                xPercents = self._x00_pc, 
                                                hits= np.zeros(shape=(4, 1))
                                                 )

        self._x00_Table = TableView_sigCurrentChanged(self)
        self._x00_Table.setObjectName("_x00_Table")
        self._x00_Table.setStyleSheet(
            """QTableView#_x00_Table QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } 
            QTableView#_x00_Table {
            border: 1px solid #%06x; 
            } 
            QTableView#_x00_Table::item:selected:!active { 
                 border: 1px solid cyan;
                 color: blue;    
            } 
            QTableView#_x00_Table::item:selected:active { 
                 border: 1px solid cyan;
                 color: white;    
            }
            """ % (((QColor('blue').lighter(170).__hash__(),) * 3)) 
            ) 

        self._x00_Table.setModel(self._x00_model)
        self._delegate_val = IntDelegate(0, 1)
        self._delegate_pc = IntDelegate(0, 100)
        self._x00_Table.setItemDelegateForColumn(0, self._delegate_val)
        self._x00_Table.setItemDelegateForColumn(1, self._delegate_pc)

        _f = self._x00_Table.font()
        _f.setPointSize(8)
        self._x00_Table.setFont(_f)
        _fh = self._x00_Table.verticalHeader().font()
        _fh.setPointSize(7)        
        self._x00_Table.verticalHeader().setFont(_fh)


        self._x00_Table.setSelectionBehavior(QAbstractItemView.SelectItems )
        self._x00_Table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._x00_Table.verticalHeader().setFixedWidth(self._x_Table.verticalHeader().width())
        self._x00_Table.verticalHeader().setDefaultSectionSize(21)
        self._x00_Table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self._x00_Table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._x00_Table.horizontalHeader().setFixedHeight(18)
        self._x00_Table.horizontalHeader().setMinimumSectionSize(0)
        self._x00_Table.setColumnWidth(0, 20)
        self._x00_Table.setColumnWidth(1, 25)
        self._x00_Table.setColumnWidth(2, 40)
        self._x00_Table.setFixedWidth(self._x_Table.verticalHeader().width() + 85 + 2 )
        self._x00_Table.setFixedHeight(self._x00_Table.horizontalHeader().height() + 21 * 4 + 2)

        # - Layout
        _xb_frame = QFrame()
        lytXb = QHBoxLayout()
        lytXb.setContentsMargins(0, 0, 0, 0)
        lytXb.setSpacing(0)
        lytXb.addWidget(self._x_Table, alignment=Qt.AlignTop)
        lytXb.addWidget(self._b1_Table, alignment=Qt.AlignTop)
        _xb_frame.setLayout(lytXb)

        lytXb_x00 = QVBoxLayout()
        lytXb_x00.setSpacing(1)
        lytXb_x00.addWidget(_xb_frame)
        lytXb_x00.addWidget(self._x00_Table)
        lytXb_x00.addStretch()
        
        lyt.addLayout(lytXb_x00)
        lyt.addStretch() 
    # endregion X + bias(+1)

    # region Lbl Multiply
        lbl_MULT = QLabel()
        font = self.font()
        font.setPointSize(14)
        lbl_MULT.setFont(font)
        lbl_MULT.setText("X")
        lbl_MULT.setFixedHeight(self._x_Table.height() + 14) 
        # - Layout
        lyt.addWidget(lbl_MULT, alignment=Qt.AlignTop)
        lyt.addStretch()        
    # endregion Lbl Multiply

    # region W1 Mx + bias
        # region W1 / Mx 
        self.W1_data = pd.DataFrame(-10 + 20 * np.random.rand(2, 2))
        self.W1_model = MatrixWithMaskAndColoredHeaderModel(
            data=self.W1_data, 
            mask=pd.DataFrame(np.random.choice(a=[False, True], size=(2, 2), p=[0.5, 0.5])),
            blockLock=pd.DataFrame(np.full((2,2), (False, False))),
            )
        self.W1_Table = MxQTableView()
        self.W1_Table.setObjectName("_W1")
        self.W1_Table.setStyleSheet(
            """MxQTableView#_W1 QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } """ % (MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__(), MxCOLORS.TBL_HEADER_GRAY.__hash__())
            )                 
        self.W1_Table.setModel(self.W1_model)

        lbl_W1 = QLabel(self.W1_Table)
        lbl_W1.setGeometry(QRect(3, 1, 30, 20))
        lbl_W1.setAlignment(Qt.AlignCenter)
        lbl_W1.setText(u"""
            <html>
                <head/>
                    <body>
                        <p>
                            <span style=\" font-size:11pt; \">W</span>
                            <span style=\" font-size:11pt; vertical-align:super;\">|1|</span>
                        </p>
                    </body>
            </html>
            """)
        lbl_W1.setAttribute(Qt.WA_TransparentForMouseEvents ) # !!!
        # endregion W1 / Mx

        # region W1 / bias
        self.W1_bias_1_data = pd.DataFrame(-10 + 20 * np.random.rand(1, 2), index=['b' + chr(0x2081)])
        self.W1_bias_1_model = MatrixWithMaskAndColoredHeaderModel(
            data=self.W1_bias_1_data, 
            mask=pd.DataFrame([[True, True]]),
            blockLock=pd.DataFrame([[False, False]]),
            hHeaderColors=[MxCOLORS.BIAS, MxCOLORS.BIAS],
            vHeaderColors=[MxCOLORS.BIAS]
            )
        
        self.W1_b1_Table = MxQTableView(hHeaderVisible=False)
        self.W1_b1_Table.setObjectName('_W1b1_Table')
        self.W1_b1_Table.setStyleSheet(""" MxQTableView#_W1b1_Table 
                                     { 
                                    border: 1px solid #b9b9b9;
                                    border-top-style:none;
                                     }
                                     """)        
        self.W1_b1_Table.setModel(self.W1_bias_1_model)
        # endregion W1 / bias
        
    # - Layout
        lyt_W1b1 = QVBoxLayout()
        lyt_W1b1.setSpacing(0)
        lyt_W1b1.addWidget(self.W1_Table, alignment=Qt.AlignTop)  
        lyt_W1b1.addWidget(self.W1_b1_Table, alignment=Qt.AlignTop)
        lyt_W1b1.addStretch()
        lyt.addLayout(lyt_W1b1)
        lyt.addStretch()
    # endregion W1 Mx + bias

    # region Lbl EQUAL
        lbl_EQUAL = QLabel() 
        lbl_EQUAL.setFont(lbl_MULT.font())
        lbl_EQUAL.setText("=")
        lbl_EQUAL.setFixedHeight(lbl_MULT.height())
        # - Layout  
        lyt.addWidget(lbl_EQUAL, alignment=Qt.AlignTop)
        lyt.addStretch()       
    # endregion Lbl EQUAL
    
    # region z1 Mx
        self._Z1_data = pd.DataFrame(np.zeros((4, 2)), 
                                     columns=['z'+chr(0x2080), 'z'+chr(0x2081)], # z₀, z₁
                                     index=["0^0", "0^1", "1^0", "1^1"])
        self._Z1_model = MatrixWithMaskAndColoredHeaderModel(
            data=self._Z1_data, 
            mask=pd.DataFrame([[False, False]] * 4),
            blockLock=pd.DataFrame(np.full((4,2), ([True]))),
            flags=Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable, 
            hHeaderColors=[MxCOLORS.W1_Col0.darker(110), MxCOLORS.W1_Col1.darker(110)], 
            vHeaderColors=[MxCOLORS.TBL_HEADER_GRAY] * 4,
            # mxExplicitColors=[[MxCOLORS.W1_Col0, MxCOLORS.W1_Col1.darker(105)]] * 4
            )
        self._Z1_Table = MxQTableView()
        self._Z1_Table.setObjectName("_Z1")
        self._Z1_Table.setStyleSheet(
            """MxQTableView#_Z1 QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } """ % (MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__(), MxCOLORS.TBL_HEADER_GRAY.__hash__())
            ) 
        def _verticalHeaderDataSmallFont(obj:MatrixWithMaskAndColoredHeaderModel):
            def inner (section, orientation, role):
                if orientation == Qt.Orientation.Vertical:
                    if role == Qt.FontRole:
                        font = QFont()
                        font.setPixelSize(11)
                        return font
                return MatrixWithMaskAndColoredHeaderModel.headerData(obj, section, orientation, role)
            return inner
        self._Z1_model.headerData = _verticalHeaderDataSmallFont(self._Z1_model)
        self._Z1_Table.setModel(self._Z1_model)
        self._Z1_Table.verticalHeader().setFixedWidth(30)
        self._Z1_Table.setSelectionBehavior(QAbstractItemView.SelectRows )      
        self._Z1_Table.setSelectionMode(QAbstractItemView.SingleSelection )      

        label_Z1 = QLabel(self._Z1_Table)
        label_Z1.setStyleSheet("background-color:#%06x; border: solid #%06x; border-width: 1px 0 1px 1px;" 
                               % (MxCOLORS.TBL_HEADER_GRAY.__hash__(), MxCOLORS.TBL_OUTER_BORDER_GRAY.__hash__())
                               )
        label_Z1.setGeometry(QRect(0, 0, 30, 20))
        label_Z1.setAttribute(Qt.WA_TransparentForMouseEvents )

        label_Z1_dmp = QLabel(label_Z1)
        label_Z1_dmp.setGeometry(1, 1, 29, 20)
        label_Z1_dmp.setStyleSheet(
            "border: solid #%06x; border-width: 0 0 1px 0; padding-left: 2px;" % MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__()
            )
        label_Z1_dmp.setText(u"""
            <html>
                <head/>
                    <body>
                        <p>
                            <span style=\" font-size:11pt; \">z</span>
                            <span style=\" font-size:11pt; vertical-align:super;\">|1|</span>
                        </p>
                    </body>
            </html>
            """)        
        label_Z1_dmp.setAttribute(Qt.WA_TransparentForMouseEvents ) 
        # label_Z1.raise_()

        # - Layout
        lytZ1 = QHBoxLayout()
        lytZ1.setSpacing(0)
        lytZ1.setContentsMargins(0, 0, 0, 0)
        lytZ1.addWidget(self._Z1_Table, alignment=Qt.AlignTop)
        lyt.addLayout(lytZ1)
    # endregion z1 Mx

    # region Activation 1
        lyActv = QVBoxLayout()
        lyActv.setSpacing(0)
        lyActv.setContentsMargins(0, 0, 0, 0)
        lyActv.addWidget(QLabel(" Activation 1: ->"))
        self.cboHiddenActivation = ToolTip_CommitOnChange_ComboBox(_list = FunctionsListsByType.HiddenLayer.keys(), 
                                                                   _mapper = self.mapper)
        self.cboHiddenActivation.setToolTipList([x.toolTip_as_html() for x in FunctionsListsByType.HiddenLayer.values()])
        self.mapper.addMapping(self.cboHiddenActivation, XOR_Slice.ColumnsMap.activation1.value) 

        lyActv.addWidget(self.cboHiddenActivation)

        lyActv.addSpacing(78) # self._Z1_Table.height() - self.lblActivation1.heigh() - self.cboHiddenActivation.height() -2...

        # region btnExpand 
        self.btnExpand = QPushButton()
        self.btnExpand.setStyleSheet("""
                                QPushButton:checked { border: 2px solid lightblue; border-radius: 4px;} 
                                QPushButton:unchecked { border: 1px solid lightgrey; border-radius: 4px; background-color: rgb(240, 240, 240); }
                                QPushButton:hover { border: 1px solid rgb(0, 255, 255); border-radius: 4px; background-color:white; }
                                """)
        
        self.btnExpand.setCheckable(True)
        self.btnExpand.setFocusPolicy(Qt.NoFocus)
        self.btnExpand.setFixedHeight(24)
        
        global gPixmapDown, gPixmapUp
        self.btnExpand.setIcon(gPixmapDown)
        self.btnExpand.setIconSize(gPixmapDown.size())
        self.btnExpand.setCursor(Qt.PointingHandCursor)
        
        self.btnExpand.setChecked(False)
        self.btnExpand.toggled.connect(self._btnExpand_toggled)
        # endregion btnExpand

        lyActv.addWidget(self.btnExpand) 
        lyActv.addStretch()
        wgtActv = QWidget()
        wgtActv.setLayout(lyActv)
        # - Layout
        lyt.addWidget(wgtActv)
    # endregion Activation 1

    # region Mx a1
        self._A1_data = pd.DataFrame(np.zeros((4, 2)), 
                                     columns=['a'+chr(0x2080), 'a'+chr(0x2081)], 
                                     index=["0^0", "0^1", "1^0", "1^1"])
        self._A1_model = MatrixWithMaskAndColoredHeaderModel(
            data=self._A1_data, 
            mask=pd.DataFrame([[False, False]] * 4),
            blockLock=pd.DataFrame(np.full((4,2), ([True]))),
            flags=Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
            hHeaderColors = [MxCOLORS.A1_0.darker(110), MxCOLORS.A1_1.darker(110)],
            vHeaderColors = [MxCOLORS.TBL_HEADER_GRAY] * 4,
            )
        
        self._A1_model.headerData = _verticalHeaderDataSmallFont(self._A1_model) # defined in Z1 Mx
        self._A1_Table = MxQTableView(min_col_width=60)
        self._A1_Table.setObjectName("_A1")
        self._A1_Table.setStyleSheet(
            """MxQTableView#_A1 QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } """ % (MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__(), MxCOLORS.TBL_HEADER_GRAY.__hash__()) 
            ) 
        self._A1_Table.setModel(self._A1_model)
        self._A1_Table.verticalHeader().setFixedWidth(30)
        self._A1_Table.setColumnWidth(0,60)
        self._A1_Table.setColumnWidth(1,60)
        self._A1_Table.setSelectionBehavior(QAbstractItemView.SelectRows )      
        self._A1_Table.setSelectionMode(QAbstractItemView.SingleSelection )     

        label_A1 = QLabel(self._A1_Table)
        label_A1.setGeometry(QRect(2, 0, 30, 20))
        label_A1.setAlignment(Qt.AlignCenter)
        label_A1.setText(u"""
            <html>
                <head/>
                    <body>
                        <p>
                            <span style=\" font-size:11pt;\">a</span>
                            <span style=\" font-size:11pt; vertical-align:super;\">|1|</span>
                        </p>
                    </body>
            </html>
            """)
        label_A1.setAttribute(Qt.WA_TransparentForMouseEvents ) 

        self._b2_Table = MxQTableView()
        self._b2_Table.setObjectName('_b2_Table')
        self._b2_Table.setStyleSheet(""" MxQTableView#_b2_Table 
                                     { 
                                    border: 1px solid #b9b9b9; 
                                    border-left-style:none;
                                     }
                                     """)
        self._b2_Table.setModel(_b_model)
        self._b2_Table.setFixedWidth(45)
        hb = self._A1_Table.height() - self._A1_Table.horizontalHeader().height()
        self._b2_Table.verticalHeader().setDefaultSectionSize(hb)
        self._b2_Table.setFixedHeight(self._A1_Table.height())

        self._b2_Table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self._b2_Table.verticalHeader().setVisible(False)
        self._b2_Table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._b2_Table.setColumnWidth(0, 45)

        lytYb = QHBoxLayout()
        lytYb.setContentsMargins(0,0,0,0)
        lytYb.setSpacing(0)
        lytYb.addWidget(self._A1_Table, alignment=Qt.AlignTop)
        lytYb.addWidget(self._b2_Table, alignment=Qt.AlignTop)

        # - Layout
        lyt.addLayout(lytYb)
        lyt.addStretch()        
    # endregion Mx a1

    # region Lbl Multiply
        lbl_MULT2 = QLabel()
        lbl_MULT2.setFont(lbl_MULT.font())
        lbl_MULT2.setText("X")
        lbl_MULT2.setFixedHeight(lbl_MULT.height()) 
        # - Layout
        lyt.addWidget(lbl_MULT2, alignment=Qt.AlignTop)
        lyt.addStretch()
    # endregion Lbl Multiply

    # region Mx W2
        self.W2_data = pd.DataFrame(-10 + 20 * np.random.rand(2, 1))
        self.W2_model = MatrixWithMaskAndColoredHeaderModel(
            data=self.W2_data, 
            mask=pd.DataFrame( [[False], [False]] ),
            hHeaderColors=[MxCOLORS.W2_Col], 
            vHeaderColors=[MxCOLORS.W2_0, MxCOLORS.W2_1],
            blockLock=pd.DataFrame([[False], [False]]),
            mxExplicitColors=[[MxCOLORS.W2_0],[MxCOLORS.W2_1]]
            )
        self.W2_Table = MxQTableView()
        self.W2_Table.setObjectName("_W2")
        self.W2_Table.setStyleSheet(
            """MxQTableView#_W2 QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } """ % (MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__(), MxCOLORS.TBL_HEADER_GRAY.__hash__())
            )         
        self.W2_Table.setModel(self.W2_model)
        self.W2_Table.setMaximumWidth(145)

        lbl_W2 = QLabel(self.W2_Table)
        lbl_W2.setGeometry(QRect(3, 1, 30, 20))
        lbl_W2.setAlignment(Qt.AlignCenter)
        lbl_W2.setText(u"""
            <html>
                <head/>
                    <body>
                        <p>
                            <span style=\" font-size:11pt; \">W</span>
                            <span style=\" font-size:11pt; vertical-align:super;\">|2|</span>
                        </p>
                    </body>
            </html>
            """)
        lbl_W2.setAttribute(Qt.WA_TransparentForMouseEvents )
        
        # region W2 / bias
        self.W2_bias_2_data = pd.DataFrame(-10 + 20 * np.random.rand(1), index=['b' + chr(0x2082)])
        self.W2_bias_2_model = MatrixWithMaskAndColoredHeaderModel(
            data=self.W2_bias_2_data, 
            mask=pd.DataFrame([[True]]),
            blockLock=pd.DataFrame([[False]]),
            hHeaderColors=[MxCOLORS.BIAS],
            vHeaderColors=[MxCOLORS.BIAS]
            )
        
        self.W2_b2_Table = MxQTableView(hHeaderVisible=False)
        self.W2_b2_Table.setObjectName('W2_b2_Table')
        self.W2_b2_Table.setStyleSheet(""" MxQTableView#W2_b2_Table 
                                     { 
                                    border: 1px solid #b9b9b9;
                                    border-top-style:none;
                                     }
                                     """)        
        self.W2_b2_Table.setModel(self.W2_bias_2_model)
        self.W2_b2_Table.setMaximumWidth(145)
        # endregion W2 / bias
        # - Layout
        ly_W2b = QVBoxLayout()
        ly_W2b.setSpacing(0)
        ly_W2b.setContentsMargins(0,0,0,0)
        ly_W2b.addWidget(self.W2_Table, alignment=Qt.AlignLeft)
        ly_W2b.addWidget(self.W2_b2_Table, alignment=Qt.AlignLeft)
        ly_W2b.addStretch()
        lyt.addLayout(ly_W2b)
    # endregion Mx W2
        
    # region Lbl EQUAL
        label_EQUAL2 = QLabel() # No copy/clone mechanism :( so...)
        label_EQUAL2.setFont(lbl_MULT.font())
        label_EQUAL2.setText("=")
        label_EQUAL2.setFixedHeight(lbl_MULT2.height())
    # - Layout
        lyt.addStretch()
        lyt.addWidget(label_EQUAL2, alignment=Qt.AlignTop)
        lyt.addStretch()
    # endregion Lbl EQUAL

    # region z2 Mx
        self._Z2_data = pd.DataFrame(np.zeros((4, 1)), 
                                     columns=[' '], 
                                     index=["0^0", "0^1", "1^0", "1^1"])
        self._Z2_model = MatrixWithMaskAndColoredHeaderModel(
            data=self._Z2_data, 
            mask=pd.DataFrame([[False]] * 4), 
            blockLock=pd.DataFrame([[True]] *4), 
            flags=Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable, 
            hHeaderColors=[MxCOLORS.Z2.darker(115)], 
            vHeaderColors=[MxCOLORS.Z2.lighter(115)] * 4
            )
        self._Z2_model.headerData = _verticalHeaderDataSmallFont(self._Z2_model)
        self._Z2_Table = MxQTableView(vHeaderVisible=False)
        self._Z2_Table.setObjectName("_Z2")
        self._Z2_Table.setStyleSheet(
            """MxQTableView#_Z2 QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } """ % (MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__(), MxCOLORS.TBL_HEADER_GRAY.__hash__()) 
            ) 
        self._Z2_Table.setModel(self._Z2_model)
        self._Z2_Table.setColumnWidth(0, 60)     
        self._Z2_Table.setSelectionBehavior(QAbstractItemView.SelectRows )      
        self._Z2_Table.setSelectionMode(QAbstractItemView.SingleSelection )    

        label_Z2 = QLabel(self._Z2_Table)
        label_Z2.setGeometry(QRect(2, 1, 60, 20))
        label_Z2.setAlignment(Qt.AlignCenter)
        label_Z2.setText(u"""
            <html>
                <head/>
                    <body>
                        <p>
                            <span style=\" font-size:11pt; \">z</span>
                            <span style=\" font-size:11pt; vertical-align:super;\">|2|</span>
                        </p>
                    </body>
            </html>
            """)
        label_Z2.setAttribute(Qt.WA_TransparentForMouseEvents ) 
        def _label_Z2_resizeEvent(event: QResizeEvent):
            QTableView.resizeEvent(self._Z2_Table, event)
            label_Z2.setFixedWidth(self._Z2_Table.columnWidth(0))
        self._Z2_Table.resizeEvent = _label_Z2_resizeEvent
        # - Layout
        lyt.addWidget(self._Z2_Table, alignment=Qt.AlignTop)
    # endregion z2 Mx
    
    # region Activation2 + A2 + LOSS
    # region Activation 2
        lyActv2 = QVBoxLayout()
        lyActv2.setSpacing(0)
        lyActv2.setContentsMargins(0, 0, 3, 0)
        lyActv2.addWidget(QLabel(" Activation 2: ->"), alignment=Qt.AlignTop)
        self.cboOutputActivation = ToolTip_CommitOnChange_ComboBox(_list = FunctionsListsByType.OutputLayer.keys(), 
                                                                   _mapper = self.mapper)
        self.cboOutputActivation.setToolTipList([x.toolTip_as_html() for x in FunctionsListsByType.OutputLayer.values()])
        self.mapper.addMapping(self.cboOutputActivation, XOR_Slice.ColumnsMap.activation2.value) 

        # - Layout
        lyActv2.addWidget(self.cboOutputActivation, alignment=Qt.AlignTop)
        lyActv2.addStretch()
    # endregion Activation 2

    # region a2 = ŷ = chr(0x0177)
        self._A2_data = pd.DataFrame([['...']], columns=[''], index=['']) # 
        self._A2_model = MatrixWithMaskAndColoredHeaderModel(
            data=self._A2_data, 
            mask=pd.DataFrame([[False]]),
            blockLock=pd.DataFrame(([True])),
            flags=Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
            hHeaderColors = [MxCOLORS.Y],
            vHeaderColors = [MxCOLORS.Y.lighter(120)]
            )
        self._A2_Table = MxQTableView(vHeaderVisible=False)
        self._A2_Table.setObjectName("_A2")
        self._A2_Table.setStyleSheet(
            """MxQTableView#_A2 QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } """ % (MxCOLORS.TBL_INNER_BORDER_GRAY.__hash__(), MxCOLORS.TBL_HEADER_GRAY.__hash__())
            ) 
        self._A2_Table.setModel(self._A2_model)
        self._A2_Table.setColumnWidth(0, 81)
        self._A2_Table.setFixedWidth(81)

        label_A2 = QLabel(self._A2_Table)
        label_A2.setGeometry(QRect(2, 0, 80, 20))
        label_A2.setAlignment(Qt.AlignCenter)
        label_A2.setText(u"""
            <html>
                <head/>
                    <body>
                        <p>
                            <span style=\" font-size:11pt;\">a</span>
                            <span style=\" font-size:11pt; vertical-align:super;\">|2|</span>
                            <span style=\" font-size:11pt;\"> = ŷ </span> 
                        </p>
                    </body>
            </html>
            """)
        label_A2.setAttribute(Qt.WA_TransparentForMouseEvents ) # !!!
        def _label_A2_resizeEvent(event: QResizeEvent):
            QTableView.resizeEvent(self._A2_Table, event)
            label_A2.setFixedWidth(self._A2_Table.columnWidth(0))
        self._A2_Table.resizeEvent = _label_A2_resizeEvent

        self._lossAvg_Model = MatrixWithMaskAndColoredHeaderModel(
                data=pd.DataFrame([['...']], columns=['Cost(loss)']), 
                mask=pd.DataFrame([[False]]),
                blockLock=pd.DataFrame([[True]]),
                flags=Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
                hHeaderColors=[MxCOLORS.LOSS_HEADER_COLOR],
                vHeaderColors=[MxCOLORS.TBL_HEADER_GRAY],
                mxExplicitColors=[MxCOLORS.LOSS_COST_COLOR.lighter(120)]
                )
        self._lossAvg_Table = MxQTableView(vHeaderVisible=False)
        self._lossAvg_Table.setObjectName('_loss')
        self._lossAvg_Table.setStyleSheet(""" MxQTableView#_loss 
                                     { 
                                    border: 1px solid #b9b9b9; 
                                    border-left-style:none;
                                     }
                                     """)
        self._lossAvg_Table.setModel(self._lossAvg_Model)
        self._lossAvg_Table.setColumnWidth(0, 80)
        self._lossAvg_Table.setFixedWidth(80)
        
        def __loss_table_focusOutEvent(event):
            self._lossAvg_Table.setCurrentIndex(QModelIndex()) # unselect for glow-ing single cell table on future click
            return QTableView.focusOutEvent(self._lossAvg_Table, event)
        self._lossAvg_Table.focusOutEvent = __loss_table_focusOutEvent
        
        _wdg_Act2_A2_Loss = QWidget()
        lyt_Act2_A2_Loss = QHBoxLayout()
        lyt_Act2_A2_Loss.setContentsMargins(0,0,0,0)
        lyt_Act2_A2_Loss.setSpacing(0)
        wdgActv2 = QWidget()
        wdgActv2.setLayout(lyActv2)
        wdgActv2.setFixedWidth(90)
        lyt_Act2_A2_Loss.addWidget(wdgActv2)
        lyt_Act2_A2_Loss.addWidget(self._A2_Table, alignment=Qt.AlignTop)
        lyt_Act2_A2_Loss.addWidget(self._lossAvg_Table, alignment=Qt.AlignTop)
        _wdg_Act2_A2_Loss.setLayout(lyt_Act2_A2_Loss)

    # endregion Mx a1       

    # region y00
        self._y00_val = self._x00_val
        self._y00_fwd = list(np.random.rand(4)) #  just to see something for develop/debug 
        self._y00_model = Y00_Model(self._y00_val, self._y00_fwd )

        self._y00_Table = TableView_sigCurrentChanged(self)
        self._y00_Table.setObjectName("_y00_Table")
        self._y00_Table.setStyleSheet(
            """QTableView#_y00_Table QTableCornerButton::section {
            border: 1px solid #%06x; 
            border-top-style:none;
            border-left-style:none;
            background-color: #%06x;
            } 
            QTableView#_y00_Table {
            border: 1px solid #%06x; 
            } 
            QTableView#_y00_Table::item:selected:!active { 
                 border: 1px solid cyan;
                 color: blue;    
            } 
            QTableView#_y00_Table::item:selected:active { 
                 border: 1px solid cyan;
            }
            """ % (((QColor('blue').lighter(170).__hash__(),) * 3)) 
            ) 

        self._y00_Table.setModel(self._y00_model)

        _f = self._y00_Table.font()
        _f.setPointSize(8)
        self._y00_Table.setFont(_f)

        # self._y00_Table.setSelectionBehavior(QAbstractItemView.SelectItems )        
        # not like in _x00_Table, no editing so it's better to see the selected row
        self._y00_Table.setSelectionBehavior(QAbstractItemView.SelectRows )        
        self._y00_Table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._y00_Table.setTabKeyNavigation(False)
        self._y00_Table.verticalHeader().setFixedWidth(self._x_Table.verticalHeader().width())
        self._y00_Table.verticalHeader().setDefaultSectionSize(21)
        self._y00_Table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        
        self._y00_Table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._y00_Table.horizontalHeader().setFixedHeight(18)
        self._y00_Table.horizontalHeader().setMinimumSectionSize(0)
        self._y00_Table.setColumnWidth(0, 20)
        
        self._y00_Table.setColumnWidth(1, 79)

        self._y00_Table.setFixedWidth( self._y00_Table.verticalHeader().width() + 20 + 79 + 2 )
        self._y00_Table.setFixedHeight(self._y00_Table.horizontalHeader().height() + 21 * 4 + 2)

        self._y00_Table.setCurrentIndex(QModelIndex()) # unselect
    # endregion y00

    # region loss / x
        self._lossPerX_model = MatrixWithMaskAndColoredHeaderModel(
            data=pd.DataFrame([[0]] * 4, columns=['Loss/X']), 
            mask=pd.DataFrame([[False]] * 4),
            blockLock=pd.DataFrame([[True]] * 4),
            flags=Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
            hHeaderColors=[MxCOLORS.LOSS_HEADER_COLOR],
            vHeaderColors=[MxCOLORS.LOSS_COST_COLOR] * 4, 
            mxExplicitColors=[[MxCOLORS.X00_COLOR],
                              [MxCOLORS.X01_COLOR],
                              [MxCOLORS.X10_COLOR],
                              [MxCOLORS.X11_COLOR]
                              ]
            )
        self._lossPerX_table = MxQTableView(vHeaderVisible=False)
        self._lossPerX_table.setObjectName('_lossPerX')
        self._lossPerX_table.setStyleSheet(""" MxQTableView#_lossPerX 
                                     { 
                                    border: 1px solid #b9b9b9; 
                                    border-left-style:none;
                                     }
                                    MxQTableView#_lossPerX::item:selected:!active { 
                                        border: 1px solid cyan;
                                        color: blue;    
                                    } 
                                    MxQTableView#_lossPerX::item:selected:active { 
                                        border: 1px solid cyan;
                                    }                                           
                                     """)
        self._lossPerX_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self._lossPerX_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self._lossPerX_table.bKeepSelectedThicked = True
        self._lossPerX_table.setModel(self._lossPerX_model)

        self._lossPerX_table.verticalHeader().setDefaultSectionSize(21)
        self._lossPerX_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self._lossPerX_table.horizontalHeader().setFixedHeight(18)        
        self._lossPerX_table.setColumnWidth(0, 80) 
        self._lossPerX_table.setFixedWidth(80)
        self._lossPerX_table.setFixedHeight(self._y00_Table.height())
    # endregion loss / x

        # - Layout
        frm_A2y00 = QFrame()
        lytYb_x00 = QVBoxLayout()
        lytYb_x00.setSpacing(1)
        lytYb_x00.setContentsMargins(0,0,0,0)
        lytYb_x00.addWidget(_wdg_Act2_A2_Loss)
        ly00 = QHBoxLayout()
        ly00.setContentsMargins(30, 0, 0, 0)
        ly00.setSpacing(0)
        lblDummy3 = QLabel()
        lblDummy3.setFixedWidth(30)
        ly00.addStretch()
        ly00.addWidget(self._y00_Table )
        ly00.addWidget(self._lossPerX_table )
        lytYb_x00.addLayout(ly00)
        lytYb_x00.addStretch()
        frm_A2y00.setLayout(lytYb_x00)
    
    # endregion Activation2 + A2 + LOSS

        lyt.addWidget(frm_A2y00)
        lyt.addStretch() 

        self.setLayout(lyt)
    # Layout Done
        # region connector
        self._connector = Connector()
        self._connector.setParent(self)
        self._connector.resize(50, 30)
        (_l, _t, _r, _b) = lyt.getContentsMargins()
        self._connector.move(_l + 3, self._x_Table.height() + _t - 9)
        # endregion connector

    # region models signals connections
        self.W1_model.dataChanged.connect(self.slot_Wx_model_dataChanged)
        self.W1_bias_1_model.dataChanged.connect(self.slot_Wx_model_dataChanged)
        self.W2_model.dataChanged.connect(self.slot_Wx_model_dataChanged)
        self.W2_bias_2_model.dataChanged.connect(self.slot_Wx_model_dataChanged)
        self._x00_model.dataChanged.connect(self.slot_Wx_model_dataChanged) # yTrue changed 

        self.xorModel.getCrtTPModel().dataChanged.connect(self._inplace_TP_params_changed, Qt.UniqueConnection)
    # endregion models
        
    # end __init__ 

    def _btnExpand_toggled(self, checked:bool):
        global gPixmapDown, gPixmapUp
        self.btnExpand.setIcon(gPixmapUp if checked else gPixmapDown)     
        self.btnExpand.setToolTip( ("collapse z..a" if checked else "expand z..a" ) + " \n (Ctrl + ~)" )

    def _inplace_TP_params_changed(self, topLeft: QModelIndex , bottomRight: QModelIndex, roles ):
        """ some TP params changed, who require un update in the crt Slice"""
        if any( topLeft.column() <= colName <= bottomRight.column() 
               for colName in (
                   XOR_Slice.ColumnsMap.loss, 
                   XOR_Slice.ColumnsMap.minRange, 
                   XOR_Slice.ColumnsMap.maxRange,
                   XOR_Slice.ColumnsMap.activation1,
                   XOR_Slice.ColumnsMap.activation2
                   )
               ):
            # at least one changed 
            if (topLeft.column() <= XOR_Slice.ColumnsMap.minRange <= bottomRight.column() or
                topLeft.column() <= XOR_Slice.ColumnsMap.maxRange <= bottomRight.column()
                ): 
                # range changed
                # in models its clipped Ok via SetData of TPModel, 
                # and now set the constraints for Matrices UI too
                _minRange = self.xorModel.getCrtTPModel().getTP().minRange
                _MaxRange = self.xorModel.getCrtTPModel().getTP().maxRange
                self.W1_model.setRange(_minRange, _MaxRange)
                self.W1_bias_1_model.setRange(_minRange, _MaxRange)
                self.W2_model.setRange(_minRange, _MaxRange)
                self.W2_bias_2_model.setRange(_minRange, _MaxRange)
            
            self.slot_Wx_model_dataChanged() # compute_z_a_loss and update the WxPanel
        else:
            # print("WxPanel xorModel.getCrtTPModel().dataChanged column", XOR_Slice.ColumnsMap(topLeft.column()), '=', topLeft.model().data(topLeft))
            pass
    
    def setModel(self, xorModel:XOR_model):
        """ set the current model, and update the mappings """ 
        self.xorModel = xorModel
        self.mapper.setModel(self.xorModel.getCrtTPModel())
        self.mapper.addMapping(self.cboHiddenActivation, XOR_Slice.ColumnsMap.activation1.value)         
        self.mapper.addMapping(self.cboOutputActivation, XOR_Slice.ColumnsMap.activation2.value) 
        self.xorModel.getCrtTPModel().dataChanged.connect(self._inplace_TP_params_changed, Qt.UniqueConnection)

    def slot_Wx_model_dataChanged(self, *args):
        self.crtXOR_Slice.compute_z_a_loss()
        self.refresh()

    def refresh(self):
        """ refresh the UI with the current Slice data """
        self.setUpdatesEnabled(False)

        # to avoid recursion, 'cause 'self.mapper.toFirst()' will trigger  self.cboHiddenActivation.currentIndexChanged
        self.cboHiddenActivation.blockSignals(True) 
        self.cboOutputActivation.blockSignals(True)
        self.mapper.toFirst()
        self.cboHiddenActivation.blockSignals(False)
        self.cboOutputActivation.blockSignals(False)
        self.setSelectedOperation(self.details_index)

        self.setUpdatesEnabled(True)
        # and emit the signal for graph panel and half-planes docks updates
        self.w1b1w2b2_Signal.emit(self.crtXOR_Slice.w1[0:2, :], self.crtXOR_Slice.w1[2:3,:], 
                                  self.crtXOR_Slice.w2[0:2, :], self.crtXOR_Slice.w2[2:3, :],
                                  self.crtXOR_Slice.activation1,
                                  self.crtXOR_Slice.activation2
                                  )
        
    def setSelectedOperation(self, iSelectedOperation:int):
        """ set the selected operation, and update the corresponding UI infos"""
        self.details_index = iSelectedOperation
        x0 = iSelectedOperation // 2
        x1 = iSelectedOperation % 2
        # display the current operation
        self._x_model.setDataFrame(pd.DataFrame([[x0, x1]], index=self._x_data.index, columns=self._x_data.columns))
        # and the current y_pred 
        self._A2_model.numpy_ndarray = self.crtXOR_Slice.y_aka_a2[iSelectedOperation:4:4] # slice of 1 element

    def Set_XOR_item(self, i:int, item:XOR_Slice):
        timer = QElapsedTimer() 
        timer.start()

        if i != item.index : # aka VirtualValue >= count
            item = XOR_Slice(-1) 
        self.crtXOR_Slice = item


        self.W1_model.blockSignals(True)
        self.W1_bias_1_model.blockSignals(True)
        self.W2_model.blockSignals(True)
        self.W2_bias_2_model.blockSignals(True)
        self._y00_model.blockSignals(True)
        self._lossAvg_Model.blockSignals(True)
        self._x00_model.blockSignals(True)

        self._x00_model.set_yTrue_xPercents_Hits(item.yParam, item.xPercents, item.xHits)

        _minRange = self.crtXOR_Slice.minRange
        _MaxRange = self.crtXOR_Slice.maxRange
        self.W1_model.numpy_ndarray = self.crtXOR_Slice.w1[0:2, :]
        self.W1_model.setbLockMask(self.crtXOR_Slice.w1_lock[0:2, :])
        self.W1_model.setRange(_minRange, _MaxRange)
        self.W1_bias_1_model.numpy_ndarray = item.w1[2:3, :]
        self.W1_bias_1_model.setbLockMask(self.crtXOR_Slice.w1_lock[2:3, :])
        self.W1_bias_1_model.setRange(_minRange, _MaxRange)

        self.W2_model.numpy_ndarray = item.w2[0:2, :]
        self.W2_model.setbLockMask(self.crtXOR_Slice.w2_lock[0:2, :])
        self.W2_model.setRange(_minRange, _MaxRange)
        self.W2_bias_2_model.numpy_ndarray = item.w2[2:3, :]
        self.W2_bias_2_model.setbLockMask(self.crtXOR_Slice.w2_lock[2:3, :])
        self.W2_bias_2_model.setRange(_minRange, _MaxRange)
        
        self._y00_model.set_Y_vals(item.yParam, item.y_aka_a2)
        self._lossAvg_Model.numpy_ndarray = item.lossAvg
        self._lossPerX_model.numpy_ndarray = self.crtXOR_Slice.lossPerX

        self._Z1_model.numpy_ndarray = self.crtXOR_Slice.z1
        self._A1_model.numpy_ndarray = self.crtXOR_Slice.a1
        self._Z2_model.numpy_ndarray = self.crtXOR_Slice.z2
        
        # self.blockSignals(False) TODO: WHY !?

        self.W1_model.blockSignals(False)
        self.W1_bias_1_model.blockSignals(False)
        self.W2_model.blockSignals(False)
        self.W2_bias_2_model.blockSignals(False)
        self._y00_model.blockSignals(False)
        self._lossAvg_Model.blockSignals(False)
        self._x00_model.blockSignals(False)

        self.refresh() 
        # print('DONE! WxPanels Set_XOR_item for pos = ', i, ' duration =', timer.elapsed())
    # end Set_XOR_item

# end class WxPanel

class Connector(QLabel):
    clicked = Signal()

    def __init__(self, delta_x = 35, delta_y = 11, txt = "...") -> None:
        self.delta_x = delta_x
        self.delta_y = delta_y
        self.txt = txt
        return super().__init__()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.save()
        try:
            painter.setPen(QPen(QColor('red'), 1))
            P1 = QPoint(3, 3)
            P2 = QPoint(3 + self.delta_x, 3)
            P3 = QPoint(3, 3 + self.delta_y)
            painter.drawPoint(P1)
            painter.drawPoint(P2)
            painter.drawPoint(P3)
            painter.drawEllipse(P1, 2.5, 2.5)
            painter.drawEllipse(P2, 2.5, 2.5)
            painter.drawEllipse(P3, 2.5, 2.5)

            painter.setPen(QPen(QColor('red'), 1))
            painter.drawLine(P1 + QPoint(2,0), P2 - QPoint(2,0))
            painter.drawLine(P1 + QPoint(0,2), P3 - QPoint(0,2))

            if self.txt:
                painter.drawText(8, self.delta_y + 13, self.txt)

        except Exception as e:
            print(e)
            pass
        painter.restore()
        # return super().paintEvent(event)
    # end paintEvent
        
    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        self.clicked.emit()
        # return super().mouseReleaseEvent(ev)
# end class Connector
        
class GraphPanel(QFrame):
    """ GraphPanel is a QWidget that contains a Graph widget with DiGraphs(directed edges) from networkx package, 
    and is used to display the graph of the XOR_Slice
    """
    def __init__(self, parent: QWidget | None = None, f: Qt.WindowFlags = Qt.WindowType.Widget) -> None:
        super().__init__(parent, f)
        self._operationIndex = -1
        self._showNodesValues = False
        self.graph = Graph()
        ly = QHBoxLayout()
        ly.setContentsMargins(0, 0, 0, 0)
        ly.addWidget(self.graph) 
        self.setLayout(ly)
        self.setMinimumSize(QSize(400, 150))
    
    @property
    def operationIndex(self) -> int:
        """ selected operation index \n
            0=0^0, 1=0^1, 2=1^0, 3=1^1 , show the corresponding values of the nodes if showNodesValues is True
        """
        return self._operationIndex 
    
    @operationIndex.setter
    def operationIndex(self, ix:int):
        self._operationIndex = ix

    @property
    def showNodesValues(self):
        return self._showNodesValues
    
    @showNodesValues.setter
    def showNodesValues(self, b:bool):
        self._showNodesValues = b

    def Set_XOR_item(self, virtualValue:int, xSlice:XOR_Slice):
        """ set the nodes and the edges of XOR_Slice, and update the graph """
        if virtualValue == xSlice.index:
            # real values
            self.graph.setEdges(xSlice.w1[0:2, :], xSlice.w1[2:3, :], 
                                xSlice.w2[0:2, :], xSlice.w2[2:3, :], 
                                xSlice.activation1, xSlice.activation2)
            ix = self._operationIndex
            if not self._showNodesValues:
                self.graph.ResetNodes()
            else:
                x0 = ix // 2
                x1 = ix % 2
                self.graph.SetNodes(np.array([x0, x1]), xSlice.z1[ix], xSlice.a1[ix], xSlice.z2[ix], xSlice.y_aka_a2[ix])
        else:
            # virtual value (out of range, no real values)
            self.graph.setEdges(np.zeros(shape=(2, 2)), np.zeros(shape=(1, 2)), 
                                np.zeros(shape=(2, 1)), np.zeros(shape=(1, 1)), 
                                '...', '...')
            self.graph.ResetNodes()

    def sizeHint(self) -> QSize:
        return QSize(840, 150)
# end class GraphPanel

class SliderPanel(QWidget):
    """ SliderPanel is a QWidget that contains a SliderEdit widget, and is used to display the current position of the XOR_Slice"""
    sigSliceChanged=Signal(int, XOR_Slice) # parameters : virtualValue Pos, xor_slice
    EMIT_MIN_TIME = 100 # wait milliseconds until emit sigSliceChanged

    def __init__(self, 
                 parent: QWidget | None = None, 
                 f: Qt.WindowFlags = Qt.WindowType.Widget) -> None:
        super().__init__(parent, f)
        self.slotGetCrtSlice = lambda : XOR_Slice()
        self.slider = SliderEdit(parent=self)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.redrawTimer = None
        ly = QVBoxLayout()
        ly.setContentsMargins(0, 0, 0, 0)
        ly.addWidget(self.slider)
        self.setLayout(ly)
        self.slider.valueChanged.connect(self.ValueChanged)
        self.setFixedHeight(23)
        self.setFocusProxy(self.slider)

    def setData(self, maxValue: int, lstTPindexes: List[int], lstTurningPointsDiff, pos: Optional[int] = None):
        """
        Sets the data for the panel.

        Args:
            maxValue (int): The maximum value for the slider.
            lstTPindexes (List[int]): A list of turning point indexes.
            lstTurningPointsDiff: The difference between turning points.
            pos (Optional[int], optional): The position to set the slider value to. Defaults to None.
        """
        bs = self.blockSignals(True)
        self.slider.setMaximum(maxValue)
        self.blockSignals(bs)
        self.slider.setTurningPoints(lstTPindexes, lstTurningPointsDiff)
        if globalParameters.KeepOnePosForAllModels:
            oldVal = self.slider.getVirtualValue()
            self.slider.setValue(oldVal)
            self.ValueChanged(oldVal)
            self.slider._valueChanged(oldVal)
        else:
            if pos is not None:
                if self.slider.value() != pos:
                    self.slider.setValue(pos)
                else:
                    self.slider._valueChanged(pos)
                    self.ValueChanged(pos)
    # end setData method
                    
    def ValueChanged(self, i:int):
        # Here is the place to emit the signal, AFTER a while, to avoid too many signals(so UI updates)
        # slider.valueChanged: SignalInstance trigger IF and ONLY IF the value WAS REALLY CHANGED
        # so no recursion pb...
        if self.redrawTimer is None:
            self.redrawTimer = QTimer(self)
            self.redrawTimer.setSingleShot(True)
            def _emitsigSliceChanged():
                #  print("_emitsigSliceChanged self.slider.virtualValue() / epoch_size", 
                #        self.slider.getVirtualValue(), self.slotGetCrtSlice().epoch_size)
                 self.sigSliceChanged.emit(self.slider.getVirtualValue(), self.slotGetCrtSlice())
            self.redrawTimer.timeout.connect(_emitsigSliceChanged)
            self.redrawTimer.start(self.EMIT_MIN_TIME)
        else:
            self.redrawTimer.start(self.EMIT_MIN_TIME)
    # end ValueChanged method

    def SetPos(self, i:int):
        # here we receive the pos from other source, Slot
        if self.slider.getVirtualValue() != i:
            # print('SetPos sliderPanel Old value= ', self.slider.value(), 'SetPos( i=)', i)
            self.slider.setValue(i) 

    def setWhatToCallToGetCrtSlice(self, slotGetTP: Callable[[],XOR_Slice]):
        """ set the function to call to get the current TP """
        self.slotGetCrtSlice = slotGetTP
# end class SliderPanel

class z1a1z2Panel(QFrame):
    """ z1a1z2Panel is a QWidget that contains 3 TableView widgets, and is used to display the 
    z1, a1, z2 evolution graphics of THE CURRENT OPERATION of a XOR_Slice"""
    def __init__(self, 
                 sigPosChangedFromHub:Signal=SliderPanel.sigSliceChanged, 
                 HubSlotForPosChanged =None, 
                 sig_extern_glow: Signal | None = None,
                 parent: QWidget | None = None, 
                 f: Qt.WindowFlags = Qt.WindowType.Widget) -> None:

        super().__init__(parent, f)
        
        self.sigPosChangedFromHub = sigPosChangedFromHub
        self.HubSlotForPosChanged = HubSlotForPosChanged

        self._arrayModel = XOR_array_model() # something

        self.plot_z1_Single = Singles_Plotter(sigPosChangedFromHub=self.sigPosChangedFromHub, 
                                              HubSlotForPosChanged=self.HubSlotForPosChanged,
                                              name='z1 s'
                                              )
        self.plot_z1_Pairs = Pairs_Plotter(sigPosChangedFromHub=self.sigPosChangedFromHub) 
        
        self.plot_a1_Single = Singles_Plotter(sigPosChangedFromHub=self.sigPosChangedFromHub, 
                                              HubSlotForPosChanged=self.HubSlotForPosChanged, 
                                              background_color=backgroundColorContrast(combineColors(MxCOLORS.A1_0, MxCOLORS.A1_1)),
                                              name='a1 s'
                                              )
        self.plot_a1_Pairs = Pairs_Plotter(sigPosChangedFromHub=self.sigPosChangedFromHub,
                                           background_color=backgroundColorContrast(combineColors(MxCOLORS.A1_0, MxCOLORS.A1_1))
                                           )
        
        self.plot_z2_Single = Singles_Plotter(sigPosChangedFromHub=self.sigPosChangedFromHub, 
                                              HubSlotForPosChanged=self.HubSlotForPosChanged, 
                                              name='z2 s'
                                              )
        self.plot_a2_Single = Singles_Plotter(sigPosChangedFromHub=self.sigPosChangedFromHub, 
                                              HubSlotForPosChanged=self.HubSlotForPosChanged, 
                                              name='a2 s'
                                              )
        am = self._arrayModel
        self.plot_z1_Single.AddSeries(am.z1[:, 0, 0], color=MxCOLORS.W1_Col0, label="Z1[0]")
        self.plot_z1_Single.AddSeries(am.z1[:, 0, 1], color=MxCOLORS.W1_Col1, label="Z1[1]")

        self.plot_z1_Pairs.AddPairs((am.z1[:, 0, 0], am.z1[:, 0, 1]), line_color=MxCOLORS.W1_Col1,  
                                    labels_colors=(MxCOLORS.W1_Col0, MxCOLORS.W1_Col1),
                                    labels_text=('Z1[0]', 'Z1[1]'))

        self.plot_a1_Single.AddSeries(am.a1[:, 0, 0], color=MxCOLORS.A1_0, label="A1[0]")
        self.plot_a1_Single.AddSeries(am.a1[:, 0, 1], color=MxCOLORS.A1_1, label="A1[1]")

        self.plot_a1_Pairs.AddPairs((am.a1[:, 0, 0], am.a1[:, 0, 1]), 
                                    line_color=combineColors(MxCOLORS.A1_0, MxCOLORS.A1_1),  
                                    labels_colors=(MxCOLORS.A1_0, MxCOLORS.A1_1),
                                    labels_text=('A1[0]', 'A1[1]'))

        self.plot_z2_Single.AddSeries(am.z2[:, 0, 0], color=MxCOLORS.Z2, label="Z2")
        self.plot_a2_Single.AddSeries(am.y_aka_a2[:, 0, 0], color=MxCOLORS.Y, label="Y")

        self.dockArea = DockArea(self)
        self.setContentsMargins(2,2,2,2)
        self.dockArea.move(0,0)

        self.dockZ1Single = Dock_Colored(name="z1 single", color=MxCOLORS.W1_Col0, 
                                         plotter=self.plot_z1_Single,
                                         sig_extern_glow=sig_extern_glow
                                         )
        self.dockZ1Pairs = Dock_Colored(name="z1 pairs", color=MxCOLORS.W1_Col0, 
                                        plotter=self.plot_z1_Pairs
                                        )
      
        self.dockA1Single = Dock_Colored(name="a1 single", color=MxCOLORS.A1_0, 
                                         plotter=self.plot_a1_Single,
                                         sig_extern_glow=sig_extern_glow
                                         )
        self.dockA1Pairs = Dock_Colored(name="a1 pairs", color=MxCOLORS.A1_0, 
                                        plotter=self.plot_a1_Pairs
                                        )

        self.dockZ2Single = Dock_Colored(name="z2 single", color=MxCOLORS.Z2, 
                                           plotter=self.plot_z2_Single,
                                           sig_extern_glow=sig_extern_glow
                                           )
        
        self.dockA2Single = Dock_Colored(name="a2 single", color=MxCOLORS.Y, 
                                          plotter=self.plot_a2_Single, 
                                          sig_extern_glow=sig_extern_glow
                                          )

        self.dockArea.addDock(self.dockZ1Pairs)
        self.dockArea.addDock(self.dockA1Pairs, "right", self.dockZ1Pairs)
        self.dockArea.addDock(self.dockA2Single, "right", self.dockA1Pairs)
        self.dockArea.addDock(self.dockZ1Single, "above", self.dockZ1Pairs)
        self.dockArea.addDock(self.dockA1Single, "above", self.dockA1Pairs)
        self.dockArea.addDock(self.dockZ2Single, "above", self.dockA2Single)
        
        ly = QVBoxLayout()
        ly.addWidget(self.dockArea)
        ly.setContentsMargins(2, 2, 2, 2)
        self.setLayout(ly)
        self._ix = 0
    # end __init__

    def sizeHint(self) -> QSize:
        return QSize(1600, 160)
    
    def SetModel(self, xorModel:XOR_model):
        """
        Sets the XOR model for the panel and the list of turning points indexes.

        Parameters:
        xorModel (XOR_model): The XOR model to set.

        Returns:
        None
        """
        self._arrayModel = xorModel.xor_array
        self._tp_indexes_list = [ix.index for ix in xorModel.lstTurningPoints]
        self.setSelectedOperation(self._ix)
    
    def setSelectedOperation(self, ix:int):
        """ set the selected operation, and update the corresponding UI infos"""
        self._ix = ix
        if ix < 0 :
            # obsolete...
            assert False, "ix < 0"
        else :
            am = self._arrayModel
            
            self.plot_z1_Single.updateSeries(am.z1[:, ix, 0], am.z1[:, ix, 1])
            self.plot_z1_Single.setTurningPoints(self._tp_indexes_list)
            self.plot_z1_Pairs.updateSeries((am.z1[:, ix, 0], am.z1[:, ix, 1]))
            self.plot_z1_Pairs.setTurningPoints(self._tp_indexes_list)

            self.plot_a1_Single.updateSeries(am.a1[:, ix, 0], am.a1[:, ix, 1])
            self.plot_a1_Single.setTurningPoints(self._tp_indexes_list)
            self.plot_a1_Pairs.updateSeries((am.a1[:, ix, 0], am.a1[:, ix, 1]))
            self.plot_a1_Pairs.setTurningPoints(self._tp_indexes_list)

            self.plot_z2_Single.updateSeries(am.z2[:, ix, 0])
            self.plot_z2_Single.setTurningPoints(self._tp_indexes_list)
            self.plot_a2_Single.updateSeries((am.y_aka_a2[:, ix, 0]))
            self.plot_a2_Single.setTurningPoints(self._tp_indexes_list)
# end class z1a1z2Panel
            
class panel_W1_HalfPlanes(Dock_Colored):
    """ panel_W1_HalfPlanes is a Dock_Colored that contains a HalfPlanes_Plotter widget, 
        and is used to display 2(two) lines x 2hp = 4 half-planes corresponding of the W1 matrix of the XOR_Slice model
    """
    def __init__(self, name, plotter: HalfPlanes_Plotter, area = None, size = (450, 300), widget = None, hideTitle = False, 
                 autoOrientation = False, label = None, color: QColor = MxCOLORS.TBL_HEADER_GRAY, 
                 sig_extern_glow: Signal | None = None, **kargs):
        super().__init__(name, plotter, area, size, widget, hideTitle, autoOrientation, label, color, sig_extern_glow, **kargs)
        self.setOrientation('horizontal', force=True)
        self.setMinimumSize(QSize(300, 280))

    def update_Planes(self, item: XOR_Slice ):
        """ update the 2 lines from the W1 matrix columns of the XOR_Slice model"""
        self.plotter.setUpdatesEnabled(False)
        self.plotter.RemoveAllLines()
        
        a, b, c = item.w1[0, 0], item.w1[1, 0], item.w1[2, 0]
        line = Line(a, b, c) # the first classification line defined by the first column of W1
        self.plotter.AddLine(line, QMarginsF(2,1,1,2), MxCOLORS.W1_Col0, Qt.HorPattern, Qt.VerPattern)
        
        a, b, c = item.w1[0, 1], item.w1[1, 1], item.w1[2, 1]
        line = Line(a, b, c) # the second classification line defined by the second column of W1
        self.plotter.AddLine(line, QMarginsF(1,2,2,1), MxCOLORS.W1_Col1, Qt.FDiagPattern, Qt.BDiagPattern) 

        # set the data for the 4 transformed points of the quadrilateral
        #   z1 are the positions of the 4 points,
        #   yParam is the y_true, 
        #   y_aka_a2 is the y_pred
        arr = np.hstack((item.z1, item.yParam.reshape(4, 1), item.y_aka_a2)) 
        self.plotter.setData_Quadrilateral(x00_ValX_ValY=arr) 

        self.plotter.setUpdatesEnabled(True)
    # end update_Planes
        
    def sizeHint(self) -> QSize:
        return QSize(420, 300)
# end class panel_W1_HalfPlanes
    
class panel_W2_HalfPlanes(Dock_Colored):
    """ panel_W2_HalfPlanes is a Dock_Colored that contains a HalfPlanes_Plotter widget
        and is used to display 1(one) line x 2 half-planes corresponding of the W2 matrix of the XOR_Slice model
    """
    def __init__(self, name, plotter: HalfPlanes_Plotter, area=None, size=(450, 300), widget=None, hideTitle=False, 
                 autoOrientation=False, label=None, color: QColor = MxCOLORS.TBL_HEADER_GRAY, sig_extern_glow: Signal | None = None, **kargs):
        super().__init__(name, plotter, area, size, widget, hideTitle, autoOrientation, label, color, sig_extern_glow, **kargs)
        self.setOrientation('horizontal', force=True)
        self.setMinimumSize(QSize(300, 280))

    def update_Planes(self, item: XOR_Slice ):
        """ update the classification line from the W2 matrix(column) of the XOR_Slice model"""
        self.plotter.setUpdatesEnabled(False)
        self.plotter.RemoveAllLines()
        
        a, b, c = item.w2[0, 0], item.w2[1, 0], item.w2[2, 0]
        line = Line(a, b, c)
        self.plotter.AddLine(line, QMarginsF(2,1,1,2), MxCOLORS.W2_1, Qt.FDiagPattern, Qt.BDiagPattern)

        # set the data for the 4 transformed points of the quadrilateral Obs: this comes from activation1(z1) = a1
        #   A1 are the positions of the 4 points,
        #   yParam is the y_true, 
        #   y_aka_a2 is the y_pred
        arr = np.hstack((item.a1, item.yParam.reshape(4, 1), item.y_aka_a2))
        self.plotter.setData_Quadrilateral(x00_ValX_ValY=arr)

        self.plotter.setUpdatesEnabled(True)
    # end update_Planes
    
    def sizeHint(self) -> QSize:
        return QSize(420, 300)

# end class panel_W2_HalfPlanes
    

