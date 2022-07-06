import tkinter
import cv2
import PIL.Image, PIL.ImageTk
import time
import multiprocessing as mp
import re
import os
import tifffile


# Used guide here:https://solarianprogrammer.com/2018/04/21/python-opencv-show-video-tkinter-window/
saveDirectory = "C:\\Users\\Mike\\Documents\\DeleteMe" # Later update to current directory + data folder or something

class App:
    def __init__(self, window, window_title, savedir, video_source=0):
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source

        # open video source (by default this will try to open the computer webcam)
        self.imRead, imWrite = mp.Pipe(False)
        vidTermRead, self.vidTermWrite = mp.Pipe(False)
        vidExptControlRead, self.vidExptControlWrite = mp.Pipe(False)
        pCam = mp.Process(target=camMain, args=(self.video_source, savedir, imWrite, vidTermRead, vidExptControlRead))
        pCam.start()

        # Grab one frame of video in order to set size of window correctly
        while(True):
            if self.imRead.poll():
                frame = self.imRead.recv()
                break
        # self.vid.width = frame.shape[0]
        # self.vid.height = frame.shape[1]
        # self.canvas = tkinter.Canvas(window, width = self.vid.width, height = self.vid.height) # Doesn't seem to be updating for some reason?
        # self.canvas = tkinter.Canvas(window, width=500, height=500)
        # # self.canvas.pack(side="left", anchor=tkinter.CENTER, expand=True)
        # self.canvas.pack(anchor=tkinter.CENTER, expand=True)

        # Button: Manually start video recording
        self.btn_snapshot=tkinter.Button(window, text="Rec Video", width=20, command=self.startVid)
        # self.btn_snapshot.pack(side="left", anchor=tkinter.NW, expand=True)
        self.btn_snapshot.pack(anchor=tkinter.NW, expand=True)

        # Button: Manually end video recording
        self.btn_snapshot = tkinter.Button(window, text="Stop Video", width=20, command=self.endVid)
        # self.btn_snapshot.pack(side="left", anchor=tkinter.NW, expand=True)
        self.btn_snapshot.pack(anchor=tkinter.NW, expand=True)

        self.canvas = tkinter.Canvas(window, width=500, height=500)
        # self.canvas.pack(side="left", anchor=tkinter.CENTER, expand=True)
        self.canvas.pack(anchor=tkinter.CENTER, expand=True)

        # Button: Start Experiment
        self.btn_snapshot = tkinter.Button(window, text="Start Expt", width=20, command=self.startExpt)
        # self.btn_snapshot.pack(side="left", anchor=tkinter.SW, expand=True)
        self.btn_snapshot.pack(anchor=tkinter.SW, expand=True)

        # Button: Cancel Experiment
        self.btn_snapshot = tkinter.Button(window, text="Cancel Expt", width=20, command=self.cancelExpt)
        # self.btn_snapshot.pack(side="left", anchor=tkinter.SW, expand=True)
        self.btn_snapshot.pack(anchor=tkinter.SW, expand=True)

        # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 3
        self.update()

        self.window.mainloop()

    def startVid(self):
        # Send command to start recording video
        self.vidExptControlWrite.send(1)

    def endVid(self):
        # Send command to stop recording video
        self.vidExptControlWrite.send(2)

    def startExpt(self):
        # Send command to stop recording video
        # self.vidExptControlWrite.send(2)
        print("wip")

    def cancelExpt(self):
        # Send command to stop recording video
        # self.vidExptControlWrite.send(2)
        print("wip")

    def update(self):
        if self.imRead.poll():
            frame = self.imRead.recv()
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tkinter.NW)

        self.window.after(self.delay, self.update)

    def __del__(self):
        self.vidTermWrite.send(0)



def camMain(video_source, saveDirectory, imWrite, vidTermRead, vidExptControlRead):
    cap = cv2.VideoCapture(0)
    remainActive = True

    # Temp - decide on video method, if tiffs kept update this
    nTiffIms = 200

    # Command key
    # 0 - waiting
    # 1 - begin saving experiment data
    # 2 - experiment complete, terminate files, reset to 0
    command = 0

    while(remainActive):
        # Check whether overall app has been terminated
        if vidTermRead.poll():
            remainActive = vidTermRead.recv()
        # If not, continue, otherwise exit loop and terminate
        else:
            # Listen for commands regarding experiment status
            if vidExptControlRead.poll():
                command = vidExptControlRead.recv()
                if command == 1:
                    # Prepare files for starting to write
                    date = re.sub('[: ]', '_', time.ctime())
                    savedir = saveDirectory + '/Data/' + date + '/camfiles'

                    # Make save directory
                    os.makedirs(savedir)

                    # Open timestamp file
                    filename = savedir + '/imdata_' + date + '.csv'
                    datafile = open(filename, 'a')

                    imCounter = 0
                    outIter = 0
                elif command == 2:
                    datafile.close()
                    command = 0

            # Grab image frame and timestamp
            frame = cap.read()[1]
            timestamp = time.time()  # temporary until better frame timestamp is figured out

            # If experiment active, save image files and timestamps
            if command == 1:
                imCounter = imCounter + 1
                if imCounter == nTiffIms:
                    outIter = outIter + 1
                    imCounter = 0

                # Save image to file
                tifffile.imwrite(savedir + '/images' + str(outIter) + '.tif', frame, photometric='rgb',
                                 compression='jpeg', append=True)
                datafile.write(str(timestamp) + '\n')
                # try:
                #     tifffile.imwrite(savedir + '/images' + str(outIter) + '.tif', frame, photometric='rgb',
                #                      compression='jpeg', append=True)
                #     datafile.write(str(timestamp) + '\n')
                # except:
                #     try:
                #         print('savefile permission denied, try 2')
                #         tifffile.imwrite(savedir + '/images' + str(outIter) + '.tif', frame, photometric='rgb',
                #                          compression='jpeg',
                #                          append=True)
                #         datafile.write(str(timestamp) + '\n')
                #     except:
                #         print('savefile permission denied, skipping')

            # Regardless, update the GUI with the video frame data
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # This has no effect for some reason, r and b remain reversed
            imWrite.send(frame)

    # When the overall app has been terminated release the video before exiting the process
    cap.release()

# Create a window and pass it to the Application object
if __name__ == '__main__':
    App(tkinter.Tk(), "Spherical Treadmill Task GUI", saveDirectory)