import unittest
import context

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QKeySequence 
from PySide6.QtWidgets import QWidget
from PySide6.QtTest import QTest
from tabs import TabDragEdit
from unittest.mock import MagicMock


class test_TabDragEdit(unittest.TestCase):
    def setUp(self):
        self.tabs = TabDragEdit(parent=MockParent())

    def test_getNextName_no_matching_tabs(self):
        result = self.tabs.getNextName("Tab")
        self.assertEqual(result, "Tab")

    def test_getNextName_matching_tabs(self):
        self.tabs.addTabAndEdit("Tab(1)", bEdit = False)
        self.tabs.addTabAndEdit("Tab(2)", bEdit = False)
        self.tabs.addTabAndEdit("Tab(3)", bEdit = False)
        result = self.tabs.getNextName("Tab")
        self.assertEqual(result, "Tab(4)")

    def test_getNextName_matching_tabs_tabs(self):
        self.tabs.addTabAndEdit("Tab(1)", bEdit = False)
        self.tabs.addTabAndEdit("Tab(2)", bEdit = False)
        self.tabs.addTabAndEdit("Tab(3)", bEdit = False)
        result = self.tabs.getNextName("Tab(1)")
        self.assertEqual(result, "Tab(1)(1)")


    def test_removeTab_with_index(self):
        # Proposed by Copilot ...
        # Me : playing with, to understand what this means... :D
        
        # Arrange
        self.tabs.tab_widget.count = MagicMock(return_value=4)
        self.tabs.tab_widget.tabText = MagicMock(return_value="Tab 3")
        self.tabs.tab_widget.tabBar().tabData = MagicMock()
        self.tabs.tab_widget.removeTab = MagicMock()

        # Act
        QTimer.singleShot(256, lambda: QTest.keyClick(self.tabs, Qt.Key_N, Qt.AltModifier)) # Alt+N = Close &Not save
        self.tabs.removeTab(2)

        # Assert
        self.tabs.tab_widget.count.assert_called_once()
        # self.tabs.tab_widget.tabText.assert_called_once_with(2)
        from unittest.mock import call
        self.tabs.tab_widget.tabText.assert_has_calls([call(2), call(2)])
        # self.tabs.tab_widget.tabBar().tabData.assert_called_once_with(2)
        self.tabs.tab_widget.tabBar().tabData.assert_has_calls([call(2), call().__bool__(), call(2), call().setParent(None)])
        self.tabs.tab_widget.removeTab.assert_called_once_with(2)


    def test_removeTab_matching_tabs_AcceptRole(self):
        self.tabs.addTabAndEdit("Tab(1)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(2)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(3)", bEdit=False)
        
        QTimer.singleShot(256, lambda: QTest.keyClick(self.tabs, Qt.Key_N, Qt.AltModifier)) # Alt+N = Close &Not save
        self.tabs.removeTab(1)
        self.assertEqual(self.tabs.count(), 3) # 2 + 1 (Tab(0) is added by default)


    def test_removeTab_current_index(self):
        self.tabs.addTabAndEdit("Tab(1)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(2)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(3)", bEdit=False)
        self.tabs.tab_widget.setCurrentIndex(1)
        
        QTimer.singleShot(256, lambda: QTest.keyClick(self.tabs, Qt.Key_N, Qt.AltModifier)) # Alt+N = Close &Not save
        self.tabs.removeTab(1)
        
        self.assertEqual(self.tabs.tab_widget.currentIndex(), 1)


    def test_removeTab_save_model(self):
        self.tabs.addTabAndEdit("Tab(1)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(2)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(3)", bEdit=False)
        mock = MockData()
        self.tabs.setTabData(1, mock)
        
        QTimer.singleShot(256, lambda: QTest.keyClick(self.tabs, Qt.Key_S, Qt.AltModifier)) # Alt+S = Close & Save
        
        self.tabs.removeTab(1)
        
        self.assertTrue(self.tabs.parent().saveModel_called)


    def test_removeTab_CancelRole(self):

        self.tabs.addTabAndEdit("Tab(1)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(2)", bEdit=False)
        self.tabs.addTabAndEdit("Tab(3)", bEdit=False)
        
        QTimer.singleShot(256, lambda: QTest.keyClick(self.tabs, Qt.Key_C, Qt.AltModifier)) # Alt+C = Cancel
        
        self.tabs.removeTab(1) # canceled so same number of tabs
        
        self.assertEqual(self.tabs.count(), 4) # 3 + 1 (Tab(0) is added by default)


    def test_removeTab_destroy_object_AcceptRole(self):
        # 
        # Nota: Tab(0) already exists!
        self.tabs.addTabAndEdit("Tab(1)", data = MockData(self.tabs), bEdit=False)
        self.tabs.addTabAndEdit("Tab(2)", data = MockData(self.tabs), bEdit=False)
        self.tabs.addTabAndEdit("Tab(3)", data = MockData(self.tabs), bEdit=False)
        # import weakref
        import gc
        obj = self.tabs.getTabData(1)
        
        referrers = gc.get_referrers(obj)
        # print(f'There are {len(referrers)} strong references to the object')
        
        QTimer.singleShot(256, lambda: QTest.keyClick(self.tabs, Qt.Key_N, Qt.AltModifier)) # Alt+N = Close &Not save
        self.tabs.removeTab(1) # removing the tab must also remove the object strong reference

        # gc.collect() # not necessary... ? 
        
        referrers = gc.get_referrers(obj)
        # print(f'There are {len(referrers)} strong references to the object')
        
        self.assertEqual(len(referrers), 0)


class MockParent(QWidget):
    def saveModel(self):
        self.saveModel_called = True
        return True

class MockData(QObject):
    pass


if __name__ == '__main__':
    unittest.main()