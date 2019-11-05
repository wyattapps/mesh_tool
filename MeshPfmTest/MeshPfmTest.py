# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import re
import time
import datetime
import matplotlib.pyplot as plt
import numpy as np
import math

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        # set title
        self.master.title('Mesh GUI Test')
        # set window variable
        self.master.resizable(width=True, height=True)
        # common panel
        common_panel = tk.LabelFrame(self, text='common')
        common_panel.grid(row=0, column=0, padx=1, pady=3, sticky=tk.NSEW)
        self.com = ttk.Combobox(common_panel)
        self.com.grid(row=0, column=0, columnspan=2, padx=1, pady=3, sticky=tk.NSEW)
        self.mySerial = None
        self.mySerFlag = None
        tk.Button(common_panel, text='refresh', width=10, command=self.refresh_serial).grid(row=0, column=2, padx=1,
                pady=3, sticky=tk.NSEW)
        self.refresh_serial()
        self.mybaudrqate = ttk.Combobox(common_panel, width=10)
        self.mybaudrqate.grid(row=1, column=0, padx=1, pady=3, sticky=tk.NSEW)
        self.mybaudrqate['value'] = [115200, 460800, 921600]
        self.mybaudrqate.current(2)
        tk.Button(common_panel, text='open', width=10, command=self.mesh_serial_open).grid(row=1, column=1, padx=1,
                pady=3, sticky=tk.NSEW)
        tk.Button(common_panel, text='close', width=10, command=self.mesh_serial_close).grid(row=1, column=2, padx=1,
                pady=3, sticky=tk.NSEW)
        # operate panel
        tk.Label(common_panel, relief='solid', text='Data Len').grid(row=2, column=0, padx=3, pady=0, sticky=tk.NSEW)
        tk.Label(common_panel, relief='solid', text='Count').grid(row=2, column=1, padx=3, pady=0, sticky=tk.NSEW)
        tk.Button(common_panel, text='Msg Send', command=self.msg_send).grid(row=2, column=2, padx=1, pady=1,
                sticky=tk.NSEW)
        self.len_entry = tk.Entry(common_panel, width=10, relief='groove')
        self.len_entry.grid(row=3, column=0, padx=3, pady=0, sticky=tk.NSEW)
        self.len_entry.insert(tk.END, '8')
        self.send_count_label = tk.StringVar()
        tk.Label(common_panel, relief='groove', textvariable=self.send_count_label).grid(row=3, column=1, padx=3, pady=0,
                sticky=tk.NSEW)
        test_button = tk.Button(common_panel, text='Auto Test', command=lambda: self.auto_test(test_button))
        test_button.grid(row=3, column=2, padx=1, pady=1, sticky=tk.NSEW)
        # valiable
        self.send_count = 0
        self.panel_row = 0
        self.panel_column = 0
        self.total_column = 1
        self.server_dict = dict()
        self.log_window = None
        self.th_lock = threading.Lock()
        self.th_add_server = None
        self.th_add_total = None
        self.th_add_hop = None
        self.auto_test_flag = True
        # status bar
        self.status = tk.StringVar()
        self.status.set('COM Closed')
        tk.Label(self, textvariable=self.status, anchor='e').grid(row=20, column=0, columnspan=20, sticky=tk.NSEW)

    def refresh_serial(self):
        current_com = self.com.get()
        # refresh serial
        ser_list = list(serial.tools.list_ports.comports())
        ser_list.sort()
        current_index = 0
        if current_com:
            for index in range(len(ser_list)):
                if current_com.split()[0] == ser_list[index].device:
                    current_index = index
                    break
        self.com['value'] = ser_list
        if len(ser_list):
            self.com.current(current_index)

    def mesh_serial_open(self):
        ser_name = self.com.get().split()[0]
        if self.mySerial:
            self.mySerial.close()

        self.mySerial = serial.Serial(ser_name, int(self.mybaudrqate.get()))
        if self.mySerial.isOpen():
            # add log windows
            new_log_win = tk.Toplevel(self)
            new_log_win.title(self.mySerial)
            frm = tk.LabelFrame(new_log_win)
            frm.grid(row=0, column=1, columnspan=6, padx=1, pady=3, sticky=tk.NSEW)
            self.log_window = tk.Text(frm, bg='white', height=60)
            self.log_window.pack(side=tk.LEFT, fill=tk.Y)
            scroll = tk.Scrollbar(frm)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            scroll.config(command=self.log_window.yview)
            self.log_window.config(yscrollcommand=scroll.set)
            tk.Button(new_log_win, text='Clear', command=lambda: self.log_window.delete(1.0, tk.END)).grid(row=1,
                        column=5, padx=1, pady=3, sticky=tk.NSEW)
            def save_log():
                data_save = self.log_window.get(1.0, tk.END)
                #def dump_file(data_save):
                timestamp = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                file_name = 'Log_%s.txt' % timestamp
                #print(file_name)
                f = open(file_name, 'a')
                f.write(data_save)
                f.close()
                #threading.Thread(target=dump_file, args=(data_save,)).start()
            tk.Button(new_log_win, text='Save', command=save_log).grid(row=1,
                        column=4, padx=1, pady=3, sticky=tk.NSEW)
            self.mySerFlag = True
            self.status.set('%s Open' % ser_name)
            th = threading.Thread(target=self.rcv_data)
            th.start()

    def mesh_serial_close(self):
        if self.mySerial:
            self.mySerFlag = False
            self.mySerial.close()
            self.status.set('%s Closed' % self.mySerial.name)

    def rcv_data(self):
        while self.mySerFlag:
            com_data = self.mySerial.readline()
            if com_data:
                self.log_window.insert(tk.END, com_data.decode('utf-8', 'ignore'))
                self.log_window.see(tk.END)
                if self.log_window.count(1.0, tk.END, 'lines')[0] == 30000:
                    data_save = self.log_window.get(1.0, tk.END)
                    self.log_window.delete(1.0, tk.END)
                    def dump_file(data_save):
                        timestamp = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                        file_name = 'Log_%s.txt' % timestamp
                        f = open(file_name, 'a')
                        f.write(data_save)
                        f.close()
                    threading.Thread(target=dump_file, args=(data_save,)).start()
                strCom = com_data.decode()
                strCom = re.sub(r',', ' ', strCom)
                strRcv = strCom.split()
                if len(strRcv) == 12:
                    update_data = dict()
                    update_data['addr'] = strRcv[1]
                    update_data['len'] = strRcv[3]
                    update_data['diff'] = strRcv[5]
                    update_data['count'] = strRcv[7]
                    update_data['ttl1'] = strRcv[9]
                    update_data['ttl2'] = strRcv[11]
                    if self.server_dict.get(update_data['addr'], 'no') == 'no':
                        threading.Thread(target=self.add_panel, args=(update_data,)).start()
                    else:
                        threading.Thread(target=self.update_panel_data, args=(update_data,)).start()

    def add_panel(self, update_data):
        if self.th_add_server:
            self.th_add_server.join()
        def add_panel_thread():
            server_panel = tk.LabelFrame(self, text='server')
            if self.panel_row == 3:
                self.panel_row = 1
                self.panel_column += 1
            else:
                self.panel_row += 1
            server_panel.grid(row=self.panel_row, column=self.panel_column, sticky=tk.NSEW)
            # line 1
            tk.Label(server_panel, relief='solid', text='Address', width=10).grid(row=0, column=0, padx=1, pady=1,
                    sticky=tk.NSEW)
            tk.Label(server_panel, relief='solid', text='Rcv Count', width=10).grid(row=0, column=1, padx=1, pady=1,
                    sticky=tk.NSEW)
            tk.Label(server_panel, relief='solid', text='Lost Rate', width=10).grid(row=0, column=2, padx=1, pady=1,
                    sticky=tk.NSEW)
            tk.Label(server_panel, relief='solid', text='Time Use', width=10).grid(row=0, column=3, padx=1, pady=1, sticky=tk.NSEW)
            tk.Label(server_panel, relief='groove', text=update_data['addr'], width=8, bg='yellow').grid(row=1, column=0, padx=1, pady=1,
                    sticky=tk.NSEW)
            rcv_count_var = tk.Label(server_panel, relief='groove')
            lost_rate_var = tk.Label(server_panel, relief='groove')
            time_use_var = tk.Label(server_panel, relief='groove')
            rcv_count_var.grid(row=1, column=1, padx=1, pady=1, sticky=tk.NSEW)
            lost_rate_var.grid(row=1, column=2, padx=1, pady=1, sticky=tk.NSEW)
            time_use_var.grid(row=1, column=3, padx=1, pady=1, sticky=tk.NSEW)

            tk.Label(server_panel, relief='solid', text='HopCome').grid(row=2, column=0, padx=1, pady=1,
                    sticky=tk.NSEW)
            tk.Label(server_panel, relief='solid', text='HopBack').grid(row=2, column=1, padx=1, pady=1,
                    sticky=tk.NSEW)
            tk.Label(server_panel, relief='solid', text='Min').grid(row=2, column=2, padx=1, pady=1, sticky=tk.NSEW)
            tk.Label(server_panel, relief='solid', text='Avg').grid(row=2, column=3, padx=1, pady=1, sticky=tk.NSEW)
            relay1_var = tk.Label(server_panel, relief='groove')
            relay2_var = tk.Label(server_panel, relief='groove')
            min_var = tk.Label(server_panel, relief='groove')
            avg_var = tk.Label(server_panel, relief='groove')
            relay1_var.grid(row=3, column=0, padx=1, pady=1, sticky=tk.NSEW)
            relay2_var.grid(row=3, column=1, padx=1, pady=1, sticky=tk.NSEW)
            min_var.grid(row=3, column=2, padx=1, pady=1, sticky=tk.NSEW)
            avg_var.grid(row=3, column=3, padx=1, pady=1, sticky=tk.NSEW)

            server_data = dict()
            server_data['rcv_count_var'] = rcv_count_var
            server_data['lost_rate_var'] = lost_rate_var
            server_data['time_use_var'] = time_use_var
            server_data['relay1_var'] = relay1_var
            server_data['relay2_var'] = relay2_var
            server_data['min_var'] = min_var
            server_data['avg_var'] = avg_var
            server_data['count'] = 0
            server_data['min'] = 0xFFFF
            server_data['avg'] = 0
            self.server_dict[update_data['addr']] = server_data
            self.th_add_server = None
            self.update_panel_data(update_data)
        self.th_add_server = threading.Thread(target=add_panel_thread)
        self.th_add_server.start()

    def update_panel_data(self, update_data):
        if self.th_add_server:
            self.th_add_server.join()
        server_data = self.server_dict[update_data['addr']]
        server_data['count'] += 1
        cur_time = int(update_data['diff'])
        cur_len = int(update_data['len'])
        cur_ttl1 = 11-int(update_data['ttl1'])
        cur_ttl2 = 11-int(update_data['ttl2'])
        if server_data['min'] > cur_time:
            server_data['min'] = cur_time
        server_data['avg'] = (server_data['avg'] * (server_data['count']-1) + cur_time) / server_data['count']
        self.update_label(server_data['rcv_count_var'], server_data['count'])
        lost_rate_value = '%.2f %%' % ((self.send_count - server_data['count']) / self.send_count * 100)
        self.update_label(server_data['lost_rate_var'], lost_rate_value)

        self.update_label(server_data['relay1_var'], cur_ttl1)
        self.update_label(server_data['relay2_var'], cur_ttl2)
        self.update_label(server_data['time_use_var'], cur_time)

        self.update_label(server_data['min_var'], server_data['min'])
        self.update_label(server_data['avg_var'], '%.2f' % server_data['avg'])
        name_hop = 'hop_%d' % (cur_ttl1+cur_ttl2)
        name_len = 'len_%d' % cur_len
        if self.server_dict.get(name_len, 'no') == 'no':
            def add_total_thread():
                total_panel = tk.LabelFrame(self, text=name_len)
                total_panel.grid(row=0, column=self.total_column, sticky=tk.NSEW)
                self.total_column += 1
                total_data = dict()
                total_data['panel'] = total_panel
                tk.Label(total_panel, relief='solid', text='Hop', width=8).grid(row=0, column=0, padx=1, pady=1,
                        sticky=tk.NSEW)
                tk.Label(total_panel, relief='solid', text='Max', width=8).grid(row=0, column=1, padx=1, pady=1,
                        sticky=tk.NSEW)
                tk.Label(total_panel, relief='solid', text='Min', width=8).grid(row=0, column=2, padx=1, pady=1,
                        sticky=tk.NSEW)
                tk.Label(total_panel, relief='solid', text='Avg', width=8).grid(row=0, column=3, padx=1, pady=1,
                                                                                sticky=tk.NSEW)

                self.server_dict[name_len] = total_data
                tk.Button(total_panel, text='DAll', command=lambda: self.draw_pic(self.server_dict[name_len], name_len, 'all')).grid(row=0,
                        column=4, padx=1, pady=1, sticky=tk.NSEW)
                self.th_add_total = None
                self.update_total_panel(name_len, name_hop, cur_time)

            if self.th_add_total:
                self.th_add_total.join()
            self.th_add_total = threading.Thread(target=add_total_thread)
            self.th_add_total.start()
        else:
            threading.Thread(target=self.update_total_panel, args=(name_len, name_hop, cur_time,)).start()

    def update_total_panel(self, name_len, name_hop, time_use):
        if self.th_add_total:
            self.th_add_total.join()
        total_data = self.server_dict[name_len]
        def update_panel_data():
            if self.th_add_hop:
                self.th_add_hop.join()
            hop_data = total_data[name_hop]
            stat_index = time_use // 10

            #if stat_index > 59:
            #    stat_index = 59
            #self.th_lock.acquire()
            #total_data['raw_data'].append(time_use)
            #if len(total_data['raw_data']) == 101:
            #    pass
            #hop_data['stat_data'][stat_index] += 1
            hop_data['count'] += 1
            if hop_data['stat_data'].get(stat_index, 'no') == 'no':
                hop_data['stat_data'][stat_index] = 1
            else:
                hop_data['stat_data'][stat_index] += 1
            if hop_data['max'] < time_use:
                hop_data['max'] = time_use
            if hop_data['min'] > time_use:
                hop_data['min'] = time_use
            hop_data['avg'] = (hop_data['avg'] * (hop_data['count'] - 1) + time_use) / hop_data['count']
            self.update_label(hop_data['max_var'], hop_data['max'])
            self.update_label(hop_data['min_var'], hop_data['min'])
            self.update_label(hop_data['avg_var'], '%.2f' % hop_data['avg'])

        if total_data.get(name_hop, 'no') == 'no':
            def add_hop_thread():
                cur_row = int(name_hop.split('_')[1]) + 1
                tk.Label(total_data['panel'] , relief='groove', text=name_hop).grid(row=cur_row, column=0, padx=1,
                                                                                    pady=1, sticky=tk.NSEW)
                max_var = tk.Label(total_data['panel'] , relief='groove')
                min_var = tk.Label(total_data['panel'] , relief='groove')
                avg_var = tk.Label(total_data['panel'] , relief='groove')
                max_var.grid(row=cur_row, column=1, padx=1, pady=1, sticky=tk.NSEW)
                min_var.grid(row=cur_row, column=2, padx=1, pady=1, sticky=tk.NSEW)
                avg_var.grid(row=cur_row, column=3, padx=1, pady=1, sticky=tk.NSEW)
                total_data[name_hop] = {'max_var': max_var, 'min_var': min_var, 'avg_var': avg_var, 'count': 0,
                                        'max': 0, 'min': 0xFFFF, 'avg': 0, 'raw_data': [], 'stat_data': {}}
                tk.Button(total_data['panel'], text='Draw', command=lambda: self.draw_pic(total_data, name_len, name_hop)).grid(row=cur_row,
                        column=4, padx=1, pady=1, sticky=tk.NSEW)
                self.th_add_hop = None
                update_panel_data()
            if self.th_add_hop:
                self.th_add_hop.join()
            self.th_add_hop = threading.Thread(target=add_hop_thread)
            self.th_add_hop.start()
        else:
            update_panel_data()

    def draw_pic(self, total_data, name_len, name_hop):
        stat_data = [0]*60
        stat_count = 0
        if name_hop == 'all':
            stat_data_dict = dict()
            min_x = 1000
            for key1 in total_data.keys():
                if key1.split('_')[0] != 'hop':
                    continue
                hop_stat_data_dict = total_data[key1]['stat_data']
                stat_count += total_data[key1]['count']
                for key2 in hop_stat_data_dict.keys():
                    if stat_data_dict.get(key2, 'no') == 'no':
                        stat_data_dict[key2] = total_data[key1]['stat_data'][key2]
                    else:
                        stat_data_dict[key2] = total_data[key1]['stat_data'][key2]
                    if key2 < min_x:
                        min_x = key2

            for key in stat_data_dict.keys():
                index = key - min_x
                if index > 59:
                    index = 59
                stat_data[index] += stat_data_dict[key]

        else:
            stat_data_dict = total_data[name_hop]['stat_data']
            min_x = 1000
            stat_count = total_data[name_hop]['count']
            for key in stat_data_dict.keys():
                if key < min_x:
                    min_x = key

            for key in stat_data_dict.keys():
                index = key - min_x
                if index > 59:
                    index = 59
                stat_data[index] += stat_data_dict[key]
        X = range(min_x-1, min_x+59)
        Y = np.array(stat_data) / stat_count
        plt.bar(X, Y, facecolor='#9999ff', edgecolor='white')
        plt.xlabel('time(10ms), count: %d' % stat_count)
        plt.ylabel('percent')
        plt.title('%s_%s_figure' % (name_len, name_hop))
        plt.show()

    def msg_send(self):
        if not self.mySerial:
            return
        if not self.mySerial.isOpen():
            return
        self.send_count += 1
        if self.send_count % 5000 == 0:
            cur_len = int(self.len_entry.get())
            if cur_len == 128:
                cur_len = 4
            self.len_entry.delete(0, tk.END)
            self.len_entry.insert(tk.END, 2*cur_len)
            for server_data in self.server_dict.values():
                server_data['max'] = 0
                server_data['min'] = 0xFFFF
                server_data['avg'] = 0
        self.send_count_label.set(self.send_count)
        order_out = [0xAA, int(self.len_entry.get())]
        self.mySerial.write(bytearray(order_out))

    def msg_send_test(self):
        if self.auto_test_flag:
            self.msg_send()
            len = int(self.len_entry.get())
            period = len // 4
            if period > 10:
                period = 10
            threading.Timer(period, self.msg_send_test).start()

    def auto_test(self, test_button):
        if test_button['text'] == 'Auto Test':
            self.auto_test_flag = True
            self.msg_send_test()
            test_button.config(text='Auto Pause')
        elif test_button['text'] == 'Auto Pause':
            self.auto_test_flag = False
            test_button.config(text='Auto Test')

    def update_label(self, mylabel, value):
        changeColor = 'white'
        if mylabel['text'] > str(value):
            changeColor = 'green'
        if mylabel['text'] < str(value):
            changeColor = 'red'
        mylabel.configure(bg=changeColor)
        mylabel.config(text=str(value))


if __name__ == '__main__':
    root = tk.Tk()
    app = Application(master=root)

    def destroy_handle():
        if app.mySerial:
            app.mySerFlag = False
            app.mySerial.close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", destroy_handle)
    app.mainloop()

