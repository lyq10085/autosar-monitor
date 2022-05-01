"""
Simple example using BarGraphItem
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtWidgets
from threading import Thread


def runGUI(pipe):
    # 每个bar = (threadid, 开始时间, 持续时间, 持续状态)
    bars = None

    def runrecv(pipe):
        global bars
        num = 0
        while True:
            bars = pipe.recv()
            bars = np.compress(bars[:, 3] != 3, bars, axis=0)  # 不画出停止运行的thread
            bars = np.compress(bars[:, 2] != 0, bars, axis=0)  # 持续时间为0的bars
            if bars.size:
                bars_running = np.compress(bars[:, 3] == 2, bars, axis=0)
                bars_waiting = np.compress(bars[:, 3] == 1, bars, axis=0)
                bars_ready = np.compress(bars[:, 3] == 0, bars, axis=0)
                # print(bars, '\n')
            # todo 更新view视图
                bg_run = pg.BarGraphItem(x0=bars_running[:, 1] / 100, y=bars_running[:, 0], width=bars_running[:, 2]/100,
                                         height=1, brush='r', pen=pg.mkPen('r', width=0.01))
                p1.addItem(bg_run)
                if bars_waiting.size:
                    bg_wait = pg.BarGraphItem(x0=bars_waiting[:, 1] / 100, y=bars_waiting[:, 0], width=bars_waiting[:, 2]/100,
                                              height=1, brush='y', pen=pg.mkPen('y', width=0.01))
                    p1.addItem(bg_wait)
                if bars_ready.size:
                    bg_ready = pg.BarGraphItem(x0=bars_ready[:, 1] / 100, y=bars_ready[:, 0], width=bars_ready[:, 2]/100,
                                               height=3, brush='g', pen=pg.mkPen('g', width=0.01))
                    p1.addItem(bg_ready)

                num += 1
                print(num)

    t1 = Thread(target=runrecv, args=(pipe,))  # 接受数据线程
    t1.start()

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

    pgantt = pg.GraphicsLayoutWidget(show=True)
    d1.addWidget(pgantt)
    region = pg.LinearRegionItem()
    region.setZValue(10)
    region.setRegion([1, 2])

    label = pg.LabelItem(justify='right')
    pgantt.addItem(label)
    p1 = pgantt.addPlot(row=1, col=0)

    p1.addItem(region, ignoreBounds=True)

    # bg1 = pg.BarGraphItem(x1=np.arange(5), y=np.arange(5), width=[1, 1, 1, 1, 1], height=[0.2] * 5, brush='b', pen='r')
    #
    #
    # p1.addItem(bg1)

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
            if index > 0 and index < 1e9:
                label.setText("<span style='font-size: 12pt'>time=%0.1f" % (mousePoint.x()))
            vLine.setPos(mousePoint.x())
            hLine.setPos(mousePoint.y())

    proxy = pg.SignalProxy(pgantt.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)

    win.show()
    pg.exec()
