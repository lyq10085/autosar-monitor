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
    # 当前core id
    core_curr = 0
    # thread配置信息
    with open('./configuration.json', 'r') as f:
        conf_dict = json.load(f)

    def runrecv(queue):  # args 是plot对象tuple
        nonlocal bars, parameters, core_curr
        while True:
            bars, parameters, core_curr = queue.get()
            bars = np.compress(bars[:, 3] != 3, bars, axis=0)  # 不画出停止运行的thread
            bars = np.compress(bars[:, 2] != 0, bars, axis=0)  # 持续时间为0的bars

            if bars.size:
                bars_running = np.compress(bars[:, 3] == 2, bars, axis=0)
                bars_waiting = np.compress(bars[:, 3] == 1, bars, axis=0)
                bars_ready = np.compress(bars[:, 3] == 0, bars, axis=0)
                bg_run = pg.BarGraphItem(x0=bars_running[:, 1] * 0.00001, y=bars_running[:, 0],
                                         width=bars_running[:, 2] * 0.00001,
                                         height=1, brush='r', pen=pg.mkPen('r', width=0.01))
                plots[core_curr].addItem(bg_run)
                if bars_waiting.size:
                    bg_wait = pg.BarGraphItem(x0=bars_waiting[:, 1] * 0.00001, y=bars_waiting[:, 0],
                                              width=bars_waiting[:, 2] * 0.00001,
                                              height=1, brush='y', pen=pg.mkPen('y', width=0.01))
                    plots[core_curr].addItem(bg_wait)
                if bars_ready.size:
                    bg_ready = pg.BarGraphItem(x0=bars_ready[:, 1] * 0.00001, y=bars_ready[:, 0],
                                               width=bars_ready[:, 2] * 0.00001,
                                               height=3, brush='g', pen=pg.mkPen('g', width=0.01))
                    plots[core_curr].addItem(bg_ready)

    app = pg.mkQApp('monitor of thread')

    # mainwindow基本属性
    win = QtWidgets.QMainWindow()
    win.resize(1500, 800)
    win.setWindowTitle(conf_dict['name'])  # 窗口名设置为配置文件名

    # dock块设置
    area = DockArea()
    win.setCentralWidget(area)
    d1 = Dock("Gantt Show", size=(900, 400))
    d2 = Dock("Thread Time Parameter", size=(500, 400))
    d3 = Dock("Gantt Show", size=(900, 400))
    d4 = Dock("Gantt Show", size=(900, 400))
    d5 = Dock("Gantt Show", size=(900, 400))
    d6 = Dock("Gantt Show", size=(900, 400))
    d7 = Dock("Gantt Show", size=(900, 400))

    area.addDock(d1, 'left')
    area.addDock(d3, 'bottom', d1)
    area.addDock(d4, 'bottom', d3)
    area.addDock(d5, 'bottom', d4)
    area.addDock(d6, 'bottom', d5)
    area.addDock(d7, 'bottom', d6)

    area.addDock(d2, 'right')

    # dock内部设置
    pgantt1 = pg.GraphicsLayoutWidget(show=True)
    d1.addWidget(pgantt1)
    pgantt2 = pg.GraphicsLayoutWidget(show=True)
    d3.addWidget(pgantt2)
    pgantt3 = pg.GraphicsLayoutWidget(show=True)
    d4.addWidget(pgantt3)
    pgantt4 = pg.GraphicsLayoutWidget(show=True)
    d5.addWidget(pgantt4)
    pgantt5 = pg.GraphicsLayoutWidget(show=True)
    d6.addWidget(pgantt5)
    pgantt6 = pg.GraphicsLayoutWidget(show=True)
    d7.addWidget(pgantt6)
    mylayout = pg.LayoutWidget()
    d2.addWidget(mylayout)

    # graphicslayout/layoutwidget内部设置
    label = pg.LabelItem(justify='right')
    pgantt1.addItem(label)
    p1 = pgantt1.addPlot(row=1, col=0)
    p2 = pgantt2.addPlot(row=2, col=0)
    p3 = pgantt3.addPlot(row=3, col=0)
    p4 = pgantt4.addPlot(row=4, col=0)
    p5 = pgantt5.addPlot(row=5, col=0)
    p6 = pgantt6.addPlot(row=6, col=0)
    plots = (p1, p2, p3, p4, p5, p6)

    t1 = Thread(target=runrecv, args=(pipe,))  # 接受数据线程
    t1.start()

    table1 = pg.TableWidget()
    table2 = pg.TableWidget()
    table3 = pg.TableWidget()
    table4 = pg.TableWidget()
    table5 = pg.TableWidget()
    table6 = pg.TableWidget()
    tables = (table1, table2, table3, table4, table5, table6)
    # pbutton1 = QPushButton('STOP')
    # pbutton2 = QPushButton('START')
    # pbutton1.setText('STOP')
    # pbutton2 = QPushButton('START')
    # pbutton2.setText('START')
    # pbutton1.clicked.connect(tostop)
    # pbutton2.clicked.connect()
    mylayout.addWidget(table1, row=1, col=0)
    mylayout.addWidget(table2, row=2, col=0)
    mylayout.addWidget(table3, row=3, col=0)
    mylayout.addWidget(table4, row=4, col=0)
    mylayout.addWidget(table5, row=5, col=0)
    mylayout.addWidget(table6, row=6, col=0)

    # mylayout.addWidget(pbutton1, row=2, col=0)
    # mylayout.addWidget(pbutton2, row=2, col=0)

    # # plot内部设置
    p1.setLabel('left', text='Thread on Core0')
    p1.setLabel('bottom', text='Time', units='ms')
    p2.setLabel('left', text='Thread on Core1')
    p2.setLabel('bottom', text='Time', units='ms')
    p3.setLabel('left', text='Thread on Core2')
    p3.setLabel('bottom', text='Time', units='ms')
    p4.setLabel('left', text='Thread on Core3')
    p4.setLabel('bottom', text='Time', units='ms')
    p5.setLabel('left', text='Thread on core4')
    p5.setLabel('bottom', text='Time', units='ms')
    p6.setLabel('left', text='Thread on core5')
    p6.setLabel('bottom', text='Time', units='ms')

    # task名称设置
    yax1 = p1.getAxis('left')
    yax2 = p2.getAxis('left')
    yax3 = p3.getAxis('left')
    yax4 = p4.getAxis('left')
    yax5 = p5.getAxis('left')
    yax6 = p6.getAxis('left')
    tick1 = []
    tick2 = []
    tick3 = []
    tick4 = []
    tick5 = []
    tick6 = []

    for threadid, threadinfo in conf_dict['threads'].items():
        if threadinfo['coreid'] == 0:
            tick1.append((int(threadid), threadinfo['threadname']))
        elif threadinfo['coreid'] == 1:
            tick2.append((int(threadid), threadinfo['threadname']))
        elif threadinfo['coreid'] == 2:
            tick3.append((int(threadid), threadinfo['threadname']))
        elif threadinfo['coreid'] == 3:
            tick4.append((int(threadid), threadinfo['threadname']))
        elif threadinfo['coreid'] == 4:
            tick5.append((int(threadid), threadinfo['threadname']))
        elif threadinfo['coreid'] == 5:
            tick6.append((int(threadid), threadinfo['threadname']))

    yax1.setTicks([tick1])
    yax2.setTicks([tick2])
    yax3.setTicks([tick3])
    yax4.setTicks([tick4])
    yax5.setTicks([tick5])
    yax6.setTicks([tick6])

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

    proxy = pg.SignalProxy(pgantt1.scene().sigMouseMoved, rateLimit=80, slot=mouseMoved)

    # 更新时间参数设置
    def updateparameters():
        nonlocal tables, core_curr
        tables[core_curr].setData(parameters)


    timer = pg.QtCore.QTimer()
    timer.timeout.connect(updateparameters)
    timer.start(50)
    # 参数更新的时钟  每50ms 更新统计时间参数

    win.show()
    pg.exec()
