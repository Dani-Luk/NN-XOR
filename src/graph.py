""" 
This module provides a custom widget for displaying a neural network graph. 
It is used to visualize the neural network's architecture and the values of its nodes and edges.
The graph is drawn using the networkx and matplotlib libraries.
The graph is updated using a QTimer object to avoid redrawing the graph too frequently.
"""

import PySide6.QtCore as QtCore
# force PySide6 to use Qt binding

from itertools import chain
import random 

import networkx as nx

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PySide6.QtWidgets import QWidget, QMainWindow, QVBoxLayout
from PySide6.QtCore import QSize, QMargins, QTimer, QElapsedTimer
from PySide6.QtGui import QPainter, QPen

from global_stuff import MxCOLORS, gApp

__all__ = ['Graph', ]

X0 = 'x' + chr(0x2080)
X1 = 'x' + chr(0x2081)
B0 = 'b0'
B1 = 'b1'
Z10 = 'z' + chr(0x2080)
Z11 = 'z' + chr(0x2081)
A0 = 'a' + chr(0x2080)
A1 = 'a' + chr(0x2081)
B2 = 'b2'
Z2 = 'z' + chr(0x2082)
Y = 'ŷ' 

class FigureCanvas2(FigureCanvas):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen_width = 1
        painter.setPen(QPen(MxCOLORS.TBL_OUTER_BORDER_GRAY, pen_width))
        painter.drawRect(self.rect() - QMargins(0, 0, 1, 1))

class Graph(QWidget):
    """
    A custom widget for displaying a neural network graph.

    Attributes:
        EMIT_MIN_TIME (int): The minimum time in milliseconds to wait before redrawing the graph.
        redrawTimer (QTimer): A QTimer object for scheduling the graph redraw.
        canvas (FigureCanvas2): The canvas for displaying the graph.
        ax (matplotlib.axes.Axes): The axes object for the graph.
        nodes_pos (dict): A dictionary mapping node names to their positions on the graph.
        G (networkx.DiGraph): The graph object representing the neural network.
        node_color (list): A list of colors for the nodes in the graph.
        edge_color (list): A list of colors for the edges in the graph.
        dictNodesLabels (dict): A dictionary mapping node names to their labels.
    """

    EMIT_MIN_TIME = 200 # min milliseconds to redraw, no rush

    def __init__(self) -> None:
        """
        Initializes the Graph widget.
        """
        super().__init__()
        self.redrawTimer = None
        self.canvas = FigureCanvas2() 
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.ax = self.canvas.figure.add_subplot(111)
        for spine in ['top', 'right', 'left', 'bottom']:
            self.ax.spines[spine].set_visible(False)

        self.nodes_pos = {
            X0: (0, 500),
            X1: (0, 200),
            B0: (100, 600),
            B1: (100, 100),
            Z10 : (280, 500),
            Z11 : (280, 200),
            A0 : (430, 500),
            A1 : (430, 200),
            B2: (550, 125),
            Z2: (650, 350),
            Y: (825, 350),
        }
        self.G = nx.DiGraph()

        self.G.add_nodes_from(self.nodes_pos)

        self.G.add_edge(X0, Z10, weight = '%0.3f' % (20 - 40 * random.random()))
        self.G.add_edge(X0, Z11, weight = '%0.3f' % (20 - 40 * random.random()))
        self.G.add_edge(X1, Z10, weight = '%0.3f' % (20 - 40 * random.random()))
        self.G.add_edge(X1, Z11, weight = '%0.3f' % (20 - 40 * random.random()))

        self.G.add_edge(B0, Z10, weight = '%0.3f' % (20 - 40 * random.random()))
        self.G.add_edge(B1, Z11, weight = '%0.3f' % (20 - 40 * random.random()))

        self.G.add_edge(Z10, A0, activation = 'ReLU')
        self.G.add_edge(Z11, A1, activation = 'ReLU')

        self.G.add_edge(A0, Z2, weight = '%0.3f' % (20 - 40 * random.random()))
        self.G.add_edge(A1, Z2, weight = '%0.3f' % (20 - 40 * random.random()))
        
        self.G.add_edge(B2, Z2, weight = '%0.3f' % (20 - 40 * random.random()),)

        self.G.add_edge(Z2, Y, activation = 'Sigmoid')

        self.node_color=['#%06x' % MxCOLORS.W1_Row0.__hash__(), '#%06x' % MxCOLORS.W1_Row1.__hash__(), 
                    '#%06x' % MxCOLORS.BIAS.__hash__(), '#%06x' % MxCOLORS.BIAS.__hash__(), 
                    '#%06x' % MxCOLORS.W1_Col0.__hash__(), '#%06x' % MxCOLORS.W1_Col1.__hash__(), 
                    '#%06x' % MxCOLORS.A1_0.__hash__(), '#%06x' % MxCOLORS.A1_1.__hash__(), 
                    '#%06x' % MxCOLORS.BIAS.__hash__(), '#%06x' % MxCOLORS.Z2.__hash__(), 
                    '#%06x' % MxCOLORS.Y.__hash__(), 
                    ] 
        
        self.edge_color=['#%06x' % MxCOLORS.W1_00.__hash__(), '#%06x' % MxCOLORS.W1_01.__hash__(), 
                    '#%06x' % MxCOLORS.W1_10.__hash__(), '#%06x' % MxCOLORS.W1_11.__hash__(), 
                    '#%06x' % MxCOLORS.BIAS.__hash__(), '#%06x' % MxCOLORS.BIAS.__hash__(), 
                    'grey', 'grey',
                    '#%06x' % MxCOLORS.W2_0.__hash__(), '#%06x' % MxCOLORS.W2_1.__hash__(), 
                    '#%06x' % MxCOLORS.BIAS.__hash__(), 'grey',
                    ]

        self.dictNodesLabels = dict()
  
    def sizeHint(self) -> QSize:
        """
        Returns the recommended size for the widget.

        Returns:
            QSize: The recommended size for the widget.
        """
        return QSize(550, 145)        

    def drawUpdated_no_rush(self, font_color='black', nodes_font_size=9):
        """
        Redraws the graph without rushing.

        Args:
            font_color (str, optional): The color of the node labels. Defaults to 'black'.
            nodes_font_size (int, optional): The font size of the node labels. Defaults to 9.
        """
        if self.redrawTimer is None:
            self.redrawTimer = QTimer(self)
            self.redrawTimer.setSingleShot(True)
            self.redrawTimer.timeout.connect(lambda: self.__drawUpdated(font_color, nodes_font_size))
            self.redrawTimer.start(self.EMIT_MIN_TIME)
        else:
            self.redrawTimer.start(self.EMIT_MIN_TIME)

    def __drawUpdated(self, font_color='black', nodes_font_size=9):
        """
        Redraws the graph.

        Args:
            font_color (str, optional): The color of the node labels. Defaults to 'black'.
            nodes_font_size (int, optional): The font size of the node labels. Defaults to 9.
        """
        if not self.isVisible() :
            return

        timer = QElapsedTimer() 
        timer.start()
        self.redrawTimer = None
        self.ax.clear()
        nx.draw_networkx_nodes(self.G, pos=self.nodes_pos,
                               node_size=[300 if k[0] == 'b' else 400 for (k, _) in self.nodes_pos.items()],
                               node_color=self.node_color, edgecolors='silver', 
                               ax=self.ax, margins=(0, 0.05))

        nx.draw_networkx_labels(self.G, self.nodes_pos, labels=self.dictNodesLabels, 
                                font_size=nodes_font_size, font_color=font_color, font_family="sans-serif", ax=self.ax, alpha=1)
        
        nx.draw_networkx_labels(self.G, self.nodes_pos, labels=dict( (k, '+1') for k, _ in self.nodes_pos.items() if k[0] == 'b'), 
                                font_size=nodes_font_size-1, font_family="sans-serif", ax=self.ax, alpha=1)
    
        nx.draw_networkx_edges (self.G, self.nodes_pos, edge_color=self.edge_color, width=1.5, 
                                arrows=True, arrowstyle='->', arrowsize=14, ax=self.ax, alpha=1)
        
        edge_labels = nx.get_edge_attributes(self.G, "weight")
        nx.draw_networkx_edge_labels(self.G, self.nodes_pos, edge_labels, label_pos=0.65, verticalalignment="center", rotate=False, ax=self.ax, 
                                     font_size=nodes_font_size-1, alpha=1)
        edge_labels_actv = nx.get_edge_attributes(self.G, "activation")
        nx.draw_networkx_edge_labels(self.G, self.nodes_pos, edge_labels_actv,verticalalignment="center", rotate=False, ax=self.ax, 
                                     font_size=nodes_font_size-1, font_color='grey', alpha=1)
        
        self.canvas.figure.subplots_adjust(0, 0, 1, 1)
        self.ax.figure.canvas.draw()        
        
        # print("graph __drawUpdated elapsed:", timer.elapsed(), '\n')

    def setValues(self, *args):
        """
        Sets the values of the nodes in the graph.

        Args:
            *args: Variable number of arguments representing the values of the nodes.
        """
        if args[0] is None:
            self.ResetNodes()
        else:
            self.SetNodes(*args)

    def SetNodes(self, x, z1, a, z2, y):
        """
        Sets the values of the input, hidden, and output nodes in the graph.

        Args:
            x (ndarray): The values of the input nodes.
            z1 (ndarray): The values of the hidden nodes.
            a (ndarray): The values of the activation nodes.
            z2 (ndarray): The values of the hidden nodes.
            y (ndarray): The values of the output nodes.
        """
        it = chain(x.flat, z1.flat, a.flat, z2.flat, y.flat)
        for k, _ in self.nodes_pos.items() :
            if k not in [B0, B1, B2 ] :
                self.dictNodesLabels[k] = '%0.3f' % (next(it, '')) + '\n|\n' + k + '\n\n'
        self.drawUpdated_no_rush(font_color='#cc0000', nodes_font_size=9)
    
    def ResetNodes(self):
        """
        Resets the values of the nodes in the graph to their default values.
        """
        for k, _ in self.nodes_pos.items() :
            if k not in [B0, B1, B2 ] :
                self.dictNodesLabels[k] = k 
        self.drawUpdated_no_rush()        

    def setEdges(self , w1, b1, w2, b2, activation1, activation2):
        """
        Sets the weights and activations of the edges in the graph.

        Args:
            w1 (ndarray): The weights of the edges between the input and hidden nodes.
            b1 (ndarray): The weights of the edges between the bias and hidden nodes.
            w2 (ndarray): The weights of the edges between the hidden and output nodes.
            b2 (ndarray): The weights of the edges between the bias and output nodes.
            activation1 (str): The activation function for the hidden nodes.
            activation2 (str): The activation function for the output nodes.
        """
        if w1 is not None:
            self.G[X0][Z10].update({'weight' :'%0.3f' % w1[0][0]})
            self.G[X0][Z11].update({'weight' :'%0.3f' % w1[0][1]})
            self.G[X1][Z10].update({'weight' :'%0.3f' % w1[1][0]})
            self.G[X1][Z11].update({'weight' :'%0.3f' % w1[1][1]})
        if b1 is not None:
            self.G[B0][Z10].update({'weight' :'%0.3f' % b1[0][0]})
            self.G[B1][Z11].update({'weight' :'%0.3f' % b1[0][1]})
        if w2 is not None:
            self.G[A0][Z2].update({'weight' :'%0.3f' % w2[0][0]})
            self.G[A1][Z2].update({'weight' :'%0.3f' % w2[1][0]})
        if b2 is not None:
            self.G[B2][Z2].update({'weight' :'%0.3f' % b2[0][0]})
        if activation1 is not None:
           self.G[Z10][A0].update({'activation': activation1})
           self.G[Z11][A1].update({'activation': activation1})
        if activation2 is not None:
            self.G[Z2][Y].update({'activation': activation2})


if __name__ == "__main__":
    winMain = QMainWindow()
    
    wdgGraph = Graph()
    wdgGraph.ResetNodes()
   
    winMain.setCentralWidget(wdgGraph)
    winMain.show()

    gApp.exec()
   
