import socket, time
from MDSplus import Device, Data, Action, Dispatch, Method, makeArray, Range, Signal, Window, Dimension

class TEST2(Device):
    '''Test device that returns a zero
    SRH: 8Nov2013
    '''
    #parts=[{'path':':HOSTIP','type':'text','value':'150.203.179.4:8051','options':('no_write_shot',)}]
    parts=[]
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('SERVER1','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('SERVER1','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})

    def init(self,*args,**kwargs):
        ''' 
        SH:20Mar2013
        '''
        print "================"
        print "Hello test class"
        print "args:", args
        print "kwargs:", kwargs
        print "returning", 0
        return 0

    INIT = init
    def store(self, arg):
        '''tell the pimax device it is time to store
        SH : 20Mar2013
        '''
        return 0
    STORE = store
