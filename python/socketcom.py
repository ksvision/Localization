import socket
from adolphus.geometry import Pose, Point, Rotation
from hypergraph.core import Edge, Graph

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
    frame_markers = {}
    for pair in hstring.split(';'):
        pose = pair.split(':')[1].split(',')
        weight = float(pose[len(pose)-1].split('|').pop())
        pose[len(pose)-1] = pose[len(pose)-1].split('|')[0]
        for i in range(len(pose)):
            pose[i] = float(pose[i])
        frame_markers.update({int(pair.split(':')[0]): \
                           {'pose':pose, 'weight':weight}})
    for marker in frame_markers:
        trans_vec = [frame_markers[marker]['pose'][0],frame_markers[marker]['pose'][1],\
                     frame_markers[marker]['pose'][2]]
        rot_mat = [[] for x in range(3)]
        for i in range(3):
            rot_mat[i] = [frame_markers[marker]['pose'][3*(i+1)], \
                          frame_markers[marker]['pose'][3*(i+1)+1], \
                          frame_markers[marker]['pose'][3*(i+1)+2]]
        t = Point(trans_vec)
        r = Rotation.from_rotation_matrix(rot_mat)
        pose = Pose(t,r)
        frame_markers[marker]['pose'] = pose
    return frame_markers

def main():
    # set up network socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost',5678))
    sock.listen(20)

    # accept incoming connection requests
    channel, details = sock.accept()
    channel.settimeout(20)

    try:
        # initialize empty graph
        graph = Graph()
        
        for i in range(7):
            # parse the incoming information from halcon
            frame_markers = {}
            hstring = channel.recv(65536)
            frame_markers = parse_from_halcon(hstring)

            # find the relative poses of the current frame markers w.r.t. one another
            local_relposes = {}
            for marker in frame_markers:
                marker_a = frame_markers[marker]
                for other in frame_markers:
                    try:
                        assert other != marker
                        assert (marker, other) not in local_relposes
                    except AssertionError:
                        continue
                    marker_b = frame_markers[other]
                    pose_ab = marker_a['pose'] - marker_b['pose']
                    pose_ba = -pose_ab
                    weight_ab = marker_a['weight'] + marker_b['weight']
                    weight_ba = weight_ab
                    local_relposes[(marker, other)] = {'pose': pose_ab, 'weight': weight_ab}
                    local_relposes[(other, marker)] = {'pose': pose_ba, 'weight': weight_ba}
            print local_relposes

            
        
    finally:
        channel.close()
        sock.close()

if __name__ == "__main__":
    main()
