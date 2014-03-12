import numpy as np
import matplotlib.pyplot as pt
import re, copy
import ctypes as c
import time as time_mod

#pulse blaster class
class pb():
    def __init__(self):
        self.pb_lib = c.cdll.LoadLibrary("/home/prl/pb_scripts/libspinapi.so.1.0.1")
        #self.pb_lib = c.cdll.LoadLibrary("/home/srh112/pb_scripts/libspinapi.so.1.0.1")
        #tmp =  self.pb_init()
        #print 'initialising: ', tmp
        #tmp = self.pb_stop()
        #print 'result of stop : ',tmp
        #tmp = self.pb_start_programming(board)
        #print 'result of start programming: ', tmp

    def pb_start_programming(self, board):
        return self.pb_lib.pb_start_programming(board)

    def pb_stop_programming(self):
        return self.pb_lib.pb_stop_programming()
        
    def pb_init(self):
        return self.pb_lib.pb_init()

    def pb_read_status(self):
        tmp = self.pb_lib.pb_read_status()
        a = bin(tmp)[2:]
        while len(a)<5:
            a = '0'+a
        output_string = a+' '
        if a[-1]=='1':
            output_string += 'Stopped '
        if a[-2]=='1':
            output_string += 'Reset '
        if a[-3]=='1':
            output_string += 'Running '
        if a[-4]=='1':
            output_string += 'Waiting '
        if a[-5]=='1':
            output_string += 'Scanning '
 
        return output_string

    def pb_close(self):
        return self.pb_lib.pb_close()

    def pb_reset(self):
        return self.pb_lib.pb_reset()

    def pb_stop(self):
        return self.pb_lib.pb_stop()

    def pb_start(self):
        return self.pb_lib.pb_start()

    def pb_select_board(self, board_num):
        return self.pb_lib.pb_select_board(c.c_uint(board_num))

    def pb_set_clock(self, clock_freq):
        self.pb_lib.pb_set_clock(c.c_double(clock_freq))

    def pb_inst_pbonly(self, bits, command, ref, time_tmp):
        #print int(bits), int(command), int(ref), c.c_double(time_tmp)
        #answer = self.pb_lib.pb_inst_pbonly(int(bits), int(command), int(ref), c.c_double(time_answer))
        time_mod.sleep(0.1)
        tmp = self.pb_lib.pb_inst_pbonly(c.c_uint(int(bits,2)), c.c_uint(command), c.c_uint(ref), c.c_double(time_tmp))
        print 'pb_inst_pbonly : %-2d %s %d %d %d'%(tmp, bits, command, ref, time_tmp)
        return tmp

    def pb_set_pulse_regs(self, channel, period, clock_high, offset):
        answer = self.pb_lib.pb_set_pulse_regs(c.c_uint(channel),c.c_double(period),c.c_double(clock_high),c.c_double(offset))
        print 'pb_set_pulse_regs: ', answer, channel, period, clock_high, offset
        return answer

