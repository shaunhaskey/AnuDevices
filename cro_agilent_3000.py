# see 3000_series_prog_guide.pdf
# important - in non prompt mode (port=5025), must use \n not \r and wont tolerate
# extra spaces e.g.  ":WAV:POINTS ?"
import socket
from time import sleep
import numpy as np
import socket, time
from MDSplus import Device, Data, Action, Dispatch, Method, makeArray, Range, Signal, Window, Dimension

class cro():
    def __init__(self,host="192.168.1.151", port=5025):
        """ 5024 port has a echo and prompt
        5025 does not, and can deal with nulls (e.g. in binary data
        """
        self.host = host
        self.port = port
        self.prompt = (self.port==5024)
        self.connect_to_cro()
        self.soc.settimeout(2)  # now expect faster response.

    def connect_to_cro(self):
        '''
        Open a socket to the CRO
        SH : 11Mar2013
        '''
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.settimeout(3)  # takes about 8 secs to respond to telnet 192.168.1.240 5024
        print 'connecting to host: %s:%d'%(self.host,self.port)
        self.soc.connect((self.host, self.port))
        print 'connected, sleep for some time....'
        #sleep(7)
        if not self.prompt:
            self.soc.send('*IDN?\n')
        welc = self.soc.recv(1000)
        print welc
        tmp = welc.split(',')
        self.model = tmp[1]
        print self.model

    def reset_cro(self):
        '''
        Clear the settings on the CRO
        SH : 11Mar2013
        '''
        print 'Resetting CRO'
        tmp = self.soc.send("*RST\n")
        print tmp
        print 'Clearing AWG'
        tmp = self.soc.send("*CLS\n")


    def close_socket(self):
        '''
        close the socket
        SH : 11Mar2013
        '''
        print 'Closing connection to CRO'
        self.soc.close()

    def status(self, debug=0):
        self.soc.send(':OPER:COND?\n')
        sleep(0.1)  # helps - not sure why (maybe if there is a fragment left)
        ret = self.soc.recv(10000)
        if (ret[-1] != '\n') or (len(ret)<3):
            print('status recvd partial reponse: {s}'.format(ret))
            ret = ret + self.soc.recv(10000)
        if debug: print(ret)
        if self.prompt:
            ret = ret.socplit('\n')[-2]
        return(int(ret.strip()))

    def retrieve(self, points=50000, channel='CHAN1', mode='RAW', fmt='BYTE', debug=0):
        """ 4MSamples ~ 1.2 sec in byte mode
        """
        from array import array as Array
        if (self.status() & 8):
            raise Exception('must be in Halt mode')
        if self.prompt and fmt[0:3] != 'ASC':
            raise Exception('must use ASCII if in prompt mode (port 5024)')
        if points>62500:
            self.soc.send(':FUNC:DISP?\n')
            restoredisplaymath = int(self.soc.recv(10))
            if restoredisplaymath:  # turn it off for a sec.
                self.soc.send(':FUNC:DISP 0\n')
        else:
            restoredisplaymath = 0

        self.soc.send(':WAV:SOURCE {c}\n'.format(c=channel))
        self.soc.send(':WAV:FORM {f}\n'.format(f=fmt))
        self.soc.send(':WAV:POINTS:MODE {m}\n'.format(m=mode))
        self.soc.send(':WAV:POINTS {p}\n'.format(p=points))
        self.soc.send(':WAV:POINTS?\n')
        pnts = int(self.soc.recv(20))
        if pnts==0:
            raise LookupError('No data in ' + channel)
        if debug: print(points, pnts)

        self.soc.send(':WAV:PRE?\n')
        """
        #I assumed this would be in binary - it is not at least by default
        hdr = self.soc.recv(2)
        if hdr[0] != '#': print('unrecognised header', hdr)
        ndigits = int(hdr[1])
        packlen = int(self.soc.recv(ndigits))
        if debug: print(ndigits, packlen)
        preamble = self.soc.recv(packlen)
        if len(preamble)<packlen:
            sleep(1)
            preamble += self.soc.recv(packlen)

        counts = Array('I')   # 'I' is u32 'H' i16
        counts.fromstring(preamble[0:12])
        XArr = Array('d')
        XArr.fromstring(preamble[12:12+16])
        """
        plen=200
        sleep(1)
        preamble = self.soc.recv(plen)

        #self.soc.send(":TIMebase:MODE?;RANGe?;DELay?;POSition?;SCALe?\n")
        #print self.soc.recv(1000)

        nums = preamble.split(',')
        print nums
        data_format, mode_type, points, n_count, xinc, xor, xref, yinc, yor, yref = nums
        print nums
        self.X_array = np.arange(int(points)) * float(xinc) + float(xor)

        XArr=np.array(nums[4:7],dtype=float)
        YArr=np.array(nums[7:10],dtype=float)
               
        self.soc.send(':WAV:DATA?\n')
        hdr = self.soc.recv(2)
        if hdr[0] != '#': print('unrecognised header', hdr)
        ndigits = int(hdr[1])
        packlen = int(self.soc.recv(ndigits))
        if debug: print(ndigits, packlen)
        pkt=''
        iters=0
        while len(pkt) < packlen:
            newpkt = self.soc.recv(packlen+1)  # +1 to allow for  \n
            pkt += newpkt
            iters += 1
        if debug: print(iters,'iters')
        if restoredisplaymath:  # turn it off for a sec.
            self.soc.send(':FUNC:DISP 1\n')

        if fmt == '': return(pkt[0:-1])  # for debug
        elif fmt.upper() == 'BYTE': 
            typecode = 'B' # unsigned is B, 
            dtype = np.uint8
        elif fmt.upper() == 'WORD': 
            typecode = 'H'  
            dtype = np.uint16
        else: raise ValueError('fmt of [{f}] not recognised - '
                               'use BYTE, WORD, ASCII (or "" for debug)'
                               .format(f=fmt))
        dat = Array(typecode)
        dat.fromstring(pkt[0:-1])
        dat = np.array(dat,dtype=dtype)
        scaled_dat = (np.array(dat) - float(yref)) * float(yinc) + float(yor)
        return({'raw_data':dat, 'data':scaled_dat,'X_array':self.X_array,'preamble':
                    {'raw_preamble':preamble, 'XInc':XArr[0], 'YInc':YArr[0], 'YOff':YArr[1], 'Xor':xor}})
                        
    def h5_save(self, filename, channels=['CHAN1'], samples=200000):
        import h5py
        import numpy as np
        f = h5py.File(filename, "w")
        wf = f.create_group("Waveforms")
        for ch in channels:
            datadict = self.retrieve(samples, ch, mode='MAX',fmt='BYTE')
            wf.attrs.create('XInc',datadict['preamble']['XInc'])  # repeated
            wf.attrs.create('scale_factor',0.001)  # repeated
            cg = wf.create_group('Channel {c}'.format(c=ch[-1]))
#            dset = cg.create_dataset(cg.name+' data', datadict['data'],dtype=np.float32)
            cg.attrs.create('YInc',datadict['preamble']['YInc'])
            cg.attrs.create('YOff',datadict['preamble']['YOff'])
            dset = cg.create_dataset(cg.name+' data', (len(datadict['data']),), dtype='uint8')
            dset[...] = datadict['data']
        f.close()



class CRO_AGILENT_3000(Device):
    '''Device to run the Agilent 3000 series cros
    SRH: 6Nov2014
    '''
    parts=[{'path':':HOSTIP','type':'text','value':'192.168.1.151:5025','options':('no_write_shot',)}]
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('H1_SERVER_1','PULSE',50, None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('H1_SERVER_1','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})
    #parts.append({'path':':PULSE_ACTION','type':'action',
    #              'valueExpr':"Action(Dispatch('CAMAC_SERVER45_1','PULSE', 50, None),Method(None,'PULSE',head))",
    #              'options':('no_write_shot',)})
    for i in range(4):
        parts.append({'path':':INPUT_%2.2d'%(i+1,),'type':'signal',})
        parts.append({'path':':INPUT_%2.2d:RAW'%(i+1,),'type':'SIGNAL',})
    parts.append({'path':':SETTINGS','type':'text'})
    parts.append({'path':':PREAMBLE','type':'text'})

    def init(self, arg):
        '''Initialise the cro by setting it to single mode
        SRH : 11Nov2014
        '''
        ip, port = self.hostip.record.split(':')
        self.ip = ip
        self.port = int(port)
        try:
            print self.settings.record
            settings_list = self.settings.record.split('\n')
            print settings_list
        except:
            print ' problem, modifying, using default'
            settings_list = [':SING']
        if len(settings_list)==0:
            print ' problem, modifying'
            settings_list = [':SING']
        if len(settings_list[0])==0:
            settings_list = [':SING']
            print ' problem, modifying'
        try:
            self.rfcro = cro(host=self.ip, port=self.port)
            for i in settings_list:
                if len(i)>1:
                    print ' sending : {}'.format(i)
                    self.rfcro.soc.send(i+'\n')
            #self.rfcro.soc.send(':SING\n')
            self.rfcro.close_socket()
        except:
            self.rfcro.close_socket()
            print "Failed to initialise cro!!!"
            raise ValueError('!!! EXCEPTION - Failed to initialise the cro')
        return 1

    INIT = init
    def store(self, arg):
        '''tell the pimax device it is time to store
        SH : 20Mar2013
        '''
        channels = ['CHAN{}'.format(i+1) for i in range(4)]
        samples = 2000000
        datadict_list = []
        try:
            ip, port = self.hostip.record.split(':')
            self.ip = ip
            self.port = int(port)
            #self.ip = "192.168.1.151"
            #self.port = 5025
            self.rfcro = cro(host=self.ip, port=self.port)
        except:
            print "  Failed to initialise cro, trying to close socket!!!"
            self.rfcro.close_socket()
            raise ValueError('!!! EXCEPTION - Failed to initialise the cro')
        got_data = False
        try:
            for i, ch in enumerate(channels):
                print 'retrieving {}.'.format(ch)
                datadict_list.append(self.rfcro.retrieve(samples, ch, mode='MAX',fmt='BYTE'))
                print 'samples:{}'.format(len(datadict_list[-1]['data']))
            got_data = True
            if len(datadict_list[-1]['data']) != samples: got_data = False
        except:
            print "  Failed to get data from the cro, trying to close socket!!!"
            self.rfcro.close_socket()
            raise ValueError('!!! EXCEPTION - Failed to get data from the cro')

        plot = False
        if plot:
            import matplotlib.pyplot as pt
            import numpy as np
            fig, ax = pt.subplots(nrows = 4, sharex = True)
            for i, datadict in enumerate(datadict_list):
                ax[i].plot(np.array(datadict['X_array'][::10]), np.array(datadict['data'][::10]))
            fig.canvas.draw();fig.show()

        #self.rfcro.soc.send(':SING\n')
        self.rfcro.close_socket()
        
        #Start putting data into the tree
        put_into_tree = True
        if put_into_tree and got_data:
            #fig, ax = pt.subplots(nrows = 4, sharex = True)
            raw_preamble = datadict_list[0]['preamble']['raw_preamble']
            nums = raw_preamble.split(',')
            print nums
            data_format, mode_type, points, n_count, xinc, xor, xref, yinc, yor, yref = nums
            for chan, datadict in enumerate(datadict_list):
                chan_node = self.__getattr__('input_%2.2d' % (chan+1,))
                chan_raw_node = self.__getattr__('input_%2.2d_raw' % (chan+1,))
                #print chan_node, chan_raw_node
                x_origin = float(datadict['preamble']['Xor'])
                clock_period = datadict['preamble']['XInc']

                data = datadict['raw_data']

                #data = datadict['data']
                #print x_origin, clock_period, len(data)
                dim = Dimension(Window(0, len(data)-1, x_origin), Range(None, None, clock_period))
                convExpr = Data.compile("{} * ($VALUE - {}) - {}".format(yinc, yref, yor))

                #rawMdsData = Int16Array(reducedRawChan)
                #rawMdsData.setUnits("counts")
                #convExpr.setUnits("Volt")
                sig = Signal(convExpr, data, dim)
                #print dim
                #print sig
                #print sig.raw
                if plot:
                    ax[chan].plot(sig.dim_of().data()[::10], sig.data()[::10])
                chan_node.putData(sig)
            if plot:
                fig.canvas.draw(); fig.show()
        return 1

    STORE = store
