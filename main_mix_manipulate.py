#coding:utf-8
import pygame
import StepClass
import UltrasonicClass
import time
import RPi.GPIO as GPIO
import os
import json
import sys
from firebase import firebase
from pyfcm import FCMNotification
from multiprocessing import Process

def isEqualtime(input_time): #compare input_time with current time(system) and return bool value
    year = int(input_time[0:4])
    month = int(input_time[5:7])
    day = int(input_time[8:10])
    hour = int(input_time[11:13])
    min = int(input_time[14:])
    c_year = 2000 +int(time.strftime('%y'))
    c_month = int(time.strftime('%m'))
    c_day = int(time.strftime('%d'))
    c_hour = int(time.strftime('%H'))
    c_min = int(time.strftime('%M'))
    print("[SYSTEM] Current Time : {0}:{1}:{2}:{3}:{4}".format(c_year,c_month,c_day,c_hour,c_min))
    print("[SYSTEM] input Time   : {0}:{1}:{2}:{3}:{4}".format(year,month,day,hour,min))
    time.sleep(5)
    if(hour == c_hour and min == c_min and year == c_year and month == c_month and c_day == day):
        return True
    else:
        return False
    
def isObsoleteTime(input_time):
    year = int(input_time[0:4])
    month = int(input_time[5:7])
    day = int(input_time[8:10])
    hour = int(input_time[11:13])
    min = int(input_time[14:])
    c_year = 2000 +int(time.strftime('%y'))
    c_month = int(time.strftime('%m'))
    c_day = int(time.strftime('%d'))
    c_hour = int(time.strftime('%H'))
    c_min = int(time.strftime('%M'))
    print("[SYSTEM] Current Time : {0}:{1}:{2}:{3}:{4}".format(c_year,c_month,c_day,c_hour,c_min))
    print("[SYSTEM] input Time   : {0}:{1}:{2}:{3}:{4}".format(year,month,day,hour,min))
    time.sleep(5)
    if(c_year > year):
        return True
    elif(c_month > month and c_year == year):
        return True
    elif(c_day > day and c_year == year and c_month == month):
        return True
    elif(c_hour > hour and c_year == year and c_month == month and c_day == day):
        return True
    elif(c_min > min and c_year == year and c_month == month and c_day == day and c_hour == hour):
        return True
    else:
        return False

def isExceedtime(input_time, threshold): #determine whether input_time exceed the threshold term and return bool value
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

def inOutingSchedule(input_time, start_time, end_time): #determine whether input_time is in the term between outing schedule
    if(input_time>=start_time and input_time<=end_time):
        return True
    else:
        return False


def getToken(fcm,patient_id): #To using Token for FCM Cloud Messaging
    rawtoken = fcm.get("/"+patient_id+"/TOKEN",None)
    if rawtoken == None:
        return None
    else:
        return rawtoken.replace('"',"",2)

def getGuardianToken(fcm,patient_id):
    rawtoken = fcm.get("/"+patient_id+"/TOKEN_GUARDIAN", None)
    if rawtoken == None:
        return None
    else:
        return rawtoken.replace('"',"",2)

def UPDATEorNOT(fcm,patient_id,input_selectedPain,input_selectedOut,isOuting):
    pains = fcm.get("/"+patient_id+"/DOSE",
                    None).keys()  # Pain name list of Database(/DOSE/[*]) ex) [cold, schizophrenia, headache ...]
    if(fcm.get("/"+patient_id+"/OUTING",None) == None or fcm.get("/"+patient_id+"/OUTING",None) == "0"):
             c_isOuting = False
             outings = []
    else:
        outings = fcm.get("/"+patient_id+"/OUTING", None).keys() #Outing Schedule list of Database (/OUTING/[*])
        c_isOuting = True
    Outinglist = []  # Two Dimentional list that contain outing dates. ex) [ ["yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM"],["yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM"]]
    Alarmlist = []  # Two Dimentional list that contain dosing dates. ex) [ ["yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM"],["yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM"]]
    for i in range(0, len(pains)):  # init Alarmlist by getting list from database and alignment
        Alarmlist.append(fcm.get("/"+patient_id+"/DOSE/" + pains[i], None))
        Alarmlist[i].sort()
    if(c_isOuting):
        for i in range(0, len(outings)):  # init Outinglist by getting list from database
            Outinglist.append(fcm.get("/"+patient_id+"/OUTING/" + outings[i], None))
    minimumTime = Alarmlist[0][0]  # To search minimumTime of Alarm
    selectedPain = pains[0]

    if(c_isOuting):
        minimumOut = Outinglist[0][1]  # To search minimumTime of Outing
        selectedOut = outings[0]

    for i in range(0, len(pains)):  # Searching minimum Alarm Time
        if Alarmlist[i][0] <= minimumTime:
            minimumTime = Alarmlist[i][0]
            selectedPain = pains[i]
        else:
            pass
    if(c_isOuting):
        for i in range(0, len(outings)):  # Searching minimum Outing Time
            if Outinglist[i][1] <= minimumOut:
                minimumOut = Outinglist[i][1]
                selectedOut = outings[i]
    else:
        minimumOut = None
        selectedOut = None
    if(selectedPain == input_selectedPain and selectedOut == input_selectedOut and isOuting == c_isOuting):
        return False
    else:
        return True



if __name__ == '__main__':
    us = UltrasonicClass.Ultrasonic() #method list : getDistance, Cleanup // this syntax is like " UltrasonicClass.UltraSonic us = new UltrasonicClass.Ultrasonic()" in JAVA
    sm = StepClass.StepMotor() #method list : step
    fcm = firebase.FirebaseApplication("https://ddoyak-362cb.firebaseio.com/",None) #fcm database object
    push_service = FCMNotification(api_key="AAAANJ-9vtU:APA91bGKUyUHMY0Rj32m9FhP4eFJTP-9xwFmSHjkTqJDmmDEmZL5tJOtJ2PvrAwL5jBErjs8uC9pjE8WRua1Iooakul7lACDwAvgYg8n5r3Jfix8Ggcw89KXVQ50UCgg-hCbPj7_uaddOsNd09fk4q-eWbt0sW2G7A")
    iteration = 0
    pygame.mixer.init()
    pygame.mixer.music.load("ifonger.mp3")
    
    mode = True # true:time check , false:distance check(whether user dose medicine)
    threshold = 7.1 # threshold of ultrasonic sensor value
    isOuting = False
    
    #Connect ID
    ids = fcm.get("/", None).keys()
    while True:
        sys.stdout.write("[SYSTEM] Input the patient ID : ")
        patient_id = raw_input()
        if(patient_id in ids):
            print("[SYSTEM] Account '"+patient_id+"' ' is connected! ")
            break;
        else:
            print("[SYSTEM] Account '"+patient_id+"' does not exist. Please Input the patient ID again.")



    while True:
         if(fcm.get("/"+patient_id+"/DOSE",None) == None or fcm.get("/"+patient_id+"/DOSE",None) == "0"):
             print("There is no Schedule for Dosing, Waiting...")
             time.sleep(3)
             continue
         else:
             pains = fcm.get("/"+patient_id+"/DOSE", None).keys() #Pain name list of Database(/DOSE/[*]) ex) [cold, schizophrenia, headache ...]
         if(fcm.get("/"+patient_id+"/OUTING",None) == None or fcm.get("/"+patient_id+"/OUTING",None) =="0"):
             print("There is no Schedule for Outing.")
             isOuting = False
         else:
             outings = fcm.get("/"+patient_id+"/OUTING", None).keys() #Outing Schedule list of Database (/OUTING/[*])
             isOuting = True
         Outinglist = [] #Two Dimentional list that contain outing dates. ex) [ ["s#yyyy#mm#dd#HH#MM","e#yyyy#mm#dd#HH#MM"],["s#yyyy#mm#dd#HH#MM","e#yyyy#mm#dd#HH#MM"]]
         Alarmlist = [] #Two Dimentional list that contain dosing dates. ex) [ ["yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM"],["yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM","yyyy#mm#dd#HH#MM"]]
         AlarmCount = 3 # Count integer to generate three alarm notification
         for i in range(0, len(pains)): #init Alarmlist by getting list from database and alignment
            Alarmlist.append(fcm.get("/"+patient_id+"/DOSE/" + pains[i], None))
            Alarmlist[i].sort()
         if(isOuting):
             for i in range(0, len(outings)): #init Outinglist by getting list from database
                Outinglist.append(fcm.get("/"+patient_id+"/OUTING/" + outings[i], None))
         minimumTime = Alarmlist[0][0] #To search minimumTime of Alarm
         selectedPain = pains[0]
         selectedPainNumber = 0

         if(isOuting):
             minimumOut = Outinglist[0][1] #To search minimumTime of Outing
             selectedOut = outings[0]
             selectedOutNumber = 0
             #outingFlag = False
         else:
             pass

         for i in range(0, len(pains)): #Searching minimum Alarm Time
             if(Alarmlist[i][0] <= minimumTime):
                 minimumTime = Alarmlist[i][0]
                 selectedPainNumber = i
                 selectedPain = pains[i]
             else:
                 pass
         if(isOuting):
             for i in range(0, len(outings)): #Searching minimum Outing Time
                 if(Outinglist[i][1] <= minimumOut):
                     minimumOut = Outinglist[i][1]
                     selectedOutNumber = i
                     selectedOut = outings[i]

             currentOutingStart = Outinglist[selectedOutNumber][1][2:] #Slicing String of Outing
             currentOutingEnd = Outinglist[selectedOutNumber][2][2:] #Slicing String of Outing

        #################### for give a different portion of medicine ##############################
         outingStackCount = list()
         if(isOuting):
             
             outingStackFlag = list()
             
             for i in range(0, len(Alarmlist[selectedPainNumber])):
                 outingStackCount.append(1)
                 outingStackFlag.append(False)
             print(outingStackCount, outingStackFlag)
             for i in range(0, len(Alarmlist[selectedPainNumber])):
                 if(Alarmlist[selectedPainNumber][i] >= currentOutingStart and Alarmlist[selectedPainNumber][i] <= currentOutingEnd):
                     outingStackFlag[i] = True
                 else:
                     outingStackFlag[i] = False
             cnt = 0
             for i in range(0, len(Alarmlist[selectedPainNumber])):
                 if(outingStackFlag[i]):
                     cnt = cnt + 1
                     outingStackCount[i] = 0
                     print(outingStackCount)
                 else:
                     outingStackCount[i] = outingStackCount[i] + cnt
                     cnt = 0
                     print(outingStackCount)
                     #outingFlag=True
             outingStackCount.reverse()
             print(outingStackCount)
         else:
             for i in range(0, len(Alarmlist[selectedPainNumber])):
                 outingStackCount.append(1)
             minimumOut = None
             selectedOut = None
                
                     
             
        ##############################################################################################

         print("[SYSYEM] Selected Pain & Time : ", selectedPain, minimumTime) #Log
         
         if(isOuting):
             print("[SYSTEM] Selected Outing Schedule : ", selectedOut,currentOutingStart,currentOutingEnd, outingStackCount) #Log
         else:
             print("[SYSTEM] No Outing Schedule")
             
         if(isObsoleteTime(minimumTime)):
             print("[SYSTEM] Current Time will be deleted. this time is not up-to-date")
             Alarmlist[selectedPainNumber].remove(minimumTime)
             #refresh the database
             result2 = fcm.patch("/"+patient_id+"/DOSE",{ selectedPain : Alarmlist[selectedPainNumber]})
             continue
         if(isOuting):
             if(isObsoleteTime(currentOutingEnd)):
                 print("[SYSTEM] Current Outing Time will be deleted. this time is not up-to-date")
                 Outinglist.remove(Outinglist[0])
                 result2 = fcm.patch("/"+patient_id+"/",{ "OUTING" : Outinglist})

         main_count = len(Alarmlist[selectedPainNumber]);

         while main_count>0: # Main Algorithm

             #--------------------------- time check mode --------------------------------------------
             if(mode): #time check mode
                print("#########################Time Check mode#########################")
                # to check the new data in database
                if(UPDATEorNOT(fcm,patient_id,selectedPain,selectedOut,isOuting)):
                    print("[SYSTEM] Need to Update!, Data will be updated")
                    break
                nextAlarmTime = Alarmlist[selectedPainNumber][0]
                print("[SYSTEM] Current Alarm Time : ",nextAlarmTime)
                if(isEqualtime(nextAlarmTime)): # when the time is to provide a medicine/ in actual use, remove "or True"
                    for j in range(0,outingStackCount[i]):
                        sm.step()
                        time.sleep(2)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() == True:
                        continue
                    mode = False
                    Alarmlist[selectedPainNumber].remove(nextAlarmTime)
                    #refresh the database
                    result2 = fcm.patch("/"+patient_id+"/DOSE",{ selectedPain : Alarmlist[selectedPainNumber]})
                    #fcm.delete("/DOSE/m1","0")
                    time.sleep(5)
                else:
                    pass
             #-------------------------------- distance check mode --------------------------------------
             else:
                print("#########################Distance Check Mode#################################")
                while True:
                    #if(outingFlag):
                    #    print("[SYSTEM] Remove Outing Schedule")
                    #    result2 = fcm.patch("/"+patient_id+"/OUTING",{selectedOut : None})
                    #
                    if(us.getDistance()>threshold): # in actual use, remove "and False"
                    #if(False): # in actual use, remove "and False"
                        result = push_service.notify_single_device(registration_id=getToken(fcm,patient_id),message_body="약을 복용하였습니다.")
                        if(getGuardianToken(fcm,patient_id)==None or getGuardianToken(fcm,patient_id)=="0"):
                            pass
                        else:
                            result = push_service.notify_single_device(registration_id=getGuardianToken(fcm,patient_id),message_body="약을 복용하였습니다.")
                        print("[SYSTEM] taking Alarm is generated in andrioid Device")
                        history = fcm.get("/"+patient_id+"/HISTORY/"+selectedPain,None)
                        if history == None or history == "0":
                            history = []
                        history.append(nextAlarmTime+"#1#"+selectedPain)
                        result = fcm.patch("/"+patient_id,{"/HISTORY" : history})
                        time.sleep(5)
                        mode = True
                        main_count = main_count - 1
                        break
                        #add to delete from database
                    else:
                        if(AlarmCount == 3):
                            if(isExceedtime(nextAlarmTime,2)): # if the medicine is not brought for 5 mintues
                                result = push_service.notify_single_device(registration_id=getToken(fcm,patient_id),message_body="[5분 경과] 약을 복용하지 않았습니다.")
                                if(getGuardianToken(fcm,patient_id)==None or getGuardianToken(fcm,patient_id)=="0"):
                                    pass
                                else:
                                    result = push_service.notify_single_device(registration_id=getGuardianToken(fcm,patient_id),message_body="[5분 경과] 약을 복용하지 않았습니다.")
                                print("[SYSTEM] 1 not taking Alarm is generated in android Device")
                                AlarmCount -= 1
                                time.sleep(5)
                            else:
                                print("[SYSTEM] Waiting... Not Taking Phase Exceedtime Minute : 5")
                                time.sleep(3)
                        elif(AlarmCount == 2) :
                            if(isExceedtime(nextAlarmTime,3)):
                                result = push_service.notify_single_device(registration_id=getToken(fcm,patient_id),message_body="[10분 경과] 약을 복용하지 않았습니다.")
                                if(getGuardianToken(fcm,patient_id)==None or getGuardianToken(fcm,patient_id)=="0"):
                                    pass
                                else:
                                    result = push_service.notify_single_device(registration_id=getGuardianToken(fcm,patient_id),message_body="[10분 경과] 약을 복용하지 않았습니다.")
                                print("[SYSTEM] 2 not taking Alarm is generated in android Device")
                                AlarmCount -= 1
                                time.sleep(5)
                            else:
                                print("[SYSTEM] Waiting... Not Taking Phase Exceedtime Minute : 10")
                                time.sleep(3)
                        elif(AlarmCount == 1) :
                            if(isExceedtime(nextAlarmTime,4)):
                                result = push_service.notify_single_device(registration_id=getToken(fcm,patient_id),message_body="[15분 경과] 약을 복용하지 않았습니다.")
                                if(getGuardianToken(fcm,patient_id)==None or getGuardianToken(fcm,patient_id)=="0"):
                                    pass
                                else:
                                    result = push_service.notify_single_device(registration_id=getGuardainToken(fcm),message_body="[15분 경과] 약을 복용하지 않았습니다.")
                                print("[SYSTEM] 3 not taking Alarm is generated in android Device")
                                AlarmCount -= 1
                                time.sleep(5)
                            else:
                                print("[SYSTEM] Waiting... Not Taking Phase Exceedtime Minute : 15")
                                time.sleep(3)
                        else:
                            if(isExceedtime(nextAlarmTime,4)):
                                result = push_service.notify_single_device(registration_id=getToken(fcm,patient_id),message_body="미 복용으로 기재합니다.")
                                if(getGuardianToken(fcm,patient_id)==None or getGuardianToken(fcm,patient_id)=="0"):
                                    pass
                                else:
                                    result = push_service.notify_single_device(registration_id=getGuardianToken(fcm,patient_id),message_body="미 복용으로 기재합니다.")
                                print("[SYSTEM] really not taking Alarm is generated in android Device")
                                history = fcm.get("/"+patient_id+"/HISTORY",None)
                                if history == None or history == "0":
                                    history = []
                                history.append(nextAlarmTime+"#0#"+selectedPain)
                                result = fcm.patch("/"+patient_id,{"/HISTORY" : history})
                                AlarmCount = 3
                                mode = True
                                main_count = main_count - 1
                                time.sleep(5)
                                break
                

                    
        
        
    
    ###push service###
    #result = push_service.notify_single_device(registration_id=getToken(fcm,patient_id),message_body="Hello2",data_message=data_message)
    
    ###database patch###
    #result2 = firebase.patch("/OUTING",{"o2" : ["s#2018#08#22#09#00", "e#2018#08#22#18#00"]})
    
    
