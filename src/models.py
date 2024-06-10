"""
Models for the XOR training process and for MVC table views.

"""

from enum import IntEnum
from typing import (Any, List, Optional, overload, Self)

import numpy as np
import pandas as pd

from PySide6.QtCore import (QAbstractTableModel, QFileInfo, QModelIndex, Qt)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QWidget

from core import *
from custom_widgets import TitledProgressBar
from global_stuff import *
from utilities import *

np.random.seed(127)  # for testing in deterministic mode


class InvalidJsonObjectTypeError(Exception):
    """Raised when the JSON object is not a dictionary."""
    pass

class UnsupportedXORJsonVersionError(Exception):
    """Raised when the XOR model JSON version is not supported."""
    pass

class MatrixWithMaskAndColoredHeaderModel(QAbstractTableModel):
    """
    A custom QAbstractTableModel that represents a matrix with a mask of locked cells and colored headers.
    """
    USER_ROLE_LOCK = Qt.ItemDataRole.UserRole
    USER_ROLE_LOCK_LOCK = Qt.ItemDataRole.UserRole + 1
    USER_ROLE_RANGE_MIN = Qt.ItemDataRole.UserRole + 2
    USER_ROLE_RANGE_MAX = Qt.ItemDataRole.UserRole + 3

    def __init__(self,
                 data: pd.DataFrame | None = None,
                 mask: pd.DataFrame | None = None,
                 blockLock: pd.DataFrame | None = None,
                 flags: Qt.ItemFlag = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable,  # type:ignore
                 hHeaderColors=[],
                 vHeaderColors=[],
                 mxExplicitColors=[]
                 ):
        """
        Initializes the MatrixWithMaskAndColoredHeaderModel.

        Args:
            data: The data for the matrix. If None, a random 2x2 matrix will be generated.
            mask: The mask for the matrix. If None, a random mask will be generated.
            blockLock: The block lock for the matrix. If None, all blocks will be unlocked.
            flags: The flags for the model items.
            hHeaderColors: The colors for the horizontal headers.
            vHeaderColors: The colors for the vertical headers.
            mxExplicitColors: The explicit colors for the matrix items. 
                If None, the cells will be colored (via paint of FloatDelegate QStyledItemDelegate and MxQTableView(QTableView).SelectionChanged) 
                based on the combination of the corresponding vertical and horizontal headers colors.
        """
        super().__init__()
        self._data = data if data is not None else pd.DataFrame( -10 + 20 * np.random.rand(2, 2) )
        self._mask = mask if mask is not None else pd.DataFrame( np.random.choice(a=[False, True], size=(2, 2), p=[0.5, 0.5]) )
        self._blockLock = blockLock if blockLock is not None else pd.DataFrame( np.full((2, 2), False) )
        self._flags = flags
        self._hHeaderColors = hHeaderColors or ['royalblue', 'olivedrab']  # 4169e1 = royalblue
        self._hHeaderColors = hHeaderColors or [0x99ca53, 0x209fdf]
        self._hHeaderColors = hHeaderColors or [0x57bef1, 0xadd276]
        self._vHeaderColors = vHeaderColors or ['gold', 'mediumvioletred']
        self._vHeaderColors = vHeaderColors or ['lightgray', 'gray']
        self._vHeaderColors = vHeaderColors or ['mediumpurple', 'coral']
        self._vHeaderColors = vHeaderColors or ['blue', 'orange']
        self._vHeaderColors = vHeaderColors or ['red', 'orange']
        self._vHeaderColors = vHeaderColors or [0xdd5555, 'orange']  
        self._vHeaderColors = vHeaderColors or [0xdd5555, 0xff8822]
        self._mxExplicitColors = mxExplicitColors
        self._min = -20
        self._max = 20

        assert self._data.shape == self._mask.shape, "mask and data must have the same shape"
        assert len(self._data.columns) == len(self._hHeaderColors), "No of columns == _hHeaderColors"
        assert len(self._data.index) == len(self._vHeaderColors), f"No of rows:{self._data.index} != _vHeaderColors:{self._vHeaderColors}"
        self._iniData = self._data.copy()

    def rowCount(self, parent=QModelIndex()):
        """
        Returns the number of rows in the model.

        Args:
            parent: The parent index. Not used in this implementation.

        Returns:
            The number of rows in the model.
        """
        return len(self._data.index)

    def columnCount(self, parent=QModelIndex()):
        """
        Returns the number of columns in the model.

        Args:
            parent: The parent index. Not used in this implementation.

        Returns:
            The number of columns in the model.
        """
        return len(self._data.columns)

    def headerData(self, section, orientation, role):
        """
        Returns the header data for the specified section.

        Args:
            section: The section index.
            orientation: The orientation of the header (horizontal or vertical).
            role: The role of the header data.

        Returns:
            The header data for the specified section.
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(self._data.index[section])
        elif role == Qt.ItemDataRole.BackgroundRole:
            if orientation == Qt.Orientation.Horizontal:
                return QColor(self._hHeaderColors[section])
            else:
                return QColor(self._vHeaderColors[section])
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter  # type:ignore

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Returns the data for the specified index and role.

        Args:
            index: The index of the item.
            role: The role of the item data.

        Returns:
            The data for the specified index and role.
        """
        match role:
            case Qt.ItemDataRole.DisplayRole:
                # if type(self._data.iloc[index.row(), index.column()]) is np.float64:
                if isinstance(self._data.iloc[index.row(), index.column()], np.floating):
                    return "%.3f" % self._data.iloc[index.row(), index.column()]
                else:
                    return str(self._data.iloc[index.row(), index.column()])
            case Qt.ItemDataRole.EditRole:
                return "%.3f" % self._data.iloc[index.row(), index.column()]
            case self.USER_ROLE_LOCK:
                return self._mask.iloc[index.row(), index.column()]
            case self.USER_ROLE_LOCK_LOCK:
                return self._blockLock.iloc[index.row()][index.column()]
            case self.USER_ROLE_RANGE_MIN:
                return self._min
            case self.USER_ROLE_RANGE_MAX:
                return self._max
            case Qt.ItemDataRole.TextAlignmentRole:
                # if type(self._data.iloc[index.row(), index.column()]) is np.float64:
                if isinstance(self._data.iloc[index.row(), index.column()], np.floating):
                    return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight  # type:ignore
                else:  # str
                    return Qt.AlignmentFlag.AlignCenter  # type:ignore
            case Qt.ItemDataRole.ForegroundRole:
                return QColor("black")
            case Qt.ToolTipRole:
                if isinstance(self._data.iloc[index.row(), index.column()], np.floating):
                    return "%.10f" % self._data.iloc[index.row(), index.column()]
                else:
                    return self._data.iloc[index.row(), index.column()]
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Sets the data for the specified index and role.

        Args:
            index: The index of the item.
            value: The new value for the item.
            role: The role of the item data.

        Returns:
            True if the data was set successfully, False otherwise.
        """
        if index.isValid():
            match role:
                case Qt.ItemDataRole.EditRole:
                    self._data.iloc[index.row(), index.column()] = float(value)
                    self.dataChanged.emit(index, index, [Qt.ItemDataRole.EditRole])
                    return True
                case self.USER_ROLE_LOCK:
                    self._mask.iloc[index.row(), index.column()] = float(value) # float NOT bool, float operate like a pointer
                    # self._mask.iloc[index.row(), index.column()] = bool(value)
                    # self.dataChanged.emit(index, index, [self.USER_ROLE_LOCK]) #  emit or not 2 ? not 2
                    return True
        return False

    def setDataFrame(self, df: pd.DataFrame):
        """
        Sets the data frame for the model.

        Args:
            df: The new data frame.

        Raises:
            AssertionError: If the shape of the new data frame is different from the current data frame.
        """
        assert self._data.shape == df.shape
        self._data = df
        self.dataChanged.emit(self.index(0, 0), self.index(0, 1))

    def getDataFrame(self):
        """
        Returns the data frame of the model.

        Returns:
            The data frame of the model.
        """
        return (self._data)

    @property
    def numpy_ndarray(self):
        """
        Returns the data of the model as a NumPy ndarray.

        Returns:
            The data of the model as a NumPy ndarray.
        """
        return self._data.to_numpy()

    @numpy_ndarray.setter
    def numpy_ndarray(self, nd):
        """
        Sets the data of the model from a NumPy ndarray.

        Args:
            nd: The new data as a NumPy ndarray.

        Raises:
            AssertionError: If the shape of the new data is different from the current data.
        """
        assert self._data.shape == nd.shape, "self._data.shape = " + str(self._data.shape) + " != nd.shape = " + str(nd.shape)
        self._data = pd.DataFrame(nd, index=self._data.index, columns=self._data.columns)
        self.dataChanged.emit(self.index(0, 0), self.index(len(self._data.index) - 1, len(self._data.columns) - 1) )

    def setbLockMask(self, mask: np.ndarray):
        """
        Sets the block lock mask for the model.

        Args:
            mask: The new block lock mask.
        """
        self._mask = pd.DataFrame(mask)

    def setRange(self, _min: int, _max: int):
        """
        Sets the range for the model.

        Args:
            _min: The minimum value of the range.
            _max: The maximum value of the range.
        """
        self._min = _min
        self._max = _max

    def RestoreDataFrameFromINI(self):
        """
        Restores the data frame from the initial data frame.
        """
        self.setDataFrame(self._iniData)

    def flags(self, index):
        """
        Returns the flags for the specified index.

        Args:
            index: The index of the item.

        Returns:
            The flags for the specified index.
        """
        return self._flags

    def ExplicitColors(self):
        """
        Returns the explicit colors for the matrix items.

        Returns:
            The explicit colors for the matrix items.
        """
        return self._mxExplicitColors

# end class Matrix2x2ViewModel


class X00_Model(QAbstractTableModel):
    """
    A custom QAbstractTableModel that represents a 4x3 matrix 
    vertical header = X00, X01, X10, X11 are the 4 possible inputs
    horizontal header = '=', '%' and 'hits' are the 3 columns
    column 1 are the expected values for the inputs
    column 2 are the percentages allocated for the inputs in random generation
    column 3 are the hits(from random generation of batches) for each input in the training process
    """

    def __init__(self, val=np.array([1, 0, 0, 1], dtype=np.int32), pc=np.array([25] * 4, dtype=np.int32)) -> None:
        """
        Initializes the X00_Model.

        Args:
            val: The values for the '=' column.
            pc: The percentages for the '%' column.
        """
        super().__init__()
        self._data = pd.DataFrame(index=['0^0', '0^1', '1^0', '1^1'], columns=['=', '%', 'hits'], dtype=np.int32)
        self._data['='] = val
        self._data['%'] = pc
        self._data['hits'] = np.zeros(4, dtype=np.int32)
        assert self._data['%'].sum() == 100

    def set_yTrue_xPercents_Hits(self, yTrue: np.ndarray, xPercents: np.ndarray, hits: np.ndarray):
        """
        Sets the yTrue, xPercents, and hits data for the model.

        Args:
            yTrue: The yTrue data.
            xPercents: The xPercents data.
            hits: The hits data.
        """
        # If data is a dict containing one or more Series (possibly of different dtypes),
        # copy=False will ensure that these inputs are not copied.
        # keep the pointer, modify the data in place
        self._data = pd.DataFrame(data={'=': yTrue.reshape(4),
                                        '%': xPercents.reshape(4),
                                        'hits': hits.reshape(4)},
                                  index=['0^0', '0^1', '1^0', '1^1'],
                                  copy=False
                                  # columns=['=', '%', 'hits']
                                  )
        # self._data['='].array = yTrue
        # self._data['%'].array = xPercents

        # self.dataChanged.emit(self.index(0,2), self.index(len(self._data.index) - 1, 2)) # no more needed


    def rowCount(self, parent: QModelIndex) -> int:
        """
        Returns the number of rows in the model.

        Args:
            parent: The parent index. Not used in this implementation.

        Returns:
            The number of rows in the model.
        """
        return len(self._data.index)

    def columnCount(self, parent: QModelIndex) -> int:
        """
        Returns the number of columns in the model.

        Args:
            parent: The parent index. Not used in this implementation.

        Returns:
            The number of columns in the model.
        """
        return len(self._data.columns)

    def flags(self, index):
        """
        Returns the flags for the specified index.

        Args:
            index: The index of the item.

        Returns:
            The flags for the specified index.
        """
        # Not editable for : last column == Hits 
        # nor last Row from Percentage column( is autocompleted with the rest to 100)
        if index.column() == 2 or (index.column() == 1 and index.row() == 3):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable  # type:ignore
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable  # type:ignore

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> Any:
        lstVheaderColors = [MxCOLORS.X00_COLOR, MxCOLORS.X01_COLOR, MxCOLORS.X10_COLOR, MxCOLORS.X11_COLOR]

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return (self._data.columns[section])
            else:
                return (self._data.index[section])
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter  # type:ignore
        elif role == Qt.BackgroundRole:
            if orientation == Qt.Vertical:
                return lstVheaderColors[section]
        # elif role == Qt.ForegroundRole: # old version, not used anymore
            # if orientation == Qt.Vertical:
                # return QColor("red")
        return super().headerData(section, orientation, role)

    def sum_pred_col_pc(self, row: int):
        # sum precedents column PerCent
        return self._data.iloc[:row, 1].sum()

    def setData(self, index: QModelIndex, value: Any, role: int) -> bool:
        if index.isValid():
            _value = 0
            try:
                _value = int(value)
            except:
                pass
            if role == Qt.EditRole:
                if index.column() == 1:  # % Column
                    c = index.column()
                    r = index.row()
                    s_pred = self.sum_pred_col_pc(r)
                    s_rest = 100 - s_pred - _value
                    s_rep = s_rest // (3 - r) # try to distribute evenly the rest
                    self._data.iloc[r + 1:-1, c] = s_rep
                    self._data.iloc[-1, c] = s_rep + (s_rest - s_rep * (3 - r)) # the rest on the last row
                self._data.iloc[index.row(), index.column()] = _value
                self.dataChanged.emit(index, index, Qt.EditRole) # to propagate the changes to the Y_model ! (although for % column is not needed)
                return True
        return False

    def data(self, index: QModelIndex, role: int) -> Any:
        match role:
            case Qt.DisplayRole:
                txt = str(self._data.iloc[index.row(), index.column()]) # display the value as text
                return txt
            case Qt.EditRole:
                return self._data.iloc[index.row(), index.column()]
            case Qt.ItemDataRole.TextAlignmentRole:
                if index.column() >= 1:
                    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                else:
                    return Qt.AlignmentFlag.AlignCenter  # type:ignore
            case Qt.ItemDataRole.ForegroundRole:
                if index.column() <= 1:  # col '=' and col '%' are editable
                    return QColor("blue")
            case _:
                return None
# end class X00_Model


class Y00_Model(QAbstractTableModel):
    """ 
    The model for the Y00 table, with 2 columns: '=' and 'ŷ/x'.
    """
    def __init__(self, preset_vals=[0, 1, 1, 0], fwd_vals=[0.78, 0.12, 0.153, 0.812]) -> None:
        super().__init__()
        self._data = pd.DataFrame(index=['0^0', '0^1', '1^0', '1^1'])
        self._data['='] = preset_vals
        self._data['ŷ/x'] = fwd_vals

    def set_Y_vals(self, preset_vals, fwd_vals):
        # self._data['='] = preset_vals
        # self._data['ŷ/x'] = fwd_vals
        # although above it's fine, 'cause here are not editable columns, but for the sake of consistency with 'copy=False'
        self._data = pd.DataFrame(data={'=': preset_vals.reshape(4),
                                        'ŷ/x': fwd_vals.reshape(4)},
                                  index=['0^0', '0^1', '1^0', '1^1'],
                                  copy=False
                                  # columns=['=', '%', 'hits']
                                  )
        self.dataChanged.emit(self.index(0, 1), self.index(len(self._data.index) - 1, 2)) # thinking : it's necessary to emit? 

    def rowCount(self, parent: QModelIndex) -> int:
        return len(self._data.index)

    def columnCount(self, parent: QModelIndex) -> int:
        return len(self._data.columns)

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable  # type:ignore

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return (self._data.columns[section])
            else:
                return (self._data.index[section])
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter  # type:ignore
        elif role == Qt.BackgroundRole:
            if orientation == Qt.Vertical:
                return QColor('blue').lighter(160)
            elif section == 1:
                return MxCOLORS.Y
        elif role == Qt.ForegroundRole:
            if orientation == Qt.Vertical:
                return QColor("red")

    def data(self, index: QModelIndex, role: int) -> Any:
        match role:
            case Qt.DisplayRole:
                if index.column() == 1:
                    return "%.7f  " % self._data.iloc[index.row(), index.column()]
                else:
                    return str(self._data.iloc[index.row(), index.column()])
            case Qt.EditRole:
                return self._data.iloc[index.row(), index.column()]
            case Qt.ItemDataRole.TextAlignmentRole:
                if index.column() == 1:
                    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter  # type:ignore
                else:
                    return Qt.AlignmentFlag.AlignCenter  # type:ignore
            case Qt.ItemDataRole.ForegroundRole:
                return QColor("blue")
            case Qt.ItemDataRole.BackgroundRole:
                if index.column() == 1:
                    return MxCOLORS.Y.lighter(110)
            case Qt.ToolTipRole:
                return "%.10f" % self._data.iloc[index.row(), index.column()]
            case _:
                return None
# end class Y00_Model


class XOR_Slice:
    """ A slice of XOR training process """
    class ColumnsMap(IntEnum):
        """ enum used for QDataWidgetMapper to map the columns of the slice 
        to the TPModel model. used in: control_panel.py > TPParamsTab > setMapping """
        index = 0 # index of slice in training process
        xPercents = 10 # % distribution of 4 inputs
        yParam = 20 # yTrue
        xHits = 25 # hits for each input
        epoch_size = 30 # number of slices in an epoch
        batch_size = 40 # number of inputs in a batch
        learning_rate = 50  # normally in (0, 100) but what if Warp speed ? 1, 2, ok max 3 :) Oscillating ?!
        w1 = 60 # weights for hidden layer, 3-th row = b1
        w1_lock = 62 # lock for w1
        z1 = 65 # z1 = x @ w1
        activation1 = 70 # activation function for hidden layer
        a1 = 80 # a1 = activation1(z1)
        w2 = 90 # weights for output layer, 3-th row = b2
        w2_lock = 92 # lock for w2
        z2 = 95 # z2 = a1 @ w2
        activation2 = 100 # activation function for output layer
        y_aka_a2 = 105 # y = activation2(z2)
        lossAvg = 110  # average loss for the slice
        lossPerX = 115 # loss for each input
        minRange = 120 # min value for weights
        maxRange = 125 # max value for weights
        cyclesPerOneStepFwdOfEpoch = 130 # aka calculus granularity ?
        seedTP = 140  # seed for random generation
        loss = 150 # loss function

    @overload
    def __init__(self, argTP: "XOR_Slice") -> None: ...
    """ like cloning """
    @overload
    def __init__(self, argTP: Optional[int] = None) -> None: ...
    """ arg=seed/invalid (default=0=random / -1 invalid fill zeros) """

    def __init__(self, argTP: Optional[Any] = None) -> None:
        if argTP is None:
            # see Up : np.random.seed(127) # for testing in deterministic mode
            argTP = np.random.randint(0, 65536)
        if type(argTP) is XOR_Slice:
            self.__dict__ = dict(vars(argTP.clone()))
            return

        assert type(argTP) is int, "not int..?!"
        self.seedTP = int(argTP)
        self.index = 0
        self.batch_size: int = 1
        self.epoch_size: int = 1
        self.cyclesPerOneStepFwdOfEpoch = 1
        self.learning_rate = 0.1
        self.activation1: str = Functions.ReLU.__name__
        self.activation2: str = Functions.sigmoid.__name__
        self.loss: str = Functions.LCE_Loss.__name__

        if self.seedTP == -1:  # Invalid, used for cloning and for TPModel init (unique pointer)
            self.index = -1  
            self.xPercents = np.array([10, 20, 30, 40], dtype=np.int32)
            self.yParam = Y_XOR_TRUE_4
            self.xHits = np.array([-1] * 4)  # definitely invalid
            self.minRange = 0
            self.maxRange = 0
            self.w1 = np.zeros(shape=(3, 2))  # 3-th row = b1
            self.w1_lock = np.zeros(shape=(3, 2), dtype=np.int32)
            self.a1 = np.zeros(shape=(4, 2))
            self.z1 = np.zeros(shape=(4, 2))
            self.w2 = np.zeros(shape=(3, 1))
            self.w2_lock = np.zeros(shape=(3, 1), dtype=np.int32)
            self.z2 = np.zeros(shape=(4, 1))
            self.y_aka_a2 = np.zeros(shape=(4, 1))
            self.lossAvg = np.ones(shape=(1, 1))
            self.lossPerX = np.ones(shape=(4, 1))
        else:
            self.w1 = np.zeros(shape=(3, 2))
            self.w1_lock = np.zeros(shape=(3, 2), dtype=np.int32)
            self.z1 = np.zeros(shape=(4, 2))
            self.a1 = np.zeros(shape=(4, 2))
            self.w2 = np.zeros(shape=(3, 1), dtype=np.int32)
            self.w2_lock = np.zeros(shape=(3, 1))
            self.z2 = np.zeros(shape=(4, 1))
            self.y_aka_a2 = np.zeros(shape=(4, 1))
            self.lossAvg = np.ones(shape=(1, 1))
            self.lossPerX = np.ones(shape=(4, 1))
            self.feedFromSeed(self.seedTP, set()) # Fill the  set() = all columns unlocked

        _self_vars_names = set(vars(self))
        _ColumnsMap_names = set(c.name for c in self.ColumnsMap)
        _sym_diff = _self_vars_names.symmetric_difference(_ColumnsMap_names)
        assert len(_sym_diff) == 0, f"TurningPoint:: ColumnsMap <> Attributes : {_sym_diff}"


    def feedFromSeed(self, seed: int, setColumnsLocked: set):
        """ Fill the slice with random(aka modulo setColumnsLocked) values based on seed """
        self.seedTP = seed
        _rng = np.random.default_rng(seed=self.seedTP)

        # _rng_Consumed : in any case We have to consume it to have a deterministic process
        _rng_Consumed = int(_rng.choice(CHOICES_LISTS.BATCH_SIZE)) # BIg pb if not converting to python int (return numpy.int32)
        if not XOR_Slice.ColumnsMap.batch_size in setColumnsLocked:
            self.batch_size = _rng_Consumed

        _rng_Consumed = int(_rng.choice(CHOICES_LISTS.EPOCH_SIZE))
        if not XOR_Slice.ColumnsMap.epoch_size in setColumnsLocked:
            self.epoch_size = _rng_Consumed
        
        _rng_Consumed = int(_rng.choice(CHOICES_LISTS.CYCLES_PER_EPOCH))
        if not XOR_Slice.ColumnsMap.cyclesPerOneStepFwdOfEpoch in setColumnsLocked:
            self.cyclesPerOneStepFwdOfEpoch = _rng_Consumed
        
        _rng_Consumed = float(round(_rng.random() * 0.98 + 0.01, 2))
        if not XOR_Slice.ColumnsMap.learning_rate in setColumnsLocked:
            self.learning_rate = _rng_Consumed
        
        _rng_Consumed = int(_rng.integers(-20, 20))
        _rng_Consumed2 = int(_rng.integers(_rng_Consumed + 1, 20, endpoint=True))
        if not XOR_Slice.ColumnsMap.minRange in setColumnsLocked:
            self.minRange = _rng_Consumed
            self.maxRange = _rng_Consumed2

        _rng_Consumed = str(_rng.choice(list(FunctionsListsByType.HiddenLayer.keys())))
        if not XOR_Slice.ColumnsMap.activation1 in setColumnsLocked:
            self.activation1: str = _rng_Consumed

        _rng_Consumed = str(_rng.choice(list(FunctionsListsByType.OutputLayer.keys())))
        if not XOR_Slice.ColumnsMap.activation2 in setColumnsLocked:
            self.activation2: str = _rng_Consumed
        
        _rng_Consumed = str(_rng.choice(list(FunctionsListsByType.LossFunction.keys())))
        if not XOR_Slice.ColumnsMap.loss in setColumnsLocked:
            self.loss: str = _rng_Consumed

        if self.index == 0:
            # Only for the first slice => random generating also percentages and w1 and w2 !

            # pCent = 100
            # lstPc = []
            # for i in range(3):
            #     it_pc = np.random.randint(pCent)
            #     lstPc.append(it_pc)
            #     pCent -= it_pc
            arrPc = (_rng.dirichlet((1, 1, 1, 1)) * 100).astype(int) # 4 values sum 100 (dirichlet(1, 1, 1, 1) is really uniform)
            arrPc[-1] = (100 - sum(arrPc[0: -1]))
            self.xPercents = arrPc

            self.yParam = Y_XOR_TRUE_4 # however, propose the real values for the first slice, but can be changed by the user

            self.xHits = np.array([0] * 4)

            # generate random values in a specified range for w1, w2 , 'cause we are in the first slice
            # However, keep the values for the possible locked by user cells!
            self.w1 = self.w1 * self.w1_lock + _rng.uniform(self.minRange, self.maxRange, (3, 2)) * (1 - self.w1_lock)

            self.w2 = self.w2 * self.w2_lock + _rng.uniform(self.minRange, self.maxRange, (3, 1)) * (1 - self.w2_lock)

        else:
            # crt index >0 => keep existent values, possibly changed in UI by the user
            # but (re :D)check clip :
            np.copyto(self.w1, self.w1.clip(self.minRange, self.maxRange))
            np.copyto(self.w2, self.w2.clip(self.minRange, self.maxRange))
        # end if self.index == 0        
            
        # Now compute : z a loss
        self.compute_z_a_loss()
    # end feedFromSeed


    def compute_z_a_loss(self):
        """ Compute z1, a1, z2, y=a2, loss 
        in point x = X_BATCH_4 
        and yParam = self.yParam NOT necessarily equal to Y_XOR_TRUE_4 !
        remember : both have exactly 4 rows, 1 column
        """
        
        x = X_BATCH_4
        yParam = self.yParam  # NOT necessarily equal to Y_XOR_TRUE_4 !
        
        x = np.hstack((x, np.ones((x.shape[0], 1)))) # append ones corresponding to bias 
        
        self.z1[:] = x @ self.w1
        self.a1[:] = FunctionsListsByType.HiddenLayer[self.activation1](self.z1).value() # activation1(z1) of hidden layer
        
        a1 = np.hstack((self.a1, np.ones((x.shape[0], 1)))) # add ones for bias
        
        self.z2[:] = a1 @ self.w2
        self.y_aka_a2[:] = FunctionsListsByType.OutputLayer[self.activation2](self.z2).value() # activation2(z2) of output layer
        
        self.lossPerX[:] = FunctionsListsByType.LossFunction[self.loss](
                self.y_aka_a2.reshape(x.shape[0]), yParam.reshape(x.shape[0])
                ).value().reshape(4, 1) # calling value() : will calculate the loss for each of the 4 possible inputs
        
        self.lossAvg[:] = FunctionsListsByType.LossFunction[self.loss](
                self.y_aka_a2.reshape(x.shape[0]), yParam.reshape(x.shape[0])
                ).cost().reshape(1, 1)  # calling cost() : will calculate the average loss 
    # end compute_z_a_loss


    def clip(self):
        """ Clip the values of w1, w2 to the range [minRange, maxRange]"""
        for attr in vars(self):
            if isinstance(getattr(self, attr), np.ndarray):
                setattr(self, attr, np.clip(
                    getattr(self, attr), self.minRange, self.maxRange))


    def clone(self):
        """ Return a new XOR_Slice with the same values as the current one """
        newSlice = XOR_Slice(-1)
        newSlice.__dict__ = dict(self.__dict__)
        for attr in newSlice.__dict__.keys():
            if isinstance(getattr(newSlice, attr), np.ndarray):
                setattr(newSlice, attr, np.copy(getattr(self, attr)))         
        return newSlice

    def __eq__(self, other: "XOR_Slice") -> bool:
        # I was thinking to use it to establish when the Fill Button from Control Panel can be active
        return (
            self.index == other.index and
            (self.xPercents == other.xPercents).all() and
            (self.yParam == other.yParam).all() and
            self.epoch_size == other.epoch_size and
            self.batch_size == other.batch_size and
            self.learning_rate == other.learning_rate and
            (self.w1 == other.w1).all() and
            (self.w1_lock == other.w1_lock).all() and
            self.activation1 == other.activation1 and
            (self.w2 == other.w2).all() and
            (self.w2_lock == other.w2_lock).all() and
            self.activation2 == other.activation2 and
            self.loss == other.loss and
            self.minRange == other.minRange and
            self.maxRange == other.maxRange and
            self.cyclesPerOneStepFwdOfEpoch == other.cyclesPerOneStepFwdOfEpoch
        )


    @staticmethod
    def getHTML_TP_equal_mark(val:int) -> str:
        """ 
        Return a string with the value of the TP 
        MUST be used to correctly update the TP HTML diff after 'Before Delete'
        """
        return f"TP = {val}"


    @staticmethod
    def diff(slice1: "XOR_Slice", slice2: "XOR_Slice | None" = None ) -> str:
        """ html string <br> separated with differences between 2 XOR_Slice"""
        
        strDiff = "<span style='color: #0000DD; text-decoration: underline;'> <b>" 
        strDiff += XOR_Slice.getHTML_TP_equal_mark(slice1.index) 
        strDiff += "</b> </span> <br>"

        lstDiff = []
        if slice2 :
            lstDiff += ['· % distribution'] if (slice1.xPercents.round(3) != slice2.xPercents.round(3)).any() else []

            lstDiff += ["· '=' yTrue"] if (slice1.yParam.round(3) != slice2.yParam.round(3)).any() else []

            lstDiff += ['· W1 weights'] if (slice1.w1[0:2, :].round(3) != slice2.w1[0:2, :].round(3)).any() else []

            lstDiff += ['· W1 lock'] if (slice1.w1_lock[0:2, :].round(3) != slice2.w1_lock[0:2, :].round(3)).any() else []

            lstDiff += ['· bias 1'] if (slice1.w1[2, :].round(3) != slice2.w1[2, :].round(3)).any() else []

            lstDiff += ['· bias 1 lock'] if (slice1.w1_lock[2, :].round(3) != slice2.w1_lock[2, :].round(3)).any() else []

            lstDiff += ['· Activation 1(hidden)'] if (slice1.activation1 != slice2.activation1) else []

            lstDiff += ['· W2 weights'] if (slice1.w2[0:2, :].round(3) != slice2.w2[0:2, :].round(3)).any() else []

            lstDiff += ['· W2 lock'] if (slice1.w2_lock[0:2, :].round(3) != slice2.w2_lock[0:2, :].round(3)).any() else []

            lstDiff += ['· bias 2'] if (slice1.w2[2, :].round(3) != slice2.w2[2, :].round(3)).any() else []

            lstDiff += ['· bias 2 lock'] if (slice1.w2_lock[2, :].round(3) != slice2.w2_lock[2, :].round(3)).any() else []

            lstDiff += ['· Activation 2(output)'] if (slice1.activation2 != slice2.activation2) else []

            lstDiff += ['· Loss'] if (slice1.loss != slice2.loss) else []

            lstDiff += ['· Batch size'] if (slice1.batch_size != slice2.batch_size) else []

            lstDiff += ['· Epoch size'] if (slice1.epoch_size != slice2.epoch_size) else []

            lstDiff += ['· Cycles / Epoch'] if (slice1.cyclesPerOneStepFwdOfEpoch != slice2.cyclesPerOneStepFwdOfEpoch) else []

            lstDiff += ['· Learning Rate'] if (round(slice1.learning_rate, 3) != round(slice2.learning_rate, 3)) else []

            lstDiff += ['· Clip values'] if (slice1.minRange != slice2.minRange or slice1.maxRange != slice2.maxRange) else []
        # end if slice2 :

        if len(lstDiff) > 0:
            strDiff += "<span style='color: #800199; font-size: 10pt'> Changes: <br>"
            strDiff += "<br>".join(lstDiff)
            strDiff += "</span>"
            strDiff += "<br> "
        else:
            strDiff += "· No changes <br>" if slice2 else ""

        return strDiff
    # end diff static method

    def toJson(self):
        """ Return a json object with the values of the current XOR_Slice"""
        json_object = {}
        json_object["index"] = self.index
        json_object["seedTP"] = self.seedTP
        json_object["batch_size"] = self.batch_size
        json_object["epoch_size"] = self.epoch_size
        json_object["cyclesPerOneStepFwdOfEpoch"] = self.cyclesPerOneStepFwdOfEpoch
        json_object["learning_rate"] = self.learning_rate
        json_object["minRange"] = self.minRange
        json_object["maxRange"] = self.maxRange

        json_object["yParam"] = self.yParam.tolist()
        json_object["xPercents"] = self.xPercents.tolist()
        json_object["w1"] = self.w1.tolist()
        json_object["w1_lock"] = self.w1_lock.tolist()
        json_object["activation1"] = self.activation1
        json_object["w2"] = self.w2.tolist()
        json_object["w2_lock"] = self.w2_lock.tolist()
        json_object["activation2"] = self.activation2
        json_object["loss"] = self.loss
        return json_object
    # end toJson method


    def fromJson(self, json_object) -> bool:
        """ Set the values of the current XOR_Slice from a json object
            raised errors must be catched in the caller method
        """
        self.index = int(json_object["index"])
        self.seedTP = int(json_object["seedTP"])
        self.batch_size = int(json_object["batch_size"])
        self.epoch_size = int(json_object["epoch_size"])
        self.cyclesPerOneStepFwdOfEpoch = int(json_object["cyclesPerOneStepFwdOfEpoch"])
        self.learning_rate = float(json_object["learning_rate"])
        self.minRange = int(json_object["minRange"])
        self.maxRange = int(json_object["maxRange"])

        self.yParam = np.asarray(json_object["yParam"], dtype=np.int64).reshape(4, 1)
        self.xPercents = np.asarray(json_object["xPercents"], dtype=np.int64).reshape(4)
        self.w1 = np.asarray(json_object["w1"], dtype=np.float64).reshape(3, 2)
        self.w1_lock = np.asarray(json_object["w1_lock"], dtype=np.int64).reshape(3, 2)

        _tmp_str = json_object.get("activation1", "")
        if _tmp_str not in FunctionsListsByType.HiddenLayer:
            # print(f'{_tmp_str} not defined resetting to ', end='')
            # _tmp_str = list(FunctionsListsByType.HiddenLayer)[0]
            # print(f'{_tmp_str}')
            print(f'Warning!\n   hidden activation function {_tmp_str} not defined, resetting to', 
                  _tmp_str := list(FunctionsListsByType.HiddenLayer)[0]
                  )
        self.activation1 = _tmp_str

        self.w2 = np.asarray(json_object["w2"], dtype=np.float64).reshape(3, 1)
        self.w2_lock = np.asarray(json_object["w2_lock"], dtype=np.int64).reshape(3, 1)

        _tmp_str = json_object.get("activation2", "")
        if _tmp_str not in FunctionsListsByType.OutputLayer:
            print(f'Warning!\n   Output activation function {_tmp_str} not defined, resetting to', 
                  _tmp_str := list(FunctionsListsByType.HiddenLayer)[0]
                  )
        self.activation2 = _tmp_str

        _tmp_str = json_object.get("loss", "")
        if _tmp_str not in FunctionsListsByType.LossFunction:
            print(f'Warning!\n   Loss function {_tmp_str} not defined, resetting to',
                   _tmp_str := list(FunctionsListsByType.LossFunction)[0]
                   )
        self.loss = _tmp_str

        return True
    # end fromJson method

# end class XOR_Slice

class TPModel(QAbstractTableModel):
    """ Turning Point Model for QDataWidgetMapper
    NOTE: We keep only 1 row in the model corresponding to the current slice
    """
    sigTPSeedChanged = Signal()  # emitted for refreshing WxPanels ...

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.__tp = XOR_Slice(-1) # the unique pointer for the current slice, not changed anymore

    def setTPData(self, tp: XOR_Slice):
        # needed for min-max range changes =>  re-clip w1, w2  from the original values
        self._Crt_ORIGINAL_Slice = tp.clone()

        # clone infos keep the same pointer
        self.__tp.__dict__ = dict(tp.clone().__dict__)

    def getTP(self) -> XOR_Slice:
        return self.__tp

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.DisplayRole) -> bool:
        name_attr = XOR_Slice.ColumnsMap(index.column()).name
        item = self.__tp
        # NOTE: int attributes bound via QDataWidgetMapper to a comboBox, will receive str value not int ...
        old_value = item.__getattribute__(name_attr)
        _type = type(old_value)
        if index.column() in (XOR_Slice.ColumnsMap.minRange, XOR_Slice.ColumnsMap.maxRange):
            item.__setattr__(name_attr, _type(value))
            # re-clip w1, w2  from the original values
            np.copyto(self.__tp.w1, self._Crt_ORIGINAL_Slice.w1.clip(self.__tp.minRange, self.__tp.maxRange))
            np.copyto(self.__tp.w2, self._Crt_ORIGINAL_Slice.w2.clip(self.__tp.minRange, self.__tp.maxRange))
            
            self.dataChanged.emit(self.createIndex(index.row(), index.column()),
                                  self.createIndex(index.row(), index.column()), 
                                  Qt.DisplayRole
                                  )
            return True
        elif old_value == _type(value):
            # print("SAME VALUES->>>> setData : ", name_attr, type(value), value, _type, _type(value))
            return False

        item.__setattr__(name_attr, _type(value))
        self.dataChanged.emit(self.createIndex(index.row(), index.column()), 
                              self.createIndex(index.row(), index.column()), 
                              Qt.DisplayRole
                              )
        return True
    # end setData

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.EditRole or role == Qt.DisplayRole:
            name_attr = XOR_Slice.ColumnsMap(index.column()).name
            value = self.__tp.__getattribute__(name_attr)
            return value
        else:
            return None

    def rowCount(self, parent=QModelIndex()):
        return 1 # only one slice


    def columnCount(self, parent=QModelIndex()):
        # return len(TurningPoint.ColumnsMap)
        # NOTE: big mistake! no error but data NOT called when col < columnCount ...:|
        return max(XOR_Slice.ColumnsMap) + 1


    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable

# end class TPModel


class XOR_array_model:
    """ Model for XOR training process keeping all the arrays (weights, a1, z1 ...) \n
    All arrays are 3 dimensional, and first dimension is the epoch size 
    """
    def __init__(self) -> None:
        """ all arrays are 3 dimensional, and first dimension is the epoch size 
        here just init with epoch size = 1 """
        self.xHits = np.zeros(shape=(1, 4)) # hits array for each possible input 0, 1, 2, 3 
                                            # conveniently corresponding to 00, 01, 10, 11

        self.w1 = np.zeros(shape=(1, 3, 2))  # 3-th row is bias...
        self.z1 = np.zeros(shape=(1, 4, 2)) # ...
        self.a1 = np.zeros(shape=(1, 4, 2))
        self.w2 = np.zeros(shape=(1, 3, 1))
        self.z2 = np.zeros(shape=(1, 4, 1))
        self.y_aka_a2 = np.zeros(shape=(1, 4, 1))
        self.lossPerX = np.zeros(shape=(1, 4, 1))
        self.lossAvg = np.zeros(shape=(1, 1, 1))
        _self_vars_names = set(vars(self))
        _XORslice_vars_names = set(c.name for c in XOR_Slice.ColumnsMap)
    
        # check if all attributes are in XOR_Slice.ColumnsMap
        assert _self_vars_names.issubset(_XORslice_vars_names), (f"{self.__class__} - XOR_SLice.ColumnsMap: " + 
                                                                 f"{_self_vars_names - _XORslice_vars_names}")

    # end __init__


    def fillModel(self, fromTP: XOR_Slice, progressBar: TitledProgressBar | None = None):
        """ Fill the model with the training process based on the XOR_Slice"""
        # if fromTP.index == 0, initialize the rng with exactly the seed from fromTP, 
        # otherwise add the seed to the index to avoid repeating the same random numbers(and therefore the distribution) into the next epoch
        
        # print("fillModel fromTP.index:", fromTP.index)
        rng = np.random.default_rng( fromTP.index + (fromTP.seedTP if fromTP.seedTP >= 0 else 0))
        epoch_size = fromTP.epoch_size

        # self.xHits = np.zeros(shape=(epoch_size, 4)) # Not Ok, implicitly float64, not what I want
        # self.xHits = np.full(shape=(epoch_size, 4), fill_value=0) # ok fill with 0, np.int32, 
        # and even better set explicitly the type to np.int32:
        self.xHits = np.zeros(shape=(epoch_size, 4), dtype=np.int32) 

        self.w1 = np.zeros(shape=(epoch_size, 3, 2))
        self.w1[0] = fromTP.w1.clip(fromTP.minRange, fromTP.maxRange) # fromTP but clipped
        self.z1 = np.zeros(shape=(epoch_size, 4, 2))
        self.a1 = np.zeros(shape=(epoch_size, 4, 2))
        self.w2 = np.zeros(shape=(epoch_size, 3, 1))
        self.w2[0] = fromTP.w2.clip(fromTP.minRange, fromTP.maxRange) # fromTP but clipped
        self.z2 = np.zeros(shape=(epoch_size, 4, 1))
        self.y_aka_a2 = np.zeros(shape=(epoch_size, 4, 1))
        self.lossPerX = np.zeros(shape=(epoch_size, 4, 1))
        self.lossAvg = np.zeros(shape=(epoch_size, 1, 1))

        learning_rate = fromTP.learning_rate

        # distribution of 4 possible inputs
        p_distribution = (fromTP.xPercents / 100)
        p_distribution[-1] = 1 - sum(p_distribution[0: -1]) # last one is 1 - sum of the others

        # training process
        for i in range(1, epoch_size):
            xHitsPerCycle = np.copy(self.xHits[i-1]) # copy the hits from the previous slice
            w1 = np.copy(self.w1[i - 1]) # copy the weights from the previous slice
            w2 = np.copy(self.w2[i - 1]) 
            # 1 epoch = 1 x {self.cyclesPerOneStepFwdOfEpoch} cycles(forward and backward propagation)
            for _ in range(fromTP.cyclesPerOneStepFwdOfEpoch):
                # random picks {fromTP.batch_size} samples from 0, 1, 2, 3 with corresponding p_distribution probability
                hits = rng.choice([0, 1, 2, 3], fromTP.batch_size, p=p_distribution)
                (ix, nbHits) = np.unique(hits, return_counts=True)
                xHitsPerCycle[ix] += nbHits # update hits for each unique values (0, 1, 2, 3), ix act as a mask (list of indexes)
                x = X_BATCH_4[hits] # make x from hits, hits act as a mask
                y_true = fromTP.yParam[hits] # make y_true from hits
                
                computed_a1, computed_a2 = XOR_forward_prop(x, 
                                          w1, FunctionsListsByType.HiddenLayer[fromTP.activation1], 
                                          w2, FunctionsListsByType.OutputLayer[fromTP.activation2]
                                          )

                dw1, dw2 = XOR_back_prop(x,
                                         FunctionsListsByType.HiddenLayer[fromTP.activation1], computed_a1,
                                         w2, FunctionsListsByType.OutputLayer[fromTP.activation2], computed_a2,
                                         y_true, FunctionsListsByType.LossFunction[fromTP.loss]
                                         )

                # apply learning rate, clip and Lock in one row aka "kill three birds with one stone" :D
                # w2 = ((w2 - dw2) * learning_rate).clip(fromTP.minRange, fromTP.maxRange) * (1 - fromTP.w2_lock) + w2 * fromTP.w2_lock
                # w1 = ((w1 - dw1) * learning_rate).clip(fromTP.minRange, fromTP.maxRange) * (1 - fromTP.w1_lock) + w1 * fromTP.w1_lock
                # NOTE : What a ... BUG! ... paying for three in a row :D
                # and good formulas
                w2 = (w2 - (dw2 * learning_rate)).clip(fromTP.minRange, fromTP.maxRange) * (1 - fromTP.w2_lock) + w2 * fromTP.w2_lock
                w1 = (w1 - (dw1 * learning_rate)).clip(fromTP.minRange, fromTP.maxRange) * (1 - fromTP.w1_lock) + w1 * fromTP.w1_lock

                self.xHits[i] = xHitsPerCycle
            # end for cyclesPerOneStepFwdOfEpoch

            self.w2[i] = w2
            self.w1[i] = w1

            if progressBar:
                progressBar.setValue(i) # update the progress bar
        
        # end for filling the arrays for the epoch
                
        # Now for X_BATCH_4,  bulk calculate the arrays: {self.z}, {self.a}, lossPerX and lossAvg
        x = X_BATCH_4
        x = np.hstack((x, np.ones((x.shape[0], 1)))) # append ones corresponding to bias, well x.shape[0] = 4
        
        self.z1 = x @ self.w1 # calculate z1
        self.a1 = FunctionsListsByType.HiddenLayer[fromTP.activation1]( self.z1).value() # calculate a1
        
        computed_a1 = np.ones((epoch_size, x.shape[0], 3)) # 3 columns for a1, 4 rows for each epoch
        computed_a1[..., 0:2] = self.a1 # fill the first 2 columns with {self.a1}, the third column is for bias, keep it == 1
        
        self.z2 = computed_a1 @ self.w2 # calculate z2
        self.y_aka_a2 = FunctionsListsByType.OutputLayer[fromTP.activation2](self.z2).value() # calculate a2

        fLoss = FunctionsListsByType.LossFunction[fromTP.loss] # get the loss function

        # bulk calculate lossPerX calling value() 
        # here self.y_aka_a2.shape = (epoch_size, 4, 1) and fromTP.yParam.shape = (4, 1)
        self.lossPerX = fLoss(self.y_aka_a2, fromTP.yParam).value()

        # then bulk calculate lossAvg calling cost() 
        # here we need to reshape self.y_aka_a2 and fromTP.yParam to (epoch_size, 4) and (4) respectively 
                # to correctly calculate the average loss 
        # and the result back to (epoch_size, 1, 1) ... all slice arrays are 2 dimensional arrays
        self.lossAvg = fLoss(self.y_aka_a2.reshape(epoch_size, x.shape[0]), fromTP.yParam.reshape(4)).cost().reshape(epoch_size, 1, 1) 

    # end fillModel method                

    def count(self, ) -> int:
        return len(self.w1)

    def deleteBefore(self, ix: int):
        """ keep pos=ix, delete previously. New arrays! """
        ix = min(max(0, ix), self.count() - 1)
        xHitsOnPos = self.xHits[ix]
        self.xHits = self.xHits[ix:] - xHitsOnPos
        self.w1 = self.w1[ix:]
        self.z1 = self.z1[ix:]
        self.a1 = self.a1[ix:]
        self.w2 = self.w2[ix:]
        self.z2 = self.z2[ix:]
        self.y_aka_a2 = self.y_aka_a2[ix:]
        self.lossPerX = self.lossPerX[ix:]
        self.lossAvg = self.lossAvg[ix:]

    def deleteAfter(self, ix: int) -> int:
        """ try to keep pos=ix, delete afterward, 
        nevertheless ix could be -1, then delete all \n
        return nb deleted. New arrays !
        """
        assert -1 <= ix <= self.count() - 1, f" -1 <= {ix} <= {self.count()}"
        iret = self.count() - ix - 1
        new_len = ix + 1
        # self.xHits =  np.resize(self.xHits, (new_len, 4))
        self.xHits = self.xHits[:new_len]
        self.w1 = self.w1[:new_len]
        self.z1 = self.z1[:new_len]
        self.a1 = self.a1[:new_len]
        self.w2 = self.w2[:new_len]
        self.z2 = self.z2[:new_len]
        self.y_aka_a2 = self.y_aka_a2[:new_len]
        self.lossPerX = self.lossPerX[:new_len]
        self.lossAvg = self.lossAvg[:new_len]
        return iret

    def append(self, newArray: "XOR_array_model"):
        """ Append newArray to the current one. Creating new arrays !"""
        if self.xHits.size > 0:
            # if we already have some data need to add + self.xHits[-1] to new generated hits
            self.xHits = np.vstack((self.xHits, newArray.xHits + self.xHits[-1]))
        else:
            # create new arrays
            self.xHits = np.copy(newArray.xHits)

        self.w1 = np.vstack((self.w1, newArray.w1))
        self.z1 = np.vstack((self.z1, newArray.z1))
        self.a1 = np.vstack((self.a1, newArray.a1))
        self.w2 = np.vstack((self.w2, newArray.w2))
        self.z2 = np.vstack((self.z2, newArray.z2))
        self.y_aka_a2 = np.vstack((self.y_aka_a2, newArray.y_aka_a2))
        self.lossPerX = np.vstack((self.lossPerX, newArray.lossPerX))
        self.lossAvg = np.vstack((self.lossAvg, newArray.lossAvg))


    # def clone(self) -> Self:
    def clone(self) -> "XOR_array_model":
        """ Return a new XOR_array_model with the same values as the current one 
        used for duplicate the model (from mainWnd, Ctrl + D) """
        newArray = XOR_array_model()
        newArray.__dict__ = dict(self.__dict__)
        for attr in newArray.__dict__.keys():
            # if type(getattr(newArray, attr)) == np.ndarray:
            if isinstance(getattr(newArray, attr), np.ndarray):
                setattr(newArray, attr, np.copy(getattr(self, attr)))                
        return newArray
    
# end class XOR_array_model


class XOR_model(QObject):
    """ 
    XOR model, contains the XOR_array_model and the list of Turning Points
    """
    sigModelChanged = Signal(int)  # Signal(CrtPos)
    "signaling that the Model was changed during delete or append(filling)"
    
    sigModelNameChanged = Signal(str)  # Signal(newName)
    "signaling that the Model Name was changed during save"
    
    wdgMainWindow: QWidget | None = None # used for TitleProgressBar in modal mode 
    "UI main window, used for displaying a TitleProgressBar"

# region init
    @overload
    def __init__(self, arg: int) -> None: ...
    @overload
    def __init__(self, arg: XOR_Slice) -> None: ...

    def __init__(self, arg: Optional[Any]) -> None:
        super().__init__()
        self.modelName = "Model 1"
        self.lstTurningPoints: List[XOR_Slice] = []
        """ list of Turning Points always contains TP[0].index == 0 """

        self.lstTurningPointsDiff: List[str] = ['']
        """ list of Differences between Turning Points \n
        always lstTurningPointsDiff[0] == '' """

        self.lst_TP_Final_Loss: List[str] = []
        """ list of TP epoch Loss, str formatted 0.3f"""

        self.__crtTPModel: TPModel = TPModel() # TPModel of TP corresponding to current slice
        self.__crtSlice = self.__crtTPModel.getTP() # pointer to the current slice, always the same pointer 
        
        self.maskParamLocks = 0 
        """mask for locks of TP parameters in Control Panel, TP Params Tab"""

        self.lastSavedFileInfo: QFileInfo | None = None

        if arg is None:
            # value to seed random generator for futures reproducibility
            arg = np.random.randint(65535) # NOTE: on the top of the module we initialize the random generator with a determined seed
        
        # creating the first TP
        if type(arg) is int:
            seedTP = XOR_Slice(arg)
        else:
            # type(arg) is XOR_Slice:
            seedTP = arg

        seedTP.index = 0
        self.xor_array = XOR_array_model()

        self.lstTurningPoints.append(seedTP)
        self.indexOfCrtBaseTP_in_lstTurningPoints = 0  # index in {self.lstTurningPoints}

        self.fillModelFromTP(seedTP)

        # self.destroyed.connect(lambda obj: print("destroyed : ", id(obj)))

# endregion init


    def getCrtTPModel(self) -> TPModel:
        return self.__crtTPModel

    def getCrtSlice(self) -> XOR_Slice:
        return self.__crtSlice

    def setPos(self, ix: int):
        """ set self.crtTPModel with infos from TP and array """
        if ix >= self.count():
            ix = self.count() - 1
        # get the corresponding TP (aka max(indexTP <= ix))
        # for i in range(len(self.lstTurningPoints) - 1, -1, -1):
        for item in reversed(self.lstTurningPoints):
            if item.index <= ix:
                # getting infos from base TP ( batch epoch etc)
                self.indexOfCrtBaseTP_in_lstTurningPoints = self.lstTurningPoints.index(item)
                baseTP = item.clone()
                # NOTE: completing with array infos
                baseTP.index = ix
                baseTP.xHits = self.xor_array.xHits[ix]
                baseTP.w1 = self.xor_array.w1[ix]
                baseTP.z1 = self.xor_array.z1[ix]
                baseTP.a1 = self.xor_array.a1[ix]
                baseTP.w2 = self.xor_array.w2[ix]
                baseTP.z2 = self.xor_array.z2[ix]
                baseTP.y_aka_a2 = self.xor_array.y_aka_a2[ix]
                baseTP.lossAvg = self.xor_array.lossAvg[ix]
                baseTP.lossPerX = self.xor_array.lossPerX[ix]

                self.__crtTPModel.setTPData(baseTP)
                # NOTE: self.__crtSlice it's already a pointer to self.__crtTPModel.__tp
                # and breaking the loop
                break
        # and that's all 
        return
    # end setPos method

    def getPos(self):
        return self.__crtSlice.index

    def count(self) -> int:
        return self.xor_array.count()

    def deleteBefore(self, ix: int):
        # if I put some indications here, you will take them as good and you will never notice that
        # .. some text is missing :D
        ix = min(max(0, ix), self.count() - 1)
        self.xor_array.deleteBefore(ix)
        tp_ix = 0
        for i in range(len(self.lstTurningPoints)):
            tp = self.lstTurningPoints[i]
            if tp.index <= ix:
                tp_ix = i
            else:
                break
        # cut the lists
        self.lstTurningPoints = self.lstTurningPoints[tp_ix:]
        self.lstTurningPointsDiff = self.lstTurningPointsDiff[tp_ix:] # here just cut the list !!!
        self.lst_TP_Final_Loss = self.lst_TP_Final_Loss[tp_ix:]
        
        # update the indexes AND the TP diff List[str] ..
        for i, tp in enumerate(self.lstTurningPoints):
            # get the rest of Diffs
            lstSplitDiff = self.lstTurningPointsDiff[i].split(XOR_Slice.getHTML_TP_equal_mark(tp.index))
            # NOW update the index of TP
            tp.index -= ix 
            # AND NOW update the diff with the new index
            new_strDiff = XOR_Slice.getHTML_TP_equal_mark(tp.index).join(lstSplitDiff)
            self.lstTurningPointsDiff[i] = new_strDiff
        
        # first TP must be updated
        self.lstTurningPoints[0].index = 0 # TP[0].index always == 0

        # and the epoch size for the first TP
        if len(self.lstTurningPoints) == 1:
            self.lstTurningPoints[0].epoch_size = self.count()
        else:
            self.lstTurningPoints[0].epoch_size = self.lstTurningPoints[1].index
        
        # actually totally reset the diff for the new [0]
        self.lstTurningPointsDiff[0] = XOR_Slice.diff(self.lstTurningPoints[0], None) 
        self.lstTurningPointsDiff[0] += self.getHTML_loss( float(self.xor_array.lossAvg[self.lstTurningPoints[0].epoch_size - 1]) )

        self.setPos(0)
        self.sigModelChanged.emit(0)
    # end deleteBefore method

    def deleteAfterPos(self, ix: int) -> int:
        """ delete after [ix, ix included IF ix > 0
        return nb deleted """
        if ix > 0:
            ix = ix - 1 # positioning on a TP will delete the TP also (IF not first TP)
        iret = self.xor_array.deleteAfter(ix)
        while self.lstTurningPoints[-1].index > ix:
            self.lstTurningPoints.pop()
            self.lstTurningPointsDiff.pop()
            self.lst_TP_Final_Loss.pop()

        # last one must be updated (IF first TP dont update epoch size for Fill
        if ix > 0:
            self.lstTurningPoints[-1].epoch_size = self.count() - self.lstTurningPoints[-1].index

        self.lst_TP_Final_Loss[-1] = f"{float(self.xor_array.lossAvg[-1]):0.3f}"
        self.setPos(ix)
        self.sigModelChanged.emit(ix)
        return iret  
    # end deleteAfterPos method

    def fillModelFromTP(self, newTP: XOR_Slice, outer_progressBar: TitledProgressBar | None = None):
        """ delete after {newTP.indexTP} and append new generating model """

        newTP = newTP.clone()  # just in case ...

        assert self.xor_array.count() >= newTP.index, f"{self.xor_array.count()=} must be >= {newTP.index=}"

        while self.lstTurningPoints[-1].index > newTP.index:
            self.lstTurningPoints.pop()
            self.lstTurningPointsDiff.pop()
            self.lst_TP_Final_Loss.pop()

        bNewTP_is_In_list = (newTP.index == self.lstTurningPoints[-1].index)
        if not bNewTP_is_In_list:
            self.blockSignals(True)
            self.xor_array.deleteAfter(newTP.index) # delete after newTP.index but keep original values on ix, to identify the changes later
            self.blockSignals(False)
            newTP.index += 1 # keep original values on ix, to identify the changes later
            # adjust last TP epoch_size
            self.lstTurningPoints[-1].epoch_size = self.xor_array.count() - self.lstTurningPoints[-1].index
        else:
            self.blockSignals(True)
            self.xor_array.deleteAfter(newTP.index - 1) # newTP.index - 1 keep it as is, fill from newTP.index
            self.blockSignals(False)
            self.lstTurningPoints.pop() # remove-it, will be created again later

        newArray = XOR_array_model()

        progressBar = outer_progressBar
        if XOR_model.wdgMainWindow:
            # for showing TitleProgressBar in modal mode (but with gApp.processEvents())
            if not progressBar:
                # it might already exist, from LoadFromJson 
                # if not, but we have a main window, we create it here
                lbl = QLabel(f"Filling model (epoch={newTP.epoch_size} x cycles={newTP.cyclesPerOneStepFwdOfEpoch})")
                lbl.setContentsMargins(10, 2, 0, 2)
                progressBar = TitledProgressBar(lbl, XOR_model.wdgMainWindow)
                progressBar.setMax_prefixValue(newTP.epoch_size)
                progressBar.setObjectName("progressBar")
                progressBar.setStyleSheet(
                    "TitledProgressBar#progressBar { background-color: #c0fcc0; border: 2px solid #6da86d } "
                    )
            
            progressBar.show()
        # end if XOR_model.wdgMainWindow
        
        # fill the new array
        newArray.fillModel(newTP, progressBar)

        if not outer_progressBar and progressBar: # short-circuit
            # closing here, because it was created here
            progressBar.close()
        # otherwise it will be closed by outer_progressBar


        # cut the possible others lists based on {self.lstTurningPoints}
        self.lstTurningPointsDiff = self.lstTurningPointsDiff[0: len(self.lstTurningPoints)]
        self.lst_TP_Final_Loss = self.lst_TP_Final_Loss[0: len(self.lstTurningPoints)]

        # set the String of differences between the last TP and the new one
        strDiff = ""
        if len(self.lstTurningPoints) > 0:
            lastTP = self.lstTurningPoints[-1].clone()
            # get last slice w1 and w2 from xor_array, possibly changed in UI => newTP
            lastTP.w1 = self.xor_array.w1[-1]
            lastTP.w2 = self.xor_array.w2[-1]
            strDiff += XOR_Slice.diff(newTP, lastTP)
        else:
            strDiff += XOR_Slice.diff(newTP, None)

        val_NewArrayLastLoss = float(newArray.lossAvg[-1])
        str_Last_Loss = self.getHTML_loss(val_NewArrayLastLoss)
        strDiff += str_Last_Loss

        # append the  infos to the lists
        self.xor_array.append(newArray)
        self.lstTurningPointsDiff.append(strDiff)
        self.lstTurningPoints.append(newTP)
        self.lst_TP_Final_Loss.append(f"{val_NewArrayLastLoss:0.3f}")

        if globalParameters.StayOnPosOnFillModel:
            ix = newTP.index # stay
        else:
            ix = self.xor_array.count() - 1 # go to the end
        self.setPos(ix)

        self.sigModelChanged.emit(ix)
        return
    # end fillModelFromTP method

    def clone(self):
        baseTP = self.lstTurningPoints[0].clone()
        baseTP.epoch_size = 1
        new_model = XOR_model(baseTP) # create a new model with the same base TP
        new_model.xor_array = self.xor_array.clone()
        if self.lastSavedFileInfo:
            new_model.lastSavedFileInfo = QFileInfo(self.lastSavedFileInfo)

        # and copy the lists
        new_model.lstTurningPoints = [tp.clone() for tp in self.lstTurningPoints]
        new_model.lstTurningPointsDiff = self.lstTurningPointsDiff.copy()
        new_model.lst_TP_Final_Loss = self.lst_TP_Final_Loss.copy()
        new_model.maskParamLocks = self.maskParamLocks
        new_model.setPos(0)

        return new_model
    # end clone method

    @staticmethod
    def LoadFromJson(jsonFile: str) -> "XOR_model | None":
        """ Load model from .json file """
        import json
        newXORmodel = None
        try:
            with open(jsonFile) as oFile:
                jsonObject = json.load(oFile)

                if type(jsonObject) is not dict:
                    # raise Exception('dict {"version", "TP list"} expected, not ', type(jsonObject))
                    raise InvalidJsonObjectTypeError('dict {"version", "TP list"} expected, not ', type(jsonObject))
                
                json_xor_version = jsonObject.get("version", None)
                if json_xor_version not in XOR_JSON_SUPPORTED_MODELS:
                    raise UnsupportedXORJsonVersionError(f"XOR model Json version '{json_xor_version}' unknown. \n" +  
                                                    f"Supported versions: {XOR_JSON_SUPPORTED_MODELS}")

                lst_TP_json = jsonObject["TP list"]
                lstTP: List[XOR_Slice] = []
                
                # create the list of Turning Points                
                for TP_Json_item in lst_TP_json:
                    tp = XOR_Slice(-1)
                    if not tp.fromJson(TP_Json_item): 
                        # actually it's not possible, No False returned from fromJson
                        # only possible exception raising
                        return None
                    lstTP.append(tp)

                newXORmodel = XOR_model(XOR_Slice(-1))

                lbl = QLabel()
                lbl.setContentsMargins(10, 2, 0, 2)
                maxOuter = sum(item.epoch_size for item in lstTP) # maxOuter = sum of all TPs epoch_size
                lenLst = len(lstTP)
                if lenLst > 1:
                    # min 2 TPs
                    outerProgress = TitledProgressBar(lbl, XOR_model.wdgMainWindow) 
                    outerProgress.setMax_prefixValue(maxOuter)
                else:
                    outerProgress = lbl

                sumConsumed = 0
                
                innerProgress = TitledProgressBar(outerProgress, XOR_model.wdgMainWindow)
                innerProgress.setObjectName("innerProgress")
                innerProgress.setStyleSheet(
                    "TitledProgressBar#innerProgress { background-color: #c0fcc0; border: 2px solid #6da86d } ")
                
                for ix, tp in enumerate(lstTP):
                    outerProgress.setText(
                        f"Loading & generating (epoch={tp.epoch_size} x cycles={tp.cyclesPerOneStepFwdOfEpoch})" +
                         f" TP: {ix + 1} / {lenLst}")
                    maxInner = tp.epoch_size
                    innerProgress.setMax_prefixValue(maxInner, sumConsumed)
                    if not innerProgress.isVisible():
                        innerProgress.show()
                    sumConsumed += maxInner
                    if tp.index > 0:
                        tp.index -= 1  # TODO : explain nicely why...
                        # explanation: the first TP keep its index = 0
                        # the next must be decreased by 1, to be correctly appended to the model
                        # 'cause the fillModelFromTP will do :
                        # newTP.index += 1 # keeping original values on ix, to identify the changes later

                    newXORmodel.fillModelFromTP(tp, innerProgress)
                # end for
                # closing the progress bars
                innerProgress.close()

        except Exception as ex:
            strError = f"Error loading model from:\n {jsonFile}\n ex: " + str(ex)
            print(strError) # aka logging to the console
            raise Exception(strError)
        
        return newXORmodel
    # end LoadFromJson method


    def SaveToJson(self, fileInfo: QFileInfo) -> str:
        """ Save model to .json file \n
        return "" if success otherwise return str(exception)
        """
        sRet = ""
        import json
        try:
            dictModel = {}
            dictModel["version"] = XOR_JSON_MODEL
            dictModel["TP list"] = self.lstTurningPoints
            jsonObject = json.dumps(dictModel, indent=2, default=XOR_Slice.toJson)
            
            with open(fileInfo.absoluteFilePath(), "w") as oFile:
                oFile.write(jsonObject)
        
        except Exception as ex:
            sRet = str(ex)

        if sRet == "":
            self.modelName = fileInfo.completeBaseName()
            self.lastSavedFileInfo = fileInfo
            self.sigModelNameChanged.emit(self.modelName) # signal for updating the Tab name

        return sRet

    @staticmethod
    def getHTML_loss(val_loss: float) -> str:
        """
        get an representative color for the loss (Red > 0.6 -> yellow > 0.3 -> green <= 0.3)
        """
        html_Loss = (f"<span style='font-size: 10pt; color:#0000DD;'>epoch Loss: "
                         f"<span style='background-color:#%06x;'> {val_loss:0.3f}</span>"
                         "</span>" % MxCOLORS.get_color_for_value(val_loss).__hash__()
                         )
        return html_Loss

if __name__ == '__main__':

    dummyWdg = QWidget()
    XOR_model.wdgMainWindow = dummyWdg
    
    mXor = XOR_model(7)
    print(mXor.count())
    print(id(mXor.xor_array.w1))
    mXor.xor_array.deleteAfter(7)
    print(id(mXor.xor_array.w1))
