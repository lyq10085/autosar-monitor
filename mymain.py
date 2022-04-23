# 处理txt监控数据
# txt 数据格式 (tick, eventid, threadid)
from typing import Any, Tuple
import time
from FSM import myThread
import matplotlib.pyplot as plt
import socket
import threading
from struct import unpack
from threading import Thread

BUFF_SIZE = 4000  # udp 缓冲区大小
PORT = 18126 # 接受数据的端口 

FILE = './temp.txt'  # 存储监控数据的文件

mutex = threading.Semaphore(1)  # udp服务器接受缓冲区 互斥信号量
empty = threading.Semaphore(BUFF_SIZE)  # 缓冲区同步信号量
full = threading.Semaphore(0)


class Monitor(object):
    # encapsulate monitordata to FSMs

    # eventid 和 trigger条件匹配
    # 0 task activate
    # 1 task terminate/activate
    # 2 isr terminate/start
    # 16 thread preempt/resume
    # todo 加入  event resoure spinlock  监控
    triggers = {0: ['activate', 'activate'], 1: ['terminate', 'start'], 2: ['terminate', 'start'],
                16: ['preempt', 'resume']}
    colordict = {'WAITING': 'lightblue', 'READY': 'green', 'RUNNING': 'red', 'SUSPENDED': 'white'}

    def __init__(self, datafile):
        self.datafile = datafile  # 监控txt文件路径
        self.threads = {}  # thread字典   threadid : Thread实例
        self.timer = {}  # 时间字典  threadid : tick for now
        # self.datafile_loaded_ptr = 0
        self.datafile_process_ptr = 0
        self.preline = ['', '', '']  # 待处理行的上一行
        # self.last_tick = 0  # 当前最大的时间戳
        # self.overflowcnt = 0  # 时间戳溢出次数

    def process(self):  # 读取监控数据 按行处理 创建状态机
        with open(self.datafile, encoding='utf-8') as f:
            # 文件指针移动到当前待处理的位置
            if not self.datafile_process_ptr:  # 第一次启动监视器
                # 预处理 寻找第一次schedule
                self.preline = f.readline().split()

                line = f.readline().split()
                while self.preline and line and self.preline[0] != line[0]:
                    self.preline = line
                    line = f.readline().split()
                flag = True
                # print('monitor is starting')

            else:
                f.seek(self.datafile_process_ptr, 0)
                line = f.readline().split()
                if not line:  # 新的数据还没有写入不能分析
                    return
                flag = True if self.preline and self.preline[0] == line[0] else False

            # 逐行读取 创建/更新状态机
            while line:

                self.parseLine(line, flag)  # 解析当前行

                # 下一行
                self.preline = line
                line = f.readline().split()
                if not line:
                    break
                flag = True if self.preline and self.preline[0] == line[0] else False

            self.datafile_process_ptr = f.tell()  # 更新待处理位置

    def parseLine(self, line, flag):  # 当前行和前一行属于一次schedule  flag = true 否则flag = false
        (tick, eventid, threadid) = (int(x) for x in line)
        if threadid in self.threads:  # thread 出现过
            if flag:  # 当前thread start or resume
                self.threads[threadid].change(Monitor.triggers[eventid][1])
            else:  # 当前 thread activate or end or preempted
                self.threads[threadid].change(Monitor.triggers[eventid][0])
        else:  # thread 第一次出现
            # 判断 thread is task or isr?  what is its initial state?
            if flag:
                inistate = 'RUNNING'
            elif eventid == 0:
                inistate = 'READY'
            elif eventid == 16:
                inistate = 'WAITING'
            else:
                inistate = 'SUSPENDED'

            self.threads[threadid] = myThread(threadid, 2 if eventid == 2 else 1, inistate)
            self.timer[threadid] = tick  # 更新 thread 状态变化时间
            # todo 画图 每个thread 都画个图

    def ganttShow(self):
        # todo fig format
        # todo gif
        # todo bar
        # todo 处理无线长度的时间帧数据
        # pass
        plt.ylim(0, len(self.threads))
        plt.yticks([i + 1 for i in range(len(self.threads))], [str(key) for key in self.threads.keys()])


class udpserver:
    def __init__(self, datafile, PORT=18126, BUFF_SIZE=4000):
        # udp通讯相关
        self.PORT = PORT
        self.SERVER = socket.gethostbyname(socket.gethostname())  # 获取本机ip
        # print(self.SERVER) UDP服务器地址
        self.BUFF_SIZE = BUFF_SIZE  # 缓冲区大小4000byte
        # self.buffer = np.zeros(self.BUFF_SIZE, dtype=int)
        self.ADDR = (self.SERVER, self.PORT)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建套接字
        self.server.bind(self.ADDR)  # 绑定套接字和地址

        # 写入文件相关
        self.datafile = datafile
        self.datafile_loaded_ptr = 0
        self.overflowcnt = 0
        self.last_tick = 0

    def receive(self):  # 填满缓冲区
        print('starting receive\n')
        data, clientaddr = self.server.recvfrom(self.BUFF_SIZE)
        # print(f'{self.ADDR} have received {self.BUFF_SIZE} bytes from {clientaddr}\n')
        data = unpack('<' + 'I' * int(len(data) / 4), data)  # bytes 转 int  小端模式
        return data

    def BuftoFile(self, data):  # 分析传递的二进制数据
        # data 是个 tuple of int
        with open(self.datafile, mode='a+') as f:
            for stamp in data:
                real_tick = (stamp & 0x0003ffff) + self.overflowcnt * 0x00040000
                if real_tick < self.last_tick:
                    self.overflowcnt += 1
                    real_tick += 0x00040000
                self.last_tick = real_tick
                f.write(f'{real_tick}\t{(stamp & 0x007c0000) >> 18}\t{stamp >> 23}\n')
            self.datafile_loaded_ptr = f.tell()


def runudpserver(server):
    while True:
        server.BuftoFile(server.receive())


def rundataprocess(monitor):
    while True:
        monitor.process()


def myformat():
    """ Format various aspect of the plot, such as labels,ticks, BBox
    :todo: Refactor to use a settings object
    """
    # format axis
    plt.tick_params(
        axis='both',  # format x and y
        which='both',  # major and minor ticks affected
        bottom='on',  # bottom edge ticks are on
        top='off',  # top, left and right edge ticks are off
        left='off',
        right='off')

    plt.xlim(0, 140)  # 横坐标单位ms
    plt.title('Gantt for Task and ISR')
    plt.xlabel('ms')
    plt.xticks([i for i in range(0, 140, 10)], [str(i) for i in range(0, 140, 10)])


if __name__ == '__main__':
    myformat()  # 初始化当前坐标区
    # server = udpserver()
    # monitor = Monitor(FILE)
    with open(FILE, 'w') as file:  # 清除上次运行的文件内容
        pass
    #
    # while True:
    #     print('start receiving')
    #     monitor.BuftoFile(server.receive())
    #
    #     t1 = time.perf_counter()
    #     monitor.process()  # 这里会超时最好使用多线程
    #     monitor.ganttShow()
    #     t2 = time.perf_counter()
    #     print(f'time cost {t2 - t1}s')

    server = udpserver(FILE)
    monitor = Monitor(FILE)
    t1 = Thread(target=runudpserver, args=[server])
    t2 = Thread(target=rundataprocess, args=[monitor])
    t1.start()
    t2.start()
