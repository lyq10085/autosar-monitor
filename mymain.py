from FSM import myThread
import socket
import json
from struct import unpack
from threading import Thread
import numpy as np
from draw import runGUI
from multiprocessing import Process, Pipe

BUFF_SIZE = 4000  # udp 缓冲区大小
SERVERIP = '192.168.1.8'
PORT = 18216  # 接受数据的端口

FILE = './temp.txt'  # 存储监控数据的文件
CONFIG_FILE = './configuration.json'  # thread和core对应关系的配置文件
MAX_NUM_Thread_PER_CORE = 100  # 每核最多thread
CORE_NUM = 1  # 核心数

# 导入配置信息
with open(CONFIG_FILE) as f:
    conf_dict = json.load(f)


class Monitor(object):
    # eventid 和 trigger条件匹配
    # 0 task activate
    # 1 task terminate/activate
    # 2 isr terminate/start
    # 16 thread preempt/resume
    # todo 加入  event resoure spinlock  监控
    triggers = {0: ['activate', 'activate'], 1: ['terminate', 'start'], 2: ['terminate', 'start'],
                16: ['preempt', 'resume']}

    statedict = {'UNKNOWN': -1, 'WAITING': 0, 'READY': 1, 'RUNNING': 2, 'SUSPENDED': 3}

    tick = 0

    def __init__(self, datafile, pipe):  # 需要给出idletask的编号
        self.datafile = datafile  # 监控txt文件路径
        self.threads = {}  # thread字典   threadid : Thread实例
        self.timer = {}  # 时间字典  threadid : tick for now
        # self.datafile_loaded_ptr = 0
        self.datafile_process_ptr = 0
        self.preline = ['', '', '']  # 待处理行的上一行
        self.tick = 0  # Monitor的当前时钟
        self.idletasks = conf_dict['core_idle']  # (coreid, idletaskid)
        self.coreloads = {}  # (coreid :  coreload)

        # narray = (Instance, CET_sum, WCET, RT_sum, WCRT, IPT_sum, WCIPT)
        self.param = {}  # (key,value) = (threadid, narray)

        # narray = (CET_current, RT_current, IPT_current)
        self.tmp_param = {}  # 每次运行的参数临时寄存 当thread结束一次运行就把参数写入self.timeparameter #(key, value) = (threadid, narray)
        self.pipe = pipe  # 给画图进程传递数据的管道

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

        # 当前进程变化前的状态
        prestate = 'UNKNOWN'

        # 当前行的数据信息
        (tick, eventid, threadid) = (int(x) for x in line)

        # thread 出现过
        if threadid in self.threads:

            prestate = self.threads[threadid].state  # 动作之前的状态

            if flag:  # 当前thread start or resume
                self.threads[threadid].change(Monitor.triggers[eventid][1])
            else:  # 当前 thread activate or end or preempted
                self.threads[threadid].change(Monitor.triggers[eventid][0])

            # 计算时间参数
            duration = tick - self.timer[threadid]
            if not (prestate == 'SUSPENDED'):
                self.tmp_param[threadid][1] += duration  # response time
            if prestate == 'RUNNING':
                self.tmp_param[threadid][0] += duration  # core execution time
            elif prestate == 'READY' and eventid == 1:  # IPT
                self.tmp_param[threadid][2] += duration

            # 计算每个核负载率
            for idletask in self.idletasks.values():
                if idletask in self.tmp_param.keys() and self.tmp_param[idletask][1]:
                    self.coreloads[conf_dict['threads'][str(idletask)]['coreid']] = \
                        1 - self.tmp_param[idletask][0] / self.tmp_param[idletask][1]

            #  每当有thread结束一次运行   计入self.param
            if self.threads[threadid].state == 'SUSPENDED':
                self.param[threadid][0] += 1  # 运行次数+1
                self.param[threadid][1] += self.tmp_param[threadid][0]  # CET_sum
                self.param[threadid][2] = max(self.param[threadid][2], self.tmp_param[threadid][0])  # WCET
                self.param[threadid][3] += self.tmp_param[threadid][1]  # RT_sum
                self.param[threadid][4] = max(self.param[threadid][4], self.tmp_param[threadid][1])  # WCRT
                self.param[threadid][5] += self.tmp_param[threadid][2]  # IPT_sum
                self.param[threadid][6] = max(self.param[threadid][6], self.tmp_param[threadid][2])  # WIPT

                # 该thread的临时时间参数清零
                for i in range(len(self.tmp_param[threadid])):
                    self.tmp_param[threadid][i] = 0

        # thread 第一次出现
        else:
            # 判断 thread is task or isr?  what is its initial state?
            if flag:
                prestate = 'READY' if eventid == 16 else 'SUSPENDED'
                inistate = 'RUNNING'
            elif eventid == 0:
                prestate = 'SUSPENDED'
                inistate = 'READY'
            elif eventid == 16:
                prestate = 'RUNNING'
                inistate = 'WAITING'
            else:
                prestate = 'RUNNING'
                inistate = 'SUSPENDED'
            # create thread
            self.threads[threadid] = myThread(threadid, 2 if eventid == 2 else 1, inistate)
            # 开始记录thread 的时间参数
            # narray = (Instance, CET_sum, WCET, RT_sum, WCRT, IPT_sum, WCIPT)
            self.param[threadid] = np.zeros((7,), dtype=np.uint64)  # 连续采集8天也不会溢出
            self.tmp_param[threadid] = np.zeros((3,), dtype=np.uint64)

        self.timer[threadid] = tick  # thread 最后一次状态变化时间

        # 处理一行产生 len(self.thread[threadid]) 个 bar 信息
        # 每个bar = (threadid, 开始时间, 持续时间, 持续状态)
        bars = np.zeros((len(self.threads), 4), dtype=int)
        # todo 只计算当前核上的thread的bars
        i = 0
        for threadname, thread in self.threads.items():
            if conf_dict['threads'][str(threadname)]['coreid'] == conf_dict['threads'][str(threadid)]['coreid']:
                bars[i, :] = np.array([thread.name, self.tick, tick - self.tick,
                                       Monitor.statedict[prestate if threadid == thread.name else thread.state]])
                i += 1

        # 计算时间参数
        # parameters = { threadid : (Instance, CET_sum, WCET, RT_sum, WCRT, IPT_sum, WCIPT), ...}
        parameters = np.zeros((len(self.threads) + 1,),
                              dtype=[('ThreadID', np.uint64), ('Instance', np.uint64),  # todo 增加thread名
                                     ('CET_avg', np.float64), ('WCET', np.uint64),
                                     ('RT_avg', np.float64), ('WCRT', np.uint64),
                                     ('IPT_avg', np.float64), ('WCIPT', np.uint64),
                                     ('CoreLoad', np.float16)])

        i = 0
        for tid, narr in self.param.items():
            if (not tid) or (not narr[0]):  # 跳过0号 idle task
                continue
            parameters['ThreadID'][i] = tid
            parameters['Instance'][i] = narr[0]
            parameters['CET_avg'][i] = narr[1] / narr[0]
            parameters['WCET'][i] = narr[2]
            parameters['RT_avg'][i] = narr[3] / narr[0]
            parameters['WCRT'][i] = narr[4]
            parameters['IPT_avg'][i] = narr[5] / narr[0]
            parameters['WCIPT'][i] = narr[6]
            # idle_on_core = self.idletasks[str(conf_dict['threads'][str(tid)]['coreid'])]  # 与当前thread 同属一核的idle task
            # if idle_on_core in self.tmp_param and self.tmp_param[idle_on_core][1]:
            #     parameters['CoreLoad'][i] = narr[1] / self.tmp_param[idle_on_core][1]
            i += 1

        # 处理idletask的数据   因为idle task永远不会停止 所以self.param中没有idle task的信息
        for core in self.coreloads.keys():
            parameters['ThreadID'][i] = self.idletasks[str(core)]
            parameters['Instance'][i] = 1
            parameters['CoreLoad'][i] = self.coreloads[core]
            i += 1

        core_curr = conf_dict['threads'][str(threadid)]['coreid']
        self.pipe.send([bars, parameters, core_curr])  # 传递bar给画图进程

        # 更新Monitor的时钟
        self.tick = tick


class UdpServer:
    def __init__(self, datafile, PORT=18126, BUFF_SIZE=4000):
        # udp通讯相关
        self.PORT = PORT
        # self.SERVER = socket.gethostbyname(socket.gethostname())  # 获取本机ip
        # print(self.SERVER) UDP服务器地址
        self.SERVER = SERVERIP
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

        # todo 计时器  当前时间-timestone > 2s 认为单片机断开连接 热插拔功能待开发中
        self.timestone = 0

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


if __name__ == '__main__':
    # myformat()  # 初始化当前坐标区
    # server = UdpServer()
    # monitor = Monitor(FILE)
    with open(FILE, 'w') as file:  # 清除上次运行的文件内容
        pass

    pipe = Pipe()  # pipe[0]接收端  pip[1]发送端
    server = UdpServer(FILE, PORT)
    monitor = Monitor(FILE, pipe[1])
    gui = Process(target=runGUI, args=(pipe[0], CORE_NUM))
    t1 = Thread(target=runudpserver, args=[server])
    t2 = Thread(target=rundataprocess, args=[monitor])
    gui.start()
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print('stop monitoring')
    gui.join()
    print("gui exiting")
