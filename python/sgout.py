import socket
import argparse
from msvcrt import kbhit, getch

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        HOST = 'localhost'
        PORT = 13441
        sock.connect((HOST, PORT))

        filename = 'poses.txt'
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
            sock.send(str(rec))
            print str(rec)
                    
            msg = sock.recv(65536)
            if msg != '':
                print msg
                if len(msg) >= 5 and msg[:5] == 'pose:':
                    FILE.write(msg[5:])
    finally:
        print 'done'
        FILE.close()
        sock.close()

if __name__ == "__main__":
    main()
