import serial
from serial.tools import list_ports
import scipy.io

TERMINATE_SIGNAL = '!'
DAQ_SYNC_IDENTIFIER = '1'
ODOR_ON_IDENTIFIER = '2'
ODOR_OFF_IDENTIFIER = '3'
OPTICAL_SENSOR_DATA_IDENTIFIER = '4'

identifier = '0'

daq_sync_timestamps = []
odor_on_timestamps = []
odor_off_timestamps = []
motion_timestamps = []
delta_xs = []
delta_ys = []

output_dict = {"DAQ_Times": daq_sync_timestamps,
               "Odor_On_Times": odor_on_timestamps,
               "Odor_Off_Times": odor_off_timestamps,
               "Motion_Times": motion_timestamps,
               "Delta_Xs": delta_xs,
               "Delta_Ys": delta_ys}

#Shift timestamps to start at 0 and correct any overflows
def adjustTimestamps(timestamps):
    previous_timestamp = 0
    overflows = 0
    for i in range(len(timestamps)):
        if previous_timestamp > timestamps[i]:
            overflows += 1
        previous_timestamp = timestamps[i]
        timestamps[i] = timestamps[i]-initial_time + overflows*MAX_VALUE #Make sure this is overflow protected

#Find available ports
ports = list_ports.comports()
ports = [p.name for p in ports]
print(ports)

#Initialize serial interface
serialPort = input("Port: ")
while serialPort not in ports:
    print("Please enter a valid port")
    serialPort = input("Port: ")
baudRate = input("Baud rate: ")

with serial.Serial(serialPort, baudRate) as ser:
    print("Opened connection on port " + serialPort)
    while ser.is_open:
        if ser.in_waiting:
            print(ser.in_waiting)
            identifier = ser.read(1).decode("utf-8")
            print(identifier)
            if identifier == DAQ_SYNC_IDENTIFIER:
                #Write to daq sync column
                daq_sync_timestamps.append(
                    int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
            elif identifier == ODOR_ON_IDENTIFIER:
                #Write to odor on column
                odor_on_timestamps.append(
                    int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
            elif identifier == ODOR_OFF_IDENTIFIER:
                #Write to odor off column
                odor_off_timestamps.append(
                    int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
            elif identifier == OPTICAL_SENSOR_DATA_IDENTIFIER:
                #Write to movement timestamp, delta x, and delta y columns
                delta_xs.append(
                    int.from_bytes(ser.read(1), "big", signed=True)) #Delta X
                delta_ys.append(
                    int.from_bytes(ser.read(1), "big", signed=True)) #Delta Y
                motion_timestamps.append(
                    int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
            elif identifier == TERMINATE_SIGNAL:
                break

#Adjust timestamps for overflow and alignment
if(len(daq_sync_timestamps) > 0):
    initial_time = daq_sync_timestamps[0]
    MAX_VALUE = 4294967295

    adjustTimestamps(daq_sync_timestamps)
    adjustTimestamps(odor_on_timestamps)
    adjustTimestamps(odor_off_timestamps)
    adjustTimestamps(motion_timestamps)

#Output to .mat file for use with MATLAB
scipy.io.savemat("out.mat", output_dict)
