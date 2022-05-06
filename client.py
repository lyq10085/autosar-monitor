# 桩模块 模拟MCU发送监控数据
import socket
from mymain import PORT
import sys

HOST = '192.168.1.8'


def transmit(datafile, ptr):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with open(datafile, 'rb') as f:
        f.seek(ptr, 0)
        data = f.read(4000)
        client.sendto(data, (HOST, PORT))
        print(f'{len(data)} have sent')


if __name__ == '__main__':
    transmit('D:\\pythongantt\\tmp.txt', int(sys.argv[1]))
    # print(type(sys.argv[1]))
