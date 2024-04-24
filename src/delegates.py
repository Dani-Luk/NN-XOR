""" This module contains custom widgets and delegates for handling float and integer values in a QTableView. 
Also MxQTableView is a custom table view for a QTableView. This table view provides a custom selection behavior and emits signals when the current item and selection are changed. 
And custom behavior for headers and selection colors passed to FloatDelegate.
Also contains a custom header view for a QTableView.
"""
from typing import Any

import numpy as np

from PySide6.QtCore import (Qt, QObject, QLocale, QTimer, Signal,
                            QModelIndex, QPersistentModelIndex, QAbstractItemModel, QItemSelection,
                            QPoint, QRect, QSize, QMargins,
                            )
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QTableView, 
                               QWidget, QLabel, QLineEdit, QSlider, QSpinBox, QPushButton, QHBoxLayout, 
                               QStyle, QStyleOptionViewItem, QStyledItemDelegate,
                               )
from PySide6.QtGui import (QColor, QColorConstants, 
                           QKeyEvent, QWheelEvent, QMouseEvent, QFocusEvent, 
                           QPen, QPainter, QDoubleValidator
                           )

from global_stuff import globalParameters, gApp, combineColors, LOCK_ICO, NOLOCK_ICO
from plotters import Dock_Colored


gApp.setWheelScrollLines(1) 

class ButtonSlideFloatEdit(QWidget):
    """
    A custom widget that combines a float input field, a slider, and a lock button.

    This widget allows the user to input a floating-point value, adjust it using a slider,
    and lock/unlock the value using a button.

    Attributes:
        BUTTON_SIZE (QSize): The size of the lock button.
        editing_finished (Signal): A signal emitted when the editing is finished.
        _DECIMALS (int): The number of decimal places to display in the float input field.

    Args:
        parent (QWidget): The parent widget.
        f (Qt.WindowFlags): The window flags for the widget.
        _min (float): The minimum value for the float input field and slider.
        _max (float): The maximum value for the float input field and slider.
    """    
    BUTTON_SIZE = QSize(20, 20)
    editing_finished = Signal()
    _DECIMALS = 3

    def __init__(self, parent: QWidget, f: Qt.WindowFlags = Qt.WindowType.Window, 
                 _min = -20, _max = 20 
                 ) -> None:
        super().__init__(parent=None)
        self._SHIFT_IS_DOWN: bool = False
        self._ALT_IS_DOWN: bool = False  
        self._min = _min
        self._max = _max
        self._blockLock = False

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup | Qt.NoDropShadowWindowHint)  # type:ignore

        self.setToolTip("Alt+/Shift + Wheel/Key Up/Down")
        self.setToolTipDuration(1000)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(180, 42)

        self.mLabel = QLabel(parent=self)
        self.mLabel.setAttribute(Qt.WA_OpaquePaintEvent)
        self.mLabel.setStyleSheet(""" QLabel
            {
            border: 1px solid #004f8e; border-radius: 3px; 
            background: white;
            border-bottom: 1px solid white; 
            border-bottom-right-radius: 0px; 
            border-bottom-left-radius: 0px;
            }""" 
                                  )

    # region floatEdit with button
        self.floatEdit = QLineEdit(parent=self)
        self.floatEdit.setMaxLength(7)
        self.floatEdit.setText("0.000")
        self.floatEdit.setStyleSheet('QLineEdit \
                            {border: 1px solid #d7e3ed; border-radius: 3px; \
                            background: #f0f7ff; \
                            background-clip: content-box; \
                            padding-right: %dpx; \
                            padding-bottom: 0px; \
                            border-top: 1px solid #c8d3dc; \
                            border-bottom: 1px solid #f0f7ff; \
                            border-bottom-right-radius: 0px; \
                            border-bottom-left-radius: 0px;}' % (self.BUTTON_SIZE.width() - 1)
                                     )

        self.floatEdit.setValidator(QDoubleValidator(
            bottom=_min, top=_max, decimals=self._DECIMALS, parent=self))

        def _my_wrapper_validator(slf: QDoubleValidator):
            def _my_validate(input: str, pos: int):
                if (input.strip() == "" or input == "-"):
                    return QDoubleValidator.Intermediate, input.strip()
                decimalPoint = QLocale().decimalPoint()

                if (input.find(decimalPoint) != -1):
                    charsAfterPoint = len(input) - input.find(decimalPoint) - 1
                    if (charsAfterPoint > slf.decimals()):
                        return QDoubleValidator.Invalid

                ok = False
                d, ok = QLocale().toDouble(input)

                if (ok and d >= slf.bottom() and d <= slf.top()):  # type: ignore
                    return QDoubleValidator.Acceptable, input.strip()
                else:
                    return QDoubleValidator.Invalid
            return _my_validate
        self.floatEdit.validator().validate = _my_wrapper_validator(
            self.floatEdit.validator())  # type: ignore

        def my_textEdited(text):
            v = 0
            try:
                v = min( max(float(text), self._min), 
                        self._max
                        )
            except:
                pass
            self.slider.blockSignals(True)
            self.slider.setValue(int(v * 1000))
            self.slider.blockSignals(False)
            return

        self.floatEdit.textEdited.connect(my_textEdited)
        # Unlike **textChanged** (), this signal(aka textEdited) is not emitted when the text is changed programmatically,

    # region lock button
        self.button = QPushButton(parent=self.floatEdit)
        self.button.setFixedSize(self.BUTTON_SIZE)
        self.button.setCheckable(True)
        self.button.setCursor(Qt.CursorShape.ArrowCursor)
        self.button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.button.setEnabled(True)

        def _clicked():
            # if not self._blockLock :
            #     self.setLock(self.button.isChecked())
            # else:
            #     self.setLock(not self.button.isChecked())
            # aka:
            self.setLock(self._blockLock ^ self.button.isChecked())
        self.button.clicked.connect(_clicked)
    # endregion lock button

        edit_layout = QHBoxLayout()
        edit_layout.setContentsMargins(1, 1, 2, 1)
        edit_layout.setSpacing(1)
        edit_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        edit_layout.addWidget(self.button)
        self.floatEdit.setLayout(edit_layout)
    # endregion floatEdit with button

    # region slider
        self.slider = QSlider(
            parent=self, orientation=Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setMouseTracking(True)
        self.slider.setMaximum(self._max * 10 ** self._DECIMALS)
        self.slider.setMinimum(self._min * 10 ** self._DECIMALS)
        self.slider.setStyleSheet("""QSlider:enabled
            {
            border: 1px solid #d7e3ed; border-radius: 3px; 
            background: #f0f7ff; 
            }"""
                                  )
        self.slider.setGeometry(1, 20, self.width()-2, 21)
        self.slider.setSingleStep(100)
        self.slider.setPageStep(1000)

        self.slider._get_fract_value = lambda: abs(self.slider.value()) % 1000  # type: ignore

        self.slider.valueChanged.connect(
            lambda v: self.floatEdit.setText(f'{(v / 10 ** self._DECIMALS):0.3f}'))

        def _sliderPressed():
            self.slider.old_fract_value = self.slider._get_fract_value()  # type: ignore
        self.slider.sliderPressed.connect(_sliderPressed)

        def _sliderMoved(v: int):
            # self.slider.blockSignals(True)
            self.slider.setValue(int(v/1000) * 1000 +
                                 (self.slider.old_fract_value if v >= 0 else -self.slider.old_fract_value))  # type: ignore
            self._setSelectionDigit(True)
            # self.slider.blockSignals(False)
        self.slider.sliderMoved.connect(_sliderMoved)

        self.lblSlider = QLabel(parent=self)
        self.lblSlider.setGeometry(0, 19, self.width(), 23)
        self.lblSlider.setObjectName("lblSlider")
        self.lblSlider.setAttribute(Qt.WA_OpaquePaintEvent)
        self.lblSlider.setStyleSheet("""QLabel#lblSlider
            {
            border: 1px solid #004f8e; 
            border-radius: 3px; 
            }"""
                                     )

        def _wrapper_sliderWheelEvent(f):
            def inner(event: QWheelEvent):
                _ret = None
                if event.modifiers() & Qt.AltModifier and event.modifiers() & Qt.ShiftModifier:  # type: ignore
                    # self.slider.blockSignals(True)
                    if event.angleDelta().x() + event.angleDelta().y() > 0:
                        self.slider.setValue(self.slider.value() + 1)
                    else:
                        self.slider.setValue(self.slider.value() - 1)
                    # self.slider.blockSignals(False)
                elif event.modifiers() & Qt.AltModifier or event.modifiers() & Qt.ShiftModifier:  # type: ignore
                    if event.angleDelta().x() + event.angleDelta().y() > 0:
                        self.slider.setValue(self.slider.value() + 10)
                    else:
                        self.slider.setValue(self.slider.value() - 10)
                else:
                    # https://forum.qt.io/topic/80728/qscrollbar-acts-differently-when-pressing-arrow-keys-and-scrolling/4
                    # A simplified formula for how Qt calculates the amount of wheel scroll is:
                    # scrollbar->singleStep() * QApplication::wheelScrollLines() * delta / 120
                    # print("before default Wheel Event:", self.slider.value())
                    # at the beginning we set : app.setWheelScrollLines(1) , so ... default it's Ok
                    _ret = f(event)

                self._setSelectionDigit()
                return _ret
            return inner

        self.slider.wheelEvent = _wrapper_sliderWheelEvent(self.slider.wheelEvent)  # type: ignore
        self.wheelEvent = self.slider.wheelEvent

        self.floatEdit.keyReleaseEvent = self.keyReleaseEvent  # type: ignore
        
        return
    # endregion slider
# end __init__

    def _setSelectionDigit(self, bSelIntPart: bool = False):
        """
        Sets the selection for the digit in the text field.

        Args:
            bSelIntPart (bool, optional): Specifies whether to select the integer part of the number. 
                If False, selects the corresponding decimal part fct by self._SHIFT_IS_DOWN + self._ALT_IS_DOWN. 
                Defaults to False.
        """
        _ndigit = self._SHIFT_IS_DOWN + self._ALT_IS_DOWN
        try:
            _ = float(self.getText())
            _start = self.getText().find(QLocale().decimalPoint())
            if _start >= 0:
                if not bSelIntPart:
                    _start += 1 + _ndigit
                    self.floatEdit.setSelection(_start, 1)
                else:
                    self.floatEdit.setSelection(0, _start)
        except:
            pass
        return
    
    def blockLook(self, bl: bool):
        self._blockLock = bl

    def setRange(self, _min: int, _max: int):
        self._min = _min
        self._max = _max
        self.floatEdit.setValidator(QDoubleValidator(bottom=self._min, top=self._max, decimals=self._DECIMALS, parent=self))
        self.slider.setMaximum(self._max * 10 ** self._DECIMALS)
        self.slider.setMinimum(self._min * 10 ** self._DECIMALS)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        match event.key():
            case Qt.Key_Shift:
                self._SHIFT_IS_DOWN = True
                self._setSelectionDigit()
                return
            case Qt.Key_Alt:
                self._ALT_IS_DOWN = True
                self._setSelectionDigit()
                return
            case Qt.Key_PageUp | Qt.Key_PageDown:
                self.slider.sliderPressed.emit()
                return

        return super().keyPressEvent(event)


    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        match event.key():
            case Qt.Key_Shift:
                self._SHIFT_IS_DOWN = False
                self._setSelectionDigit()
                return
            case Qt.Key_Alt:
                self._ALT_IS_DOWN = False
                self._setSelectionDigit()
                return
            case keyUpDown if keyUpDown in (Qt.Key_Up, Qt.Key_Down):
                qwe = QWheelEvent(
                    QPoint(90, 20),
                    self.mapToGlobal(QPoint(90, 20)),
                    QPoint(0, 0),
                QPoint(0, 120 if keyUpDown == Qt.Key_Up else -120),
                    Qt.MouseButton.NoButton,  # type: ignore
                    (
                        # type: ignore
                        (Qt.KeyboardModifier.ShiftModifier if self._SHIFT_IS_DOWN else Qt.KeyboardModifier.NoModifier)
                        |
                        (Qt.KeyboardModifier.AltModifier if self._ALT_IS_DOWN else Qt.KeyboardModifier.NoModifier)
                    ),
                    Qt.ScrollPhase(),  # type: ignore
                    False,
                    Qt.MouseEventNotSynthesized
                )
                gApp.sendEvent(self.slider, qwe)
                return
            case Qt.Key_PageUp:
                if self.slider.value() + 1000 <= self.slider.maximum():
                    self.slider.sliderMoved.emit(self.slider.value() + 1000)
                return
            case Qt.Key_PageDown:
                if self.slider.value() - 1000 >= self.slider.minimum():
                    self.slider.sliderMoved.emit(self.slider.value() - 1000)
                return
            case Qt.Key_Space:
                self.button.click()
                return

        return super().keyReleaseEvent(event)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        # self.editing_finished.emit()
        self.close()
        return super().mousePressEvent(ev)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self.floatEdit.selectAll()
        self.floatEdit.setFocus()

    def getLock(self) -> bool:
        return self.button.isChecked()

    def setLock(self, bl: bool):
        self.button.setChecked(bl)
        if bl:
            self.button.setIcon(LOCK_ICO)
        else:
            self.button.setIcon(NOLOCK_ICO)

    def setText(self, pText: str):
        val = 0
        try:
            val = float(pText)
        except:
            pass
        val = min(max(val, self._min), self._max)
        self.slider.setValue(int(val * 10 ** self._DECIMALS))

    def getText(self):
        return f'{self.slider.value()/1000:0.3f}'

    def setGeometry(self, glTopLeft: QPoint, glBottomRight: QPoint, pAlignment: Qt.AlignmentFlag):
        # glTopLeft = self.mapToGlobal(rect.topLeft())
        newEditWidth = glBottomRight.x() - glTopLeft.x()
        newEditWidth = max(newEditWidth, 65)
        newEditWidth = min(newEditWidth, 180)

        import operator
        from functools import reduce
        enum_alignement = reduce(operator.or_, (x & pAlignment for x in Qt.AlignmentFlag))  # type: ignore
        self.floatEdit.setAlignment(enum_alignement)
        # self.floatEdit.setAlignment(pAlignment) # type: ignore
        # self.floatEdit.setAlignment(Qt.AlignmentFlag(Qt.AlignHorizontal_Mask&pAlignment) | Qt.AlignmentFlag(Qt.AlignVertical_Mask&pAlignment))

        self.floatEdit.move(int((180/2 - newEditWidth/2)), 1)
        self.floatEdit.setFixedWidth(newEditWidth + 1)
        self.floatEdit.setFixedHeight(glBottomRight.y() - glTopLeft.y()+2)
        
        self.mLabel.setFixedSize(self.floatEdit.width() + 2, self.floatEdit.height() + 1)
        self.mLabel.move(self.floatEdit.x() - 1, 0)

        self.setFixedHeight(glBottomRight.y() - glTopLeft.y() + 25)

        self.lblSlider.move(0, self.height() - 23)
        self.slider.move(1, self.height() - 22)

        self.slider.raise_()
        self.floatEdit.raise_()

        self.move(glBottomRight.x() - int((180 + newEditWidth)/2),  glTopLeft.y() - 1)
        return
# end class ButtonSlideFloatEdit


class FloatDelegate(QStyledItemDelegate):
    """
    A delegate for handling float values in a QTableView.

    This delegate provides custom editing and rendering behavior for float values in a QTableView.
    It allows the user to edit the float value using a custom editor widget and renders the float
    value with customizable colors and styles.

    Attributes:
        _defaultChar (str): The default character to display in the editor widget.
        KeepSelectedThicked (bool): Flag indicating whether to keep the selected item thickened.
    """
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._defaultChar = ""
        self.KeepSelectedThicked = False

    def setDefaultChar(self, txt: str):
        self._defaultChar = txt

    def createEditor(self, parent, option, index: QModelIndex | QPersistentModelIndex):
        self._parent = parent
        # min.max in setEditorData editor.setRange
        return ButtonSlideFloatEdit(parent)

    def _setTextAfterFocus(self, editor: ButtonSlideFloatEdit):
        try:
            editor.slider.blockSignals(True)
            editor.floatEdit.setText(self._defaultChar)
            editor.setText(self._defaultChar)
            # editor.floatEdit.setCursorPosition(1)
            self._defaultChar = ""
            editor.slider.blockSignals(False)
        except Exception as ex:
            # editor already deleted. (by Esc, click)
            # print(ex)
            pass

    def setEditorData(self, editor: ButtonSlideFloatEdit, index: QAbstractItemModel):
        val = float(index.data(Qt.ItemDataRole.EditRole) or "0")  # type: ignore
        look = bool(index.data(Qt.ItemDataRole.UserRole))  # type: ignore
        blockLook = bool(index.data(Qt.ItemDataRole.UserRole + 1))  # type: ignore
        _min = index.data(Qt.ItemDataRole.UserRole + 2)  # type: ignore
        _max = index.data(Qt.ItemDataRole.UserRole + 3)  # type: ignore
        if not self._defaultChar:
            editor.setText(f"{val:0.3f}")
        else:
            QTimer.singleShot(10, lambda: self._setTextAfterFocus(editor))
        editor.setLock(look)
        editor.blockLook(blockLook)
        editor.setRange(_min, _max)

    def setModelData(self, editor: ButtonSlideFloatEdit, model, index):
        val = editor.getText() or "0"
        bLook = editor.getLock()
        # first this one
        model.setData(index, bLook, role=Qt.ItemDataRole.UserRole)
        # type: ignore
        model.setData(index, val, role=Qt.ItemDataRole.EditRole)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        _state = option.state  # type: ignore
        _iColor = QColor('azure')
        try:
            _iColor = QColor(self._colorMap[index.row()][index.column()])
        except:
            pass
        painter.save()
        try:
            # painter.setRenderHint(QPainter.Antialiasing, True)
            painter.fillRect(option.rect, _iColor)  # type: ignore
            painter.setPen(index.data(Qt.ItemDataRole.ForegroundRole))
            # _rect = option.rect # 'FATAL' big pb issue error ! it's a pointer! :)))
            _rect = option.rect + QMargins(0, 0, 0, 0)
            _txt = index.data(Qt.ItemDataRole.DisplayRole)
            try:
                _ = float(_txt)
                # right ! a new instance ;)
                _rect = option.rect - QMargins(0, 0, 12, 0)
                _ = int(_txt)
                _rect = option.rect + QMargins(0, 0, 6, 0)
            except:
                pass
            gApp.style().drawItemText(painter,
                                      _rect,  
                                      index.data(Qt.ItemDataRole.TextAlignmentRole), # type: ignore
                                      option.palette,  # type: ignore
                                      True,
                                      _txt)  # type: ignore

            if _state & QStyle.State_Selected:
                if self.KeepSelectedThicked:
                    painter.setPen(QPen(QColor('royalblue'), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin,))  # type: ignore
                    painter.drawRoundedRect(
                        option.rect - QMargins(1, 1, 1, 1), 2, 2)  # type: ignore
                else:
                    if _state & QStyle.State_Active:
                        painter.setPen(QPen(
                            QColorConstants.Svg.cyan, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin,))  # type: ignore
                        painter.drawRoundedRect(
                            option.rect - QMargins(0, 0, 1, 1), 1, 1)  # type: ignore
                    else:
                        painter.setPen(QPen(
                            QColorConstants.Svg.khaki, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))  # type: ignore
                        painter.drawRoundedRect(
                            option.rect - QMargins(0, 0, 1, 1), 1, 1)  # type: ignore

            if index.data(Qt.ItemDataRole.UserRole):  # type: ignore
                iconRect = QRect(option.rect)  # type: ignore
                iconRect.setLeft(iconRect.left() + iconRect.width() - 11)
                iconRect.setTop(iconRect.top() + 1)
                iconRect.setSize(QSize(12, 12))
                LOCK_ICO.paint(painter, iconRect)

        except Exception as ex:
            print('FloatDelegate Paint exception:', ex.__repr__())

        painter.restore()
    # paint end

    def setMatrixColor(self, colorMap):
        self._colorMap = colorMap

    def updateEditorGeometry(self, editor: ButtonSlideFloatEdit, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        editor.setGeometry(self._parent.mapToGlobal(option.rect.topLeft()),  # type: ignore
                           self._parent.mapToGlobal(
                               option.rect.bottomRight()),  # type: ignore
                           index.data(Qt.ItemDataRole.TextAlignmentRole))  # type: ignore
# end class FloatDelegate


class IntDelegate(QStyledItemDelegate):
    """ A delegate for handling integer values in a QTableView. 
    This delegate provides custom editing and rendering behavior for integer values in a QTableView.
    It allows the user to edit the integer value using spin box editor widget and renders the integer value with customizable colors and styles."""
    def __init__(self, min: int, max: int) -> None:
        super().__init__()
        self._min = min
        self._max = max

    def setMinimum(self, min):
        self._min = min

    def setMaximum(self, max):
        self._max = max

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> QWidget:
        spinBox = QSpinBox(parent=parent)
        spinBox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spinBox.setMinimum(self._min)
        if index.column() == 1:
            spinBox.setMaximum(
                100 - index.model().sum_pred_col_pc(index.row()))
        else:
            spinBox.setMaximum(self._max)
        return spinBox

    def setEditorData(self, editor: QSpinBox, index: QModelIndex | QPersistentModelIndex) -> None:
        editor.setValue(int(index.data(Qt.EditRole)))
        # return super().setEditorData(editor, index)

    def setModelData(self, editor: QSpinBox, model: QAbstractItemModel, index: QModelIndex | QPersistentModelIndex) -> None:
        model.setData(index, editor.value(), Qt.EditRole)
        # return super().setModelData(editor, model, index)
# end class IntDelegate


"""
NOTE: https://stackoverflow.com/questions/11895388/how-to-implement-delegate-in-qheaderview
For the record, if you want to style a QHeaderView section, 
you'll have to do it either via the header data model (changing Qt::FontRole, etc.) 
or derive your own QHeaderView (don't forget to pass it to your table with "setVerticalHeader()") 
    and overwrite the its paintSection()-function. i.e.: 
        void YourCustomHeaderView::paintSection
"""
class CustomHeaderView(QHeaderView):
    """A custom header view for a QTableView.
    """
    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None) -> None:
        super().__init__(orientation, parent)
        self._parent: QTableView = parent  # type: ignore
        self._orientation: Qt.Orientation = orientation
        self.setSectionsClickable(True)

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int) -> None:
        painter.save()
        try:
            color = self._parent.model().headerData(logicalIndex, self._orientation,
                                                    Qt.ItemDataRole.BackgroundRole) or QColor('white')  # type: ignore
            painter.fillRect(rect, color)
            painter.setPen(QPen(QColor('lightgray'), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin,))
            painter.drawRect(rect - QMargins(-1, -1, 1, 1))
            painter.restore()
            painter.save()
            _txt = self._parent.model().headerData(logicalIndex, self._orientation, Qt.ItemDataRole.DisplayRole)
            if not _txt.isascii():
                # unicode -> subscript so up a little
                _f = painter.font()
                _f.setPointSize(_f.pointSize() + 2)
                painter.setFont(_f)
                if self._orientation == Qt.Orientation.Horizontal:
                    rect += QMargins(0, 5, 0, 0)

            gApp.style().drawItemText(painter,
                                      rect,
                                      Qt.AlignmentFlag.AlignHCenter | Qt.AlignVCenter,  # type: ignore
                                      gApp.palette(),
                                      True,
                                      _txt
                                      )
        except Exception as e:
            print(e)

        painter.restore()
# end class CustomHeaderView


class TableView_sigCurrentChanged(QTableView):
    """ 
    A custom table view that emits a signal when the current item is changed.
    """
    sigCurrentChanged = Signal(int, QObject) # second parameter is to identify the sender from multiple connected into a Hub

    def currentChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        if current.isValid():
            self.sigCurrentChanged.emit(current.row(), self)
        else:
            self.sigCurrentChanged.emit(-1, self)
        return super().currentChanged(current, previous)
# end class TableView_sigCurrentChanged


class MxQTableView(QTableView):
    """
    A custom table view for a QTableView.
    This table view provides a custom selection behavior and emits signals when the current item and selection are changed.
    And custom behavior for headers and selection colors passed to FloatDelegate.
    """
    sigGlow = Signal(QColor)
    sigCurrentChanged = Signal(int, QObject) # second parameter is to identify the sender from multiple connected into a Hub
    sigSelectionChanged = Signal(Any)  # Lst_selected
    __COL_WIDTH_Max = 120
    __ROW_HEIGHT = 30
    __V_HEADER_WIDTH = 30
    __H_HEADER_HEIGHT = 20

    def __init__(self, parent: QWidget | None = None,
                 hHeaderVisible=True,
                 vHeaderVisible=True,
                 min_col_width=60) -> None:
        """ Initializes the MxQTableView.
        """
        QTableView.__init__(self, parent)
        self.__COL_WIDTH_min = min_col_width
        self._hHeaderVisible = hHeaderVisible
        self._vHeaderVisible = vHeaderVisible
        self.bKeepSelectedThicked = False

        if self._hHeaderVisible:
            self.setHorizontalHeader(CustomHeaderView(Qt.Orientation.Horizontal, self))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setFixedHeight(MxQTableView.__H_HEADER_HEIGHT)
        self.horizontalHeader().setVisible(self._hHeaderVisible)

        if self._vHeaderVisible:
            self.setVerticalHeader(CustomHeaderView(Qt.Orientation.Vertical, self))
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setFixedWidth(MxQTableView.__V_HEADER_WIDTH)
        self.verticalHeader().setVisible(self._vHeaderVisible)

        self.setTabKeyNavigation(False)
        self.setStyleSheet("""MxQTableView QTableCornerButton::section {
            border: 1px solid rgb(220, 220, 220); 
            background: rgb(230, 230, 230);
            }"""
                           )
        return
    # end __init__

    def setModel(self, model: QAbstractItemModel) -> None:
        super().setModel(model)
        _height = self.horizontalHeader().height() if self._hHeaderVisible else 0
        _height += (MxQTableView.__ROW_HEIGHT) * model.rowCount()

        self.setMinimumWidth(
            (
                (self.verticalHeader().width()
                 if self._vHeaderVisible else 0)
                + (self.__COL_WIDTH_min + 1) * model.columnCount()
            ))
        self.setMaximumWidth(
            (
                (self.verticalHeader().width()
                 if self._vHeaderVisible else 0)
                + (MxQTableView.__COL_WIDTH_Max + 1) * model.columnCount()
            ))
        self.setFixedHeight(_height + 2)


    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.edit(self.currentIndex())
            return
        elif event.key() in range(Qt.Key_0, Qt.Key_9 + 1):
            self.itemDelegate().setDefaultChar(str(event.key() - Qt.Key_0))
            self.edit(self.currentIndex())
            return
        elif event.key() == Qt.Key_Minus:
            self.itemDelegate().setDefaultChar("-")
            self.edit(self.currentIndex())
            return

        # move to next/previous 'Table' (W1b1 / w2b2 context), somewhat ...
        if (event.key() == Qt.Key_Down and self.currentIndex().row() == self.model().rowCount() - 1):
            newEvent = QKeyEvent(event.type(), Qt.Key_Tab, Qt.NoModifier)
            gApp.postEvent(self, newEvent)
        if (event.key() == Qt.Key_Up and self.currentIndex().row() == 0):
            newEvent = QKeyEvent(event.type(), Qt.Key_Tab, Qt.ShiftModifier)
            gApp.postEvent(self, newEvent)
        else:
            return super().keyPressEvent(event)


    def currentChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        if current.isValid():
            self.sigCurrentChanged.emit(current.row(), self)
        else:
            self.sigCurrentChanged.emit(-1, self)
        return super().currentChanged(current, previous)


    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        lstRowsSelected = []
        for item in self.selectedIndexes():
            lstRowsSelected.append(item.row())
        self.sigSelectionChanged.emit(lstRowsSelected)
        lst_row_column = [(item.row(), item.column()) for item in self.selectedIndexes()] # type: ignore

        nRows = self.model().rowCount()
        nCols = self.model().columnCount()

        if not self.model().ExplicitColors():
            mxColors = np.ndarray(shape=(nRows, nCols), dtype=QColor) # this are all combined colors of V + H headers
            mxSelectedColors = np.full(shape=(nRows, nCols), fill_value=None, dtype=QColor) # this are interested for us

            for row in range(nRows):
                for col in range(nCols):
                    HheaderColor = self.model().headerData( col, Qt.Horizontal, Qt.BackgroundRole)  # type: ignore
                    VheaderColor = self.model().headerData( row, Qt.Vertical, Qt.BackgroundRole)  # type: ignore
                    mxColors[row, col] = combineColors( HheaderColor, VheaderColor) # combine the colors of the V and H headers
                    # if (row, col) in ((item.row(), item.column()) for item in self.selectedIndexes()):  # type: ignore
                    if (row, col) in lst_row_column:  
                        mxSelectedColors[row, col] = mxColors[row, col]

            column_counts = np.array([np.count_nonzero(mxSelectedColors[:, c]) for c in range(nCols)]) # count of selected cells in each column
            full_mask = np.asarray(column_counts == nRows) # mask of full columns
            indexes_full_columns = np.nonzero(full_mask)[0] # indexes of full columns
            
            if indexes_full_columns.size: # if there are full columns
                #  Columns have priority
                for c in indexes_full_columns:
                    # fill the entire column with the color of the H header
                    mxSelectedColors[:, c].fill(self.model().headerData(c, Qt.Horizontal, Qt.BackgroundRole))  # type: ignore
            else:
                rows_counts = np.array([np.count_nonzero(mxSelectedColors[r, :]) for r in range(nRows)]) # count of selected cells in each row
                full_mask = np.asarray(rows_counts == nCols) # mask of full rows
                indexes_full_rows = np.nonzero(full_mask)[0] # indexes of full rows
                if indexes_full_rows.size: # if there are full rows
                    for r in indexes_full_rows:
                        # fill the entire row with the color of the V header
                        mxSelectedColors[r, :].fill(self.model().headerData(r, Qt.Vertical, Qt.BackgroundRole))  # type: ignore

            mxAllCells = np.where(mxSelectedColors, mxSelectedColors,  mxColors) 
            # combine the selected colors with the rest of the colors: mxSelectedColors if not None, else mxColors

        else:
            # if there are SOME explicit colors
            arr = np.array(self.model().ExplicitColors())
            if not arr.shape:
                arr.shape = (1, 1)
            elif len(arr.shape) == 1:
                arr.shape = (1, arr.shape[0])
            repetitions = ((nRows - 1) // arr.shape[0] + 1, (nCols - 1) // arr.shape[1] + 1)
            mxAllCells = np.tile(arr, repetitions) # repeat the explicit colors to fill the entire table
            mxAllCells = mxAllCells[:nRows, :nCols] # cut the extra cells
        # end if ExplicitColors()

        newfloatdelegate = FloatDelegate()
        newfloatdelegate.setMatrixColor(mxAllCells)
        newfloatdelegate.KeepSelectedThicked = self.bKeepSelectedThicked
        # force repaint
        self.setItemDelegate(newfloatdelegate)

        setColors = set()

        for ix in self.selectedIndexes():
            setColors.add(mxAllCells[ix.row(), ix.column()])


        if not globalParameters.StopAnnoyingGlowSignal:
            QTimer.singleShot( 200, lambda: Dock_Colored.classGlow(list(setColors)) )
    
        # return super().selectionChanged(selected, deselected) ?
    # end selectionChanged method         
   
# end class MxQTableView


if __name__ == "__main__":
    import pandas as pd
    from models import MatrixWithMaskAndColoredHeaderModel as MatrixModel

    model = MatrixModel(hHeaderColors=['yellow', 'orange'])

    tbl = MxQTableView(vHeaderVisible=False)
    tbl.setSelectionMode(QAbstractItemView.MultiSelection)
    tbl.bKeepSelectedThicked = True
    tbl.setModel(model)

    tbl2 = MxQTableView()

    _data = pd.DataFrame(-10 + 20 * np.random.rand(2, 2))
    _data.columns = [1, 2]
    _mask = pd.DataFrame(np.random.choice(a=[False, True], size=(2, 2), p=[0.5, 0.5]))
    _blockLock = pd.DataFrame(np.full((2, 2), [True, False]))

    model2 = MatrixModel(data=_data, mask=_mask, blockLock=_blockLock)
    tbl2.setModel(model2)

    lyt = QHBoxLayout()
    lyt.addStretch()
    lyt.addWidget(tbl)
    lyt.addStretch()
    lyt.addWidget(tbl2)
    lyt.addStretch()

    wnd = QWidget()
    wnd.setLayout(lyt)
    wnd.resize(610, 480)
    wnd.show()

    gApp.exec()
