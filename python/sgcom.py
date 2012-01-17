import serial, time
import socket
import argparse
from msvcrt import kbhit, getch

# pause program (for sec or msec)
class wait(object):
    def __init__(self, amt, unit):
        if unit == 'ms':
            time.sleep(float(amt/1000.0))
        else:
            time.sleep(float(amt))

# read a formatted message from SG
def get_msg(comobj):
    while (1):
        s = ''
        c = comobj.read()
        if c == '~':
            s += c
            while (c != '`'):
                c = comobj.read()
                s += c
            break
    return s

# send a formatted message to SG
def send(msg, comobj, se='no_set_end'):
    while (1):
        comobj.flushInput()
        for i in range(len(msg)):
            comobj.write(msg[i])
            wait(50,'ms')
        cpy = msg[0] + '!' + msg[2:]
        ack = get_msg(comobj)
        if (ack != cpy):
            continue
        break
    if (se == 'set_end'):
        set_end(comobj)

def set_end(comobj):
    while (1):
        send('~#SetEnd`', comobj)
        ack = get_msg(comobj)
        if (ack != '~!ParameterUpdate`'):
            continue
        else:
            break
        
# parse msg into pose format in meters
def parse_pose(msg):
    splitmsg = msg.split('|')
    for i in range(len(splitmsg)):
        if splitmsg[i][0] == '+':
            splitmsg[i] = splitmsg[i][1:]
    parsedpose = str(float(splitmsg[2])/100.0) + ' ' + str(float(splitmsg[3])/100.0)
    return parsedpose

def main():
    try:
        # parse command line arguments for SG settings
        parser = argparse.ArgumentParser(description='Initialize SG settings.')
        parser.add_argument('nolm', type=int, help='number of landmarks')
        parser.add_argument('refid', type=int, help='reference landmark ID')
        ui = parser.parse_args()
        
        # begin serial communication with SG
        sg = serial.Serial('COM8', 115200, timeout=2)
        
        # set parameters for SG localization system
        send('~#CalcStop`', sg)
        send('~#IDNum|' + str(ui.nolm) + '`', sg, 'set_end')
        send('~#RefID|' + str(ui.refid) + '`', sg, 'set_end')
        send('~#HeightFix|No`', sg, 'set_end')
        send('~#MarkType|HLD1S`', sg, 'set_end')
        send('~#MarkMode|Map`', sg, 'set_end')
        send('~#BaudRate|115200`', sg, 'set_end')
        send('~#MapMode|Start`', sg)
        # begin map-building mode
        print '------ MAP-BUILDING MODE ------\n'
        sg.flushInput()
        while (1):
            msg = get_msg(sg)
            if (msg):
                print msg
            if msg == '~!ParameterUpdate`':
                break
        # once all markers have been found, begin online mode
        print '------ ONLINE MODE ------\n'
        # create a text file for poses
        filename = 'sgposes.txt'
        FILE = open(filename, 'w')
        # data is initially not recorded to file
        rec = 0
        while (1):
            # if a key is hit
            if kbhit():
                # catch the key
                key = ord(getch())
                # if key is 'r', toggle recording of data to file
                if key == 114:
                    rec = rec ^ 1
            # send data to be recorded only if the toggle setting is 1
            msg = get_msg(sg)
            if (msg):
                print msg
            if rec == 1:
                if msg[1:3] == '^I':
                    pose = parse_pose(msg)
                    FILE.write(pose+'\n')
                else:
                    continue                
    finally:
        # close recordings file
        FILE.close()
        # close serial communication with SG
        sg.close()

if __name__ == "__main__":
    main()
