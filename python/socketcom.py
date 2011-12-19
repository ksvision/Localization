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
    global cf_markers
    for pair in hstring.split(';'):
        ID = int(pair.split(':')[0])
        pose = pair.split(':')[1].split(',')
        error = float(pose[len(pose)-1].split('|').pop())
        pose[len(pose)-1] = pose[len(pose)-1].split('|')[0]
        for i in range(len(pose)):
            pose[i] = float(pose[i])
        trans_vec = [pose[0], pose[1], pose[2]]
        rot_mat = [[] for x in range(3)]
        for i in range(3):
            rot_mat[i] = [pose[3*(i+1)], pose[3*(i+1)+1], pose[3*(i+1)+2]]
        t = Point(trans_vec)
        r = Rotation.from_rotation_matrix(rot_mat)
        pose = Pose(t,r)
        cf_markers.append(Marker(ID,pose,error))

def main():
    global cf_markers
    
    # set up network socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost',5678))
    sock.listen(20)

    # accept incoming connection requests
    channel, details = sock.accept()
    channel.settimeout(20)

    try:
        for i in range(7):
            cf_markers = []
            hstring = channel.recv(65536)
            parse_from_halcon(hstring)
    finally:
        channel.close()
        sock.close()

if __name__ == "__main__":
    main()
