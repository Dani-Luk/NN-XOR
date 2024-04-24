""" 
    Interval Class [min, max] 
    Line Class ax + by + c = 0
        distFromPoint(p:QPointF) -> Tuple[float, QPointF]
        PolygonsClockwiseLine(margins:QMarginsF = QMarginsF(0, 0, 0, 0)) -> Tuple[List[QPointF], List[QPointF], List[QPointF]]
"""

from typing import List, Set, Tuple
import numpy as np

from dataclasses import dataclass

from PySide6.QtCore import QMarginsF, QPointF


@dataclass
class Interval:
    """A class representing a float interval [min, max]."""
    min: float
    max: float

    def __post_init__(self):
        """Check if the interval is valid."""
        assert self.min <= self.max, "The minimum value must be less than or equal to the maximum value."

    def __contains__(self, item):
        """Check if an item is within the interval."""
        if type(item) is float or isinstance(item, np.floating):
            return self.min <= item <= self.max
        elif type(item) is np.ndarray:
            return ((self.min <= item).all() <= self.max).all()
    
    def __iter__(self):
        """Return an iterator over the interval's minimum and maximum values."""
        return (x for x in (self.min, self.max))
        # or :
        # yield self.min
        # yield self.max


# @dataclass(init=False)
@dataclass()
class Line:
    """
    Represents a line in the form of ax + by + c = 0.

    Attributes:
        a (float): The coefficient of x in the line equation.
        b (float): The coefficient of y in the line equation.
        c (float): The constant term in the line equation.
    """

    a: float
    b: float
    c: float

    def __post_init__(self):
        """Check if the line is valid."""
        assert (self.a != 0 or self.b != 0) or self.c == 0, "At least one of a and b must be non-zero, OR also c == 0"
        

    def getY(self, x: float) -> float:
        """
        Calculates the y-coordinate of a point on the line given the x-coordinate.

        Args:
            x (float): The x-coordinate of the point.

        Returns:
            float: The y-coordinate of the point on the line.
        """
        assert self.b != 0, "b must be non-zero"
        return (-self.c - self.a * x) / self.b

    def getX(self, y: float) -> float:
        """
        Calculates the x-coordinate of a point on the line given the y-coordinate.

        Args:
            y (float): The y-coordinate of the point.

        Returns:
            float: The x-coordinate of the point on the line.
        """
        assert self.a != 0, "a must be non-zero"
        return (-self.c - self.b * y) / self.a

    def FctForXY(self, x: float, y: float) -> float:
        """
        Calculates the value of the line equation ax + by + c for the given x and y coordinates.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.

        Returns:
            float: The value of the line equation for the given coordinates.
        """
        return self.a * x + self.b * y + self.c

    def distFromPoint(self, p: QPointF) -> Tuple[float, QPointF]:
        """ 
        Calculate the distance from a point to a line and return the distance and the position of the corresponding point on the line.
        Args:
            p (QPointF): The point for which the distance is calculated.

        Returns:
            Tuple[float, QPointF]: A tuple containing the distance from the point to the line 
            and the position of the corresponding point on the line.
        """
        a2_plus_b2 = self.a ** 2 + self.b ** 2
        dist = abs(self.a * p.x() + self.b * p.y() + self.c) / a2_plus_b2 ** 0.5
        xLine = (self.b * (self.b * p.x() - self.a * p.y()) - self.a * self.c) / a2_plus_b2
        yLine = (self.a * (self.a * p.y() - self.b * p.x()) - self.b * self.c) / a2_plus_b2
        return (dist, QPointF(xLine, yLine))

    def __getPointsCrossing_0_1_Square(self, margins: QMarginsF) -> List[QPointF]:
        """
        Get the points where the line represented by the equation ax + by + c = 0 
        crosses the square with side length 1 + the given margins.

        Args:
            margins (QMarginsF): The margins to be applied to the square.

        Returns:
            List[QPointF]: A list of QPointF objects representing the points of intersection.
        """
        setPoints: Set[tuple[float, float]] = set()  # to avoid duplicates because the interval is closed
        xinterval = Interval(0 - margins.left(), 1 + margins.right())
        yinterval = Interval(0 - margins.bottom(), 1 + margins.top())
        if self.a:
            for y in yinterval:
                x = self.getX(y)
                if x in xinterval:
                    setPoints.add((x, y))
        if self.b:
            for x in xinterval:
                if x not in (x_checked[0] for x_checked in setPoints):
                    y = self.getY(x)
                    if y in yinterval:
                        setPoints.add((x, y))
        return list(QPointF(*x) for x in setPoints)
    # end of __getPointsCrossing_0_1_Square

    def PolygonsClockwiseLine(self, margins:QMarginsF = QMarginsF(0, 0, 0, 0)) -> Tuple[List[QPointF], List[QPointF], List[QPointF]]:
        """
        Having 00, 01, 11, 10 square +/- margins
        Return tuple :
        the list of intersection points of line with the square (len = 0 / 1 / 2)
        and corresponding 1 or 2 polygons(closed) formed by the line with the sides of the square 
        """
        lstPoints = [
                    QPointF(0 - margins.left(), 0 - margins.bottom()), 
                    QPointF(0 - margins.left(), 1 + margins.top()), 
                    QPointF(1 + margins.right(), 1 + margins.top()), 
                    QPointF(1 + margins.right(), 0 - margins.bottom())
                    ]
        lstCrossingPoints = self.__getPointsCrossing_0_1_Square(margins)

        if len(lstCrossingPoints) <= 1 :
                return (lstCrossingPoints, lstPoints + [lstPoints[0]], [])

        assert len (lstCrossingPoints) == 2, " Non Euclidean space ?! :) " 
        # We have 2 
        p1 = lstCrossingPoints[0] 
        p2 = lstCrossingPoints[1] 
        line = [p1, p2]
        i = 0
        lst_i = []
        p = line.pop(0)
        inserted = 0
        while inserted < 2 :
            p11 = lstPoints[i]
            p22 = lstPoints[(i+1) % len(lstPoints)]
            if p11.x() == p22.x() == p.x() or p11.y() == p22.y() == p.y() :
                inserted += 1 
                if p in lstPoints:
                    # print("NOT insert(i+1, p) cause EXIST:", i+1, p)
                    i = (i + 1) % len(lstPoints)
                else:
                    # print("insert(i+1, p) :", i+1, p)
                    lstPoints.insert(i+1, p)
                    i = (i + 2) % len(lstPoints)
                if line:
                    p = line.pop(0)
            else:
                i = (i + 1) % len(lstPoints)

        lst_i = []
        i = 0
        # print("lstPoints, line_p1, line_p2", lstPoints, p1, p2)
        while len(lst_i) < 2:
            if lstPoints[i] == p1 or lstPoints[i] == p2 :
                lst_i.append(i)
            i += 1

        i1 = lst_i[0]
        i2 = lst_i[1]
        polygon1 = lstPoints[i1 : i2+1]
        polygon2 = lstPoints[i2 : ] + lstPoints[ : i1+1]
        return (lstCrossingPoints, polygon1, polygon2)
# end of class Line


