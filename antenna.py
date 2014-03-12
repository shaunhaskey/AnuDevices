import socket, time
from MDSplus import Device, Data, Action, Dispatch, Method, makeArray, Range, Signal, Window, Dimension
import tcp_comm

class ANTENNA(Device):
    '''Device to talk to Labview and integrate it into MDSplus better
    '''
    parts=[{'path':':HOSTIP','type':'text','value':'150.203.179.4:8051','options':('no_write_shot',)}]
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER45_1','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER45_1','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':RFTUNE1','type':'numeric','value':0})
    parts.append({'path':':RFTUNE2','type':'numeric','value':0})
    parts.append({'path':':RFTUNE3','type':'numeric','value':0})
    parts.append({'path':':RFTUNE4','type':'numeric','value':0})
    parts.append({'path':':CONFIG','type':'numeric','value':0})

    def init(self, arg):
        '''initialise the labview device over a socket
        SH:20Mar2013
        '''
        try:
            error = None
            start_time = time.time()
            print '####################################################'
            print 'Antenna init has started : MDSplus Device, SH 6Nov2013'
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
        '''tell the labview device it is time to store
        SH : 20Mar2013
        '''
        try:
            error = None
            print '####################################################'
            print 'Antenna store has started : MDSplus Device, SH 6Nov2013'
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
            print "%s\n" % (str(e),)
            print(' finished in {:.2f}s'.format(time.time() - start_time))
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))
            #return 0
    STORE = store
