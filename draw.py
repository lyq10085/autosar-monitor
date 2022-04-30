"""
Simple example using BarGraphItem
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtWidgets

app = pg.mkQApp('monitor of thread')

win = QtWidgets.QMainWindow()

area = DockArea()
win.setCentralWidget(area)
win.resize(1000, 500)
win.setWindowTitle('WatchDog')
d1 = Dock("Gantt Show", size=(700, 400))
d2 = Dock("Thread Time Parameter", size=(300, 400))
area.addDock(d1, 'left')
area.addDock(d2, 'right')

view = pg.widgets.RemoteGraphicsView.RemoteGraphicsView()
# view.pg.setConfigOptions(antialias=True)  ## prettier plots at no cost to the main process!
view.setWindowTitle('pyqtgraph example: RemoteSpeedTest')
app.aboutToQuit.connect(view.close)

pgantt = pg.GraphicsLayoutWidget(show=True)
d1.addWidget(pgantt)
region = pg.LinearRegionItem()
region.setZValue(10)
region.setRegion([1, 2])
# Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this
# item when doing auto-range calculations.

label = pg.LabelItem(justify='right')
pgantt.addItem(label)
p1 = pgantt.addPlot(row=1, col=0)

p1.addItem(region, ignoreBounds=True)
bg1 = pg.BarGraphItem(x1=np.arange(5), y=np.arange(5), width=[1, 1, 1, 1, 1], height=[0.2] * 5, brush='b', pen='r')
p1.addItem(bg1)
vLine = pg.InfiniteLine(angle=90, movable=False)
hLine = pg.InfiniteLine(angle=0, movable=False)
p1.addItem(vLine, ignoreBounds=True)
p1.addItem(hLine, ignoreBounds=True)

vb = p1.vb


def mouseMoved(evt):
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    if p1.sceneBoundingRect().contains(pos):
        mousePoint = vb.mapSceneToView(pos)
        index = int(mousePoint.x())
        if index > 0 and index < 5:
            label.setText("<span style='font-size: 12pt'>time=%0.1f" % (mousePoint.x()))
        vLine.setPos(mousePoint.x())
        hLine.setPos(mousePoint.y())


proxy = pg.SignalProxy(pgantt.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)


def update(bars):
    pass



win.show()
pg.exec()
