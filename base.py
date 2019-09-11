from multiprocessing import Process, Manager, Queue, RLock, Condition
import requests
from datetime import datetime as dat
from concurrent.futures import ThreadPoolExecutor
from time import time as tim
from tkinter import *
from bs4 import BeautifulSoup


class Main(Frame):
    def __init__(self, tk, name, year):
        super().__init__()
        self.tk = tk
        self.graph()
        self.start(name, year)
        self.text = ['Using only process', 'Using treads and queues', 'Using treads and locks']

    def start(self, name, year):
        self.manager = Manager()
        self.dict = self.manager.dict()
        self.dict1 = self.manager.dict()
        self.one = OneFM(0, self.dict, name, year)
        self.two = TwoFM(name, year)
        self.three = ThreeFM(self.dict1, name, year)
        self.one.start()
        self.two.start()
        self.three.start()
        self.three.join()
        self.two.join()
        self.one.join()

    def graph(self):
        self.tk.title('Graph')
        self.tk.geometry("400x200")
        self.pack(fill=BOTH, expand=1)
        self.canvas = Canvas(self.tk, width=400, height=200, bg='white')
        self.canvas.pack(fill=BOTH, expand=1)

    def draw(self):
        d = []
        s1 = []
        s2 = []
        s3 = []
        for i in self.one.data():
            s1.append(i[:-1])
        for i in self.two.data():
            s2.append(i[:-1])
        for i in self.three.get():
            s3.append(i[:-1])
        d.append(s1)
        d.append(s2)
        d.append(s3)


        if d:
            mn = []
            mx = []
            for i in d:
                mn.extend([x[0] for x in i])
                mx.extend([x[1] for x in i])

            mn = min(mn)
            mx = max(mx)
            md = mx - mn
            cx = 400./md
            c = 0
            y_s = 200./36.

            for i, v in enumerate(d):
                for k in v:
                    self.canvas.create_rectangle(cx *(k[0] - mn), c * y_s, cx*(k[1] - mn), c * y_s + 4, fill='#caeafc', outline='')
                    c += 1
                self.canvas.create_line(0, c * y_s - 1, 400, c * y_s - 1, fill='lightblue')
                self.canvas.create_text(200, c * y_s - 40, text=self.text[i])

    def __str__(self):
        s = 'Считывание результатов первого месяца каждого месяца:\n'
        s += str(self.one)
        s += '\n'
        s += str(self.two)
        s += '\n'
        s += str(self.three)
        s += '\n'
        s += '\nВремя работы каждого процесса\n'
        s += 'Первый: ' + str(calc(self.one.data()))
        s += '\n'
        s += 'Второй: ' + str(calc(self.two.data()))
        s += '\n'
        s += 'Третий: ' + str(calc(self.three.get()))
        return s


def stat(date, name):
    start = tim()
    data = []
    results = []
    response = requests.get(
        'http://iss.moex.com/iss/history/engines/stock/markets/shares/boards/tqbr/securities.xml?date={}'.format(date))
    soup = BeautifulSoup(response.text, 'lxml')
    a = soup.findAll('row')
    for i in a:
        if not i: continue
        if not i.has_attr('shortname'): continue
        if i['shortname'] == name:
            data.append(float(i['close']))

    if data:
        max_day = 0
        min_day = 0
        for i, n in enumerate(data):
            try:
                if max_day < data[i + 1] - n:
                    max_day = data[i + 1] - n
                else:
                    continue

                if min_day > data[i + 1] - n:
                    min_day = data[i + 1] - n
            except:
                pass

        data.sort()
        min = data[0]
        max = data[-1]
        results.append([data])
    end = tim()
    return (start, end, results)


def calc(a):
    m = min([i[0] for i in a])
    mx = max([i[1] for i in a])
    return mx - m


class OneFM(Process):
    def __init__(self,i, d, name, year):
        super().__init__(target=self.stat, args=(i, d))
        self.name = name
        self.year = year
        self.d = d

    def __str__(self):
        return str(self.d.values()[0])

    def data(self):
        return self.d.values()[0].copy()

    def stat(self, ind, d):
        a = []
        for i in range(1, 13):
            start_date = dat(self.year, i, 1)
            a.append(stat(start_date, self.name))
        d[ind] = a


class TwoFM(Process):
    def __init__(self, name, year):
        super().__init__()
        self.queue = Queue()
        self.name = name
        self.year = year
        self.r = []

    def run(self):

        with ThreadPoolExecutor(max_workers=2) as pool:
            q = {pool.submit(self.stat, self.name, dat(self.year, m, 1)): m for m in range(1, 13)}

    def __str__(self):
        return str(self.r)

    def data(self):
        while not self.queue.empty():
            self.r.append(self.queue.get())
        return self.r

    def stat(self, name, date):
        self.queue.put(stat(date, name))


class ThreeFM(Process):
    def __init__(self, d, name, year):
        super().__init__()
        self.d = d
        self.name = name
        self.year = year
        self.r = []
        self._mutex = RLock()
        self._empty = Condition(self._mutex)
        self._full = Condition(self._mutex)

    def run(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            q = {pool.submit(self.put, self.name, dat(self.year, m, 1)): m for m in range(1, 13)}

    def __str__(self):
       return str(self.d.values()[0])

    def put(self, name, date):
        with self._full:
            while len(self.r) >= 12:
                self._full.wait()
            self.r.append(stat(date, name))
            self.d[0] = self.r
            self._empty.notify()

    def get(self):
        return self.d.values()[0]


if __name__ == '__main__':
    root = Tk()
    m = Main(root, 'Аэрофлот', 2018)
    root.after(1, m.draw)
    root.mainloop()
    print(m)

