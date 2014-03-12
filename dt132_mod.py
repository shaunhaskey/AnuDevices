from MDSplus import Device,Data,Action,Dispatch,Method, makeArray, Range, Signal, Window, Dimension
from Dt200WriteMaster import Dt200WriteMaster
import acq200
import transport

from time import sleep
import time
import os
import numpy

class DT132_MOD(Device):
    """
    D-Tacq ACQ132  32 channel transient recorder
    
    Methods:
    Add() - add a DTAO32 device to the tree open for edit
    Init(arg) - initialize the DTAO32 device 
                write setup parameters and waveforms to the device
    Store(arg) - store the data acquired by the device
    Help(arg) - Print this message
    
    Nodes:
    
    :HOSTIP - mdsip address of the host storing the data.  Usually 192.168.0.254:8106
     BOARDIP'- ip addres sof the card as a string something like 192.168.0.40
     COMMENT - user comment string
     DI[0-5] - time(s) of the signal on this internal wire (trig reference or clock reference)
            :wire - string specifying the source of this signal { 'fpga','mezz','rio','pxi','lemo', 'none }
            :bus  - string specifying the destination of this signal { 'fpga','rio','pxi', 'none }
    :ACTIVE_CHANS - number of active channels {8, 16, 32}
     INT_CLOCK - stored by module (representation of internal clock       
     TRIG_SRC - reference to DIn line used for trigger (DI3)
     TRIG_EDGE - string {rising, falling} 
     CLOCK_SRC - reference to line (DIn) used for clock or INT_CLOCK
     CLOCK_DIV - NOT CURRENTLY IMPLIMENTED 
     CLOCK_EDGE -  string {rising, falling}
     CLOCK_FREQ - frequency for internal clock
     PRE_TRIG - pre trigger samples MUST BE ZERO FOR NOW
     POST_TRIG - post trigger samples
     SEGMENTS - number of segments to store data in NOT IMPLIMENTED FOR NOW
     CLOCK - Filled in by store place for module to store clock information
     RANGES - place for module to store calibration information 
     STATUS_CMDS - array of shell commands to send to the module to record firmware version  etc
     BOARD_STATUS - place for module to store answers for STATUS_CMDS as signal
     INPUT_[01-32] - place for module to store data in volts (reference to INPUT_NN:RAW)
                  :RAW - place for module to store raw data in volts for each channel
                  START_IDX - first sample to store for this channel
                  END_IDX - last sample to store for this channel
                  INC - decimation factor for this channel
     INIT_ACTION - dispatching information for INIT
     STORE_ACTION - dispatching information for STORE
    """
    
    parts=[
        {'path':':HOSTIP','type':'text','value':'192.168.0.254','options':('no_write_shot',)},
        {'path':':BOARDIP','type':'text','value':'192.168.0.0','options':('no_write_shot',)},
        {'path':':COMMENT','type':'text'},
        ]
    for i in range(6):
        parts.append({'path':':DI%1.1d'%(i,),'type':'numeric','options':('no_write_shot',)})
        parts.append({'path':':DI%1.1d:BUS'%(i,),'type':'text','options':('no_write_shot',)})
        parts.append({'path':':DI%1.1d:WIRE'%(i,),'type':'text','options':('no_write_shot',)})
    parts2=[
        {'path':':ACTIVE_CHANS','type':'numeric','value':32,'options':('no_write_shot',)},        
        {'path':':INT_CLOCK','type':'axis','options':('no_write_model','write_once')},       
        {'path':':TRIG_SRC','type':'numeric','valueExpr':'head.di3','options':('no_write_shot',)},
        {'path':':TRIG_EDGE','type':'text','value':'rising','options':('no_write_shot',)},
        {'path':':CLOCK_SRC','type':'numeric','valueExpr':'head.int_clock','options':('no_write_shot',)},
        {'path':':CLOCK_DIV','type':'numeric','value':1,'options':('no_write_shot',)},
        {'path':':CLOCK_EDGE','type':'text','value':'rising','options':('no_write_shot',)},
        {'path':':CLOCK_FREQ','type':'numeric','value':1000000,'options':('no_write_shot',)},
        {'path':':PRE_TRIG','type':'numeric','value':0,'options':('no_write_shot',)},
        {'path':':POST_TRIG','type':'numeric','value':128,'options':('no_write_shot',)},
        {'path':':SEGMENTS','type':'numeric','value':1,'options':('no_write_shot',)},
        {'path':':CLOCK','type':'axis','options':('no_write_model','write_once')},
        {'path':':RANGES','type':'numeric','options':('no_write_model','write_once')},
        {'path':':STATUS_CMDS','type':'text','value':makeArray(['cat /proc/cmdline', 'get.d-tacq.release']),'options':('no_write_shot',)},
        {'path':':BOARD_STATUS','type':'SIGNAL','options':('no_write_model','write_once')},
        ]
    parts.extend(parts2)
    del parts2
    for i in range(32):
        parts.append({'path':':INPUT_%2.2d'%(i+1,),'type':'signal','options':('no_write_model','write_once',)})
        parts.append({'path':':INPUT_%2.2d:RAW'%(i+1,),'type':'SIGNAL', 'options':('no_write_model','write_once')})
        parts.append({'path':':INPUT_%2.2d:START_IDX'%(i+1,),'type':'NUMERIC', 'options':('no_write_shot')})
        parts.append({'path':':INPUT_%2.2d:END_IDX'%(i+1,),'type':'NUMERIC', 'options':('no_write_shot')})
        parts.append({'path':':INPUT_%2.2d:INC'%(i+1,),'type':'NUMERIC', 'options':('no_write_shot')})
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})
    
    clock_edges=['rising', 'falling']
    trigger_edges = clock_edges
    trig_sources=[ 'DI0',
                   'DI1',
                   'DI2',
                   'DI3',
                   'DI4',
                   'DI5',
                   ]
    clock_sources = trig_sources
    clock_sources.append('INT_CLOCK')
    
    masks = {8: '11110000000000001111000000000000',
             16:'11111111000000001111111100000000',
             32:'11111111111111111111111111111111',
             }
    wires = [ 'fpga','mezz','rio','pxi','lemo', 'none', 'fpga pxi']
    
    del i
    
        
    def init(self, arg):
        """
        Initialize the device
        Send parameters
        Arm hardware
        """
        print "ANUDEVICES : this is the edited one2 13/06/2012"
        debug=os.getenv("DEBUG_DEVICES")
        try:
            error="Must specify a board ipaddress"
            boardip=str(self.boardip.record)
            error=None
            error="Must specify active chans as int in (8,16,32)"
            active_chans = int(self.active_chans)
            error=None
            if active_chans not in (8,16,32) :
                print "active chans must be in (8, 16, 32)"
                active_chans = 32
            error="Trig source must be a string"
            trig_src = str(self.trig_src.record)[-3:] #NEW
            #print "trig_src :", trig_src
            #trig_src=self.trig_src.record.getOriginalPartName().getString()[1:]
            error=None
            if debug:
                print "trig_src is %s\n" % trig_src
            if not trig_src in self.trig_sources:
                raise Exception, "Trig_src must be in %s" % str(self.trig_sources)
            error='Trig edge must be a string'
            trig_edge=self.trig_edge.record.getString()
            #print "trig_edge:", trig_edge
            error=None
            error="Clock source must be a string"
            #clock_src=self.clock_src.record.getOriginalPartName().getString()[1:]
            clock_src = str(self.clock_src.record)[-3:] #NEW
            #print "clock_src:",clock_src
            error=None
            if debug:
                print "clock_src is %s\n" % clock_src
            if not clock_src in self.clock_sources:
                raise Exception, "Clock_src must be in %s" % str(self.clock_sources)
            if (clock_src == 'INT_CLOCK'):
                error="Must specify a frequency for internal clock"
                clock_freq = int(self.clock_freq)
                error=None
            else:
                error="Must specify a frequency for external clock"
                clock_freq = int(self.clock_freq)
                error="Must specify a divisor for external clock"
                clock_div = int(self.clock_div)
                error=None
            error="Must specify pre trigger samples"
            pre_trig=int(self.pre_trig.data()*1024)
            error="Must specify post trigger samples"
            post_trig=int(self.post_trig.data()*1024)
            #print "connecting to board ip:", boardip
            error="Unable to connect to digitiser - is it on??"
            start_time = time.time()
            UUT = acq200.Acq200(transport.factory(boardip))
            UUT.set_abort()
            UUT.clear_routes()
            #print 'make UUT :', time.time() - start_time
            #start_time = time.time()
            error=None
            #print "connected"
            for i in range(6):
                line = 'd%1.1d' % i
                try:
                    wire = str(self.__getattr__('di%1.1d_wire'%i).record)
                    if wire not in self.wires :
                        print "DI%d:wire must be in %s" % (i, str(self.wires), )
                        wire = 'fpga'
                except:
                    wire = 'fpga'
                try:
                    bus = str(self.__getattr__('di%1.1d_bus'%i).record)
                    if bus not in self.wires :
                        print "DI%d:bus must be in %s" % (i, str(self.wires),)
                        bus = ''
                except:
                    bus = ''
                UUT.set_route(line, 'in %s out %s' % (wire, bus,))
                #print 'set_route', line, wire, bus
            #print 'make setup lines :', time.time() - start_time
            #start_time = time.time()
            UUT.setChannelCount(active_chans)
            #print "set active channels:", active_chans

            #SHAUN EDIT FOR FAST DTACQ
            if os.getenv('DTACQFAST')=='YES16' and boardip=='192.168.1.9':
                UUT.uut.acq2sh('set.channelSpeedMask 80008000000000008000800000000000')
                print 'FAST SPEED MASK 1'
            if os.getenv('DTACQFAST')=='YES32' and boardip=='192.168.1.9':
                UUT.uut.acq2sh('set.channelSpeedMask G000000000000000G000000000000000')
                print 'FAST SPEED MASK 2'



            if clock_src == 'INT_CLOCK' :
                print "INT_CLOCK"
                #UUT.uut.acqcmd("setInternalClock %d" % clock_freq) - SHAUN ALTERATION (two commands below)
                UUT.uut.acqcmd("setInternalClock %d DO1" % clock_freq)
                UUT.uut.acqcmd("-- setDIO -1-----")
            #SHAUN EDIT FOR FAST DTACQ
            elif os.getenv('DTACQFAST')=='YES16' and boardip=='192.168.1.9':
                 UUT.uut.acqcmd("-- setExternalClock --fin %d --fout %d DI0" % (1000, 16000,)) #SHAUN TEMPORARY EXT CLOCK TEST!!!
            elif os.getenv('DTACQFAST')=='YES32' and boardip=='192.168.1.9':
                 UUT.uut.acqcmd("-- setExternalClock --fin %d --fout %d DI0" % (1000, 32000,)) #SHAUN TEMPORARY EXT CLOCK TEST!!!
            else:
                print 'clock external'
                #UUT.uut.acqcmd("-- setExternalClock --fin %d --fout %d DI0" % (clock_freq/1000, clock_freq/1000,))- SHAUN ALTERATION
                #UUT.uut.acqcmd("-- setExternalClock --fin %d --fout %d DI1" % (clock_freq/1000, clock_freq/1000,))
                UUT.uut.acqcmd("-- setExternalClock --fin %d --fout %d DI0" % (1000, 2000,)) #SHAUN TEMPORARY EXT CLOCK TEST!!!
                print "-- setExternalClock --fin %d --fout %d DI0" % (1000, 2000,)


            if os.getenv('DTACQFAST')=='YES16' and boardip=='192.168.1.9':
                pre_trig=pre_trig*8
                post_trig=post_trig*8
            if os.getenv('DTACQFAST')=='YES32' and boardip=='192.168.1.9':
                pre_trig=pre_trig*16
                post_trig=post_trig*16

            #print "prePostMode:", pre_trig, post_trig, trig_src,trig_edge
            UUT.setPrePostMode(pre_trig, post_trig, trig_src, trig_edge)
            #print 'everything else :', time.time() - start_time
            #start_time = time.time()

            UUT.set_arm()
            #print 'arm :', time.time() - start_time
            #start_time = time.time()
            print 'armed'
            # UUT.uut.acq.p.sendline('bye')
            # UUT.uut.sh.p.sendline('bye')
            # UUT.uut.statemon.sendline('bye')
            # print 'hello'

            # print UUT.uut.acq.p.isalive()
            # print 'blah'
            # UUT.uut.acq.p.close()
            # print 'finished 1'
            # time_mod.sleep(10)
            # UUT.uut.sh.p.close()
            # print 'finished 2'
            # time_mod.sleep(10)
            # UUT.uut.statemon.close()

            # UUT.uut.acq.p.sendline('bye')
            # UUT.uut.sh.p.sendline('bye')
            # UUT.uut.statemon.sendline('bye')
            # print 'sleeping'
            # import time as time_mod
            # time_mod.sleep(10)
            # print 'blah'
            # import pexpect
            # UUT.uut.acq.p.expect(pexpect.EOF)
            # print 'blah2'

            # #UUT.uut.acq.p.flush()
            # print 'close acq'
            # print 'close acq'
            # del UUT.uut.acq.p
            # #UUT.uut.acq.p.close(False)
            # print 'close acq'
            # #UUT.uut.sh.p.close()
            # print 'close sh'
            # #UUT.uut.statemon.close()
            # print 'close statemon'
            return  1

        except Exception,e:
            print 'some kind of error'
            if error is not None:
                e=error
            print "%s\n" % (str(e),)
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))
            return 0

    INIT=init
        
    def getVins(self, UUT):
        vins = UUT.uut.acq2sh('get.vin 1:32')
        vins = vins[0]
        vins = vins[:-1]
        return makeArray(numpy.array(vins.split()).astype('int'))

        
    def getInternalClock(self, UUT):
        clock_str = UUT.uut.acqcmd('getInternalClock').split()[0].split('=')[1]
        print "clock_str is -%s-" % clock_str
	freq = int(clock_str)
        #SHAUN EDIT TO ALLOW 32 MSPS AND 16MSPS TO BE CLOCK RATES
	#if freq > 16000000 :
	#    freq = 2000000
        return freq

    def store(self, arg):
        """
        Store the data from the device
        Fetch and store the device status (firmware etc)
        If the device is finished
        For each channel that is on and active in the mask
        read the data
        store the data into the raw nodes
        store the expression into the data nodes
        """
        print "=========== ANUDEVICES SH edited dt132.py 13/06/2012 ==========="
        stall=os.getenv("Shaun_Stall")
        debug=os.getenv("DEBUG_DEVICES")
        try:
            error="Must specify a board ipaddress"
            boardip=str(self.boardip.record)
            error=None
            UUT = acq200.Acq200(transport.factory(boardip))
            try:
                ans = []
                cmds = self.status_cmds.record
                for cmd in cmds:
                    print cmd
                    a = UUT.uut.acq2sh(cmd)
                    ans.append(a)
                self.board_status.record = Signal(makeArray(ans),None,makeArray(cmds))
            except Exception, e:
                pass

            complete = 0
            tries = 0
            complete2=0
            tries2 = 0
            #SHAUN MODIFICATION SO THAT IT CAN BE RUN IN A LOOP AND WILL STALL HERE UNTIL CARD GOES TO POSTPROCESS
            if stall=="YES":
                print "stall is yes"
                while complete2==0:
                    if UUT.get_state().split()[-1] != "ST_STOP" :
                        tries2 +=1
                        sleep(1)
                        #print 'Still in run state'
                    else:
                        complete2=1
                        print 'Finished'
            #End Shaun Modification
            while not complete and tries < 60 :
                if UUT.get_state().split()[-1] == "ST_POSTPROCESS" :
                    tries +=1
                    sleep(1)
                else:
                    complete=1
            if UUT.get_state().split()[-1] != "ST_STOP" :
                raise Exception, "Device not Triggered \n device returned -%s-" % UUT.get_state().split()[-1]
            if debug:
                print "about to get the vins\n"
            vins = self.getVins(UUT)
            self.ranges.record = vins
            (tot, pre, post, run) = UUT.get_numSamples()
            pre = int(pre)*-1
            post = int(post)-1
            mask = UUT.uut.acqcmd('getChannelMask').split('=')[-1]
            print mask
            error="Clock source must be a string"
            #clock_src=self.clock_src.record.getOriginalPartName().getString()[1:]
            clock_src=str(self.clock_src.record)[-3:] #edit!!
            #print "clock_src:", clock_src
            error=None
            if clock_src == 'INT_CLOCK' :
                self.clock.record = Range(delta=1./self.getInternalClock(UUT))
            else:
                self.clock.record = Range(delta=1./self.getInternalClock(UUT)) #TEST FOR 32MHZ clock!!! - getInternalCock is deceptively named - it also works for external clock and is the second value that is given when setting it
                
                #self.clock.record = Range(delta=1./self.clock_src.data()) #SHAUN EDIT!!!!!

                #SHAUN FAST DTACQ EDIT
#                if os.getenv('DTACQFAST')=='YES16' and boardip=='192.168.1.9':
#                    self.clock.record = Range(delta=1./(16000000)) #SHAUN EDIT!!!!!
#                if os.getenv('DTACQFAST')=='YES32' and boardip=='192.168.1.9':
#                    self.clock.record = Range(delta=1./(32000000)) #SHAUN EDIT!!!!!

                #print self.clock_src.data()
                #self.clock.record = self.clock_src
            clock = self.clock.record
            #print 'clock record being used is : '#SHAUN EDIT
            if debug:
                print "about to ask it to mdsconnect"
            #print "mdsConnect %s" % str(self.hostip.record)
            UUT.uut.acq2sh("mdsConnect %s" % str(self.hostip.record))
            if debug:
                print "about to ask it to mdsopen"
            #print 'mdsOpen %s %d'  % (self.boardip.tree.name, self.boardip.tree.shot,)
            UUT.uut.acq2sh('mdsOpen %s %d'  % (self.boardip.tree.name, self.boardip.tree.shot,))

            #SHAUN EDIT START
            mdsputchsent=0 #Remember if command has been sent - initialise to be 0
            listofchannels="" #Initialise list of channels to be used by bulk command
            for spot in range(32):#Build list of channels to be used
                chan_node = self.__getattr__('input_%2.2d' % (spot+1,))
                if chan_node.on:
                    listofchannels=listofchannels + str(spot+1) + ","
            if listofchannels[len(listofchannels)-1]==",": #remove the last comma
                listofchannels=listofchannels[:len(listofchannels)-1]

            #Shaun edit for DTACQ Fast Sampling
            if os.getenv('DTACQFAST')=='YES16' and boardip=='192.168.1.9':
                listofchannels='1,5,17,21'
            if os.getenv('DTACQFAST')=='YES32' and boardip=='192.168.1.9':
                listofchannels='1,17'
                
            mdsputchbulkcommand=1 #switch to use bulk mdsputch or not
            #SHAUN EDIT END
            
            for chan in range(32):
                if debug:
                    print "working on channel %d" % chan
                chan_node = self.__getattr__('input_%2.2d' % (chan+1,))
                chan_raw_node = self.__getattr__('input_%2.2d_raw' % (chan+1,))
                if chan_node.on :
                    if debug:
                        print "it is on so ..."
                    if mask[chan:chan+1] == '1' :
                        try:
                            start = max(int(self.__getattr__('input_%2.2d_start_idx'%(chan+1))), pre)
                            print "start = %d" %start
                        except:
                            start = pre
                        try:
                            end = min(int(self.__getattr__('input_%2.2d_end_idx'%(chan+1))), post)
                        except:
                            end = post
                        try:
                            inc = int(self.__getattr__('input_%2.2d_inc'%(chan+1)))
                            print "inc = %d" % inc
                        except:
                            inc = 1
                        if debug:
                            print "build the command"
                        #!!!!!!!!!!!!!!! SHAUN MODIFIED THE FOLLOWING LINE (ADDED the +1 on the third argument to fix 1 more sample in time/data - ORIGINALLY WASN"T THERE - also replaced %%calsig with %%CAL to reduce complexity of the created tree - Boyd???)
                        command = "mdsPutCh --field %s:raw --expr %%CAL --timebase %d,%d,%d %d" % (chan_node.getFullPath(), int(start-pre), int(end-pre)+1, int(inc), chan+1)
                        command = command.replace('\\','\\\\')
                        if debug:
                            print "about to execute %s" % command

                        #START Shaun EDIT TO USE MDSPUTCH TO DO LOTS OF CHANNELS (mdsputchbulkcommand decides if it is used)
                        if mdsputchbulkcommand==1:
                            if mdsputchsent==0: #Check to see if command has already been sent
                                fieldstring=str(chan_node.getFullPath()) #building the string
                                fieldstring=fieldstring[0:len(fieldstring)-2]+"%02d" #building the string
                                bulkcommand = "mdsPutCh --field %s:raw --expr %%CAL --timebase %d,%d,%d %s" % (fieldstring, int(start-pre), int(end-pre)+1, int(inc), listofchannels)
                                bulkcommand = bulkcommand.replace('\\','\\\\')
                                print bulkcommand
                                UUT.uut.acq2sh(bulkcommand) #send command
                                mdsputchsent=1 #Remember the command has been sent                        
                        else:
                            UUT.uut.acq2sh(command) #ORIGINAL COMMAND
                        #END SHAUN EDIT
                        if inc > 1 :
                            clk=''
                            delta=''
                            begin=''
                            end=''
                            try :
                                clk = self.clock.evaluate()
                                delta = clk.delta
                                begin = clk.begin
                                ending = clk.end
                            except:
                                pass
                            if delta :
                                axis = Range(begin, ending, delta/inc)
                                window = Window(start/inc, end/inc, trigger)
                                dim = Dimension(window, axis)
                            else:
                                dim = Data.Compile('Map($,$)', Dimension(Window(start/inc, end/inc, trigger), clock), Range(start, end, inc))
                                raw = Data.compile('data($)', chan_raw_node)
                                chan_node.record = Signal(raw, None, dim)
                        else:
			    raw = Data.compile('data($)', chan_raw_node)
                            chan_node.record = Signal(raw, None, Dimension(Window(start, end, self.trig_src), clock))
            UUT.uut.acq2sh('mdsClose %s' % (self.boardip.tree.name,))
        except Exception,e :
            if error is not None:
                e=error
            print "Error storing DT132 Device\n%s" % ( str(e), )
            raise RuntimeError('!!! EXCEPTION - %s'%(str(e)))
            return 0
                
        return 1

    STORE=store

    def help(self, arg):
        """ Help method to describe the methods and nodes of the DTAO32 module type """
        help(DT132)
        return 1

