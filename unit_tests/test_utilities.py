import unittest
import context

from context import TestCase_ext

from typing import List
from utilities import Line
from PySide6.QtCore import QPointF, QMarginsF

QPointF.__iter__ = lambda self: (i for i in (self.x(), self.y()) )
# create a new iterator method for QPointF from a generator yielding x and y coordinates

class TestLine(TestCase_ext):

    def test_getY(self):
        line = Line(2, 3, 4)
        result = line.getY(5)
        self.assertAlmostEqual(result, -14 / 3)

    def test_getX(self):
        line = Line(2, 3, 4)
        result = line.getX(5)
        self.assertAlmostEqual(result, -19 / 2)

    def test_FctForXY(self):
        line = Line(2, 3, 4)
        result = line.FctForXY(5, 6)
        self.assertAlmostEqual(result, 32)

    def test_distFromPoint(self):
        line = Line(1, 1, -2)
        p = QPointF(2, 2)
        dist, point = line.distFromPoint(p)
        self.assertIterableAlmostEqual([dist, point], 
                                       [2 ** 0.5, QPointF(1, 1)]
                                       )


    def test_PolygonsClockwiseLine_0(self):
        line = Line(1, 1, -4.00000001)
        margins = QMarginsF(0, 1, 1, 0)
        result = line.PolygonsClockwiseLine(margins)
        expected_result = ([], 
                           [QPointF(0.000000, 0.000000),
                            QPointF(0.000000, 2.000000),
                            QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 0.000000),
                            QPointF(0.000000, 0.000000)
                           ],
                           []
                           )

        self.assertIterableAlmostEqual(result, expected_result, "intersection points == 0 not passed")

    
    def test_PolygonsClockwiseLine_1(self):
        line = Line(1, 1, -4.0)
        margins = QMarginsF(0, 1, 1, 0)
        result = line.PolygonsClockwiseLine(margins)
        expected_result = ([QPointF(2.000000, 2.000000)
                            ], 
                           [QPointF(0.000000, 0.000000),
                            QPointF(0.000000, 2.000000),
                            QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 0.000000),
                            QPointF(0.000000, 0.000000)
                           ],
                           []
                           )

        self.assertIterableAlmostEqual(result, expected_result, "intersection points == 1 not passed")

    def test_PolygonsClockwiseLine_2(self):
        line = Line(1, 1, -3.99999997)
        margins = QMarginsF(0, 1, 1, 0)
        result = line.PolygonsClockwiseLine(margins)
        expected_result = ([QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 2.000000)
                            ], 
                           [QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 2.000000)
                           ],
                           [QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 0.000000),
                            QPointF(0.000000, 0.000000),
                            QPointF(0.000000, 2.000000),
                            QPointF(2.000000, 2.000000)
                            ]
                           )

        self.assertIterableAlmostEqual(result, expected_result, "intersection points == 2 not passed")

    def test_PolygonsClockwiseLine_2_bisect(self):
        line = Line(1, 1, -2)
        margins = QMarginsF(0, 1, 1, 0)
        result = line.PolygonsClockwiseLine(margins)
        expected_result = ([QPointF(0.000000, 2.000000),
                            QPointF(2.000000, 0.000000)
                            ], 
                           [QPointF(0.000000, 2.000000),
                            QPointF(2.000000, 2.000000),
                            QPointF(2.000000, 0.000000)
                           ],
                           [QPointF(2.000000, 0.000000),
                            QPointF(0.000000, 0.000000),
                            QPointF(0.000000, 2.000000),
                            ]
                           )

        self.assertIterableAlmostEqual(result, expected_result, "intersection points == 2 bisect not passed")


    def test_getPointsCrossing_0_1_Square(self):
        line = Line(2, 3, 4)
        margins = QMarginsF(1, 2, 3, 4)
        result = line._Line__getPointsCrossing_0_1_Square(margins)
        expected_result = [
            QPointF(-1.000000, -2/3), 
            QPointF(4.000000, -4.0000000)
            ]

        self.assertIterableAlmostEqual(result, expected_result, "test_getPointsCrossing_0_1_Square not passed")

if __name__ == '__main__':
    unittest.main()