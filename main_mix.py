import StepClass
import UltrasonicClass
import time
import RPi.GPIO as GPIO
import os
import json
from firebase import firebase
from pyfcm import FCMNotification
from multiprocessing import Process

def isEqualtime(input_time):
    year = int(input_time[0:4])
    month = int(input_time[5:7])
    day = int(input_time[8:10])
    hour = int(input_time[11:13])
    min = int(input_time[14:])
    c_year = int(time.strftime('%y'))
    c_month = int(time.strftime('%m'))
    c_day = int(time.strftime('%d'))
    c_hour = int(time.strftime('%H'))
    c_min = int(time.strftime('%M'))
    time.sleep(5)
    if(hour == c_hour and min == c_min and year == c_year and month == c_month and c_day == day):
        return True
    else:
        return False
    

def isExceedtime(input_time, threshold):
    hour = int(input_time[11:13])
    min = int(input_time[14:])
    c_hour = int(time.strftime('%H'))
    c_min = int(time.strftime('%M'))
    tmin = 60*hour + min
    tcmin = 60*c_hour + c_min
    if((tcmin-tmin)>threshold):
        return True
    else:
        return False

def getToken(fcm):
    rawtoken = fcm.get("/TOKEN",None)
    return rawtoken.replace('"',"",2)

if __name__ == '__main__':
    us = UltrasonicClass.Ultrasonic() #method list : getDistance, Cleanup
    sm = StepClass.StepMotor() #method list : step
    fcm = firebase.FirebaseApplication("https://ddoyak-362cb.firebaseio.com/",None) #fcm database object
    push_service = FCMNotification(api_key="AAAANJ-9vtU:APA91bGKUyUHMY0Rj32m9FhP4eFJTP-9xwFmSHjkTqJDmmDEmZL5tJOtJ2PvrAwL5jBErjs8uC9pjE8WRua1Iooakul7lACDwAvgYg8n5r3Jfix8Ggcw89KXVQ50UCgg-hCbPj7_uaddOsNd09fk4q-eWbt0sW2G7A")
    
    mode = True # true:time check , false:distance check(whether user dose medicine)
    threshold = 5 # threshold of ultrasonic sensor value
    while True:
       if(mode): #time check mode
            pains = fcm.get("/DOSE",None).keys()
            outings = fcm.get("/OUTING",None).keys()
            Outinglist = []
            Alarmlist = []
            AlarmCount = 3

            for i in range(0,len(pains)):
                Alarmlist.append(fcm.get("/DOSE/"+pains[i],None))
                Alarmlist[i].sort()
            for i in range(0,len(outings)):
                Outinglist.append(fcm.get("/OUTING"+outings[i],None))

            minimumTime = Alarmlist[0][0]
            selectedPain = pains[0]
            selectedPainNumber = 0
            minimumOut = Outinglist[0][0]
            selectedOut = outings[0]
            selectedOutNumber = 0

            for i in range(0, len(pains)):
                if Alarmlist[i][0] <= minimumTime:
                    minimumTime = Alarmlist[i][0]
                    selectedPainNumber = i
                    selectedPain = pains[i]
                else:
                    pass
            for i in range(0,len(outings)):
                if Outinglist[i][0] <= minimumOut:
                    minimumOut = Outinglist[i][0]
                    selectedOutNumber = i
                    selectedOut = outings[i]
            
            print("Selected Pain & Time : ",selectedPain, minimumTime, "Selected Outing Schedule : ", selectedOut)

            

            nextAlarmTime = minimumTime
            if(isEqualtime(nextAlarmTime) or True): # when the time is to provide a medicine
                sm.step()
                mode = False
                Alarmlist[selectedPainNumber].remove(nextAlarmTime)
                #refresh the database
                result2 = fcm.patch("/DOSE",{ selectedPain : Alarmlist[selectedPainNumber]})
                #fcm.delete("/DOSE/m1","0")
                
                time.sleep(5)
            else:
                pass
        #distance check mode
       else:
            if(us.getDistance()>threshold and False):
                #result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="user takes a medicine.")
                print("[SYSTEM] taking Alarm is generated in andrioid Device")
                history = fcm.get("/HISTORY/"+selectedPain,None)
                if history == None:
                    history = []
                history.append(nextAlarmTime+"#1#"+selectedPain)
                result = fcm.patch("/",{"/HISTORY" : history})
                time.sleep(5)
                #add to delete from database
            else:
                if(AlarmCount == 3):
                    if(isExceedtime(nextAlarmTime,5)): # if the medicine is not brought for 5 mintues
                        #result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="user does not take a medicine.")
                        print("[SYSTEM] 1 not taking Alarm is generated in android Device")
                        AlarmCount -= 1
                        time.sleep(5)
                    else:
                        pass
                elif(AlarmCount == 2) :
                    if(isExceedtime(nextAlarmTime,10)):
                        #result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="user does not take a medicine.")
                        print("[SYSTEM] 2 not taking Alarm is generated in android Device")
                        AlarmCount -= 1
                        time.sleep(5)
                elif(AlarmCount == 1) :
                    if(isExceedtime(nextAlarmTime,15)):
                        #result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="user does not take a medicine.")
                        print("[SYSTEM] 3 not taking Alarm is generated in android Device")
                        AlarmCount -= 1
                        time.sleep(5)
                else:
                    if(isExceedtime(nextAlarmTime,15)):
                        #result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="user does not take a medicine.")
                        print("[SYSTEM] really not taking Alarm is generated in android Device")
                        history = fcm.get("/HISTORY",None)
                        if history == None:
                            history = []
                        history.append(nextAlarmTime+"#0#"+selectedPain)
                        result = fcm.patch("/",{"/HISTORY" : history})
                        AlarmCount = 3
                        mode = True
                        time.sleep(5)
                

                    
        
        
    
    ###push service###
    #result = push_service.notify_single_device(registration_id=getToken(fcm),message_body="Hello2",data_message=data_message)
    
    ###database patch###
    #result2 = firebase.patch("/OUTING",{"o2" : ["s#2018#08#22#09#00", "e#2018#08#22#18#00"]})
    
    