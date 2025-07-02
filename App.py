from flask import Flask, render_template, Response, request
import cv2
import mediapipe as mp
import math
import time
import numpy as np
import threading
import json
#render_template bakal otomatis ke folder templates.

# WSGI (Web Server Gateway Interface) 
app = Flask(__name__)

# for pausing purpose.
pause_event = threading.Event()
pause_event.set()

# for locking the thread, to reset the calibration values.
reset_lock = threading.Lock()
reset_requested = threading.Event()

normalizedRatios = [] # list of 100 normalized "merem" ratios, which comes from averaging "ratios" stack. filled once at the start of the program.
nRatioAvg = 0 # Average of normalizedRatios which are expected to be filled with merem normalized ratios as a way to calibrate.
sd = 0 # standard deviation of meremAvg. float32 or 10^-6 precision.`

text_lock = threading.Lock() # to lock the resources as the server sends morse and hasil to the page.
text_update_event = threading.Event()
morse = "" # the morse code conveyed by the user's right eyelid.
hasil = "" # the alphabetic translation of said morse code.

stop_event = threading.Event()

# ini namanya "decorator"
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_stream', methods=['POST'])
def toggle_stream():
    if pause_event.is_set():
        pause_event.clear()  # Pause
        return {'status': 'paused'}
    else:
        pause_event.set()    # Resume
        return {'status': 'playing'}

@app.route('/calibrate', methods=['POST'])
def reset_data():
    reset_requested.set()
    return {'status': 'reset done'}

@app.route('/quit', methods=['POST'])
def quit_stream():
    reset_data()
    global hasil, morse
    with text_lock:
        hasil=""
        morse=""
        text_update_event.set()
    stop_event.set()  # Signal the loop to exit
    return "Stopped", 200

# Server-Sent Events (SSE)
# to send hasil and morse strings to the page.
@app.route('/results')
def results():
    def event_stream():
        while True:
            # Wait until text is updated
            text_update_event.wait()
            text_update_event.clear()

            with text_lock:
                payload = {
                    "hasil": hasil,
                    "morse": morse
                }

                data = json.dumps(payload)

                yield f"data: {data}\n\n"

    return Response(event_stream(), content_type='text/event-stream')

def generate_frames():
    stop_event.clear()

    cap = cv2.VideoCapture(0)

    global morse, hasil

    idList = [160, 144, 158, 153, 33, 133]
    detector = FaceMeshDetector(target=idList)

    ratios = [] # stack filled with 10 ratios from 10 frames. constantly updated.

    melek = False # current frame eyelid status.
    swMerem = 0 # stopwatch for merem.
    swMelek = time.time() # stop watch for melek.

    while not stop_event.is_set():
        # pausing point. pausing event handler.
        pause_event.wait()

        # calibrate request handler.
        if reset_requested.is_set():
            with reset_lock:
                normalizedRatios.clear()
                nRatioAvg = 0
                sd = 0
                reset_requested.clear()

        ## read the camera frame
        success, img = cap.read()

        if not success:
            break
        
        find, face = detector.findFaceMesh(img) # returning array of 467(more or less) landmark coordinates of a (singular) person's face in the image. 
        if find == True:

            # the targeted landmark coordinates. 
            # 6 specific landmark coordinates located around the perimeter of the right eye.
            # indexed by the findFaceMesh() method which only relevant in this particular module.  
            # naturally the order highly matters.
            kananLmAtas = face[5] #5
            kananLmBawah = face[2] #2
            kananLmAtas2 = face[4] #4
            kananLmBawah2 = face[3] #3
            kananLmOuter = face[0] #0
            kananLmInner = face[1] #1

            # finding the distance of each spesific pair of landmarks. these distances/lines will be used to calculate "Eye Aspect Ratio". 
            kananVertikal = detector.findDistance(kananLmAtas, kananLmBawah)
            kananVertikal2 = detector.findDistance(kananLmAtas2, kananLmBawah2)
            kananHorizontal = detector.findDistance(kananLmInner, kananLmOuter)

            # drawing said distances as lines on the frame/image. 
            cv2.line(img, kananLmAtas, kananLmBawah, (0,0,255), 1)
            cv2.line(img, kananLmAtas2, kananLmBawah2, (0,0,255), 1)
            cv2.line(img, kananLmInner, kananLmOuter, (0,0,255), 1)

            # calculating EAR as percentage.
            ratio = ((kananVertikal+kananVertikal2)/(2*kananHorizontal))*100

            # normalizing ratios by averaging 10 frames, including the current one.
            if len(ratios) > 10:
                ratios.pop(0)

            ratios.append(ratio)
            nRatio = np.mean(ratios) # normalized ratio.

            # the average of normalized ratio. expected to be filled with merem ones as a way to calibrate this system.
            # only accessed at the first time the app opens.
            if len(normalizedRatios) < 100:
                normalizedRatios.append(nRatio)
                nRatioAvg = np.mean(normalizedRatios)

                sd = np.std(ratios, dtype = np.float32) # the standard deviation.
                
                # to write calibration progress on the live feed images. 
                cv2.putText(img, f"tunggu: {len(normalizedRatios)}/100", (400, 20), cv2.FONT_ITALIC, 1, (255,255,0), 3)
            else:
                # z score : nilai deviasi dari titik data relatif rata-rata.
                # contohnya z score 27 dari mean 23 dan sd 2 = 27-23/2 = 2 poin (melenceng sejauh 2 sd dari mean)    
                zScore = (nRatio-nRatioAvg)/sd

                if zScore > 1: # if melek
                    with text_lock:
                        if abs(time.time()-swMelek) >= 2:
                            swMelek = time.time()
                            if morse[-2:] != "  ":
                                morse += " "
                                text_update_event.set() 

                        if melek == False: # and if merem previously
                            # it's a sign of user done blinking
                            morse += kedipmorse(swMerem) # parse that signal with kedipmorse() and the starting merem time.
                            text_update_event.set()

                    swMerem = 0 # resetting the merem stopwatch, because it's melek now.
                    melek = True # set the status.

                else: # if merem
                    if melek == True: # and if melek previously
                        swMerem = time.time() # start the merem stopwatch (counting merem duration).

                    swMelek = time.time() # reset the melek stopwatch.

                    melek = False # set the status.

                with text_lock:
                    hasil = decrypt(morse) # decrypting the given signals so far.
                    text_update_event.set()

        # live feeding the frames/img.jpg to the page. 
        _, buffer = cv2.imencode('.jpg',img)
        img = buffer.tobytes()

        # idk
        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')
    
    cap.release()




###ajnsabdhbhb
###

def decrypt(message):
    MORSE_CODE_DICT = {'A': '.-', 'B': '-...',
                    'C': '-.-.', 'D': '-..', 'E': '.',
                    'F': '..-.', 'G': '--.', 'H': '....',
                    'I': '..', 'J': '.---', 'K': '-.-',
                    'L': '.-..', 'M': '--', 'N': '-.',
                    'O': '---', 'P': '.--.', 'Q': '--.-',
                    'R': '.-.', 'S': '...', 'T': '-',
                    'U': '..-', 'V': '...-', 'W': '.--',
                    'X': '-..-', 'Y': '-.--', 'Z': '--..',
                    '1': '.----', '2': '..---', '3': '...--',
                    '4': '....-', '5': '.....', '6': '-....',
                    '7': '--...', '8': '---..', '9': '----.',
                    '0': '-----', ', ': '--..--', '.': '.-.-.-',
                    '?': '..--..', '/': '-..-.', '-': '-....-',
                    '(': '-.--.', ')': '-.--.-'}

    # extra space added at the end to access the
    # last morse code
    message += ' '

    decipher = ''
    citext = ''
    i = 0
    for letter in message:

        # checks for space
        if (letter != ' '):

            # counter to keep track of space
            i = 0

            # storing morse code of a single character
            citext += letter

        # in case of space
        else:
            # if i = 1 that indicates a new character
            i += 1

            # if i = 2 that indicates a new word
            if i == 2 :

                # adding space to separate words
                decipher += ' '
            else:
                try:
                    search = list(MORSE_CODE_DICT.keys())[list(MORSE_CODE_DICT
                                                            .values()).index(citext)]
                    # accessing the keys using their values (reverse of encryption)
                except:
                    search = ""
                decipher += search
                citext = ''

    return decipher



def kedipmorse(start):
    duration = abs(time.time()-start)
    if duration >= 1:
        return "-"
    elif duration > 0:
        return "."
    else:
        return ""


       

class FaceMeshDetector:
    def __init__(self, target):
        self.mpFaceMesh = mp.solutions.face_mesh
        self.faceMesh = self.mpFaceMesh.FaceMesh(static_image_mode=False,
                                                 max_num_faces=1,
                                                 min_detection_confidence=0.5,
                                                 min_tracking_confidence=0.5)
        self.target = target

    def findFaceMesh(self, img):
        """
                Finds face landmarks in BGR Image.
        :param img: Image to find the face landmarks in.
        :param draw: Flag to draw the output on the image.
        :return: Image with or without drawings
        """
        self.imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.faceMesh.process(self.imgRGB)
        # faces = []
        face = []
        detection = False
        if results.multi_face_landmarks:
            detection = True    
            faceLms = results.multi_face_landmarks[0]
            for id,lm in enumerate(faceLms.landmark):
                if id in self.target:
                    ih, iw, ic = img.shape
                    x, y = int(lm.x * iw), int(lm.y * ih)
                    face.append([x,y])
                else : pass
        return detection, face

    def findDistance(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2

        length = math.hypot(x2 - x1, y2 - y1)

        return length

if __name__=="__main__":
    app.run(threaded=True)