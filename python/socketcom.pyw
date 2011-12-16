import socket
from adolphus.geometry import Pose, Point, Rotation

def parse_from_halcon(hstring):
    """\
    Convert tuple data in string format from HALCON into the camera ID and
    target pose.

    @param hstring: the string data from HALCON.
    @type hstring: C{str}
    @return: Camera ID and target pose.
    @rtype: C{str}, L{Pose}
    """
    frame_dict = {}
    for pair in hstring.split(';'):
        pose = pair.split(':')[1].split(',')
        for i in range(len(pose)):
            pose[i] = float(pose[i])
        frame_dict.update({int(pair.split(':')[0]):pose})
    for item in frame_dict:
        trans_vec = [frame_dict[item][0],frame_dict[item][1],\
                     frame_dict[item][2]]
        rot_mat = [[] for x in range(3)]
        for i in range(3):
            rot_mat[i] = [frame_dict[item][3*(i+1)],\
                          frame_dict[item][3*(i+1)+1],\
                          frame_dict[item][3*(i+1)+2]]
        t = Point(trans_vec)
        r = Rotation.from_rotation_matrix(rot_mat)
        pose = Pose(t,r)
        frame_dict[item] = pose
    return frame_dict
    

# set up network socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('localhost',5678))
sock.listen(20)

# accept incoming connection requests
channel, details = sock.accept()
channel.settimeout(20)

hstring = ''
try:
    for i in range(7):
        hstring = channel.recv(65536)
        frame_dict = {}
        frame_dict = parse_from_halcon(hstring)
        print frame_dict
finally:
    channel.close()
    sock.close()
