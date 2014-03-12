import socket, time, os
from MDSplus import Device, Data, Action, Dispatch, Method, makeArray, Range, Signal, Window, Dimension
import numpy as np
import ctypes as c
import pb_class

class PULSE_BLASTERS(Device):
    '''Device to configure pulse blasters
    '''
    parts=[{'path':':HOSTIP','type':'text','value':'150.203.179.105','options':('no_write_shot',)},
        {'path':':PORT','type':'numeric','value':2527,'options':('no_write_shot',)}]

    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER40_1','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER40_1','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':FORCE_INIT','type':'action',
                  'valueExpr':"Action(Dispatch('150.203.179.70:8004','',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})

    parts.append({'path':':PROGRAM','type':'numeric'})
    parts.append({'path':':PROGRAM:BITS','type':'numeric','value':np.array([16777215, 0, 0])})
    parts.append({'path':':PROGRAM:OPCODE','type':'numeric','value':np.array([0, 0, 6])})
    parts.append({'path':':PROGRAM:ADDRESS','type':'numeric','value':np.array([0,0,-1])})
    parts.append({'path':':PROGRAM:TIME','type':'numeric','value':np.array([200000000.0,100000000.0,100000000.0])})
    for i in range(1,20):
        parts.append({'path':':T%d'%(i),'type':'structure'})
        list = ['NAME', 'EQUAL', 'TIME','UNIT','RISING','FIRST_RISE','FIRST_FALL']
        for j in list:
            parts.append({'path':':T%d:%s'%(i,j),'type':'numeric','value':10})


    def init(self, arg):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        print 'in the PB TEST init method'
        try:
            error = None
            print '####################################################'
            print 'Camera Init has started : MDSplus Device, SH 19Mar2013'

            #build the string to send, and send it
            self.build_string('INIT')
            self.send_receive()
            if self.return_value=='2':
                #dispatch whatever is required to program the pulse blasters
                self.send_pb_settings()
            return 1
        except Exception,e:
            #Catch exceptions, then throw another exception so the dispatcher fails on this item
            if error is not None:
                e=error
            print "%s" % (str(e),)
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))


    def build_string(self,phase):
        '''Put together a string to send to the labview server
        SH:20Mar2013
        '''
        self.shot = self.getTree().shot
        self.tree_loc = self.getPath()
        self.termination_character = '\r\n'
        self.sep_char = chr(0x09) 
        print 'Building string to send to Labview:'
        self.send_string = phase + self.sep_char + str(self.tree_loc) + self.sep_char + str(self.shot) + self.termination_character
        print self.send_string.rstrip(self.termination_character)

    def send_receive(self):
        '''Send the command, and get the return status
        SH:20Mar2013
        '''
        print 'Connecting to host: %s:%d'%(self.hostip.record,self.port.record)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(10) #10 second timeout
        self.s.connect((str(self.hostip.record), int(self.port.record)))
        print 'Connected, sending string:%s'%(self.send_string.rstrip(self.termination_character))
        self.s.send(self.send_string)
        print '  Waiting for return message'
        data = ''
        count=0
        while (not data.endswith(self.termination_character)) or count>10:
            tmp = self.s.recv(100)
            #print '  received some data : %s'%(tmp)
            data += tmp
            count+=1
        print 'Finished receiving data, returned string :%s'%(data.rstrip(self.termination_character))
        self.data = data.rstrip(self.termination_character)
        self.return_value = self.data[0]
        if len(self.data)>2:
            self.return_message = self.data[1:]
        else:
            self.return_message = ''
        time.sleep(0.5)
        print 'Closing socket'
        self.s.close()
        print 'Socket closed'
        print 'Check return status from Labview'
        #check the returned value for success (0) or fail (1)
        if self.return_value=='0':
            print ' Initialisation success, returned message:%s'%(self.return_message)
        elif self.return_value=='1':
            raise RuntimeError(' Labview failed, returned message:%s'%(self.return_message))
        elif self.return_value=='2':
            print 'Told to update the PULSE BLASTERS!!!'
        else:
            raise RuntimeError(' Labview failed unknown return value - not 1 or 0, returned message:%s'%(self.data))

    INIT = init


    def store(self, arg):
        '''tell the labview device it is time to store
        SH : 20Mar2013
        '''
        print 'in the PB TEST store method'
        # try:
        #     error = None
        #     print '####################################################'
        #     print 'Camera Store has started : MDSplus Device, SH 19Mar2013'
        #     self.build_string('STORE')
        #     self.send_receive()
        #     return 1
        # except Exception,e:
        #     if error is not None:
        #         e=error
        #     print "%s\n" % (str(e),)
        #     raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))
        #     return 0
    STORE = store


    def send_pb_settings(self,):
        try:
            print 'getting data from tree'
            bits = self.program_bits.record.data()
            print bits.__class__, bits
            opcodes = self.program_opcode.record.data()
            print opcodes.__class__, opcodes
            address = self.program_address.record.data()
            print address.__class__, address
            times = self.program_time.record.data()
            print times.__class__, times
        except:
            print 'failed to read commands from the tree'
            raise RuntimeError('failed to read commands from the tree')

        print '################################################'
        print '#INITIALISE THE BOARD AND SOFTWARE LIBRARY'
        print 'load spinapi library'
        clock_freq = 120; board = 0; PULSE_PROGRAM = 0
        CONTINUE = 0; STOP = 1; LOOP = 2; END_LOOP = 3; JSR = 4
        RTS = 5; BRANCH = 6; LONG_DELAY = 7; WAIT = 8; RTI = 9
        dict_multiplier = {'ns':1, 'us':1000, 'ms':1000000, 's':1000000000}
        PB = pb_class.pb() #this loads library and executs pb_init()
        print 'select board number %d return :'%(board,), 
        tmp = PB.pb_select_board(board)
        print tmp
        if tmp <0:
            raise ValueError("Error selecting board number")
        print 'initialise board return :',
        tmp = PB.pb_init()
        print tmp
        if tmp < 0:
            raise ValueError("Error initialising board")
        print 'set board clock frequency  %d MHz'%(clock_freq,)
        PB.pb_set_clock(clock_freq)
        tmp = PB.pb_reset()
        #tmp = PB.pb_stop()
        print tmp
        if tmp < 0:
            raise ValueError("Error stopping board")
        time.sleep(0.1)

        clock_list=[]
        print '#################################################'
        print '#SET THE CLOCKS'
        for i in range(0,len(clock_list)):
            freq = clock_list[i]
            if freq != None:
                print 'set clock %d, frequency %.2fHz'%(3-i,freq)
                period = int(float(clock_freq)/100.*10**9/freq) #60MHz correction included
                tmp = PB.pb_set_pulse_regs(3-i, period, period/2, 0)
                if tmp < 0:
                    raise ValueError("Error setting output clock")
        #################################################

        #insert a dummy command to begin with, this leads to the wait command which is stalling for a trigger
        #This current one flashes channel 20 so you know a new program has been received and started
        start_command = PB.pb_inst_pbonly('0'*24, CONTINUE, 0, dict_multiplier['ms']*500)
        if start_command != 0:
            raise ValueError("Error programming board - first command return not 0")
        curr_command = 0
        tmp = PB.pb_inst_pbonly(4*'0'+'1'+'0'*19, CONTINUE, 0, dict_multiplier['ms']*500)
        curr_command += 1
        if tmp != curr_command:
            raise ValueError("Error programming board - program return not incrementing")
        tmp = PB.pb_inst_pbonly('0'*24, CONTINUE, 0, dict_multiplier['ms']*500)
        curr_command += 1
        if tmp != curr_command:
            raise ValueError("Error programming board - program return not incrementing")

        wait_command = PB.pb_inst_pbonly('0'*24, WAIT, 0, 500000000)
        curr_command += 1
        if wait_command != curr_command:
            raise ValueError("Error programming board - program return not incrementing")
        bits = ['000000000000100000000000','000000000000000000000000','000000000000100000000000']
        opcodes = [0,0,0]
        address = [0,0,0]
        times = [15000000,485000000,11000000]
        #send off the commands
        for cur_bits, cur_opcode, cur_address, cur_time in zip(bits, opcodes, address, times):
            #for i in command_list_new:
            #word = ''.join(i[1])
            #print bin(int(word,2)), i[2],  0, i[0]/1000000
            #tmp = PB.pb_inst_pbonly(word, i[2], 0, i[0])
            tmp = PB.pb_inst_pbonly(cur_bits, cur_opcode, cur_address, cur_time)
            curr_command += 1
            if tmp != curr_command:
                raise ValueError("Error programming board - program return not incrementing")
            time.sleep(0.1)
        #final command to set all channels to '0'
        tmp = PB.pb_inst_pbonly('0'*24, CONTINUE, 0, 500*dict_multiplier['ms'])
        curr_command += 1
        if tmp != curr_command:
            raise ValueError("Error programming board - program return not incrementing")
        #branch back to the WAIT for trigger command
        tmp = PB.pb_inst_pbonly('0'*24, BRANCH, wait_command, 500*dict_multiplier['ms'])
        curr_command += 1
        if tmp != curr_command:
            raise ValueError("Error programming board - program return not incrementing")

        #FINISH PROGRAMMING AND SOFTWARE TRIGGER TO START EVERYTHING
        print 'pb_stop_programming return:', 
        tmp = PB.pb_stop_programming()
        print tmp
        if tmp != 0:
            raise ValueError("Error finish programming board")
        time.sleep(0.1)
        tmp = PB.pb_reset()
        print 'PB_reset return :', tmp
        time.sleep(0.1)
        tmp = PB.pb_start()
        print 'pb_start return : ', tmp
        if tmp != 0:
            raise ValueError("Error starting the program")
        tmp = PB.pb_close()
        print 'pb_close return :', tmp
        if tmp != 0:
            raise ValueError("Error closing the board")
        print 'Program finished'
        return 1


