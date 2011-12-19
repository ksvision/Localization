import socket
from adolphus.geometry import Pose, Point, Rotation

class Marker(object):
    """\
    Marker class
    """
    def __init__(self, ID=None, pose=None, error=None):
        """\
        Constructor
        """
        self.ID = ID
        self.pose = pose
        self.error = error

    @property
    def get_ID(self):
        """\
        Return the marker ID
        """
        return self.ID

    @property
    def get_pose(self):
        """\
        Return the marker's pose
        """
        return self.pose

    @property
    def get_error(self):
        """\
        Return the marker's error
        """
        return self.error

    def update_ID(self, ID):
        """\
        Update the marker's ID
        """
        self.ID = ID

    def update_pose(self, pose):
        """\
        Update the marker's pose
        """
        self.pose = pose

    def update_error(self, error):
        """\
        Update the marker's error
        """
        self.error = error

    

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
        weight = float(pose[len(pose)-1].split('|').pop())
        pose[len(pose)-1] = pose[len(pose)-1].split('|')[0]
        for i in range(len(pose)):
            pose[i] = float(pose[i])
        frame_dict.update({int(pair.split(':')[0]): \
                           {'pose':pose, 'weight':weight}})
    for item in frame_dict:
        trans_vec = [frame_dict[item]['pose'][0],frame_dict[item]['pose'][1],\
                     frame_dict[item]['pose'][2]]
        rot_mat = [[] for x in range(3)]
        for i in range(3):
            rot_mat[i] = [frame_dict[item]['pose'][3*(i+1)], \
                          frame_dict[item]['pose'][3*(i+1)+1], \
                          frame_dict[item]['pose'][3*(i+1)+2]]
        t = Point(trans_vec)
        r = Rotation.from_rotation_matrix(rot_mat)
        pose = Pose(t,r)
        frame_dict[item]['pose'] = pose
    return frame_dict

def main():
    # set up network socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost',5678))
    sock.listen(20)

    # accept incoming connection requests
    channel, details = sock.accept()
    channel.settimeout(20)

    try:
        for i in range(7):
            frame_dict = {}
            hstring = channel.recv(65536)
            frame_dict = parse_from_halcon(hstring)
            print frame_dict
    finally:
        channel.close()
        sock.close()

if __name__ == "__main__":
    main()
