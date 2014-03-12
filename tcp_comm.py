import socket, time
import select

class tcp_ip_connection():
    def __init__(self, ip, port, phase, tree_loc, shot):
        self.ip = ip
        self.port = port
        self.phase = phase
        self.tree_loc = tree_loc
        self.shot = shot
        self.termination_character = '\r\n'
        self.sep_char = chr(0x09) 
        print ' Building string to send to Labview:'
        self.send_string = phase + self.sep_char + str(self.tree_loc) + self.sep_char + str(self.shot) + self.termination_character
        print ' ' + self.send_string.rstrip(self.termination_character)

    def send_receive(self):
        '''Send the command, and get the return status
        SH:20Mar2013
        '''
        print ' Connecting to host: %s:%s'%(self.ip, self.port)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setblocking(0)
        self.s.settimeout(3)
        self.s.connect((str(self.ip), int(self.port)))
        print ' Connected, sending string:%s'%(self.send_string.rstrip(self.termination_character))
        self.s.send(self.send_string)
        print ' Waiting for return message'
        data = ''
        count=0
        while (not data.endswith(self.termination_character)) and count<3:
            ready = select.select([self.s], [], [], 2)
            if ready[0]:
                data += self.s.recv(4096)
            print ' ' + data
            ends_with_term = data.endswith(self.termination_character)
            print '  data ends with term character:', ends_with_term
            count += 1
        print ' Finished receiving data, returned string :%s'%(data.rstrip(self.termination_character))
        print ' Closing socket'
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        print ' Checking data'
        if not ends_with_term:
            raise RuntimeError(' Received message does not end in termination character')
        self.data = data.rstrip(self.termination_character)
        if len(self.data)>0:
            self.return_value = self.data[0]
            if len(self.data)>2:
                self.return_message = self.data[1:]
            else:
                self.return_message = ''
        time.sleep(0.1)
        if self.return_value=='0':
            print ' Success, returned message:%s'%(self.return_message)
        elif self.return_value=='1':
            raise RuntimeError(' Labview failed, returned message:%s'%(self.return_message))
        else:
            raise RuntimeError(' Labview failed unknown return value - not 1 or 0, returned message:%s'%(self.data))

