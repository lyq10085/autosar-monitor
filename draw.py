"""
Simple example using BarGraphItem
"""
import json
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtWidgets
from PyQt5.QtWidgets import QPushButton
# from PyQt5.QtCore import pyqtSignal
from threading import Thread

stopsign = False


def gettopsign():
    global stopsign
    return stopsign


def tostop():
    global stopsign
    if not stopsign:
        stopsign = True


def tostart():
    global stopsign
    if stopsign:
        stopsign = False


def runGUI(pipe, core_num=1):
    # 每个bar = (threadid, 开始时间, 持续时间, 持续状态)
    bars = None
    # parameters = { threadid : (Instance, CET_sum, WCET, RT_sum, WCRT, IPT_sum, WCIPT), ...}
    parameters = {}
    with open('./configuration.json', 'r') as f:
        conf_dict = json.load(f)

    def runrecv(pipe):
        nonlocal bars, parameters
        num = 0
        while True:
            bars, parameters = pipe.recv()
            # print(parameters)
            bars = np.compress(bars[:, 3] != 3, bars, axis=0)  # 不画出停止运行的thread
            bars = np.compress(bars[:, 2] != 0, bars, axis=0)  # 持续时间为0的bars

            # 区分core

            if bars.size:
                bars_running = np.compress(bars[:, 3] == 2, bars, axis=0)
                bars_waiting = np.compress(bars[:, 3] == 1, bars, axis=0)
                bars_ready = np.compress(bars[:, 3] == 0, bars, axis=0)
                # print(bars, '\n')
                # todo 更新view视图
                bg_run = pg.BarGraphItem(x0=bars_running[:, 1] * 0.00001, y=bars_running[:, 0],
                                         width=bars_running[:, 2] * 0.00001,
                                         height=1, brush='r', pen=pg.mkPen('r', width=0.01))
                p1.addItem(bg_run)
                if bars_waiting.size:
                    bg_wait = pg.BarGraphItem(x0=bars_waiting[:, 1] * 0.00001, y=bars_waiting[:, 0],
                                              width=bars_waiting[:, 2] * 0.00001,
                                              height=1, brush='y', pen=pg.mkPen('y', width=0.01))
                    p1.addItem(bg_wait)
                if bars_ready.size:
                    bg_ready = pg.BarGraphItem(x0=bars_ready[:, 1] * 0.00001, y=bars_ready[:, 0],
                                               width=bars_ready[:, 2] * 0.00001,
                                               height=3, brush='g', pen=pg.mkPen('g', width=0.01))
                    p1.addItem(bg_ready)

                num += 1
                # print(num)

    #
    # t1 = Thread(target=runrecv, args=(pipe,))  # 接受数据线程
    # t1.start()
    # 信号

    app = pg.mkQApp('monitor of thread')

    # mainwindow基本属性
    win = QtWidgets.QMainWindow()
    win.resize(1500, 800)
    win.setWindowTitle('WatchDog')

    # dock块设置
    area = DockArea()
    win.setCentralWidget(area)
    d1 = Dock("Gantt Show", size=(900, 400))
    d2 = Dock("Thread Time Parameter", size=(500, 400))
    area.addDock(d1, 'left')
    area.addDock(d2, 'right')

    # dock内部设置
    pgantt = pg.GraphicsLayoutWidget(show=True)
    d1.addWidget(pgantt)
    mylayout = pg.LayoutWidget()
    d2.addWidget(mylayout)

    # graphicslayout/layoutwidget内部设置
    label = pg.LabelItem(justify='right')
    pgantt.addItem(label)
    p1 = pgantt.addPlot(row=1, col=0)
    p2 = pgantt.addPlot(row=1, col=1)
    p3 = pgantt.addPlot(row=2, col=0)
    p4 = pgantt.addPlot(row=2, col=1)
    p5 = pgantt.addPlot(row=3, col=0)
    p6 = pgantt.addPlot(row=3, col=1)

    t1 = Thread(target=runrecv, args=(pipe,))  # 接受数据线程
    t1.start()

    table = pg.TableWidget()
    pbutton1 = QPushButton('STOP')
    pbutton2 = QPushButton('START')
    pbutton1.setText('STOP')
    # pbutton2 = QPushButton('START')
    # pbutton2.setText('START')
    pbutton1.clicked.connect(tostop)
    # pbutton2.clicked.connect()
    mylayout.addWidget(table, row=1, col=0)
    mylayout.addWidget(pbutton1, row=2, col=0)
    mylayout.addWidget(pbutton2, row=2, col=0)

    # # plot内部设置
    p1.setLabel('left', text='Thread ID')
    p1.setLabel('bottom', text='Time', units='ms')
    region = pg.LinearRegionItem()
    region.setZValue(10)
    region.setRegion([0, 10])
    p1.addItem(region, ignoreBounds=True)
    vLine = pg.InfiniteLine(angle=90, movable=False)
    hLine = pg.InfiniteLine(angle=0, movable=False)
    p1.addItem(vLine, ignoreBounds=True)
    p1.addItem(hLine, ignoreBounds=True)

    # plot的viewbox
    vb = p1.vb

    # 鼠标移动交互
    def mouseMoved(evt):
        nonlocal p1, vLine, hLine
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if p1.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            if 0 < index < 1e9:
                label.setText("<span style='font-size: 12pt'>time=%0.1f ms" % (mousePoint.x()))
            vLine.setPos(mousePoint.x())
            hLine.setPos(mousePoint.y())

    proxy = pg.SignalProxy(pgantt.scene().sigMouseMoved, rateLimit=80, slot=mouseMoved)

    # 更新时间参数设置
    def updateparameters():
        nonlocal table
        table.setData(parameters)

    timer = pg.QtCore.QTimer()
    timer.timeout.connect(updateparameters)
    timer.start(50)

    # 参数更新的时钟  每50ms 更新统计时间参数

    win.show()
    pg.exec()
