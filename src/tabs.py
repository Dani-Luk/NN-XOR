"""
This module contains the TabDragEdit class, a custom widget for managing draggable and editable tabs.
"""

from itertools import count
from typing import Callable, Optional, Union

from PySide6.QtCore import (QEvent, QKeyCombination, QObject, QPoint, QSize, 
                            Qt, QTimer, Signal)
from PySide6.QtGui import (QFontMetrics, QIcon, QKeyEvent, QKeySequence,
                           QAction, QWheelEvent )
from PySide6.QtWidgets import (QDockWidget, QHBoxLayout, 
                               QMainWindow, QMenu, QMessageBox, QPushButton,
                               QSizePolicy, QTabBar, QTabWidget, QToolButton,
                               QVBoxLayout, QWidget)

from global_stuff import *
from custom_widgets import FileNameLineEdit
from models import XOR_model


class TabDragEdit(QWidget):
    """
    A custom widget for managing draggable and editable tabs.

    Args:
        parent (QWidget|None): The parent widget. Defaults to None.
        fnGetNewModel (Callable|None): A function that returns a new model. Defaults to None.
        crtModel (Optional[XOR_model]): The current model. Defaults to None.
        menu (Optional[QMenu]): The menu associated with the widget. Defaults to None.
    """
    sigModelChanged = Signal(XOR_model)
    _PLUS_UNICODE = chr(0x271A)

    def __init__(self, parent: QWidget | None = None,
                 fnGetNewModel: Callable | None = None,
                 crtModel: Optional[XOR_model] = None, 
                 menu: Optional[QMenu] = None
                 ):
        """
        Initializes the TabDragEdit widget.

        Args:
            parent (QWidget|None): The parent widget. Defaults to None.
            fnGetNewModel (Callable|None): A function that returns a new model. Defaults to None.
            crtModel (Optional[XOR_model]): The current model. Defaults to None.
            menu (Optional[QMenu]): The menu associated with the widget. Defaults to None.
        """
        super().__init__(parent)

        self._parent = parent
        self.fnGetNewModel = fnGetNewModel
        self._id_generator = count(1, 1)
        self.setToolTip("F2/DblClick, +/Ins, -/Del")
        self.setToolTipDuration(1000)

        self.tab_widget = QTabWidget()
        self.menu = menu

        self.btn_menu = QToolButton(self)
        btn_menu = self.btn_menu
        btn_menu.setToolTip("Alt + M")
        btn_menu.setShortcut(QKeySequence(Qt.AltModifier | Qt.Key_M))
        btn_menu.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        btn_menu.setIcon(QIcon('./images/menu-24.ico'))
        btn_menu.setStyleSheet("""QToolButton { 
                               background-color: #9dd9d2;  
                               border:1px solid #9dd9d2;
                               }
                               QToolButton:hover:pressed {
                               background-color: #bde9e2;
                               }
                               QToolButton:hover:!pressed {
                               background-color: #8dc9c2;
                               }
                               QToolButton::menu-indicator { 
                               image: none; 
                               }
                               """)
        btn_menu.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        if menu:
            btn_menu.setMenu(menu)
        btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.DelayedPopup)
        btn_menu.clicked.connect(lambda: btn_menu.showMenu())

        self.tab_widget.setFixedHeight(50)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(True)

        self.tab_widget.setStyleSheet("QTabWidget::pane {\
                                        border:2 solid #9dd9d2; \
                                        background-color: #9dd9d2;\
                                    }"
                                      )

        self.tab_widget.tabBar().setStyleSheet("""
                                            QTabBar{
                                                font-weight: normal;
                                            }
                                            QTabBar::tab:selected {
                                                font-weight: normal;
                                                background-color: #9dd9d2;
                                            }
                                            QTabBar::tab:hover:selected {
                                                font-weight: normal;
                                                background-color: #8dc9c2;
                                            }
                                            QTabBar::tab:hover:!selected {
                                                font-weight: normal;
                                                background-color: #d0e0e0;
                                            }
                                            """)

        def _tabBarClicked(ix: int):
            if ix == self.tab_widget.tabBar().count() - 1:
                self.createNewTab()
                # and the rest is done in the currentChanged Slot

        self.tab_widget.tabBar().tabBarClicked.connect(_tabBarClicked)

        def _currentChanged(ix: int):
            # prevent moving Tabs in the last position
            if self.tab_widget.tabBar().tabText(self.tab_widget.tabBar().count() - 1).strip() != self._PLUS_UNICODE:
                _bSig = self.tab_widget.tabBar().blockSignals(True)
                self.tab_widget.tabBar().moveTab(self.tab_widget.tabBar().count() - 1, self.tab_widget.tabBar().count() - 2)
                self.tab_widget.tabBar().blockSignals(_bSig)
                return
            if not (0 <= ix < self.tab_widget.count()) or ix == self.tab_widget.tabBar().count() - 1:
                # if ix not valid OR ix in last position( == '+' tab) => reject
                _bSig = self.tab_widget.tabBar().blockSignals(True)
                self.tab_widget.setCurrentIndex(
                    self.tab_widget.tabBar().count() - 2)
                self.tab_widget.tabBar().blockSignals(_bSig)
                return
            _model: XOR_model = self.tab_widget.tabBar().tabData(ix)
            if _model:
                self.sigModelChanged.emit(_model)

        self.tab_widget.tabBar().currentChanged.connect(_currentChanged)
        self.tab_widget.tabBar().tabBarDoubleClicked.connect(self.editTab)

        self.tab_widget.tabBar().minimumTabSizeHint = lambda _: QSize(150, 30)

        _name = self.getNextName("")
        if crtModel:
            crtModel.setParent(self) # that will keep the data(QObject) alive
            if hasattr(crtModel, "modelName"):
                _name = crtModel.modelName
        self.addTabAndEdit(name=_name, bEdit=False, data=crtModel)
        self.addTabAndEdit(name=self._PLUS_UNICODE + " ", data=None, bEdit=False)

        self.tab_widget.setCurrentIndex(0)

        self.tab_widget.tabCloseRequested.connect(self.removeTab)
        self.tab_widget.setFixedHeight(self.tab_widget.tabBar().height() + 2)

        btn_menu.setFixedSize(self.tab_widget.height(), self.tab_widget.height() - 6)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(1, 0, 1, 0)
        tab_layout = QHBoxLayout()
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        wdg_menu = QWidget(self)
        wdg_menu.setFixedSize(self.tab_widget.height() + 4, self.tab_widget.height())
        wdg_menu.setObjectName('wdg_menu')
        wdg_menu.setStyleSheet("QWidget#wdg_menu { border-bottom: 2 solid #%06x; }" % 0x9dd9d2)
        btn_menu.setParent(wdg_menu)

        btn_menu.move(2, 2)

        tab_layout.addWidget(wdg_menu)
        tab_layout.addWidget(self.tab_widget)

        main_layout.addLayout(tab_layout)

        self.setLayout(main_layout)
        self.setWindowTitle("Tab Dialog")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusProxy(self.tab_widget.tabBar())
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_widget.setFocusProxy(self.tab_widget.tabBar())
        self.tab_widget.tabBar().setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tab_widget.tabBar().installEventFilter(self)
            # and that's how I did it(again !?) to put the visible focus('rectangle' focus) on the Tab :D
        self.btn_menu.setFocus()
        QTimer.singleShot(256-1, (lambda: gApp.sendEvent(self.btn_menu, QKeyEvent(
            QEvent.KeyPress, Qt.Key_Tab, Qt.KeyboardModifier.NoModifier))))
        if self._parent:
            # WinMain will react also on this keys
            self._parent.installEventFilter(self)
    # end __init__

    def count(self) -> int:
        return self.tab_widget.count() - 1 # -1 for the '+' tab

    def currentIndex(self) -> int:
        return self.tab_widget.currentIndex()

    def slotModelNameChangedDuringSave(self, newName: str):
        """ set the Current Tab text """
        self.tab_widget.tabBar().setTabText(
            self.tab_widget.tabBar().currentIndex(), newName)

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        if (ev.key() in (Qt.Key_F2, Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space) 
            and not ev.modifiers() & Qt.ControlModifier
            ):
            self.editTab(self.tab_widget.tabBar().currentIndex())
            return
        
        if ev.key() in (Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_Minus):
            self.tab_widget.tabCloseRequested.emit(
                self.tab_widget.currentIndex())
            return
        
        if ev.key() in (Qt.Key_Insert, Qt.Key_Plus):
            self.createNewTab()
            return
        return super().keyPressEvent(ev)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if type(watched) == QTabBar:
            if event.type() == QEvent.Wheel:
                wheelEvent: QWheelEvent = event
                event.accept()
                # I really feel this way :))
                if wheelEvent.angleDelta().x() + wheelEvent.angleDelta().y() > 0:
                    self.goNextTab()
                else:
                    self.goPreviousTab()
                return True

            if event.type() == QEvent.KeyPress:
                ev: QKeyEvent = event
                if ev.keyCombination() == QKeyCombination(Qt.ControlModifier, Qt.Key_Right):
                    if self.tab_widget.currentIndex() + 1 <= self.tab_widget.count() - 1:
                        # there is place to move right
                        sigBlocked = self.blockSignals(True)
                        self.tab_widget.tabBar().moveTab(self.tab_widget.currentIndex(),self.tab_widget.currentIndex() + 1)
                        # Force SetVisible currentIndex Tab
                        set_visible_ix = self.tab_widget.currentIndex()
                        self.tab_widget.tabBar().setCurrentIndex(set_visible_ix - 1)
                        self.tab_widget.tabBar().setCurrentIndex(set_visible_ix)
                        self.blockSignals(sigBlocked)
                    return True

                if ev.keyCombination() == QKeyCombination(Qt.ControlModifier, Qt.Key_Left):
                    if self.tab_widget.currentIndex() - 1 >= 0:
                        # there is place to move left
                        sigBlocked = self.blockSignals(True)
                        self.tab_widget.tabBar().moveTab(self.tab_widget.currentIndex() - 1, self.tab_widget.currentIndex())
                        # Force SetVisible currentIndex Tab
                        set_visible_ix = self.tab_widget.currentIndex()
                        self.tab_widget.tabBar().setCurrentIndex(set_visible_ix - 1)
                        self.tab_widget.tabBar().setCurrentIndex(set_visible_ix)
                        self.blockSignals(sigBlocked)
                    return True

        elif issubclass(type(watched), QMainWindow) and event.type() == QEvent.KeyPress:
            ev: QKeyEvent = event
            if ev.key() == Qt.Key_Tab or ev.key() == Qt.Key_Backtab:
                if ev.modifiers() & Qt.ControlModifier:
                    event.accept()
                    if ev.key() == Qt.Key_Tab:
                        self.goNextTab()
                    else:  # Exclusive so :  Tab ^ Back_tab
                        self.goPreviousTab()
                    return True
            if ev.keyCombination() in ( QKeyCombination(Qt.ShiftModifier, Qt.Key_Insert),
                                        QKeyCombination(Qt.ControlModifier, Qt.Key_Insert),
                                        QKeyCombination(Qt.ShiftModifier, Qt.Key_Plus),
                                        QKeyCombination(Qt.ControlModifier, Qt.Key_Plus),
                                        QKeyCombination(Qt.ShiftModifier | Qt.KeypadModifier, Qt.Key_Plus),
                                        QKeyCombination(Qt.ControlModifier | Qt.KeypadModifier, Qt.Key_Plus)
                                        ):
                self.createNewTab()
                return True

            if ev.key() == Qt.Key_Delete or ev.key() == Qt.Key_Minus:
                if ev.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
                    self.tab_widget.tabCloseRequested.emit(self.tab_widget.currentIndex())
            # return False
        return super().eventFilter(watched, event)
    # end eventFilter

    def createNewTab(self):
        _newModel = None
        if self.fnGetNewModel:
            _newModel = self.fnGetNewModel()
            _newModel.setParent(self)
        self.addTabAndEdit(data=_newModel)
    #end createNewTab

    def addTabAndEdit(self, name: str = "", ix: Optional[int] = None, data: Union[XOR_model, QObject, None] = None, bEdit: Optional[bool] = True) -> int:
        match self.tab_widget.count():
            case nb if nb in (15, 20, 25):
                msgBox = QMessageBox(QMessageBox.Information, "Hmmm", "You know, you already have %d tabs...😁"
                                     % self.tab_widget.count(), QMessageBox.NoButton)
                btn = QPushButton()
                msgBox.addButton(btn, QMessageBox.RejectRole)
                btn.hide()
                QTimer.singleShot(nb * 100, lambda: msgBox.reject())
                msgBox.exec()
            case 30:
                msgBox = QMessageBox(QMessageBox.Information, "Hmmm 2",
                                     "You already have 30 tabs!\n This is the last one allowed...😐", QMessageBox.NoButton)
                btn = QPushButton()
                msgBox.addButton(btn, QMessageBox.RejectRole)
                btn.hide()
                QTimer.singleShot(3000, lambda: msgBox.reject())
                msgBox.exec()
            case nb if nb > 30:
                msgBox = QMessageBox(
                    QMessageBox.Information, "I told you!", "Let's say that's the limit 🤪")
                msgBox.exec()
                return self.tab_widget.currentIndex()
            case _:
                pass

        if name == "":
            name = "Model " + str(next(self._id_generator))
            if data and hasattr(data, "modelName"): # short-circuit
                    data.modelName = name

        if ix is None:
            ix = self.tab_widget.count() - 1 if self.tab_widget.count() >= 1 else 0

        self.tab_widget.insertTab(ix, QWidget(), name.strip())

        if data:
            self.tab_widget.tabBar().setTabData(ix, data)
            data.setParent(self) # that it will keep the data(QObject) alive
            if hasattr(data, "sigModelNameChanged"):
                data.sigModelNameChanged.connect(self.slotModelNameChangedDuringSave, Qt.UniqueConnection)

        self.tab_widget.tabBar().setCurrentIndex(ix)
        if bEdit:
            self.editTab(ix)
        return ix
    # end addTabAndEdit

    def editTab(self, ix: int):
        assert ix != self.tab_widget.tabBar().count()-1, "how is possible ?! :D"
        assert ix == self.tab_widget.currentIndex(), "how it's possible ?! :D"

        oldTxt = self.tab_widget.tabText(ix).strip()

        wdg_edit = QWidget(self)
        wdg_edit.setMinimumSize(QSize(10, 10))
        wdg_edit.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup | Qt.NoDropShadowWindowHint)  # type:ignore

        edt = FileNameLineEdit(defaultValidName=oldTxt, parent=wdg_edit)
        edt.setFont(self.tab_widget.tabBar().font())
        edt.setStyleSheet(
            "FileNameLineEdit { font-weight: normal; border: 1 solid #78a5a0; }")
        edt.setMinimumSize(QSize(10, 10))

        def _keyPressEvent(ev: QKeyEvent):
            if ev.key() in (Qt.Key_Tab, Qt.Key_Enter, Qt.Key_Return):
                wdg_edit.close()
            elif ev.key() == Qt.Key_Escape:
                edt.setText(str(oldTxt))
            return FileNameLineEdit.keyPressEvent(edt, ev)
        edt.keyPressEvent = _keyPressEvent

        def _textChanged(txt: str):
            fm: QFontMetrics = edt.fontMetrics()
            textSize = fm.size(Qt.TextSingleLine, txt, 0)
            wdg_edit.setFixedWidth(textSize.width() + 7)
            edt.resize(wdg_edit.size())
        edt.textChanged.connect(_textChanged)

        wdg_edit.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup | Qt.NoDropShadowWindowHint) 

        def _closeEvent(*args):
            # prevent flickering tabs
            newTabName = edt.text().strip()
            if self.tab_widget.tabText(ix).strip() != newTabName:
                self.tab_widget.setTabText(ix, newTabName)
                _data: XOR_model = self.tab_widget.tabBar().tabData(self.tab_widget.tabBar().currentIndex())
                if _data and hasattr(_data, "modelName"): # short-circuit
                    _data.modelName = newTabName

        wdg_edit.closeEvent = _closeEvent

        wdg_edit.show()
        wdg_edit.activateWindow()
        pTopLeft = self.tab_widget.tabBar().mapToGlobal(
            self.tab_widget.tabBar().tabRect(ix).topLeft())
        wdg_edit.move(pTopLeft + QPoint(9, 6))
        wdg_edit.resize(
            self.tab_widget.tabBar().tabSizeHint(ix) - QSize(41, 12))
        edt.resize(wdg_edit.size())

        edt.setText(oldTxt)
        edt.setFocus()
    # end editTab

    def removeTab(self, ix: Optional[int] = None):
        """
        Remove a tab from the tab widget.

        Args:
            ix (Optional[int]): The index of the tab to remove. If not provided, the current index will be used.

        Returns:
            None

        Raises:
            None
        """
        if self.tab_widget.count() <= 2 or self.tab_widget.tabText(ix).strip() == self._PLUS_UNICODE:
            # can't remove the last 'real' tab or the '+' tab
            return
        if not ix:
            ix = self.tab_widget.currentIndex()

        msgBox = QMessageBox(QMessageBox.Warning, "Closing model ", 'Do you want to save "%s" ?' % (
                                 self.tab_widget.tabText(ix).strip()))
        btnSave = msgBox.addButton("&Save", QMessageBox.AcceptRole)
        btnOk = msgBox.addButton("Do&n't Save", QMessageBox.AcceptRole)
        btnCancel = msgBox.addButton("&Cancel", QMessageBox.RejectRole)
        msgBox.exec()
        clickedButton = msgBox.clickedButton()
        if clickedButton == btnCancel:
            return
        elif clickedButton == btnSave:
            if self._parent:
                try:
                    if not self._parent.saveModel():
                        return
                except:
                    print(f"no 'saveModel()' interface in {type(self._parent)}")
                    return

        if ix == self.tab_widget.currentIndex():
            # we have to set the current index on another tab to avoid
            # PB : AUTO click on '+' on removeTab
            lst_try_new_crt = [+1, -1, +2, -2] 
            # find a new current index in this order of preference
            for dx in lst_try_new_crt:
                new_crt = ix + dx
                if 0 <= new_crt <= self.tab_widget.count() - 1:
                    if self.tab_widget.tabText(new_crt).strip() != self._PLUS_UNICODE:
                        # got it (into version without stuck '+' in last position)
                        # we have min 3 tabs so one should be found 
                        # now set the current index on it to avoid # PB : AUTO click on '+' on removeTab
                        self.tab_widget.setCurrentIndex(new_crt)
                        break # got it
        
        if self.tab_widget.tabBar().tabData(ix):  
            self.tab_widget.tabBar().tabData(ix).setParent(None) # destroy QObject, release memory
        self.tab_widget.removeTab(ix)
    # end removeTab
        
    def goNextTab(self):
        new_ix = self.tab_widget.currentIndex() + 1
        if new_ix <= self.tab_widget.count() - 2:
            self.tab_widget.setCurrentIndex(new_ix)

    def goPreviousTab(self):
        new_ix = self.tab_widget.currentIndex() - 1
        if new_ix >= 0:
            self.tab_widget.setCurrentIndex(new_ix)

    def getNextName(self, _name: str = "") -> str:
        """
        Returns the next available name for a tab in the tab widget.

        Args:
            _name (str): The base name to start with. Defaults to an empty string.

        Returns:
            str: The next available name for a tab.

        """
        if _name == "":
            return "Model " + str(next(self._id_generator))
        
        lstPrefixMatched = list(self.tab_widget.tabBar().tabText(i)
                                for i in range(self.tab_widget.tabBar().count())
                                if self.tab_widget.tabBar().tabText(i).startswith(_name)
                                )
        # the list of tab names that start with _name
        
        if not lstPrefixMatched:
            # if not such tab name, we are good to go with _name
            return _name

        for i in range(self.tab_widget.tabBar().count()):
            try_this = _name + f'({i + 1})'
            if try_this not in lstPrefixMatched:
                return try_this

        return 'impossible 😄'
    # end getNextName

    def setTabData(self, ix: int, data: QObject):
        """ set the data associated with the tab at the specified index."""
        data.setParent(self) # that it will keep the data(QObject) alive
        self.tab_widget.tabBar().setTabData(ix, data)

    def getTabData(self, ix: int) -> QObject:
        """Returns the data associated with the tab at the specified index."""
        return self.tab_widget.tabBar().tabData(ix)
# end class TabDragEdit
    

if __name__ == "__main__":
    gen_id = count(0)
    
    winMain = QMainWindow()
    winMain.setWindowTitle("TabDragEdit test")

    lstAct = []
    for i in range (5):
        act = QAction()
        f = lambda checked, val=i: print(i, val)
        act.triggered.connect(lambda checked : f(checked, i))
        act.setText(f"Action {i+1:02d} ")
        lstAct.append(act)

    menu = QMenu()
    menu.addActions(lstAct)

    def _newData():
        mArr = XOR_model(1)
        return mArr

    tab = TabDragEdit(winMain, _newData, XOR_model(3), menu)

    tab.addTabAndEdit(bEdit=False, data=XOR_model(3))
    tab.addTabAndEdit(bEdit=False, data=XOR_model(3))
    tab.addTabAndEdit(bEdit=False, data=XOR_model(3))
    tab.tab_widget.setCurrentIndex(0)

    ly = QVBoxLayout()
    ly.addWidget(tab)

    btn = QPushButton("Add with data provided(next to current)")
    btn.clicked.connect(lambda: tab.addTabAndEdit(
            tab.getNextName(tab.tab_widget.tabBar().tabText(tab.currentIndex())), 
            ix=tab.currentIndex() + 1, 
            data=XOR_model(3) )
            )
    ly.addWidget(btn)

    btn = QPushButton("Add in pos=0")
    btn.clicked.connect(lambda: tab.addTabAndEdit("Added_in_pos_0 " + str(next(gen_id)), 0))
    ly.addWidget(btn)

    btn = QPushButton("&Delete (current)")
    btn.clicked.connect(tab.removeTab)
    ly.addWidget(btn)

    ly.addWidget(btn)
    childWdg = QWidget()
    childWdg.setLayout(ly)
    dock = QDockWidget("dock tab edit test", parent=winMain)
    dock.setWidget(childWdg)
    dock.setMinimumHeight(100)

    winMain.addDockWidget(Qt.BottomDockWidgetArea, dock)
    winMain.resize(800, 200)
    winMain.show()

    gApp.exec()
