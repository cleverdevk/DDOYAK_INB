#coding:utf-8

from firebase import firebase
from pyfcm import FCMNotification
import pygame

def getToken(fcm): #To using Token for FCM Cloud Messaging
    rawtoken = fcm.get("/TOKEN",None)
    return rawtoken.replace('"',"",2)
push_service = FCMNotification(api_key="AAAANJ-9vtU:APA91bGKUyUHMY0Rj32m9FhP4eFJTP-9xwFmSHjkTqJDmmDEmZL5tJOtJ2PvrAwL5jBErjs8uC9pjE8WRua1Iooakul7lACDwAvgYg8n5r3Jfix8Ggcw89KXVQ50UCgg-hCbPj7_uaddOsNd09fk4q-eWbt0sW2G7A")
fcm = firebase.FirebaseApplication("https://ddoyak-362cb.firebaseio.com/",None)
result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="약을 복용하였습니다.")
