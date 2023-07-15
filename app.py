import streamlit as st
from PIL import Image
import cv2
import numpy as np
from keras.models import model_from_json
from main import *
from PIL import Image


def detect_emotion(img):
    json_file = open('model/emotion_model.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    
    emotion_model = model_from_json(loaded_model_json)
    
    emotion_model.load_weights('model/emotion_model.h5')
    
    frame = cv2.resize(img, (1280, 720))
    face_detector = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_default.xml')
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    num_faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)
    
    for (x,y,w,h) in num_faces:
        cv2.rectangle(frame, (x,y-50), (x+w, y+h+10), (0,255,0), 4)
        roi_gray_frame = gray_frame[y:y + h, x:x + w]
        cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray_frame, (48, 48)), -1), 0)
        
        emotion_prediction = emotion_model.predict(cropped_img)
        maxindex = int(np.argmax(emotion_prediction))
        cv2.putText(frame, emotion_dict[maxindex], (x+5, y-20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        
        
    return frame, maxindex
    
   
    
if __name__=='__main__':

    st.title("Music Recommender System")
    
    emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful", 4: "Happy", 5: "Sad", 6: "Surprised"}
    # genres = {"Action":28, "Comedy":35, "Crime":80, "Fantasy":14, "Horror":27, "Thriller":53}
    
    try:

        img_file_buffer = st.camera_input("Capture")
        if img_file_buffer is not None:
            image = Image.open(img_file_buffer)
            cv2_img = np.array(image)
            img, id = detect_emotion(cv2_img)
            
        st.write("Detected Emotion: "+emotion_dict[id])
            
        if st.button('Recommend Music'):
            tracks = recom_song(emotion_dict[id])
            for track in tracks:
                st.write(f'Link to Track" {track}')
                    
    except:
        st.write("Please try again!")
            
        
