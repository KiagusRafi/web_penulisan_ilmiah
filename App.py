from flask import Flask, render_template, Response
import cv2
import mediapipe as mp
import math
import time
import numpy as np
#render_template bakal otomatis ke folder templates.

# WSGI (Web Server Gateway Interface) 
app = Flask(__name__)

def generate_frames():
    cap = cv2.VideoCapture(0)

    idList = [160, 144, 158, 153, 33, 133]
    detector = FaceMeshDetector(target=idList)

    ratios = [] # stack filled with 10 ratios from 10 frames. constantly updated.
    normalizedRatios = [] # list of 100 normalized "merem" ratios, which comes from averaging "ratios" stack. filled once at the start of the program.

    melek = False # current frame eyelid status.
    swMerem = 0 # stopwatch for merem.
    swMelek = time.time() # stop watch for melek.
    morse = "" # the morse code conveyed by the user's right eyelid.
    hasil = "" # the alphabetic translation of said morse code.
    meremAvg = 0 # Average of normalizedRatios which are expected to be filled with merem normalized ratios as a way to calibrate. 
    sd = 0 # standard deviation of meremAvg. float32 or 10^-6 precision.

    while True:
        ## read the camera frame
        success, img = cap.read()

        if not success:
            break
        
        face = detector.findFaceMesh(img) # returning array of 467(more or less) landmark coordinates of a (singular) person's face in the image. 
        
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

        # finding the distance of each elaborate pair of landmarks. these distances/lines will be used to calculate "Eye Aspect Ratio" 
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
            meremAvg = np.mean(normalizedRatios)

            sd = np.std(ratios, dtype = np.float32) # the standard deviation.
            
            # to write calibration progress on the live feed images. 
            cv2.putText(img, f"tunggu: {len(ratios)}/100", (500, 20), cv2.FONT_ITALIC, 1, (255,255,0), 3)
        else:
            # z score : nilai deviasi dari titik data relatif rata-rata.
            # contohnya z score 27 dari mean 23 dan sd 2 = 27-23/2 = 2 poin (melenceng sejauh 2 sd dari mean)    
            zScore = (nRatio-meremAvg)/sd

            if zScore > 1: # if melek
                # to add a white space if the user melek for 2s or more.
                # the decrypt() function only expects 2 space maximum in the end of string "morse" (2 spaces will be translated as 1, and 1 space will be the sign of the next letter).
                # given more, it will break.
                # blame whoever made that in geeksforgeeks.
                if abs(time.time()-swMelek) >= 2:
                    swMelek = time.time()
                    if morse[-2:] != "  ":
                        morse = morse + " "

                if melek == False: # and if merem previously
                    # it's a sign of user done blinking
                    morse = morse + kedipmorse(swMerem) # parse that signal with kedipmorse() and the starting merem time.

                swMerem = 0 # resetting the merem stopwatch, because it's melek now.
                melek = True # set the status.

            else: # if merem
                if melek == True: # and if melek previously
                    swMerem = time.time() # start the merem stopwatch (counting merem duration).

                swMelek = time.time() # reset the melek stopwatch.

                melek = False # set the status.


            hasil = decrypt(morse) # decrypting the given signals so far.

            # just to write the melek status, conveyed morse code, and it's alphabetic translation. 
            if melek:
                warna = (0,255,0)
            else:
                warna = (0,0,255)

            cv2.putText(img, str(melek), (10, 70), cv2.FONT_ITALIC, 3, warna, 3)
            cv2.putText(img, morse, (70, 10), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 255), 1)
            cv2.putText(img, hasil, (70, 30), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)

        # imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


        # live feeding the frames/img.jpg to the page. 
        ret, buffer = cv2.imencode('.jpg',img)
        img = buffer.tobytes()

        # idk
        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')


# ini namanya "decorator"
@app.route('/')
def index(): 
    #kolor babe
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')


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
        self.results = self.faceMesh.process(self.imgRGB)
        # faces = []
        face = []
        # if self.results.multi_face_landmarks:
        faceLms = self.results.multi_face_landmarks[0]
        for id,lm in enumerate(faceLms.landmark):
            if id in self.target:
                ih, iw, ic = img.shape
                x, y = int(lm.x * iw), int(lm.y * ih)
                # face.append([x, y])
                face.append([x,y])
            else : pass
            # faces.append(face)
        # print(face)
        return face

    def findDistance(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2

        length = math.hypot(x2 - x1, y2 - y1)

        return length

if __name__=="__main__":
    app.run()