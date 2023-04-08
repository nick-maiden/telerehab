import base64
import cv2
from django.shortcuts import render
import numpy as np
import plotly.graph_objs as go
import plotly.offline as opy
import plotly.graph_objs as go
from django.shortcuts import render
import plotly.graph_objs as go
import numpy as np
from datastore.datastore import data_store
import json

def frames_upload(request):
    # Testing phase, assume that the session is being written to for the first time (
    # we are not appending frames, just adding whatever frames received to the session
    # file and closing it).

    # Output request to server terminal for testing
    data = json.loads(request.body)
    print(data)

    user_id = data.get('user_id')       # Should be "1" for testing (note that this is a string)
    session_id = data.get('session_id') # Should be "2" for testing (again, this is a string)

    assert(user_id == "1")
    assert(session_id == "2")

    session_data = data.get('frames')   # Assuming this is a dictionary of frames, where
                                        # keys are frame number and values are a list of
                                        # 3D coordinates. Could also be a list of frames
                                        # if prefered

    data_store.set_session(session_data)
    data_store.write_session(session_id)


def visualise_coordinates(request):
    # Assume that we want session and user both with id "1"
    # These would actually be contained within the request
    session_id = "1"
    user_id = "1"
    users = data_store.get_users()
    user = users.get(user_id)
    
    if not user:
        # user with this id does not exist ...
        pass
    if not user['sessions'].get(session_id):
        # this session doesn't exist, or it does but this user wasn't part of it
        pass
    if not data_store.populate_session(session_id):
        # session file could not be located, ignore this case currently.
        # above check should prevent this ever being true
        pass

    session_frames = data_store.get_session()
    frames = []

    for session_frame in session_frames.values():
        keypoints3D_arrays = []
        for kp in session_frame:
            keypoints3D_arrays.append(np.array([kp.get('x', 0), kp.get('y', 0), kp.get('z', 0)]))

        keypoints2D_arrays = [(int(kp[0] * 100 + 300), int(kp[1] * 100 + 300)) for kp in keypoints3D_arrays]

        img = np.zeros((600, 600, 3), dtype=np.uint8)

        for kp in keypoints2D_arrays:
            cv2.circle(img, kp, 2, (0, 0, 255), -1)

        # define connections based on BlazePose Keypoints: Used in MediaPipe BlazePose
        connections = [
            (0, 4),
            (0, 1),
            (4, 5),
            (5, 6),
            (6, 8),
            (1, 2),
            (2, 3),
            (3, 7),
            (10, 9),
            (12, 11),
            (12, 14),
            (14, 16),
            (16, 22),
            (16, 20),
            (16, 18),
            (18, 20),
            (11, 13),
            (13, 15),
            (15, 21),
            (15, 19),
            (15, 17),
            (17, 19),
            (12, 24),
            (11, 23),
            (24, 23),
            (24, 26),
            (23, 25),
            (26, 28),
            (25, 27),
            (28, 32),
            (28, 30),
            (30, 32),
            (27, 29),
            (27, 31),
            (29, 31)
        ]

        for joint1, joint2 in connections:
            pt1 = keypoints2D_arrays[joint1]
            pt2 = keypoints2D_arrays[joint2]
            cv2.line(img, pt1, pt2, (255, 0, 0), 1)

        _, buffer = cv2.imencode('.png', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        frames.append(img_base64)

    frames = json.dumps(frames)
    return render(request, 'animation.html', {'frames': frames})