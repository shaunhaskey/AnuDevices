#!/usr/bin/env python
"""
Get and set transmitter values via SNMP

Usage:
transmitter [-h] [1|2] [read|measure|write|program] [phase|freq|...] [value]


IMPORTANT!!!: 
 --- when setting mode and frequency, need to put tx into 'standby' mode.

# TODO:
 - where required, check transmitter mode before setting value.
 - set_var timeout check currently only works for integer value - generalise this for all responses

 - start up sequence
     - tx 1, 2, to aux
     - tx 1, 2 to filament
     - both should have vfilv2 now starting to rise
         - TODO: should raise an alarm if the filament voltages don't rise
         - TODO: should have a monitor function which reads value every x seconds

Tested with python 2.6

Requirements:
  - argparse (for python <= 2.6)
  - netsnmp

Authors:
2013: Dave Pretty
"""

# Programs currently require int dtype
PROGRAMS = {
    'recycle_after_high_power_blast': (
        ('assert', 'operating_status', 'on'),
        ('write', 'operating_status', 'standby'),
        ('assert', 'operating_status', 'standby'),
        ('write', 'llrf_operation_mode', 'cw'),
        ('assert', 'llrf_operation_mode', 'cw'),
        ('write', 'operating_status', 'on'),
        ('assert', 'operating_status', 'on'),
        ('write', 'operating_status', 'standby'),
        ('assert', 'operating_status', 'standby'),
        ('write', 'llrf_operation_mode', 'pulsed_plasma'),
        ('assert', 'llrf_operation_mode', 'pulsed_plasma'),
        ('write', 'operating_status', 'on'),
        ('assert', 'operating_status', 'on'),
    )
}

import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import time

import netsnmp


# If True, then setting values on transmitter will be disabled.
READ_ONLY = True
READ_ONLY = False

#timeout in seconds
TIMEOUT = 60

OPERATING_STATUS_CODES = {
    16: "off",
    48: "filament",
    64: "standby",
    112: "on",
    224: "aux"
}

MODULATION_CODES = {
    32: "dsb",
    161: "amc",
    162: "e_amc",
    176: "dcc_3_6",
    177: "dcc_2_6",
    178: "dcc_1_6",
    254: "drm",
}

AUDIO_PROCESSING_CODES = {
    13: "no_processing",
    16: "lp_wide",
    17: "lp_bessel",
    32: "bp_4_5_ccir",
    48: "clipper_09db",
    49: "clipper_12db",
    50: "clipper_15db",
    64: "option_1",
    65: "option_2",
    66: "option_3",
    67: "option_4",
    68: "option_5",
    69: "option_6",
}

OSCILLATOR_CODES = {
    2: "o1_quartz",
    3: "o1_synth",
    4: "o1_stratus",
    12: "o2_quartz",
    13: "o2_synth",
    14: "o2_stratus"
}

LLRF_OPERATION_MODE_CODES = {
    1: "pulsed_plasma",
    2: "flat_top",
    3: "cw"
}


# dtype is the type expected by snmp
# value_map is map of snmp values to descriptive values. descriptive values are used when showing results, and are
# optional when setting values.
# Because descriptive values can be used in command line, keep them lower case and without spaces or special chars.

SNMP_VARIABLES = {
    "nominal_power": {
        "description": "Nominal transmitter power in kW",
        "dtype": int,
        "read": "desNomPower",
    },
    "minimal_power": {
        "description": "Minimal transmitter power in kW",
        "dtype": int,
        "read": "desMinPower"
    },
    "transmitter_id": {
        "description": "Transmitter identification string",
        "dtype": str,
        "read": "desTxID"
    },
    "warning_alarm_state": {
        "description": "State of the Warning Alarm Display on ECOS2 HMI.",
        "dtype": int,
        "read": "staWarning",
        "value_map": {0: 'off', 1: 'on'}
    },
    "fault_alarm_state": {
        "description": "State of the Fault Alarm Display on ECOS2 HMI.",
        "dtype": int,
        "read": "staWarning",
        "value_map": {0: 'off', 1: 'on'}
    },
    "defect_alarm_state": {
        "description": "State of the Defect Alarm Display on ECOS2 HMI.",
        "dtype": int,
        "read": "staWarning",
        "value_map": {0: 'off', 1: 'on'}
    },
    "trip_alarm_state": {
        "description": "State of the Trip Alarm Display on ECOS2 HMI.",
        "dtype": int,
        "read": "staWarning",
        "value_map": {0: 'off', 1: 'on'}
    },
    "operating_location": {
        "description": "Operating location",
        "dtype": int,
        "read": "staOpLocation",
        "value_map": {1: "local", 2: "remote", 3: "computer", 4: "snmp"}
    },
    "operating_mode": {
        "description": "Operating mode",
        "dtype": int,
        "read": "staOpMode",
        "value_map": {0: "controller", 1: "manual", 2: "auto"}
    },
    "target_operating_status": {
        "description": "Nominal (target) operating status",
        "dtype": int,
        "read": "staOpStatusNominal",
        "value_map": OPERATING_STATUS_CODES
    },
    "operating_status": {
        "description": "Operating status",
        "dtype": int,
        "read": "staOpStatusCurrent",
        "write": "cmdOpStatus",
        "value_map": OPERATING_STATUS_CODES
    },
    "modulation_mode": {
        "description": "Modulation",
        "dtype": int,
        "read": "staModulation",
        "write": "cmdModulation",
        "value_map": MODULATION_CODES
    },
    ###
    ### audio mode assumed to be working, but disabled only because it has so many options it clutters the variable list
    ###
    #"audio_mode": {
    #    "description": "Audio processing mode",
    #    "dtype": int,
    #    "read": "staAudio",
    #    "write": "cmdAudioProcessing",
    #    "value_map": AUDIO_PROCESSING_CODES
    #},
    "program_number": {
        "description": "Program number",
        "dtype": int,
        "read": "staProgramNr",
        "write": "cmdProgramNr"
    },
    "oscillator": {
        "description": "Oscillator mode",
        "dtype": int,
        "read": "staOscillator",
        # TODO: documentation says 'set active oscillator' - is this the same as oscillator mode?
        # "write": "cmdActiveOscillator",
        "value_map": OSCILLATOR_CODES
    },
    "llrf_operation_mode": {
        "description": "LLRF Operation mode",
        "dtype": int,
        "read": "staLLRFOpm",
        "write": "cmdLLLRFOpm",
        "value_map": LLRF_OPERATION_MODE_CODES,
    },
    "llrf_pulse_power": {
        "description": "LLRF Pulse Power. Range [kW]: pulsed: 1-200, flat_top: 1-150, cw: 1-40",
        "dtype": int,
        "read": "staLLRFPpw",
        "write": "cmdLLLRFPpw"
    },
    "llrf_phase_shift": {
        "description": "LLRF Phase Shift. Range [deg]: -180 - 180",
        "dtype": int,
        "read": "staLLRFPhd",
        "write": "cmdLLLRFPhd"
    },
    "llrf_pulse_length": {
        "description": "LLRF pulse length. Range [ms]: 1-100",
        "dtype": int,
        "read": "staLLRFPln",
        "write": "cmdLLLRFPln"
    },
    "llrf_pulse_rep_rate": {
        "description": "LLRF pulse repetition rate. Range [mHz]: 100-10000",
        "dtype": int,
        "read": "staLLRFPrr",
        "write": "cmdLLLRFPrr"
    },
    "ig1v2": {
        "description": "Ig1V2",
        "dtype": int,
        "measure": "measIg1V2",
    },
    "ig2v2": {
        "description": "Ig2V2",
        "dtype": int,
        "measure": "measIg2V2",
    },
    "vg2v2": {
        "description": "Vg2V2",
        "dtype": int,
        "measure": "measVg2V2",
    },
    "iav2": {
        "description": "IaV2",
        "dtype": int,
        "measure": "measIa1V2",
    },
    "vav2": {
        "description": "VaV2",
        "dtype": int,
        "measure": "measVaV2",
    },
    "vswr": {
        "description": "Vswr",
        "dtype": int,
        "measure": "measVswr",
    },
    "pfwd": {
        "description": "Pfwd",
        "dtype": int,
        "measure": "measPfwd",
    },
    "apd": {
        "description": "APD",
        "dtype": int,
        "measure": "measApd",
    },
    "vfilv2": {
        "description": "VfilV2",
        "dtype": int,
        "measure": "measVfilV2",
    },
    "vg1v2": {
        "description": "Vg1V2",
        "dtype": int,
        "measure": "measVg1V2",
    },
    "water_conductivity": {
        "description": "Water conductivity",
        "dtype": int,
        "measure": "measWater",
    },
    "vav1": {
        "description": "VaV1",
        "dtype": int,
        "measure": "measVaV1",
    },
    "iav1": {
        "description": "IaV1",
        "dtype": int,
        "measure": "measIaV1",
    },
    "vfilv1": {
        "description": "VfilV1",
        "dtype": int,
        "measure": "measVfilV1",
    },
    "vrefd": {
        "description": "VrefD",
        "dtype": int,
        "measure": "measVrefD",
    },
    "modulation_index": {
        "description": "Modulation Index",
        "dtype": int,
        "measure": "measModulationIndex",
    },
    "frequency": {
        "description": "Frequency [Hz]",
        "dtype": int,
        "measure": "measFrequency",
        "write": "cmdFrequency",
    },
    "preset_power": {
        "description": "Preset Power",
        "dtype": int,
        "measure": "measPresetPower",
        "write": "cmdPresetPower",
    },
    "operating_hours_filament": {
        "description": "Filament operating hours",
        "dtype": int,
        "measure": "measOpCounterFilament",
    },
    "operating_hours_blackheating": {
        "description": "Black heating operating hours",
        "dtype": int,
        "measure": "measOpCounterBlackHeating",
    },
    "operating_hours_anode": {
        "description": "Anode operating hours",
        "dtype": int,
        "measure": "measOpCounterAnode",
    },
    "fault_reset": {
        "description": "Fault Reset",
        "dtype": int,
        "write": "cmdFaultReset",
    },

}


TRANSMITTER_IPS = {
    1: "192.168.3.1",
    2: "192.168.3.2"
}

SNMP_VERSION = 2
COMMUNITY_STRING = 'private'

########################################################################
## Set up logging
#########################################################################

# Minimum log level handled by logging module.
LOG_LEVEL = logging.INFO

# Minimum log level stored in logfile.
LOGFILE_LEVEL = logging.INFO

LOGFILENAME = '/var/log/transmitters/transmitters.log'

LOGFILE_WHEN = 'W6'  # On Sunday
LOGFILE_INTERVAL = 1  # every sunday


def get_logger(tx_number):
    """Get logger for a given transmitter.

    Args:
        tx_number: transmitter number

    """
    logger = logging.getLogger('transmitters')
    logger.setLevel(LOG_LEVEL)
    logfile_handler = TimedRotatingFileHandler(LOGFILENAME, when=LOGFILE_WHEN,
                                               interval=LOGFILE_INTERVAL)
    logfile_handler.setLevel(LOGFILE_LEVEL)
    logfile_format_str = '%(asctime)s - tx ' + str(tx_number) + ' - %(levelname)s: %(message)s'
    logfile_formatter = logging.Formatter(logfile_format_str)
    logfile_handler.setFormatter(logfile_formatter)
    logger.addHandler(logfile_handler)
    return logger



########################################################################
## Main code
########################################################################


class Transmitter(object):
    """Interface to transmitter."""

    def __init__(self, tx_number, read_only=True):
        """
        Args:
           tx_number (int or str) - transmitter number - either 1 or 2

        Keyword args:
           read_only (bool, default=True) - if True, cannot write to transmitter.

        """
        self.tx_number = int(tx_number)
        self.read_only = read_only
        self.ip_address = TRANSMITTER_IPS[self.tx_number]
        self.session = netsnmp.Session(DestHost=self.ip_address,
                                       Version=SNMP_VERSION,
                                       Community=COMMUNITY_STRING)
        self.logger = get_logger(self.tx_number)

    def read_or_measure_variable(self, variable, access_mode, show_descriptive=True):
        var = netsnmp.Varbind(tag=SNMP_VARIABLES[variable][access_mode], iid="0")
        value = self.session.get(netsnmp.VarList(var))[0]
        if show_descriptive and 'value_map' in SNMP_VARIABLES[variable]:
            casted_value = SNMP_VARIABLES[variable]['dtype'](value)
            descriptive_value = SNMP_VARIABLES[variable]['value_map'][casted_value]
            value = descriptive_value + " [%s]" % value
        self.logger.info("%s value of %s: result %s" % (access_mode, variable, value))
        return value

    def read_variable(self, variable):
        return self.read_or_measure_variable(variable, 'read')

    def measure_variable(self, variable):
        return self.read_or_measure_variable(variable, 'measure')

    def run_program(self, program_name):
        # Note: programs currently require int dtypes
        message = "Starting program %s." % program_name
        self.logger.info(message)
        print message
        for instruction in PROGRAMS[program_name]:
            if instruction[0] == 'write':
                self.write_variable(instruction[1], instruction[2])
            elif instruction[0] == 'assert':
                self.assert_variable(instruction[1], instruction[2])
        message = "Successfully completed program %s." % program_name
        self.logger.info(message)
        print message

    def assert_variable(self, variable, value):
        # Currently we require int

        check_mode = 'read'
        if 'measure' in SNMP_VARIABLES[variable]:
            check_mode = 'measure'

        expected_value = self.get_snmp_value(variable, value)
        current_value = self.read_or_measure_variable(variable, check_mode, show_descriptive=False)
        equal_values = int(expected_value) is int(current_value)
        message = "Assert %s == %s. Result: %s" % (variable, str(value), str(equal_values))
        print message
        try:
            assert equal_values
            self.logger.info(message)
        except AssertionError:
            self.logger.exception(message)
            raise

    def get_snmp_value(self, variable, value):
        """for a given variable value, return snmp value (usually int).

        value may be either snmp value or descriptive_value.

        """
        if 'value_map' in SNMP_VARIABLES[variable]:
            for snmp_var, desc_var in SNMP_VARIABLES[variable]['value_map'].items():
                if value.lower() == desc_var.lower():
                    value = str(snmp_var)
        return value

    def write_variable(self, variable, value):
        if self.read_only:
            message = "Cannot set value of variable in READ_ONLY mode."
            self.logger.exception(message)
            raise Exception(message)

        value = self.get_snmp_value(variable, value)

        self.logger.info("Request write value %s to variable %s" % (value,  variable))
        var = netsnmp.Varbind(tag=SNMP_VARIABLES[variable]['write'], iid="0", val=str(value))
        self.session.set(netsnmp.VarList(var))

        if 'read' in SNMP_VARIABLES[variable] and SNMP_VARIABLES[variable]['dtype'] is int:
            check_mode = 'read'
        elif 'measure' in SNMP_VARIABLES[variable] and SNMP_VARIABLES[variable]['dtype'] is int:
            check_mode = 'measure'
        else:
            message = "Cannot read or measure variable %s as integer, so not waiting to confirm it is set."
            self.logger.info(message)
            print message
            return

        t0 = time.time()
        while True:
            time.sleep(1)
            if (time.time() - t0) > TIMEOUT:
                message = "Timeout while waiting for variable to be set"
                self.logger.exception(message)
                raise Exception(message)
            current_value = int(self.read_or_measure_variable(variable, check_mode, show_descriptive=False))
            if current_value == int(value):
                break
            else:
                print "Waiting: currently the value is %d. expect %d" % (current_value, int(value))
        time.sleep(1)
        message = "Confirmed variable %s set to %s" % (variable, value)
        self.logger.info(message)
        print message


def variable_methods(var):
    available_methods = []
    for method in ['read', 'measure', 'write']:
        if method in SNMP_VARIABLES[var]:
            available_methods.append(method)
    return available_methods

max_var_len = max([len(key) for key in SNMP_VARIABLES.keys()])


def main():
    transmitter = Transmitter(args.tx_number[0], read_only=READ_ONLY)
    if args.method in ['read', 'measure']:
        print transmitter.read_or_measure_variable(args.variable[0], args.method)
    elif args.method == 'write':
        transmitter.write_variable(args.variable[0], args.value[0])
    elif args.method == 'program':
        transmitter.run_program(args.program[0])
    elif args.method == 'list':
        for variable, value in sorted(SNMP_VARIABLES.items()):
            var_methods = variable_methods(variable)
            var_str = ""
            for method in ['read', 'measure', 'write']:
                if method in var_methods:
                    var_str += method[0]
                else:
                    var_str += "."
            var_str += " "
            var_str += variable
            var_str += (max_var_len-len(variable) + 5)*"."
            var_str += value['description']
            if 'value_map' in value:
                var_str += " (" + ", ".join(sorted(value.get('value_map').values())) + ")"
            print var_str

if __name__ == "__main__":
    ########################################################################
    ## Parse arguments
    ########################################################################

    parser = argparse.ArgumentParser(description="Get and set transmitter values via SNMP.")

    parser.add_argument('tx_number', metavar='tx_number',
                        type=int, nargs=1, choices=[1, 2], help="Transmitter number (1 or 2)")
    subparsers = parser.add_subparsers(title="method", dest="method")

    parser_read = subparsers.add_parser("read", help="read value of a transmitter variable")
    parser_measure = subparsers.add_parser("measure", help="measure value of a transmitter variable")
    parser_write = subparsers.add_parser("write", help="write value of a transmitter variable")

    parser_list = subparsers.add_parser("list", help="list variables for transmitter")
    parser_program = subparsers.add_parser("program", help="run program for transmitter")


    def get_variable_choices(mode):
        """
        Arguments:
           mode: 'read', 'measure', 'write'
        """
        choices = []
        for variable, value in SNMP_VARIABLES.items():
            if mode in value:
                choices.append(variable)
        return sorted(choices)

    parser_read.add_argument('variable', metavar='variable',
                             nargs=1, choices=get_variable_choices('read'),
                             help="Variable to read. Choices: %(choices)s")

    parser_measure.add_argument('variable', metavar='variable',
                                nargs=1, choices=get_variable_choices('measure'),
                                help="Variable to measure. Choices: %(choices)s")

    parser_program.add_argument('program', metavar='program',
                                nargs=1, choices=sorted(PROGRAMS.keys()),
                                help="Program to run. Choices: %(choices)s")

    parser_write.add_argument('variable', metavar='variable',
                              nargs=1, choices=get_variable_choices('write'),
                              help="Variable to write. Choices: %(choices)s")

    parser_write.add_argument('value', metavar='value',
                              nargs=1, help="Value of variable to write to transmitter.")

    args = parser.parse_args()
    main()
