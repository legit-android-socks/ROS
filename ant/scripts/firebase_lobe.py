#!/usr/bin/env python

import sys
import sched
from multiprocessing import Process
import calendar
import time
import xml.etree.ElementTree as ET
import json
import urllib2
import pyrebase
import rospy
from std_msgs.msg import String

# Exception class definition
class TokenRequestExrror(Exception):
    """Could not retreive token exception."""
    pass
class InvalidTokenException(Exception):
    """Received invalid authentication token exception."""
    pass
class EmptyQueueException(Exception):
    """The user queue is empty."""
    pass
class PermissionDeniedException(Exception):
    """Permission denied"""
    pass
class NoUIDException(Exception):
    """NoUIDException"""
    pass
class UserOfflineException(Exception):
    """User is offline exception"""
    pass

# Parse .xml file
TREE = ET.parse('firebase_config.xml')
ROOT = TREE.getroot()

OID = ROOT[0][0].text
RID = ROOT[0][1].text
ACCESSKEY = ROOT[0][2].text

#EMAIL = ROOT[2][0].text
#PASSWORD = ROOT[2][1].text

FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDC23ZxJ7YjwVfM0BQ2o6zAtWinFrxCrcI",
    "authDomain": "brainyant-2e30d.firebaseapp.com",
    "databaseURL": "https://brainyant-2e30d.firebaseio.com/",
    "storageBucket": "gs://brainyant-2e30d.appspot.com/",
    #"serviceAccount": "./brainyant-a3fa8afc4ec3.json"
}

FIREBASE = pyrebase.initialize_app(FIREBASE_CONFIG)
AUTH = FIREBASE.auth()
DB = FIREBASE.database()

GET_TOKEN_DATA = {
    'ownerID': OID,
    'robotID': RID,
    'accessKey': ACCESSKEY
}

try:
    REQUEST = urllib2.Request('https://robots.brainyant.com:8080/robotLogin')
    REQUEST.add_header('Content-Type', 'application/json')
    RESPONSE = urllib2.urlopen(REQUEST, json.dumps(GET_TOKEN_DATA))
    TOKEN = json.loads(RESPONSE.read())['customToken']
    if TOKEN is None:
        raise TokenRequestExrror
except TokenRequestExrror:
    print('Error! Could not retreive signin token from server. Server might be down.')

try:
    USERID = None
    USER = AUTH.sign_in_with_custom_token(TOKEN)
    REFRESH = AUTH.refresh(USER['refreshToken'])
    USERID = REFRESH['userId']
    IDTOKEN = REFRESH['idToken']
    if USERID is None:
        raise InvalidTokenException
except InvalidTokenException:
    print('Can not sign in to firebase. Invalid token.')

# ROS publisher
MOTION_PUB = rospy.Publisher('motion', String, queue_size=5)

def motion_topic_streamer(userid):
    """Listen for changes in firebase ControlData"""
    rospy.init_node('firebase_lobe', anonymous=True)
    rate = rospy.Rate(10) #10Hz
    motion_stream = DB.child('users').child(OID).child('robots').child(RID).child('users').child(userid).child("ControlData").order_by_key().stream(motion_stream_handler, IDTOKEN, None)
    rate.sleep()
    motion_stream.close()

def motion_stream_handler(message):
    """Stream handler. Publish data to topic."""
    rospy.loginfo(message["data"])
    MOTION_PUB.publish(str(message["data"]))

def user_queue_streamer():
    """Listen for changes in firebase user queue"""
    queue_stream = DB.child('users').child(OID).child('robots').child(RID).child('queue').stream(queue_stream_handler, None)
    queue_stream.close()

def queue_stream_handler(message):
    """Queue stream handler. Get first user in queue"""
    print("[QUEUE_CHANGES]: {}".format(message["data"]))

# DB set and get functions
def get_control_data(userid):
    """Return ControlData values from firebase"""
    control_data = DB.child('users').child(OID).child('robots').child(RID).child('users').child(userid).child("ControlData").order_by_key().get(token=IDTOKEN)
    return control_data

def start_reset_online_every_n_secs(n):
    """Start a recurring function that resets the robot as online every n seconds"""
    s = sched.scheduler(time.time, time.sleep)
    s.enter(n, 1, set_online, (s, n))
    s.run()

def set_online(s, n):
    """Set field value of isOnline to True every n seconds"""
    #global COUNTER
    #COUNTER += 1
    DB.child('users').child(OID).child('robots').child(RID).child('profile').update({'isOnline': True}, token=IDTOKEN)
    s.enter(n, 1, set_online, (s,n))

def set_offline():
    """Set field value of isOnline to False"""
    DB.child('users').child(OID).child('robots').child(RID).child('profile').update({'isOnline': False}, token=IDTOKEN)

def is_online():
    """Return field value of isOnline"""
    return DB.child('users').child(OID).child('robots').child(RID).child('profile').child('isOnline').get(token=IDTOKEN).val()

def get_name():
    """Return robot name field value"""
    name = DB.child('users').child(OID).child('robots').child(RID).child('profile').child('name').get(token=IDTOKEN).val()
    return name

def get_description():
    """Return robot description field value"""
    description = DB.child('users').child(OID).child('robots').child(RID).child('profile').child('description').get(token=IDTOKEN).val()
    return description

def set_robotOn(entry):
    """Set robotOn flag to True"""
    DB.child('users').child(OID).child('robots').child(RID).child('queue').child(entry).update({"robotOn": True}, token=IDTOKEN)

def set_startControl(entry):
    """Record timestamp when control session starts"""
    timestamp = calendar.timegm(time.gmtime())
    DB.child('users').child(OID).child('robots').child(RID).child('queue').child(entry).update({"startControl": timestamp}, token=IDTOKEN)

def get_first_user():
    """Get first user information"""
    aux = DB.child('users').child(OID).child('robots').child(RID).child('queue').order_by_key().limit_to_first(1).get(token=IDTOKEN)
    try:
        for i in aux.each():
            uid = i.val()['userId']
            useron = i.val()['userOn']
            user_entry = i.key()
    except TypeError:
        #print("[empty queue"))
        return (None, None, None)
    return (uid, useron, user_entry)

def get_useron():
    """Get first user status"""
    aux = DB.child('users').child(OID).child('robots').child(RID).child('queue').order_by_key().limit_to_first(1).get(token=IDTOKEN)
    for i in aux.each():
        useron = i.val()['userOn']
    return useron

if __name__ == '__main__':

#read xml
#ask for token
#get custom token
#sign in with custom token

#set robot online (recurring)
    #global COUNTER 
    #COUNTER = 0
    p1 = Process(target = start_reset_online_every_n_secs, args = [1])
    p1.start()
#robot name & description
    print(get_name())
    print(get_description())
#wait for users
    # Get UID
    print("Waiting for user ...")
    USER_ENTRY = None
    UID = None
    while UID is None:
        try:
            (UID, USERON, USER_ENTRY) = get_first_user()
            if UID is None:
                raise EmptyQueueException
        except EmptyQueueException:
            print("[empty queue]")
    print("Found user --> UID: {}".format(UID))
#get userOn
    while not USERON:
        try:
            USERON = get_useron()
            if not USERON:
                raise UserOfflineException
        except UserOfflineException:
            print('[user is offline]')
    print('User is online')

    print('Robot is on. Starting control session ...')
    set_robotOn(USER_ENTRY)
    set_startControl(USER_ENTRY)
    
    print('Waiting for commands ...')
#listen for commands
    CONTROL_DATA = get_control_data(OID)
    print(CONTROL_DATA.key())
    for item in CONTROL_DATA.each():
        print("{}: {}".format(item.key(), item.val()))

    try:
        while not rospy.is_shutdown():
            motion_topic_streamer(OID)
    except rospy.ROSInterruptException:
        print("ERROR: ROS Interrupted")
    except KeyboardInterrupt:
        print("ERROR: Keyboard Interrupt detected!")

#cleanup
p1.join()
