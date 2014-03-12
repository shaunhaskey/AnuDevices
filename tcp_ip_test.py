import socket, time
import select
#from MDSplus import Device, Data, Action, Dispatch, Method, makeArray, Range, Signal, Window, Dimension
import tcp_comm

class TCP_IP_TEST():
    def __init__(self, shot, tree, ip, port):
        self.shot = shot
        self.tree_loc = tree
        self.ip = ip
        self.port = port

    def init(self,):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        try:
            error = None
            start_time = time.time()
            print '####################################################'
            print 'Antenna init has started : MDSplus Device, SH 6Nov2013'
            tcp = tcp_comm.tcp_ip_connection(self.ip, self.port, 'INIT', self.tree_loc, self.shot)
            tcp.send_receive()
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            return 1
        except Exception,e:
            #Catch exceptions, then throw another exception so the dispatcher fails on this item
            if error is not None:
                e=error
            print "%s" % (str(e),)
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))


    def store(self,):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        try:
            error = None
            print '####################################################'
            start_time = time.time()
            print 'Antenna store has started : MDSplus Device, SH 1May2013'
            tcp = tcp_comm.tcp_ip_connection(self.ip, self.port, 'STORE', self.tree_loc, self.shot)
            tcp.send_receive()
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            return 1
        except Exception,e:
            #Catch exceptions, then throw another exception so the dispatcher fails on this item
            if error is not None:
                e=error
            print "%s" % (str(e),)
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))





class TCP_IP_TEST_OLD():
    def __init__(self, shot, tree, ip, port):
        self.shot = shot
        self.tree_loc = tree
        self.ip = ip
        self.port = port

    def init(self,):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        print 'Hello world TCP_IP test init'
        try:
            error = None
            print '####################################################'
            print 'Antenna init has started : MDSplus Device, SH 1May2013'

            #build the string to send, and send it
            self.build_string('INIT')
            self.send_receive()
            return 1
        except Exception,e:
            #Catch exceptions, then throw another exception so the dispatcher fails on this item
            if error is not None:
                e=error
            print "%s" % (str(e),)
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))


    def store(self,):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        print 'Hello world TCP_IP test init'
        try:
            error = None
            print '####################################################'
            print 'Antenna init has started : MDSplus Device, SH 1May2013'

            #build the string to send, and send it
            self.build_string('STORE')
            self.send_receive()
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
        #self.shot = self.getTree().shot
        #self.tree_loc = self.getPath()
        self.termination_character = '\r\n'
        self.sep_char = chr(0x09) 
        print 'Building string to send to Labview:'
        self.send_string = phase + self.sep_char + str(self.tree_loc) + self.sep_char + str(self.shot) + self.termination_character
        print self.send_string.rstrip(self.termination_character)

    def send_receive(self):
        '''Send the command, and get the return status
        SH:20Mar2013
        '''
        ip, port = self.ip, self.port#self.hostip.record.split(':')
        #print 'Connecting to host: %s:%d'%(self.hostip.record,self.port.record)
        print 'Connecting to host: %s:%s'%(ip, port)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setblocking(0)
        self.s.settimeout(5) #10 second timeout
        #self.s.connect((str(self.hostip.record), int(self.port.record)))
        self.s.connect((str(ip), int(port)))
        print 'Connected, sending string:%s'%(self.send_string.rstrip(self.termination_character))
        self.s.send(self.send_string)
        print '  Waiting for return message'
        data = ''
        count=0
        while (not data.endswith(self.termination_character)) and count<3:
            ready = select.select([self.s], [], [], 5)
            if ready[0]:
                data += self.s.recv(4096)
            print data
            print 'data ends with term character:',data.endswith(self.termination_character)
            count += 1
        #    print count
        #    tmp = self.s.recv(100)
        #    #print '  received some data : %s'%(tmp)
        #    data += tmp
        #    count+=1
        print 'Finished receiving data, returned string :%s'%(data.rstrip(self.termination_character))
        print 'Closing socket'
        self.s.close()
        print 'checking data'
        self.data = data.rstrip(self.termination_character)
        self.return_value = self.data[0]
        if len(self.data)>2:
            self.return_message = self.data[1:]
        else:
            self.return_message = ''
        time.sleep(0.5)
        print 'Socket closed'
        print 'Check return status from Labview'
        #check the returned value for success (0) or fail (1)
        if self.return_value=='0':
            print ' Initialisation success, returned message:%s'%(self.return_message)
        elif self.return_value=='1':
            raise RuntimeError(' Labview failed, returned message:%s'%(self.return_message))
        else:
            raise RuntimeError(' Labview failed unknown return value - not 1 or 0, returned message:%s'%(self.data))


