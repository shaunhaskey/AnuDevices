from MDSplus import Device,Data,Action,Dispatch,Method, makeArray, Range, Signal, Window, Dimension
#from Dt200WriteMaster import Dt200WriteMaster
import acq200, serial, time, os
#import transport

class SH_AMP2(Device):
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
        {'path':':SETTINGS','type':'text','value':'< 106 8 106 8 106 8 >\n'*16,'options':('no_write_shot',)},
        {'path':':READBACK','type':'text','options':()},
        {'path':':AMP_SUCCESS','type':'text','options':()},
        ]
    parts.append({'path':':INIT_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER','INIT',50,None),Method(None,'INIT',head))",
                  'options':('no_write_shot',)})
    parts.append({'path':':STORE_ACTION','type':'action',
                  'valueExpr':"Action(Dispatch('CAMAC_SERVER','STORE',50,None),Method(None,'STORE',head))",
                  'options':('no_write_shot',)})
    
    def init(self, arg):
        """
        Initialize the device
        """
        print "this is sh_amp"

        #Get amplifier settings from tree

        data, data2 = self.get_settings()
        print data

        print 'Coil Settings read in Successfully'
        print 'Opening serial port'

        #try to open the serial port
        try:
            ser=serial.Serial(0, 19200, timeout=1)
        except serial.SerialException:
            exit("Unable to open the serial port!!! Check no other program is using it")
        print 'Serial Port Open'

        #Send the ~Send Settings~ Command, and then send the settings themselves
        ser.flushInput()
        self.sendMicroCommand(ser, '7')
        ser.flushInput()
        print 'Sending settings for amplifiers via RS232'
        for i in range(0,16):
            for j in range(0,6):
                data[i][j]
                ser.write(chr(data[i][j]))

        #Check for echoed values and confirm they are correct
        self.waitForData(ser, 96)
        returnedData=map(ord,ser.read(96))
        print 'Echoed Values:'
        print returnedData
        if returnedData==data2:                 #Check validity of Echoed Values
            print 'ReturnedValuesCorrect'
        else:
            print 'ReturnedValuesIncorrect'

        time.sleep(0.5)                         #Give the micro time to return to default state

        #Send ~Transmit To Amplifiers~ Command
        print 'Sending ~Transmit To Amplifiers~ Command Sequence to Micro'
        self.sendMicroCommand(ser, '3')
        self.sendMicroCommand(ser, '6')

        #Wait for success reply from Micro, close Serial Port and Exit
        print 'Wait for success reply from Micro'
        self.waitForData(ser, 1)
        test=ord(ser.read())
        print ser.read()
        if test==1:
            print 'Finished Transmitting - Success!!!!'
        else:
            print 'Transmission Failed!!!!!'


        print 'Closing serial port'
        ser.close()

        return 1
    

    def waitForData(self, ser, numberOfBytes):
        delayCount=0
        while ((ser.inWaiting()<numberOfBytes)&(delayCount<50)):
            delayCount=delayCount+1        #Wait for all values to arrive - Need to be able to get out of this!!!!!
            #print delayCount
            time.sleep(0.1)                #Small delay that adds up   
        if delayCount == 50:               #Return a value to represent data waiting or timeout
            exit("Error !!!! : Timeout waiting for reply from Microcontroller - RS232->current loop not working or Microcontroller switched off----")  


    def sendMicroCommand(self, ser, command):
        ser.write(command)
        self.waitForData(ser, 1)
        if ser.read() != command:
            exit("Incorrect Echoed Value")      #Read echoed value
        ser.write(chr(13))                      #Send Enter to execute command




    INIT=init

    def store(self, arg):
        """
        Store the data from the device
        """
        print '============Helical / Toroidal Mirnov Array Serial Connection - Post Shot======='
        #Open the Serial Port
        try:
            ser=serial.Serial(0, 19200, timeout=1)
        except serial.SerialException:
            exit("Unable to open the serial port!!! Check no other program is using")
        print 'Serial Port Open'
        ser.flushInput()

        #Send Transmit Command
        print 'Sending ~Transmit To Amplifiers~ Command Sequence to Micro'
        self.sendMicroCommand(ser, '3')
        self.sendMicroCommand(ser, '6')

        #Wait for success reply from Micro, close Serial Port and Exit
        print 'Wait for success reply from Micro'
        self.waitForData(ser, 1)
        test=ord(ser.read())
        print ser.read()
        if test==1:
            print 'Finished Transmitting - Success!!!!'
        else:
            print 'Transmission Failed!!!!!'
            exit("Transmission Failure Error From Micro")

        print 'Obtain Values that were stored in the amplifier switch chips from the Micro'
        self.sendMicroCommand(ser, '6')
        self.waitForData(ser, 96)
        returnedData=map(ord,ser.read(96))
        print 'Values That Were Stored in the Amplifier Switch Chips'
        print returnedData

        #Readback the old settings
        data, data2 = self.get_settings()


        if returnedData==data2:
            print '=====================Success - Correct Return Values========'
            returnedValueSuccess=1
        else:
            print '======================Fail - Incorrect Return Values========'
            returnedValueSuccess=0

        ser.close()
        print 'Serial Port Closed'

        linelength = 6
        n_loops = len(returnedData)/linelength
        anotherOutput=''
        for i in range(n_loops):
            tmp_line = returnedData[i*linelength:(i+1)*linelength]
            line_str = ' '.join('%d' %i for i in tmp_line)
            output_str = '< %s >\n' %line_str
            #print output_str
            anotherOutput+=output_str



        if returnedValueSuccess==1:
            anotherOutput+='SUCCESS'
        else:
            anotherOutput+='FAIL'

        new_data = Data.makeData(anotherOutput)
        self.readback.putData(new_data)
        if returnedValueSuccess==1:
            new_data2=Data.makeData('1')
        else:
            new_data2=Data.makeData('0')

        self.amp_success.putData(new_data2)

        #node.putData(new_data)
        #node2=t.getNode('.shaunampbox:amp_success')
        #node2.putData(new_data2)
        #print 'Received Data written to MDSplus Shot Number :' + str(shot_number)


        return 1

    STORE=store

    def get_settings(self):
        fileData = str(self.settings.record)
        data=[]; data2=[]
        for line in fileData.split('\n'):
            formatted_line = line.strip('\n').strip('\r').strip(' ').strip('<').strip('>').strip(' ')
            if formatted_line != '':
                formatted_line = map(int,formatted_line.split(' '))
                data.append(formatted_line)
                data2.extend(formatted_line)
        return data, data2

    def help(self, arg):
        """ Help method to describe the methods and nodes of the DTAO32 module type """
        help(DT132)
        return 1


