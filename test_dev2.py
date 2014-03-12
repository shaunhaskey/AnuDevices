from MDSplus import Device,Data,Action,Dispatch,Method, makeArray, Range, Signal, Window, Dimension
import time, os
import numpy as np
import ctypes as c

#import transport

class TEST_DEV2(Device):
    """
    Test for fast timers
    """
    parts=[{'path':'.PB1','type':'structure'}]
    parts.append({'path':'.PB1:PROGRAM','type':'numeric'})
    parts.append({'path':'.PB1:PROGRAM:BITS','type':'numeric','value':np.array([16777215, 0, 0])})
    parts.append({'path':'.PB1:PROGRAM:OPCODE','type':'numeric','value':np.array([0, 0, 6])})
    parts.append({'path':'.PB1:PROGRAM:ADDRESS','type':'numeric','value':np.array([0,0,-1])})
    parts.append({'path':'.PB1:PROGRAM:TIME','type':'numeric','value':np.array([200000000.0,100000000.0,100000000.0])})
    for i in range(1,20):
        parts.append({'path':'.PB1.T%d'%(i),'type':'structure'})
        list = ['NAME', 'EQUAL', 'TIME','UNIT','RISING','FIRST_RISE','FIRST_FALL']
        for j in list:
            parts.append({'path':'.PB1.T%d:%s'%(i,j),'type':'numeric','value':10})
            
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    def init(self, arg):
        """
        Initialize the device
        """
        print "this is test_dev init2"
        def init_sequence(PB, board = 0, clock = 100.0):
            tmp = PB.pb_stop()
            print 'stop :', tmp
            print 'setting clock frequency:', clock
            PB.pb_set_clock(clock)
            tmp = PB.pb_start_programming(board)
            print 'start_programming :',board, ' result :', tmp

        def close_sequence(PB, board = 0, clock = 100.0):
            tmp = PB.pb_start()
            print 'start :', tmp
            time.sleep(5)
            tmp = PB.close()
            print 'closed :', tmp

        try:
            print 'initialise PB'
            self.PB = pb()
        except:
            print 'failed to initialise PB'

        try:
            bits = self.pb1_program_bits.record.data()
            print bits.__class__, bits
            opcodes = self.pb1_program_opcode.record.data()
            print opcodes.__class__, opcodes
            address = self.pb1_program_address.record.data()
            print address.__class__, address
            times = self.pb1_program_time.record.data()
            print times.__class__, times
        except:
            print 'failed to read commands from the tree'

        try:
            init_sequence(self.PB)
        except:
            print 'failed to initialise the pulse blasters'

        try:
            for i in range(0,len(bits)):
                print bits[i], opcodes[i], address[i], times[i]
                self.PB.pb_inst_pbonly(bits[i], opcodes[i], address[i], times[i])
        except:
            print 'failed to send program to pulse blasters'

        try:
            close_sequence(self.PB)
        except:
            print 'failed to close pulseblasters'
        print 'finisahed'
        return 1

    INIT=init

    def store(self, arg):
        """
        Store the data from the device
        """
        return 1

    STORE=store

    def help(self, arg):
        """ Help method to describe the methods and nodes of the DTAO32 module type """
        return 1


class pb():
    def __init__(self):
        #self.pb_lib = c.cdll.LoadLibrary("/home/srh112/SpinAPI/spinapi_src/libspinapi.so.1.0.1")
        self.pb_lib = c.cdll.LoadLibrary("/home/prl/spin_tmp/SpinAPI/spinapi_src/libspinapi.so.1.0.1")
        tmp =  self.pb_init()
        print 'initialising: ', tmp

    def pb_start_programming(self, board):
        return self.pb_lib.pb_start_programming(board)

    def pb_stop_programming(self):
        return self.pb_lib.pb_stop_programming()
        
    def pb_init(self):
        self.pb_lib.pb_init()

    def pb_close(self):
        return self.pb_lib.pb_close()

    def pb_stop(self):
        return self.pb_lib.pb_stop()

    def pb_start(self):
        return self.pb_lib.pb_start()

    def pb_set_clock(self, clock_freq):
        self.pb_lib.pb_set_clock(c.c_double(clock_freq))

    def pb_inst_pbonly(self, bits, command, ref, time):
        print bits, command, ref, time
        return self.pb_lib.pb_inst_pbonly(int(bits), int(command), int(ref), c.c_double(time))
