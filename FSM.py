from transitions import Machine


class myThread(object):  # 任务和中断的状态机
    taskstates = ['WAITING', 'READY', 'RUNNING', 'SUSPENDED']
    isrstates = ['RUNNING', 'READY', 'SUSPENDED']
    tasktransitions = [{'trigger': 'activate', 'source': 'SUSPENDED', 'dest': 'READY'},
                       {'trigger': 'start', 'source': 'READY', 'dest': 'RUNNING'},
                       {'trigger': 'resume', 'source': 'READY', 'dest': 'RUNNING'},
                       {'trigger': 'wait', 'source': 'RUNNING', 'dest': 'WAITING'},
                       {'trigger': 'release', 'source': 'WAITING', 'dest': 'READY'},
                       {'trigger': 'preempt', 'source': 'RUNNING', 'dest': 'READY'},
                       {'trigger': 'terminate', 'source': 'RUNNING', 'dest': 'SUSPENDED'}
                       ]
    isrtransitions = [{'trigger': 'start', 'source': 'SUSPENDED', 'dest': 'RUNNING'},
                      {'trigger': 'terminate', 'source': 'RUNNING', 'dest': 'SUSPENDED'},
                      # {'trigger': 'preempt', 'source': 'RUNNING', 'dest': 'READY'},  # 嵌套中断关闭
                      # {'trigger': 'resume', 'source': 'READY', 'dest': 'RUNNING'}
                      ]

    def __init__(self, name, threadtype, inistate='SUSPENDED'):
        self.name = name
        self.inistate = inistate
        self.type = threadtype
        if (threadtype == 1):  # 1 for task, 2 for isr
            self.machine = Machine(model=self, states=myThread.taskstates, transitions=myThread.tasktransitions,
                                   initial=self.inistate)
        else:
            self.machine = Machine(model=self, states=myThread.isrstates, transitions=myThread.isrtransitions,
                                   initial=self.inistate)

    def change(self, operation):
        try:
            func = getattr(self, operation)
            return func()
        except AttributeError:
            print('No such trigger method')

        return False
