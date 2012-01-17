import socket
import argparse
from msvcrt import kbhit, getch

from adolphus.geometry import Pose, Point, Rotation
from hypergraph.core import Edge, Graph
from hypergraph.path import dijkstra
from hypergraph.connectivity import connected
    
# parse incoming string data from halcon into python dictionary format
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
    try:
        for pair in hstring.split(';'):
            pose = pair.split(':')[1].split(',')
            weight = float(pose[len(pose)-1].split('|').pop())
            pose[len(pose)-1] = pose[len(pose)-1].split('|')[0]
            for i in range(len(pose)):
                pose[i] = float(pose[i])
            frame_markers.update({int(pair.split(':')[0]): \
                               {'pose':pose, 'weight':weight}})
        for marker in frame_markers:
            trans_vec = [frame_markers[marker]['pose'][3],frame_markers[marker]['pose'][7],\
                         frame_markers[marker]['pose'][11]]
            rot_mat = [[] for x in range(3)]
            for i in range(3):
                rot_mat[i] = [frame_markers[marker]['pose'][4*i],
                              frame_markers[marker]['pose'][4*i+1],
                              frame_markers[marker]['pose'][4*i+2]]
            t = Point(trans_vec)
            r = Rotation.from_rotation_matrix(rot_mat)
            pose = Pose(t,r)
            frame_markers[marker]['pose'] = pose
    except:
        pass
    return frame_markers

def main():
    # parse command line arguments for reference marker id
    parser = argparse.ArgumentParser(description='Choose reference marker.')
    parser.add_argument('ref_id', type=int, help='ID of the reference marker')
    ui = parser.parse_args()
    # set up network socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost',5678))
    sock.listen(20)
    # accept incoming connection requests
    channel, details = sock.accept()
    #channel.settimeout(20)
    # create a text file for poses
    filename = 'ourposes.txt'
    FILE = open(filename, 'w')
    try:
        # acceptable forms of 'yes' and 'no' for quiting prompts
        end = ''
        yes_set = set(['y', 'Y', 'yes', 'Yes', 'YES'])
        no_set = set(['n', 'N', 'no', 'No', 'NO'])

        '''-------------------'''
        ''' MAP-BUILDING MODE '''
        '''-------------------'''
        print '*************** MAP-BUILDING MODE ***************\n'
        # initialize empty graph and the global relative poses (GRPs)
        graph = Graph()
        global_relposes = {}
        while(True):
            # if a key is pressed
            if kbhit():
                # catch the key
                key = ord(getch())
                # calculate the current shortest path to the reference using dijkstra's algorithm
                curr_prev = dijkstra(graph, ui.ref_id)
                # find the unconnected vertices (markers)
                uc_verts = [um for um in curr_prev if um != ui.ref_id and curr_prev[um] == None]
                # if 's' is pressed on the keyboard, update user on all current registered and unconnected markers
                if key == 115:
                    print len(graph.vertices), 'Registered marker(s):', list(graph.vertices)
                    print len(uc_verts), 'Unconnected marker(s):', uc_verts, '\n'
                # if 'q' is pressed on the keyboard, notify user of all registered markers and also if...
                # ... (i) reference marker is not registered or (ii) not all registered markers have a ...
                # ... route back to the reference marker
                # give user the option to exit
                elif key == 113:
                    # if the reference marker is not registered as a vertex in the graph, tell user they ...
                    # ... cannot go into online mode without it
                    # give them option to end the program
                    if ui.ref_id not in graph.vertices:
                        print 'The reference marker has not been registered.  You cannot continue to'
                        print 'online mode without it.'
                        end = raw_input('Are you sure you want to end the program? (y/n): ')
                        if end in yes_set:
                            return
                        else:
                            pass
                    else:
                        try:
                            # show the number of registered markers
                            print '- There are currently', len(graph.vertices),'registered markers:', list(graph.vertices)
                            # warn user of any disconnections in the graph
                            if not connected(graph):
                                print '- The following have no route to the reference marker:', uc_verts
                            else:
                                print '- All markers have a route to the reference marker.'
                                pass
                        finally:
                            # ask the user if they want to end map-building mode despite the warning
                            while(end not in (yes_set | no_set)):
                                end = raw_input('End map-building mode? (y/n): ')
                            # end or continue map-building mode depending on user's choice
                            if end in yes_set:
                                break
                            else:
                                pass
            # parse the incoming data from halcon
            frame_markers = {}
            hstring = channel.recv(65536)
            if not hstring or hstring == 'no markers found':
                pass
            # if socket is closed from the other end (halcon), stop the program
            # elif hstring == 'connection closed':
                # print '---- CONNECTION CLOSED (HALCON) ----'
                # return
            else:
                frame_markers = parse_from_halcon(hstring)

            # update the set of vertices in the graph with the local markers
            graph.vertices.update(frame_markers)
            # find the local relative poses (LRPs) of the markers w.r.t. one another and use them ...
            # ... to update the GRP and the graph
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
                    # if the edge joining the two markers does not exist in neither the GRPs nor the graph, ...
                    # ... add it to both from the LRPs
                    if (marker, other) not in global_relposes:
                        global_relposes[(marker, other)] = local_relposes[(marker, other)]
                        global_relposes[(other, marker)] = local_relposes[(other, marker)]
                        graph.add_edge(Edge((marker, other)), local_relposes[(marker, other)]['weight'])
                    # however, if it already exists and the weight of the new one is less than the existing one, ...
                    # ... replace the existing ones in the GRPs and graph with the new one
                    else:
                        if weight_ab < global_relposes[(marker, other)]['weight']:
                            global_relposes[(marker, other)] = local_relposes[(marker, other)]
                            global_relposes[(other, marker)] = local_relposes[(other, marker)]
                            graph.weights[Edge((marker, other))] = weight_ab
            # send message back to halcon telling it python prog. is done processing frame data and ready for more
            #channel.send('d')
        # write the graph information to file
        FILE.write('------ GRAPH ------\n\n')
        FILE.write(str(graph)+'\n\n')
        # obtain the "previous array" of the shortest path as determined by dijkstra's algorithm
        prev = dijkstra(graph, ui.ref_id)
        # write title of section (marker poses) to file
        FILE.write('------ MARKER POSES ------\n\n')
        # find the global pose (and its associated aggregate weight) of each marker in the map w.r.t. the reference marker
        gmarkposes = {}
        for marker in prev:
            pose_comp = Pose()
            agg_weight = 0.0
            curr_i = marker
            prev_i = prev[curr_i]
            # skip markers that are disconnected from the reference
            if not prev_i and curr_i != ui.ref_id:
                continue
            # loop until reference is reached
            while prev_i:
                edge_i = (curr_i, prev_i)
                pose_comp += global_relposes[edge_i]['pose']
                agg_weight += global_relposes[edge_i]['weight']
                curr_i = prev_i
                prev_i = prev[curr_i]
            # store the global pose and weight of the marker
            gmarkposes[marker] = {'pose': pose_comp, 'weight': agg_weight}
            # write the global pose to the file
            FILE.write(str(marker)+': '+str(gmarkposes[marker])+'\n\n')
        FILE.write('------------------------------------------------------\n\n')
        

        '''-------------'''
        ''' ONLINE MODE '''
        '''-------------'''
        print '\n\n*************** ONLINE MODE ***************\n'
        # write title of section (marker poses) to file
        FILE.write('------ ONLINE MODE ------\n\n')
        # data is initially not recorded to file
        rec = 0
        while(True):
            # if a key is pressed
            if kbhit():
                # catch the key
                key = ord(getch())
                # if 'q' is pressed on the keyboard, give user the option to exit
                if key == 113:
                    end = raw_input('Are you sure you want to end the program? (y/n): ')
                    if end in yes_set:
                        return
                    else:
                        pass
                # if key is 'r', toggle recording of data to file
                if key == 114:
                    rec = rec ^ 1
            # parse the incoming data from halcon
            frame_markers = {}
            hstring = channel.recv(65536)
            if not hstring or hstring == 'no markers found':
                pass
            # if socket is closed from the other end (halcon), stop the program
            # elif hstring == 'connection closed':
                # print '---- CONNECTION CLOSED (HALCON) ----'
                # return
            else:
                frame_markers = parse_from_halcon(hstring)
            # find the camera pose that yields the minimum aggregate weight of all markers in the frame
            bestmarker = None
            bestpose = None
            minweight = float('inf')
            for marker in frame_markers:
                if marker in gmarkposes:
                    marker_i = frame_markers[marker]
                    gcampose = -marker_i['pose'] + gmarkposes[marker]['pose']
                    gcamweight = marker_i['weight'] + gmarkposes[marker]['weight']
                    if gcamweight < minweight:
                        bestmarker = marker
                        bestpose = gcampose
                        minweight = gcamweight
                else:
                    pass
            print '----------------------------'
            print 'through marker: ', bestmarker
            print 'pose: ', bestpose
            print 'weight: ', minweight
            print '----------------------------'
            # if record toggle is on, record the poses to file
            if rec == 1:
                if (bestpose):
                    temp = str(bestpose.T).split(',')
                    bestpose_str = temp[0][1:] + ' ' + temp[1][1:]
                    FILE.write(bestpose_str+'\n')
            # send message back to halcon telling it python prog. is done processing frame data and ready for more
            #channel.send('d')
    finally:
        FILE.close()
        channel.close()
        sock.close()
        print '---- CONNECTION CLOSED (PYTHON) ----'

if __name__ == "__main__":
    main()
