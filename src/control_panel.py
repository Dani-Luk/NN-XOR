"""
This module contains the implementation of the control panel for the XOR neural network application.
The control panel consists of various widgets and classes used for user interaction and data manipulation.
"""
# thx copilot :D

__all__ = ['BlueHoverLabel', 'LabelLock', 'LabelLockBuddy', 'IntSpinBox', 'PercentSpinBox', 'ControlPanel']


from typing import List, Tuple

from PySide6.QtCore import (Property, QEvent, QKeyCombination, QModelIndex,
                            QObject, QPersistentModelIndex, QPoint, QRect,
                            QRegularExpression, QSize, Qt, Signal)
from PySide6.QtGui import (QCursor, QEnterEvent, QFocusEvent, QMouseEvent,
                           QPainter, QPaintEvent, QPalette,
                           QRegularExpressionValidator, QResizeEvent)
from PySide6.QtWidgets import (QCheckBox, QDataWidgetMapper, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QProxyStyle, QPushButton, QSizePolicy, QSpinBox,
                               QStyle, QStyledItemDelegate,
                               QStyleOptionViewItem, QTabWidget, QVBoxLayout,
                               QWidget)

from global_stuff import *
from core import *
from models import TPModel, XOR_model, XOR_Slice
from custom_widgets import (CommitOnChange_ComboBox, ToolTip_ComboBox,
                            ToolTip_CommitOnChange_ComboBox)


class BlueHoverLabel(QLabel):
    """
    A custom QLabel subclass that provides hover functionality with a blue background color.

    This class overrides the enterEvent and leaveEvent methods to change the style sheet
    of the label and its buddy (if available) when the mouse enters or leaves the label.

    Attributes:
        hoverBuddy (bool): Flag indicating whether the buddy widget should also change its style.
        _styleSheet (str): The original style sheet of the label.
        _buddyStyleSheet (str): The original style sheet of the buddy widget.

    Methods:
        enterEvent(event: QEnterEvent) -> None: Event handler for mouse enter event.
        leaveEvent(event: QEvent) -> None: Event handler for mouse leave event.
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.hoverBuddy = False
        self._styleSheet = self.styleSheet()
        self._buddyStyleSheet = ""

    def enterEvent(self, event: QEnterEvent) -> None:
        """
        Event handler for mouse enter event.

        Changes the style sheet of the label and its buddy (if available) to show a blue background color.

        Args:
            event (QEnterEvent): The mouse enter event.

        Returns:
            None
        """
        self._styleSheet = self.styleSheet()
        self._buddyStyleSheet = ""
        if self.buddy() and self.hoverBuddy:
            self._buddyStyleSheet = self.buddy().styleSheet()
        self.setStyleSheet(
            self._styleSheet + " \n BlueHoverLabel { background-color:rgba(230, 255, 255, 255); color:blue; }")
        if self.buddy() and self.hoverBuddy:
            self.buddy().setStyleSheet(self._buddyStyleSheet
                                       + f" \n {type(self.buddy()).__name__}"
                                       + " { background-color:rgba(230, 255, 255, 255); color:blue;}")
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.setStyleSheet(self._styleSheet)
        if self.buddy() and self.hoverBuddy:
            self.buddy().setStyleSheet(self._buddyStyleSheet)
        return super().leaveEvent(event)


class LabelLock(BlueHoverLabel):
    """
    A custom label widget with a lock icon that can be toggled on and off.

    Inherits from BlueHoverLabel.

    Signals:
        sigLockChanged(bool): Signal emitted when the lock state is changed.

    Args:
        text (str): The text to display on the label.
        bLock (bool, optional): The initial lock state. Defaults to False.
        parent (QWidget | None, optional): The parent widget. Defaults to None.
    """

    _pixmap_lock = LOCK_ICO.pixmap(QSize(12, 12))
    _pixmap_nolock = NOLOCK_ICO.pixmap(QSize(12, 12))
    sigLockChanged = Signal(bool)

    def __init__(self, text: str, bLock: bool = False, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setStyleSheet("LabelLock { padding-right: 9; }")
        self._locked = bLock
        self.setLock(self._locked)

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        super().paintEvent(arg__1)
        painter = QPainter(self)
        pixmap = self._pixmap_lock if self._locked else self._pixmap_nolock
        painter.drawPixmap(QPoint(self.width() - 12, 1), pixmap)

    def setLock(self, bLock):
        """
        Set the lock state of the label.

        Args:
            bLock (bool): The lock state to set.
        """
        if self._locked != bLock:
            self._locked = bLock
            self.repaint()
            self.sigLockChanged.emit(self._locked)

    def isLocked(self) -> bool:
        """
        Get the current lock state of the label.

        Returns:
            bool: True if the label is locked, False otherwise.
        """
        return self._locked

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        """
        Handle the mouse release event.

        Toggles the lock state of the label and emits the sigLockChanged signal.

        Args:
            ev (QMouseEvent): The mouse event.
        """
        self.setLock(not self._locked)
        return super().mouseReleaseEvent(ev)


class LabelLockBuddy(LabelLock):
    """
    A custom label widget with a lock feature and a buddy widget.

    Inherits from the LabelLock class.

    Parameters:
    - text (str): The text to display on the label.
    - objBuddy (QWidget): The buddy widget associated with the label.
    - buddyHeight (int | None): The fixed height of the buddy widget (optional).
    - bLock (bool): The initial lock state of the label (default: False).
    - parent (QWidget | None): The parent widget (optional).

    Signals:
    - sigLockChanged: Emitted when the lock state of the label changes.

    """

    def __init__(self, text: str, objBuddy: QWidget, buddyHeight: int | None = None, bLock: bool = False, parent: QWidget | None = None):
        super().__init__(text, bLock, parent)
        self.setBuddy(objBuddy)
        if buddyHeight:
            objBuddy.setFixedHeight(buddyHeight)
        self.sigLockChanged.connect(
            lambda lock: self.buddy().setEnabled(not lock))


class _ListLabelsLockBuddy(QObject):
    """
    A helper class for managing a list of LabelLockBuddy objects and their associated masks.

    Attributes:
        sigMaskChanged (Signal): A signal emitted when the mask value changes.

    Methods:
        getMask(): Returns the current mask value.
        setMask(mask): Sets the mask value and updates the LabelLockBuddy objects accordingly.
        AlterMask(pow, bit): Alters the mask value based on the given power and bit value.
        append(__object, ixColumnMap): Appends a LabelLockBuddy object to the list and updates the mask value.
        getColumnsMapLOCKED(): Returns a set of column maps that are locked based on the current mask value.
    """

    sigMaskChanged = Signal(int)

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._mask: int = 0
        self._list: List[LabelLockBuddy] = []
        self._listColumnMap: List[int] = []

    def getMask(self) -> int:
        return self._mask

    def setMask(self, mask):
        """
        Sets the mask value and updates the LabelLockBuddy objects accordingly.

        Args:
            mask: The new mask value.
        """
        self._mask = mask
        self.blockSignals(True)
        for i in range(len(self._list)):
            objItem = self._list[i]
            objItem.blockSignals(True)
            bLock = bool(self._mask & (2 ** i))
            objItem.setLock(bLock)
            objItem.buddy().setEnabled(not bLock)
            objItem.blockSignals(False)
        self.blockSignals(False)

    def AlterMask(self, pow: int, bit: bool):
        """
        Alters the mask value based on the given power and bit value.

        Args:
            pow: The power value.
            bit: The bit value.
        """
        if bit:
            self._mask |= 2 ** pow
        else:
            self._mask &= 2 ** len(self._list) - 1 - 2 ** pow
        self.sigMaskChanged.emit(self._mask)

    def append(self, _object: LabelLockBuddy, ixColumnMap: XOR_Slice.ColumnsMap) -> None:
        """
        Appends a LabelLockBuddy object to the list and updates the mask value.

        Args:
            _object: The LabelLockBuddy object to append.
            ixColumnMap: The associated column map.
        """
        self._list.append(_object)
        self._listColumnMap.append(ixColumnMap)
        pow = len(self._list) - 1
        if _object.isLocked:
            self._mask += 2 ** pow
        _object.sigLockChanged.connect(
            lambda bLock: self.AlterMask(pow, bLock))

    def getColumnsMapLOCKED(self) -> set:
        """
        Returns a set of column maps that are locked based on the current mask value.

        Returns:
            A set of locked column maps.
        """
        lockedSet = set()
        for i in range(len(self._list)):
            if self._mask & (2 ** i):
                lockedSet.add(self._listColumnMap[i])
        return lockedSet


class AlignDelegate(QStyledItemDelegate):
    """
    A delegate class for aligning items in a view.

    This delegate allows you to specify the alignment of items in a view.
    It inherits from QStyledItemDelegate and overrides the initStyleOption method
    to set the displayAlignment option based on the specified alignment.

    Args:
        alignment (Qt.Alignment): The alignment for the items in the view.
        parent (QObject | None, optional): The parent object. Defaults to None.
    """

    def __init__(self, alignment: Qt.Alignment, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.m_alignment = alignment

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> None:
        """
        Initialize the style option for the specified item.

        This method is called by the view to initialize the style option for the specified item.
        It sets the displayAlignment option based on the alignment specified in the constructor.

        Args:
            option (QStyleOptionViewItem): The style option for the item.
            index (QModelIndex | QPersistentModelIndex): The model index of the item.
        """
        super().initStyleOption(option, index)
        option.__setattr__("displayAlignment", self.m_alignment)


class AlignComboBoxProxy(QProxyStyle):
    """
    A proxy style class for aligning the text in a combo box item to the center.
    """

    def drawItemText(self, painter: QPainter, rect: QRect, flags: int, pal: QPalette, enabled: bool, text: str, textRole) -> None:
        """
        Draws the text of a combo box item with aligned center.

        Args:
            painter (QPainter): The painter object used for drawing.
            rect (QRect): The rectangle defining the item's area.
            flags (int): The flags specifying the item's state.
            pal (QPalette): The palette used for drawing.
            enabled (bool): Indicates if the item is enabled.
            text (str): The text to be drawn.
            textRole: The role of the text.

        Returns:
            None
        """
        return super().drawItemText(painter, rect, Qt.AlignCenter, pal, enabled, text, textRole)


class wdgInterval(QWidget):
    """
    A custom widget representing an interval with minimum and maximum values.

    Args:
        parent (QWidget | None): The parent widget. Defaults to None.
        mapper (QDataWidgetMapper | None): The data widget mapper. Defaults to None.
    """

    def __init__(self, parent: QWidget | None = None, mapper: QDataWidgetMapper | None = None) -> None:
        super().__init__(parent)
        self._delegate = None
        if mapper:
            self._delegate = mapper.itemDelegate()

        self._min = IntSpinBox(-20, 19)
        # self._min.setPrefix("min:")
        self._min.setFixedWidth(45)
        self._min.setValue(-20)
        self._max = IntSpinBox(-19, 20)
        # self._max.setPrefix("Max:")
        self._max.setFixedWidth(45)
        self._max.setValue(20)

        ly = QHBoxLayout()
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(1)
        ly.addWidget(self._min)
        ly.addWidget(QLabel(" - "))
        ly.addWidget(self._max)
        self.setLayout(ly)

        def _reviewMax():
            """
            Updates the maximum value and emits a commitData signal if a delegate is set.
            """
            if self._delegate:
                self._delegate.commitData.emit(self._min)
            new_val = max(self._max.value(), self._min.value() + 1)
            if self._max.value() != new_val:
                self._max.setValue(new_val)
        self._min.valueChanged.connect(_reviewMax)

        def _reviewMin():
            """
            Updates the minimum value based on the current maximum value.

            If a delegate is set, emits a commitData signal with the current maximum value.
            Calculates a new minimum value based on the current maximum value and sets it if different.
            """
            if self._delegate:
                self._delegate.commitData.emit(self._max)
            new_val = min(self._min.value(), self._max.value() - 1)
            if self._min.value() != new_val:
                self._min.setValue(new_val)
        self._max.valueChanged.connect(_reviewMin)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocusProxy(self._min)


class IntSpinBox(QSpinBox):
    """
    A custom spin box widget that allows setting button symbols on the fly.

    Inherits from QSpinBox.

    Parameters:
    - _min (int): The minimum value of the spin box. Default is 0.
    - _max (int): The maximum value of the spin box. Default is 99.
    - offset (int): The offset value used to adjust the width of the spin box when buttons are shown or hidden. Default is 0.
    - parent (QWidget | None): The parent widget of the spin box. Default is None.
    """

    def __init__(self, _min: int = 0, _max: int = 99, offset: int = 0, parent: QWidget | None = None) -> None:
        _min, _max = min(_min, _max), max(_min, _max)
        self.offset = offset
        super().__init__(parent)
        self.setRange(_min, _max)
        self.setButtonSymbols(QSpinBox.NoButtons)
        self.bButtons = False

    def enterEvent(self, event) -> None:
        self.setButtons()
        return super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setButtons()
        return super().leaveEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self.setButtons()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.setButtons()

    def setButtons(self):
        """
        Sets the buttons for the IntSpinBox based on the cursor position and focus.

        If the cursor is within the IntSpinBox's rectangle or the IntSpinBox has focus,
        the buttons are displayed. Otherwise, the buttons are hidden.

        Returns:
            None
        """
        cursorPos = QCursor.pos()
        if (self.rect().contains(self.mapFromGlobal(cursorPos)) or
                self.hasFocus()):
            if not self.bButtons:
                self.setFixedWidth(self.width() + self.offset)
                self.setButtonSymbols(QSpinBox.UpDownArrows)
                self.bButtons = True
        else:
            if self.bButtons:
                self.setFixedWidth(self.width() - self.offset)
                self.setButtonSymbols(QSpinBox.NoButtons)
                self.bButtons = False


class PercentSpinBox(IntSpinBox):
    """
    A custom spin box widget for representing percentages.

    This widget supports values from 1 to 99, representing percentages from 1% to 99%.
    However, it also supports values greater than 100, allowing percentages from 101% to 300%.
    This is useful for setting the learning rate on turbo mode. :))

    Attributes:
        _min (int): The minimum value of the spin box.
        _max (int): The maximum value of the spin box.
        parent (QWidget | None): The parent widget of the spin box.
        floatValue property (float): The float value of the spin box.
    """

    def __init__(self, _min: int = 1, _max: int = 99, parent: QWidget | None = None) -> None:
        """
        Initializes a PercentSpinBox object.

        Args:
            _min (int): The minimum value of the spin box. Defaults to 1.
            _max (int): The maximum value of the spin box. Defaults to 99.
            parent (QWidget | None): The parent widget of the spin box. Defaults to None.
        """
        _min, _max = min(_min, _max), max(_min, _max)
        assert _min >= 0, "however :D"
        super().__init__(_min, _max, offset=0, parent=parent)
        self.setSuffix("%")
        self.setMinimumWidth(45)

        def _textChanged(text):
            if self.value() >= 100:
                self.setSuffix("% 😅")
                self.setFixedWidth(72)
            else:
                self.setSuffix("%")
                self.setFixedWidth(45)
        self.textChanged.connect(_textChanged)

    def getFloatValue(self) -> float:
        """
        Returns the float value of the spin box.

        Returns:
            float: The float value of the spin box.

        """
        return round(self.value() / 100, 2)

    def setFloatValue(self, v: float):
        """
        Sets the float value of the spin box.

        Args:
            v (float): The float value to set.

        """
        self.setValue(round(v * 100))
        # NOTE: if self.setValue(int(v * 100)) => 29 -> 28, 58 -> 57 -> 56 !! :D
        # 'cause :
        # >>> 0.58 * 100
        # 57.99999999999999
        # >>> 0.57 * 100
        # 56.99999999999999
        # >>> 0.56 * 100
        # 56.00000000000001
        # >>> 0.55 * 100
        # 55.00000000000001

    floatValue = Property(float, getFloatValue, setFloatValue)


class GlobalParamsTab(QWidget):
    """
    Global parameters Tab

    This class represents the tab for global parameters in the control panel.
    It provides a user interface for modifying and saving global parameters.

    Signals:
        - sig_Save_UI_Requested: Signal emitted when the UI save action is requested.
        - sig_Load_UI_Requested: Signal emitted when the UI load action is requested.
    """

    sig_Save_UI_Requested = Signal()
    sig_Load_UI_Requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        ly = QFormLayout()
        ly.setContentsMargins(0, 5, 0, 0)
        ly.setSpacing(5)
        ly.setRowWrapPolicy(QFormLayout.DontWrapRows)
        ly.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        ly.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)

        def buildLabel_Check(txtLabel: str, attrName: str) -> Tuple[QLabel, QCheckBox]:
            """
            Build a label and checkbox pair.

            Args:
                txtLabel (str): The text to be displayed on the label.
                attrName (str): The name of the attribute to be associated with the checkbox.

            Returns:
                Tuple[QLabel, QCheckBox]: A tuple containing the label and checkbox objects.
            """
            chk = QCheckBox()
            chk.setChecked(getattr(globalParameters, attrName))
            chk.stateChanged.connect(lambda state: setattr(
                globalParameters, attrName, bool(state)))
            lbl = BlueHoverLabel(txtLabel)
            toolTip = getattr(
                getattr(type(globalParameters), attrName), "__doc__", "")
            lbl.setToolTip(toolTip)
            chk.setToolTip(toolTip)
            lbl.setBuddy(chk)
            lbl.hoverBuddy = True
            lbl.mouseReleaseEvent = lambda ev: chk.setChecked(
                not chk.isChecked())
            return lbl, chk

        ly.addRow(*buildLabel_Check("<i>'Keep'</i> &Focus On Slider:", GlobalParameters.KeepFocusOnSlider.fget.__name__))
        ly.addRow(*buildLabel_Check("Keep &One Pos For All Models:", GlobalParameters.KeepOnePosForAllModels.fget.__name__))
        ly.addRow(*buildLabel_Check("&Stay On Pos On Fill Model:", GlobalParameters.StayOnPosOnFillModel.fget.__name__))
        ly.addRow(*buildLabel_Check("Stop &annoying Glow signal ", GlobalParameters.StopAnnoyingGlowSignal.fget.__name__))

        cboPlottersGranularity = CommitOnChange_ComboBox( CHOICES_LISTS.GRANULARITY, None, True)
        cboPlottersGranularity.setFixedWidth(45)
        validator = QRegularExpressionValidator( QRegularExpression("([1-9]|[1-9]\\d|100|200)"))
        # validator = QRegularExpressionValidator(QRegularExpression("([1-9]|[1-9]\\d{0,2}"))
        cboPlottersGranularity.setValidator(validator)
        cboPlottersGranularity.setEditText(str(globalParameters.plottersGranularity))

        def _cboPlottersGranularity_currentTextChanged():
            globalParameters.plottersGranularity = int(cboPlottersGranularity.lineEdit().text())
            lbl.setToolTip(GlobalParameters.plottersGranularity.__doc__)
            cboPlottersGranularity.setToolTip(lbl.toolTip())
        cboPlottersGranularity.currentTextChanged.connect(
            _cboPlottersGranularity_currentTextChanged)
        lbl = BlueHoverLabel("Plotters &Granularity:")
        lbl.setToolTip(GlobalParameters.plottersGranularity.__doc__)
        cboPlottersGranularity.setToolTip(lbl.toolTip())
        lbl.setBuddy(cboPlottersGranularity)
        lbl.hoverBuddy = True
        lbl.mouseReleaseEvent = lambda ev: cboPlottersGranularity.setFocus()
        ly.addRow(lbl, cboPlottersGranularity)

        ly_WithSaveBtn = QVBoxLayout()
        ly_WithSaveBtn.addLayout(ly)
        btnSave = QPushButton('&Save')
        btnSave.setToolTip("Save the global parameters\nto the .ini file.")
        btnSave.setMaximumWidth(100)
        btnSave.clicked.connect(globalParameters.saveToINI)

        lyBtn = QHBoxLayout()
        lyBtn.addStretch()
        lyBtn.addWidget(btnSave, Qt.AlignRight)

        ly_WithSaveBtn.addStretch()

        ly_WithSaveBtn.addLayout(lyBtn)

        btnSaveUI = QPushButton('Save')
        btnSaveUI.setMaximumWidth(100)
        btnSaveUI.clicked.connect(lambda: self.sig_Save_UI_Requested.emit())

        btnLoadUI = QPushButton('Load')
        btnLoadUI.setMaximumWidth(100)
        btnLoadUI.clicked.connect(lambda: self.sig_Load_UI_Requested.emit())

        grpDocksParams = QGroupBox(" Docks settings (state and pos) ")
        grpDocksParams.setStyleSheet("""
                        QGroupBox::title {
                            top: 10px;
                            left: 10px;
                            }""")

        grpDocksParams.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        grpDocksParams.setMaximumWidth(228)
        lygrp = QHBoxLayout()
        lygrp.setContentsMargins(10, 10, 5, 5)
        lygrp.addWidget(btnSaveUI, Qt.AlignLeft)
        lygrp.addWidget(btnLoadUI, Qt.AlignLeft)
        lygrp.addStretch()
        grpDocksParams.setLayout(lygrp)

        ly_WithSaveBtn.addWidget(grpDocksParams, stretch=0)

        self.setLayout(ly_WithSaveBtn)
    # end __init__
# end class GlobalParamsTab

class TPParamsTab(QWidget):
    """
    This class represents the Turning Points Parameters Tab and the list of Locked Parameters.
    Note: the list of Locked Parameters are per Model NOT per TP(Turning Point)
        Useful when you want to lock some parameters and continuing training from a specific TP.

    Signals:
        sigMaskChanged(int): Signal emitted when the mask is changed.

    Args:
        parent (QWidget | ControlPanel | None): The parent widget.

    Attributes:
        sigMaskChanged (Signal): Signal emitted when the mask is changed.

    """

    sigMaskChanged = Signal(int)

    def __init__(self, parent: "QWidget | ControlPanel | None" = None) -> None:
        super().__init__(parent)
        # self._parent = parent
        _itemHeight = 22
        self.lstLLB = _ListLabelsLockBuddy(self)
        self.lstLLB.sigMaskChanged.connect(
            lambda msk: self.sigMaskChanged.emit(msk))

        self._pixmap_lock = LOCK_ICO.pixmap(QSize(10, 10))
        self._pixmap_nolock = NOLOCK_ICO.pixmap(QSize(10, 10))

        self.mapper = QDataWidgetMapper(self)

        ly = QFormLayout()
        ly.setContentsMargins(0, 1, 0, 0)
        ly.setSpacing(2)
        ly.setRowWrapPolicy(QFormLayout.DontWrapRows)
        ly.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        ly.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        ly.setLabelAlignment(Qt.AlignRight)

        self.crtIndex = QLineEdit()
        self.crtIndex.setFixedSize(43, _itemHeight)
        self.crtIndex.setEnabled(False)
        self.crtIndex.setAlignment(Qt.AlignRight)

        self.btnFill = QPushButton("Fill  ", self)
        self.btnFill.setFocusPolicy(Qt.ClickFocus)
        self.btnFill.setToolTip("Fill Model from pos (Ctrl+F)")
        self.btnFill.setFixedSize(58, _itemHeight)
        self.btnFill.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.btnFill.setShortcut(QKeyCombination(Qt.ControlModifier, Qt.Key_F))

        lyIxFill = QHBoxLayout()
        lyIxFill.setContentsMargins(0, 0, 0, 0)
        lyIxFill.setSpacing(2)
        lyIxFill.addWidget(self.crtIndex)
        lyIxFill.addWidget(self.btnFill)
        wdgIxFill = QWidget()
        wdgIxFill.setLayout(lyIxFill)
        ly.addRow("Crt index:", wdgIxFill)

        self.rngSpinBox = IntSpinBox(0, 65535, 14)
        self.rngSpinBox.setFixedWidth(65)
        self.rngSpinBox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        # QStyle.SP_BrowserReload, looking ok for refresh :)
        refresh_ico = self.style().standardIcon(QStyle.SP_BrowserReload)
        self.btnRefresh = QPushButton(self.rngSpinBox)
        self.btnRefresh.setToolTip("Randomize (Ctrl+R)")
        self.btnRefresh.setIcon(refresh_ico)
        self.btnRefresh.setFixedSize(19, 19)
        self.btnRefresh.move(44, 3)
        self.btnRefresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnRefresh.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        def _btnRefresh_clicked(_):
            self.rngSpinBox.setValue(np.random.randint(0, 65536))
            if self.rngSpinBox.hasFocus():
                self.rngSpinBox.lineEdit().setSelection(0, 10)
        self.btnRefresh.clicked.connect(_btnRefresh_clicked)
        self.btnRefresh.setShortcut(QKeyCombination(Qt.ControlModifier, Qt.Key_R))

        lblRngSeed = BlueHoverLabel("rng &seed:")
        ly.addRow(lblRngSeed, self.rngSpinBox)
        lblRngSeed.mouseReleaseEvent = lambda ev: self.rngSpinBox.setFocus()
        lblRngSeed.setBuddy(self.rngSpinBox)

        def _rngSpinBox_valueChanged(i: int):
            if self.tpModel.getTP().seedTP != i:
                _tp = self.tpModel.getTP()
                _tp.feedFromSeed(i, self.lstLLB.getColumnsMapLOCKED())
                if _tp.index == 0:
                    self.tpModel.setTPData(_tp)
                self.refresh()
                self.tpModel.setData(self.tpModel.createIndex(
                    1, XOR_Slice.ColumnsMap.minRange), _tp.minRange, Qt.DisplayRole)  # to force Clip from rng seed change
                self.tpModel.sigTPSeedChanged.emit()
        self.rngSpinBox.valueChanged.connect(_rngSpinBox_valueChanged)

        self.batchSizeComboBox = CommitOnChange_ComboBox(CHOICES_LISTS.BATCH_SIZE, self.mapper, True)
        self.batchSizeComboBox.setFixedWidth(45)
        validator = QRegularExpressionValidator(QRegularExpression("([1-9]|[1-4]\\d|50)"))
        self.batchSizeComboBox.setValidator(validator)
        lblLLB = LabelLockBuddy("&Batch size:", self.batchSizeComboBox, _itemHeight)
        ly.addRow(lblLLB, self.batchSizeComboBox)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.batch_size)

        self.epochSizeComboBox = CommitOnChange_ComboBox(CHOICES_LISTS.EPOCH_SIZE, self.mapper, True)
        validator = QRegularExpressionValidator(QRegularExpression("([1-9]\\d{0,2}|[1-4]\\d{3}|5000)"))
        self.epochSizeComboBox.setValidator(validator)
        lblLLB = LabelLockBuddy("&Epoch size:", self.epochSizeComboBox, _itemHeight)
        ly.addRow(lblLLB, self.epochSizeComboBox)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.epoch_size)

        self.cyclesFor1EpochComboBox = CommitOnChange_ComboBox(CHOICES_LISTS.CYCLES_PER_EPOCH, self.mapper, True)
        self.cyclesFor1EpochComboBox.setFixedWidth(45)
        validator = QRegularExpressionValidator(QRegularExpression("([1-9]|10)"))
        self.cyclesFor1EpochComboBox.setValidator(validator)
        lblLLB = LabelLockBuddy("C&ycles / 1 Epoch:", self.cyclesFor1EpochComboBox, _itemHeight)
        ly.addRow(lblLLB, self.cyclesFor1EpochComboBox)
        self.lstLLB.append(
            lblLLB, XOR_Slice.ColumnsMap.cyclesPerOneStepFwdOfEpoch)

        # normally max=100% => 1 Warp Speed... 3 should be enough :D
        self.learningRateSpinBox = PercentSpinBox(1, 300)
        lblLLB = LabelLockBuddy("Learning &rate:", self.learningRateSpinBox, _itemHeight + 2)
        ly.addRow(lblLLB, self.learningRateSpinBox)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.learning_rate)

        def _valueChanged(ix):
            self.mapper.itemDelegate().commitData.emit(self.learningRateSpinBox)
        self.learningRateSpinBox.valueChanged.connect(_valueChanged)

        self.clipValues = wdgInterval(self, self.mapper)
        lblLLB = LabelLockBuddy("&Clip values [min-Max]:", self.clipValues, _itemHeight + 2)
        ly.addRow(lblLLB, self.clipValues)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.minRange)

        self.cboHiddenActivation = ToolTip_CommitOnChange_ComboBox(FunctionsListsByType.HiddenLayer.keys(), self.mapper)
        self.cboHiddenActivation.setToolTipList([x.toolTip_as_html() for x in FunctionsListsByType.HiddenLayer.values()])
        self.cboHiddenActivation.setMinimumWidth(self.clipValues.width() + 3)
        lblLLB = LabelLockBuddy("&Hidden activation:", self.cboHiddenActivation, _itemHeight)
        ly.addRow(lblLLB, self.cboHiddenActivation)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.activation1)

        self.cboOutputActivation = ToolTip_CommitOnChange_ComboBox(FunctionsListsByType.OutputLayer.keys(), self.mapper)
        self.cboOutputActivation.setToolTipList([x.toolTip_as_html() for x in FunctionsListsByType.OutputLayer.values()])
        self.cboOutputActivation.setMinimumWidth(self.clipValues.width() + 3)
        lblLLB = LabelLockBuddy("&Output activation:", self.cboOutputActivation, _itemHeight)
        ly.addRow(lblLLB, self.cboOutputActivation)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.activation2)

        self.cboLoss = ToolTip_CommitOnChange_ComboBox(FunctionsListsByType.LossFunction.keys(), self.mapper)
        self.cboLoss.setToolTipList([x.toolTip_as_html() for x in FunctionsListsByType.LossFunction.values()])
        self.cboLoss.setMinimumWidth(self.clipValues.width() + 3)
        lblLLB = LabelLockBuddy("&Loss:", self.cboLoss, _itemHeight)
        ly.addRow(lblLLB, self.cboLoss)
        self.lstLLB.append(lblLLB, XOR_Slice.ColumnsMap.loss)

        self.setLayout(ly)

        self.setTabOrder(self.rngSpinBox, self.batchSizeComboBox)
        self.setTabOrder(self.batchSizeComboBox, self.epochSizeComboBox)
        self.setTabOrder(self.epochSizeComboBox, self.cyclesFor1EpochComboBox)
        self.setTabOrder(self.cyclesFor1EpochComboBox, self.learningRateSpinBox)
        self.setTabOrder(self.learningRateSpinBox, self.clipValues)
        self.setTabOrder(self.clipValues, self.cboHiddenActivation)
        self.setTabOrder(self.cboHiddenActivation, self.cboOutputActivation)
        self.setTabOrder(self.cboOutputActivation, self.cboLoss)
    # end __init__

    def setParamsMaskFromModel(self, msk: int):
        self.lstLLB.setMask(msk)

    def setMapping(self, tpModel: TPModel):
        self.tpModel = tpModel

        self.mapper.setModel(self.tpModel)

        self.mapper.addMapping(self.crtIndex, XOR_Slice.ColumnsMap.index.value)
        self.mapper.addMapping(self.rngSpinBox, XOR_Slice.ColumnsMap.seedTP.value)
        self.mapper.addMapping(self.batchSizeComboBox, XOR_Slice.ColumnsMap.batch_size.value)
        self.mapper.addMapping(self.epochSizeComboBox, XOR_Slice.ColumnsMap.epoch_size.value)
        self.mapper.addMapping(self.cyclesFor1EpochComboBox, XOR_Slice.ColumnsMap.cyclesPerOneStepFwdOfEpoch.value)
        self.mapper.addMapping(self.learningRateSpinBox, XOR_Slice.ColumnsMap.learning_rate.value, b'floatValue')
        self.mapper.addMapping(self.clipValues._min, XOR_Slice.ColumnsMap.minRange.value)
        self.mapper.addMapping(self.clipValues._max, XOR_Slice.ColumnsMap.maxRange.value)
        self.mapper.addMapping(self.cboHiddenActivation, XOR_Slice.ColumnsMap.activation1.value)
        self.mapper.addMapping(self.cboOutputActivation, XOR_Slice.ColumnsMap.activation2.value)
        self.mapper.addMapping(self.cboLoss, XOR_Slice.ColumnsMap.loss.value)

        self.mapper.toFirst()
    # end setMapping

    def refresh(self):
        """
        Refreshes the control panel by updating the values and signals.

        This method is responsible for refreshing the control panel by updating the values and signals
        of the various components. It temporarily blocks the signals of the tpModel, clipValues._min,
        and clipValues._max objects to prevent any unwanted signal emissions during the refresh process.
        After the refresh is complete, it unblocks the signals to allow normal signal handling.

        """
        self.tpModel.blockSignals(True)
        self.clipValues._min.blockSignals(True)
        self.clipValues._max.blockSignals(True)
        self.mapper.toFirst()
        self.clipValues._min.blockSignals(False)
        self.clipValues._max.blockSignals(False)
        self.tpModel.blockSignals(False)
# end class TPParamsTab

class ControlPanel(QTabWidget):
    """
    ControlPanel class represents a custom tab widget for controlling parameters and settings of the application.

    Args:
        parent (QWidget | None): The parent widget. Defaults to None.
    """

    sigTPChanged = Signal(int) # emitted when the TP is changed via the combo box cboTP, with the TP.index as argument

    def __init__(self,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Initialize the ControlPanel widget

        # Create the Turning Points model
        self.crtSliceModel = TPModel()

        # Create the combo box for selecting Turning Points
        self.cboTP = ToolTip_ComboBox(self)

        # Create the tabs for different parameter settings
        self.tabTP = TPParamsTab(self)
        self.tabGlobalParam = GlobalParamsTab(self)

        # Add the tabs to the ControlPanel widget
        self.insertTab(1, self.tabTP, "&Turning points:                    ")
        self.insertTab(1, self.tabGlobalParam, "&Global parameters")

        # Set focus policy for the combo box
        self.cboTP.setFocusPolicy(Qt.StrongFocus)

        # Set tooltips for the tabs
        self.setTabToolTip(0, "Alt+T")
        self.setTabToolTip(1, "Alt+G")

        # Create a dummy label for keyboard navigation
        lblDummy = QLabel("&T", self)
        lblDummy.setBuddy(self.cboTP)
        lblDummy.move(-1000, -1000)

        # Set the style for the combo box
        self.cboTP.setStyle(AlignComboBoxProxy())

        # Set tooltip list for the combo box
        self.cboTP.setToolTipList([''])

        # Add items to the combo box
        self.cboTP.addItem('0')

        # Set fixed width and height for the combo box
        self.cboTP.setFixedWidth(67)
        self.cboTP.setFixedHeight(self.tabBar().height() - 9)

        # Set the position of the combo box
        self.cboTP.move(95, 4)

        # Set item delegate for the combo box
        self.cboTP.setItemDelegate(AlignDelegate(Qt.AlignCenter, self.cboTP))

        # Set style sheet for the combo box
        self.cboTP.setStyleSheet("""QComboBox { background-color:#e9e9e9; } 
                                    QComboBox QAbstractItemView {
                                    background: #e9e9e9;
                                    selection-background-color: lightblue;
                                }""")

        # Set event handlers for the combo box
        def _enterEvent(event):
            self.tabBar().setCurrentIndex(0)
            ToolTip_ComboBox.enterEvent(self.cboTP, event)
        self.cboTP.enterEvent = _enterEvent

        def _focusInEvent(e: QFocusEvent):
            self.tabBar().setCurrentIndex(0)
            ToolTip_ComboBox.focusInEvent(self.cboTP, e)
        self.cboTP.focusInEvent = _focusInEvent

        # Connect signals and slots for the combo box
        self.cboTP.highlighted.connect(self._RefreshFinalTPLoss)

        def _cboTP_currentIndexChanged(ix: int):
            if ix == -1:
                return
            self.tabBar().setCurrentIndex(0)
            self.sigTPChanged.emit(self.cboTP.itemData(ix).index)
        self.cboTP.currentIndexChanged.connect(_cboTP_currentIndexChanged)
        self.cboTP.activated.connect(_cboTP_currentIndexChanged)

        # Create a label for displaying epoch loss
        self.lblEpochLoss = QLabel("epoch Loss: ", self)
        self.lblEpochLoss.setStyleSheet(
            "border: 1px solid lightgray; border-radius: 3px; background: rgba(255, 255, 255, 1); color: blue; ")

        # Connect signal and slot for the Fill button
        self.tabTP.btnFill.clicked.connect(self.FillFromCrtTP)

        # Set the minimum size for the ControlPanel widget
        self.setMinimumSize(420, 278)

        # Resize the widget
        self.resize(self.size())
    # end __init__

    # Override the resizeEvent method
    def resizeEvent(self, arg__1: QResizeEvent) -> None:
        self.lblEpochLoss.move(arg__1.size().width() -
                               self.lblEpochLoss.width() - 3, self.cboTP.y())
        return super().resizeEvent(arg__1)

    # Private method to refresh the final(per epoch) TP loss
    def _RefreshFinalTPLoss(self, ix: int):
        self.lblEpochLoss.setText(
            "epoch Loss: " + self.mXORmodel.lst_TP_Final_Loss[ix])
        val = float(self.mXORmodel.lst_TP_Final_Loss[ix])
        self.lblEpochLoss.setStyleSheet(
            f" border: 1px solid lightgray; border-radius: 3px; background: '#%06x'; color: blue;"
            "" % MxCOLORS.get_color_for_value(val).__hash__())
        self.lblEpochLoss.adjustSize()
        self.resize(self.size())
        return

    # Method to fill the model from the current TP
    def FillFromCrtTP(self):
        if not self.tabTP.btnFill.hasFocus():
            # force Validate current active control and then Fill..
            self.tabTP.btnFill.setFocus()
        _tp = self.crtSliceModel.getTP()
        self.mXORmodel.fillModelFromTP(_tp)
        self.cboTP.blockSignals(True)
        # self._fillCboTP() # already done by fillModelFromTP emit.sigModelChanged
        self.cboTP.setCurrentIndex(self.cboTP.count()-1)
        self.cboTP.blockSignals(False)

    # Method to refresh the combo box and tab from XOR model
    def RefreshCboAndTabFromXORmodel(self):
        """refresh cbo and Tab infos, No signal emitted"""
        self.cboTP.blockSignals(True)
        self.cboTP.setCurrentIndex(self.mXORmodel.indexOfCrtBaseTP_in_lstTurningPoints)
        self.cboTP.setToolTip(self.cboTP.lstToolTips[self.cboTP.currentIndex()])
        self.tabTP.refresh()
        self._RefreshFinalTPLoss(self.cboTP.currentIndex())
        self.cboTP.blockSignals(False)

    # Private method to set the parameter mask back to the model
    def _setParamsMaskBack2Model(self, msk):
        self.mXORmodel.maskParamLocks = msk

    # Method to set the XOR model
    def setXORModel(self, model: XOR_model):
        self.mXORmodel = model
        self.tabTP.setParamsMaskFromModel(self.mXORmodel.maskParamLocks)
        self.tabTP.sigMaskChanged.connect(self._setParamsMaskBack2Model, Qt.UniqueConnection)
        self.mXORmodel.sigModelChanged.connect(self._fillCboTP, Qt.UniqueConnection)
        self.crtSliceModel = model.getCrtTPModel()
        self.crtSliceModel.blockSignals(True)
        self.tabTP.setMapping(self.crtSliceModel)
        self._fillCboTP()
        self.RefreshCboAndTabFromXORmodel()
        self.crtSliceModel.blockSignals(False)

    # Private method to fill the combo box with turning points
    def _fillCboTP(self):
        # print("_fillCboTP")
        lstTP = self.mXORmodel.lstTurningPoints
        if len(lstTP) == 0:
            return
        assert len(lstTP) > 0

        self.cboTP.setToolTipList(self.mXORmodel.lstTurningPointsDiff)
        self.blockSignals(True)
        self.cboTP.clear()
        for i in range(len(lstTP)):
            self.cboTP.addItem(str(lstTP[i].index), lstTP[i])
        self.blockSignals(False)


if __name__ == "__main__":
    from slider import SliderEdit

    wdgCtrlPanel = ControlPanel()
    XOR_model.wdgMainWindow = wdgCtrlPanel
    
    lstTP: List[XOR_Slice] = []
    tp = XOR_Slice()
    tp.index = 0
    tp.batch_size = 1
    tp.epoch_size = 100
    tp.cyclesPerOneStepFwdOfEpoch = 3
    tp.learning_rate = 0.1
    tp.minRange = -1
    tp.maxRange = 11
    tp.activation1 = Functions.LeakyReLU.__name__
    tp.activation2 = Functions.sigmoid.__name__
    tp.loss = Functions.LCE_Loss.__name__

    xorModel = XOR_model(tp)


    def _sigModelChanged(newPos: int):
        slider.setTurningPoints([ix.index for ix in xorModel.lstTurningPoints], [
                                ix for ix in xorModel.lstTurningPointsDiff])
        slider.setMaximum(xorModel.count() - 1)
        slider.setValue(newPos)
        # force trigger if no changed pos
        slider._valueChanged(newPos)

    xorModel.sigModelChanged.connect(_sigModelChanged)

    wdgCtrlPanel.setXORModel(xorModel)
    wdgCtrlPanel.RefreshCboAndTabFromXORmodel()
    ly = QVBoxLayout()
    ly.setContentsMargins(0, 0, 0, 0)
    ly.addWidget(wdgCtrlPanel)
    slider = SliderEdit()
    slider.setMaximum(xorModel.count()-1)
    slider.setTurningPoints([ix.index for ix in xorModel.lstTurningPoints], list(
        map(str, xorModel.lstTurningPoints)))

    def _slider_valueChanged(i: int):
        xorModel.setPos(i)
        wdgCtrlPanel.RefreshCboAndTabFromXORmodel()
    slider.valueChanged.connect(_slider_valueChanged)

    wdgCtrlPanel.sigTPChanged.connect(slider.setValue)

    ly.addWidget(slider)

    globalParameters.sigKeepFocusOnSlider.connect(lambda: slider.setFocus(), Qt.UniqueConnection)

    win = QWidget()
    win.setContentsMargins(1, 1, 1, 1)
    win.setLayout(ly)
    win.show()
    win.resize(480, 320)

    gApp.exec()
