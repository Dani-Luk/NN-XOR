"""
Some custom widgets : FileNameLineEdit, 
ToolTip_ComboBox, CommitOnChange_ComboBox, ToolTip_CommitOnChange_ComboBox, 
FadingMessageBox, TitledProgressBar
"""

from typing import List, Sequence

from PySide6.QtCore import (QEasingCurve, QEvent, QPoint, QPropertyAnimation,
                            QRegularExpression, Qt, QTimer)
from PySide6.QtGui import (QCursor, QEnterEvent, QKeyEvent, QRegion,
                           QShowEvent, QTextDocument)
from PySide6.QtWidgets import (QComboBox, QDataWidgetMapper, QFrame,
                               QHBoxLayout, QLineEdit, QMessageBox,
                               QProgressBar, QSizePolicy, QToolTip,
                               QVBoxLayout, QWidget)

from global_stuff import *


class FileNameLineEdit(QLineEdit):
    """
    A custom line edit widget for entering file names.

    This widget enforces a specific pattern for file names and provides additional functionality for handling text changes.

    Attributes:
        _pattern (QRegularExpression): The regular expression pattern used to validate file names.

    Methods:
        checkText(txt: str) -> bool: Checks if the given text matches the file name pattern.
        __init__(defaultValidName='Name', parent=None) -> None: Initializes the FileNameLineEdit instance.
        keyPressEvent(arg__1: QKeyEvent) -> None: Handles key press events for the line edit.

    """

    _pattern = QRegularExpression(r"[^<>:\"/\\|?*]+")

    @staticmethod
    def checkText(txt: str) -> bool:
        """
        Checks if the given text matches the file name pattern.

        Args:
            txt (str): The text to be checked.

        Returns:
            bool: True if the text matches the file name pattern, False otherwise.
        """
        resMatch = FileNameLineEdit._pattern.match(txt)
        return (resMatch.captured() == txt)

    def __init__(self, defaultValidName='FileName', parent=None) -> None:
        """
        Initializes the FileNameLineEdit instance.

        Args:
            defaultValidName (str): The default valid name to be displayed in the line edit.
            parent (QWidget): The parent widget.

        Raises:
            AssertionError: If the defaultValidName does not match the file name pattern.
        """
        super().__init__(parent)
        assert FileNameLineEdit.checkText(defaultValidName), "defaultValidName not OK: " + f"{defaultValidName}"
        self._defaultValidName = defaultValidName
        self.setText(self._defaultValidName)
        self.setMaxLength(MAX_LEN_FILENAME_JSON)

        def _textChanged(txt: str):
            if not FileNameLineEdit.checkText(txt) or not txt.strip():
                # this should be latest processed
                QTimer.singleShot(0, lambda: self.setText(self._defaultValidName))
                self.setSelection(0, len(self.text()))
        self.textChanged.connect(_textChanged)
        return

    def keyPressEvent(self, arg__1: QKeyEvent) -> None:
        """
        Handles key press events for the line edit.

        Args:
            arg__1 (QKeyEvent): The key event.

        Returns:
            None
        """
        if arg__1.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Backspace,
                            Qt.Key_Delete, Qt.Key_Enter, Qt.Key_Tab,
                            Qt.Key_Home, Qt.Key_End,
                            Qt.Key_Escape):
            return super().keyPressEvent(arg__1)

        if FileNameLineEdit.checkText(arg__1.text()):
            return super().keyPressEvent(arg__1)

        arg__1.accept()
        return
# end class FileNameLineEdit


class ToolTip_ComboBox(QComboBox):
    """ Show html ToolTip text on highlighting view items"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.lstToolTips: List[str] = []

        # Connect the entered signal of view
        self.view().entered.connect(self.showTooltip)
        # self.highlighted.connect(self.show_tooltip)

        # Initialize a QTimer to check mouse cursor position periodically
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.timeout.connect(self.check_mouse_position)

        # Initialize tooltip visibility flag
        self.tooltip_visible = False

        self._qtt = QToolTip()
        self.setToolTipDuration(2000)

        def _currentIndexChanged(ix: int):
            self.hide_toolTip()
            if ix < 0:
                return
            try:
                self.setToolTip(self.lstToolTips[ix])
            except Exception as ex:
                # print(ex)
                self.setToolTip('')
        self.currentIndexChanged.connect(_currentIndexChanged)
        return
    # end _init__

    def setToolTipList(self, lstTT: List[str]):
        self.lstToolTips = lstTT

    def enterEvent(self, event) -> None:
        try:
            self.setToolTip(self.lstToolTips[self.currentIndex()])
        except:
            pass
        super().enterEvent(event)

    def _showTT(self):
        qTextDoc = QTextDocument()
        qTextDoc.setHtml(self.TT_itemText)
        _pos = self.mapToGlobal(QPoint(int(-qTextDoc.idealWidth()) - 8, - 14))
        self._qtt.showText(_pos, self.TT_itemText, w=self,
                           rect=self.view().viewport().rect())

    def showTooltip(self, index):
        # Get the text of the hovered item
        try:
            item_text = self.lstToolTips[index.row()]
        except:
            pass

        self.TT_itemText = item_text
        self._showTT()
        self.tooltip_timer.start(100)  # Check every 100 milliseconds
        self.tooltip_visible = True

    def hide_toolTip(self):
        self._qtt.hideText()
        self.tooltip_visible = False
        self.tooltip_timer.stop()

    def check_mouse_position(self):
        # Check if the mouse cursor is outside the combo's view
        if not self.tooltip_visible:
            return
        self._showTT()  # show repeatedly to stay visible
        qRegionView = QRegion(self.view().viewport().rect())
        if (not qRegionView.contains(self.view().mapFromGlobal(QCursor.pos()))):
            self.hide_toolTip()
# end class ToolTipComboBox


class CommitOnChange_ComboBox(QComboBox):
    """
    A custom QComboBox widget that commits changes on every index change or text edit.

    Args:
        _list (Sequence): The list of items to populate the combo box with.
        _mapper (QDataWidgetMapper | None, optional): The data widget mapper associated with the combo box. Defaults to None.
        bEdit (bool, optional): Specifies whether the combo box is editable. Defaults to False.
        parent (QWidget | None, optional): The parent widget. Defaults to None.
    """

    def __init__(self, _list: Sequence, _mapper: QDataWidgetMapper | None = None, bEdit: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(bEdit)
        self.setInsertPolicy(QComboBox.NoInsert)
        self._delegate = None
        if _mapper:
            self._delegate = _mapper.itemDelegate()

        self.addItems(map(str, _list))
        assert self.count() > 0

        if self._delegate:
            def _currentIndexChanged(_):
                if self._delegate:
                    bs = self.blockSignals(True)
                    self._delegate.commitData.emit(self) # CommitOnChange
                    self.blockSignals(bs)
            self.currentIndexChanged.connect(_currentIndexChanged)
            self.highlighted.connect(lambda ix: self.setCurrentIndex(ix))

        if bEdit:
            def _editTextChanged(text: str):
                v = 0
                try:
                    v = int(text)
                except:
                    pass
                if v == 0:
                    # if empty text, set to first item
                    self.setCurrentText(self.itemText(0))
                    self.lineEdit().selectAll()
            self.editTextChanged.connect(_editTextChanged)
# end class CommitOnChangeCboBox


class ToolTip_CommitOnChange_ComboBox(CommitOnChange_ComboBox, ToolTip_ComboBox):
    """ A custom combo box widget that combines the functionality of `CommitOnChange_ComboBox` and `ToolTip_ComboBox`.
    It inherits from both classes and provides additional features.

    Args:
        _list (Sequence): The list of items to populate the combo box.
        _mapper (QDataWidgetMapper | None, optional): The data widget mapper to use for mapping data to the combo box. Defaults to None.
        bEdit (bool, optional): Flag indicating whether the combo box is editable. Defaults to False.
        parent (QWidget | None, optional): The parent widget. Defaults to None.
    """

    def __init__(self, _list: Sequence, _mapper: QDataWidgetMapper | None = None, bEdit: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(_list, _mapper, bEdit, parent)  
        # MRO is super() ! ;)


class FadingMessageBox(QMessageBox):
    """ Fade, close and destroy an informative QMessageBox, \n
        by animating windowOpacity 1 -> 0, in 'delay' mSec, with QEasingCurve.InQuart \n
        If hovered, stop animation and set windowOpacity to 1 \n
        NOTE: it set 'self.setAttribute(Qt.WA_DeleteOnClose)'
    """

    def __init__(self, title: str, text: str, delay: int, parent: QWidget, icon=QMessageBox.Information, **args) -> None:
        super().__init__(parent=parent, **args)

        self.setModal(False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setIcon(icon)
        self.setWindowTitle(title)
        self.setText(text)
        self.addButton("Got it", QMessageBox.AcceptRole)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.InQuint)
        self.animation.setDuration(delay)
        self.animation.finished.connect(self.close)
        self.installEventFilter(self)
        
    def enterEvent(self, event: QEnterEvent) -> None:
        self.animation.stop()
        self.setWindowOpacity(1)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        if not self.isActiveWindow():
            self.animation.start()
        return super().leaveEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        self.animation.start()
        return super().showEvent(event)

    def eventFilter(self, obj, event: QEvent):
        if obj == self:
            if event.type() == QEvent.WindowActivate:
                self.animation.stop()
                self.setWindowOpacity(1)
            elif event.type() == QEvent.WindowDeactivate:
                self.animation.start()
        return super().eventFilter(obj, event)
# end class FadingMessageBox


class TitledProgressBar(QFrame):
    """
    A custom widget that displays a titled progress bar.

    Args:
        wdgTitle (QWidget): The widget to be used as the title who can be also a TitledProgressBar
        Note: The widget should have a setText method
        max (int): The maximum value of the progress bar.
        parent (QWidget | None, optional): The parent widget. Defaults to None.
        prefixValue (int, optional): The prefix value to be added to the progress bar value. Defaults to 0.
    """

    def __init__(self, wdgTitle: QWidget, parent: QWidget ) -> None:
        assert parent, "parent is None"
        assert wdgTitle, "wdgTitle is None"
        super().__init__(parent, f=Qt.Dialog | Qt.FramelessWindowHint)
        self.wdgTitle = wdgTitle
        self.prefixValue = 0
        self.setWindowModality(Qt.WindowModal)
        self.setWindowOpacity(0.77)

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 5, 10)
        ly.setSpacing(0)
        self.wdgTitle.setParent(self)
        ly.addWidget(wdgTitle)

        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 1)
        self.progressBar.setFormat("%v / %m")
        lyProgress = QHBoxLayout()
        lyProgress.setContentsMargins(10, 0, 5, 0)
        lyProgress.addWidget(self.progressBar)

        ly.addLayout(lyProgress)
        self.setLayout(ly)

        self.setMinimumWidth(400)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.adjustSize()

    def setTitleWidget(self, wdgTitle: QWidget):
        self.wdgTitle = wdgTitle

    def setText(self, text: str):
        if hasattr(self.wdgTitle, "setText"):
            self.wdgTitle.setText(text)

    def setValue(self, ix: int):
        self.progressBar.setValue(ix)
        if hasattr(self.wdgTitle, "setValue"):
            self.wdgTitle.setValue(self.prefixValue + ix)
        gApp.processEvents()
        # self.repaint()

    def setMax_prefixValue(self, max: int, prefixValue: int = 0):
        self.progressBar.setRange(0, max)
        self.prefixValue = prefixValue
        self.setValue(0)
# end class TitledProgressBar


if __name__ == "__main__":
    from random import randint
    # from time import sleep

    from PySide6.QtWidgets import QLabel, QPushButton

    wdg = QWidget()

    iPushed = 0

    btnProgress = QPushButton("show Progress")
    btnFading = QPushButton("show Fading")
    ly = QVBoxLayout()
    ly.setContentsMargins(20, 20, 20, 120)
    ly.addWidget(btnProgress)
    ly.addWidget(btnFading)
    wdg.setLayout(ly)

    def _btnProgressClick():
        global iPushed
        iPushed += 1
        lst = [100 * randint(1, 10) for _ in range(5)]
        maxOuter = sum(lst)
        sumConsumed = 0
        lbl = QLabel("test")
        lbl.setContentsMargins(10, 10, 0, 5)
        lbl.adjustSize()

        outerProgress = TitledProgressBar(lbl, wdg)
        outerProgress.setMax_prefixValue(maxOuter, sumConsumed)

        innerProgress = TitledProgressBar(outerProgress, wdg)
        innerProgress.setObjectName("innerProgress")
        innerProgress.setStyleSheet("TitledProgressBar#innerProgress { background-color: #c0fcc0; border: 2px solid #68ca68 } ")
        
        for ix, maxInner in enumerate(lst):
            outerProgress.setText(f"test {iPushed} => TP : {ix} / {len(lst)}")
            innerProgress.setMax_prefixValue(maxInner, sumConsumed)
            if not innerProgress.isVisible():
                innerProgress.show()    
            sumConsumed += maxInner
            for i in range(maxInner):
                # sleep(0.0001)
                gApp.processEvents()
                # print(i)
                innerProgress.setValue(i)
        
        innerProgress.close()
    btnProgress.clicked.connect(_btnProgressClick)

    def _btnFadingClick():
        FadingMessageBox("Fading", "Fading model... Done !", 1700, wdg, QMessageBox.Information).show()
    btnFading.clicked.connect(_btnFadingClick)

    wdg.show()
    wdg.resize(320, 240)

    gApp.exec()
