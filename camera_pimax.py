import socket, time
from MDSplus import Device, Data, Action, Dispatch, Method, makeArray, Range, Signal, Window, Dimension
import tcp_comm

class CAMERA_PIMAX(Device):
    '''Device to talk to the pimax camera shot controller
    SRH: 8Nov2013
    '''
    parts=[{'path':':HOSTIP','type':'text','value':'150.203.179.4:8051','options':('no_write_shot',)}]
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER45_1','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER45_1','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})

    parts.append({'path':'.PIMAX','type':'structure'})
    parts.append({'path':'.PIMAX:IMAGES','type':'numeric'})
    parts.append({'path':'.PIMAX:SETTINGS','type':'text'})
    parts.append({'path':'.PLL','type':'structure'})
    parts.append({'path':'.PLL:LOCKRANGE','type':'text'})
    parts.append({'path':'.SCAN','type':'structure'})
    parts.append({'path':'.SCAN:PHASES','type':'text'})


    def init(self, arg):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        try:
            error = None
            start_time = time.time()
            print '####################################################'
            print 'PIMAX init has started : MDSplus Device, SH 6Nov2013'
            self.shot = self.getTree().shot
            self.tree_loc = self.getPath()
            ip, port = self.hostip.record.split(':')
            self.ip = ip
            self.port = int(port)
            tcp = tcp_comm.tcp_ip_connection(self.ip, self.port, 'INIT', self.tree_loc, self.shot)
            tcp.send_receive()
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            #return 1
        except Exception,e:
            #Catch exceptions, then throw another exception so the dispatcher fails on this item
            if error is not None:
                e=error
            print "%s" % (str(e),)
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))

    INIT = init

    def store(self, arg):
        '''tell the pimax device it is time to store
        SH : 20Mar2013
        '''
        try:
            error = None
            print '####################################################'
            print 'PIMAX store has started : MDSplus Device, SH 6Nov2013'
            self.shot = self.getTree().shot
            start_time = time.time()
            self.tree_loc = self.getPath()
            ip, port = self.hostip.record.split(':')
            self.ip = ip
            self.port = int(port)
            tcp = tcp_comm.tcp_ip_connection(self.ip, self.port, 'STORE', self.tree_loc, self.shot)
            tcp.send_receive()
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            #return 1
        except Exception,e:
            if error is not None:
                e=error
            tcp.s.shutdown(socket.SHUT_RDWR)
            tcp.s.close()
            print "%s\n" % (str(e),)
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))
            #return 0
    STORE = store
