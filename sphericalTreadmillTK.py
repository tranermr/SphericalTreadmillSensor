from tkinter import *
import numpy as np
import cv2
from PIL import Image, ImageTk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import serial
from serial.tools import list_ports
import scipy.io
import threading
import time

### Serial setup

TERMINATE_SIGNAL = '!'
DAQ_SYNC_IDENTIFIER = '1'
ODOR_ON_IDENTIFIER = '2'
ODOR_OFF_IDENTIFIER = '3'
OPTICAL_SENSOR_DATA_IDENTIFIER = '4'

ser = None
identifier = '0'
experimentActive = True
serialDone = False


daq_sync_timestamps = []
odor_on_timestamps = []
odor_off_timestamps = []
motion_timestamps = []
position_x = []
position_y = []
position_z = []

new_position_x = []
new_position_y = []

output_dict = {"DAQ_Times": daq_sync_timestamps,
               "Odor_On_Times": odor_on_timestamps,
               "Odor_Off_Times": odor_off_timestamps,
               "Motion_Times": motion_timestamps,
               "Position_X": position_x,
               "Position_Y": position_y,
               "Position_Z": position_z}

window = Tk()
window.geometry("1300x500")
windowActive = True

capture = cv2.VideoCapture(0)

cameraLabel = Label(window)
cameraLabel.grid(row=0, column=0)

dataLabel = Label(window)
dataLabel.grid(row=0, column=1)

serialThreadLabel = Label(window)

MAX_VALUE = 4294967295
COS_45 = 0.70710678118

TIMESTEP = 200000 #Microseconds
lastTimestamp = 0

lastX = 0
lastY = 0
lastZ = 0

deltaX1 = 0
deltaY1 = 0
deltaX2 = 0
deltaY2 = 0

MINIMUM_DELTA = 10

def sensorReadsToPositions():
    global deltaX1, deltaY1, deltaX2, deltaY2, lastX, lastY, lastZ
    #Translate sensor reads to standard basis
    deltaX = 0.5*(deltaX1+deltaX2)
    deltaY = COS_45*(deltaY1+deltaY2)
    deltaZ = COS_45*(deltaY1-deltaY2)

    #V2
    #deltaX = COS_45*(deltaX1+deltaX2)
    #deltaY = 0.5*(deltaY1+deltaY2)
    #deltaZ = COS_45*(deltaY1-deltaY2)

    #Append deltas to previous position and save
    if abs(deltaX) >= MINIMUM_DELTA:
        lastX += deltaX
        
        

    if abs(deltaY) >= MINIMUM_DELTA:
        lastY += deltaY
        
        

    if abs(deltaZ) >= MINIMUM_DELTA:
        lastZ += deltaZ

    if abs(deltaX) >= MINIMUM_DELTA or abs(deltaY) >= MINIMUM_DELTA:
        new_position_x.append(lastX)
        new_position_y.append(lastY)

    if abs(deltaX) >= MINIMUM_DELTA or abs(deltaY) >= MINIMUM_DELTA or abs(deltaZ) >= MINIMUM_DELTA:
        position_x.append(lastX)
        position_y.append(lastY)
        position_z.append(lastZ)

    #Reset sensor counters
    deltaX1 = 0
    deltaY1 = 0
    deltaX2 = 0
    deltaY2 = 0

#Shift timestamps to start at 0 and correct any overflows
def adjustTimestamps(timestamps):
    previous_timestamp = 0
    overflows = 0
    for i in range(len(timestamps)):
        if previous_timestamp > timestamps[i]:
            overflows += 1
        previous_timestamp = timestamps[i]
        timestamps[i] = timestamps[i]-initial_time + overflows*MAX_VALUE

def checkData():
    global experimentActive, deltaX1, deltaY1, deltaX2, deltaY2, lastTimestamp, serialDone
    while(windowActive):
        if ser.is_open and experimentActive:
            if ser.in_waiting:
                #print(ser.in_waiting)
                try:
                    identifier = ser.read(1).decode("utf-8")
                    #print(identifier)
                except:
                    identifier = None
                if identifier == DAQ_SYNC_IDENTIFIER:
                    #Write to daq sync column
                    daq_sync_timestamps.append(
                        int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
                    print("DAQ sync")
                elif identifier == ODOR_ON_IDENTIFIER:
                    #Write to odor on column
                    odor_on_timestamps.append(
                        int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
                    print("Odor on")
                elif identifier == ODOR_OFF_IDENTIFIER:
                    #Write to odor off column
                    odor_off_timestamps.append(
                        int.from_bytes(ser.read(4), "big", signed=False)) #Timestamp
                    print("Odor off")
                elif identifier == OPTICAL_SENSOR_DATA_IDENTIFIER:
                    #Write to movement timestamp, delta x and delta y counters
                    timestamp = int.from_bytes(ser.read(4), "big", signed=False)
                    motion_timestamps.append(timestamp)
                    
                    deltaX1 += int.from_bytes(ser.read(1), "big", signed=True) #Delta X1
                    deltaY1 += int.from_bytes(ser.read(1), "big", signed=True) #Delta Y1
                    deltaX2 += int.from_bytes(ser.read(1), "big", signed=True) #Delta X2
                    deltaY2 += int.from_bytes(ser.read(1), "big", signed=True) #Delta Y2
                    
                    if timestamp - lastTimestamp > TIMESTEP or timestamp < lastTimestamp:
                        sensorReadsToPositions()
                        lastTimestamp = timestamp

                elif identifier == TERMINATE_SIGNAL:
                    print("TERMINATE")
                    experimentActive = False
    serialDone = True

def liveFeed():
    global cameraLabel
    while(windowActive):
        time.sleep(0.02)
        ret, img = capture.read()
        if ret and windowActive:
            try:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                im = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(image=im)
                cameraLabel.imgtk = imgtk
                cameraLabel.configure(image=imgtk)
            except:
                print("Couldn't display image")

def liveDataSetup():
    plt.title("Movement")
    plt.xlabel("Left <-> Right")
    plt.ylabel("Backwards <-> Forwards")

def liveData():
    global dataLabel
    while(windowActive):
        time.sleep(0.02)
        if(len(new_position_x) > 0):
            plt.plot(new_position_x, new_position_y, 'bo')
            new_position_x.clear()
            new_position_y.clear()

        if(windowActive):
            try:
                fig = plt.gcf()
                fig.canvas.draw()
                im = Image.frombytes('RGB',
                                     fig.canvas.get_width_height(),
                                     fig.canvas.tostring_rgb())
                imgtk = ImageTk.PhotoImage(image=im)
                dataLabel.imgtk = imgtk
                dataLabel.configure(image=imgtk)
            except:
                print("Couldn't display plot")

def main():
    global ser, windowActive
    #Find available ports
    ports = list_ports.comports()
    ports = [p.name for p in ports]
    print(ports)

    #Initialize serial interface
    serialPort = input("Port: ")
    while serialPort not in ports:
        print("Please enter a valid port")
        serialPort = input("Port: ")
    ser = serial.Serial(serialPort, 115200)
    print("Opened connection on port " + serialPort)

    liveDataSetup()
    #updateLiveFeed()
    
    #Start threads
    serialThread = threading.Thread(target=checkData)
    cameraThread = threading.Thread(target=liveFeed)
    plottingThread = threading.Thread(target=liveData)

    serialThread.start()
    cameraThread.start()
    plottingThread.start()

    window.mainloop()

    #Cleanup
    windowActive = False
    print("done")
    capture.release()
    while not serialDone:
        pass
    ser.close()

    #Adjust timestamps for overflow and alignment
    if(len(daq_sync_timestamps) > 0):
        initial_time = daq_sync_timestamps[0]

        adjustTimestamps(daq_sync_timestamps)
        adjustTimestamps(odor_on_timestamps)
        adjustTimestamps(odor_off_timestamps)
        adjustTimestamps(motion_timestamps)

    #Output to .mat file for use with MATLAB
    scipy.io.savemat("out.mat", output_dict)

if __name__ == '__main__':
    main()
