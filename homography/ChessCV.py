import cv2
import numpy as np
import sys

class CCV:
    def __init__(self, square_width, board_size, cam_height, cam_width, fps,
                 webcam=True, cam_number=0, input_video=None, write_video=True, output_video=None,
                 cam_mat='../camera_calibration/camera_matrix.csv', dist_coeff='../camera_calibration/dist_coeff.csv'):
        # read in camera matrix and distortion coefficients
        cam_mat_file = open(cam_mat, 'rb')
        dist_coeff_file = open(dist_coeff, 'rb')
        # read matrices from file
        self.K = np.loadtxt(cam_mat_file, delimiter=',')
        self.dist_coeffs = np.loadtxt(dist_coeff_file, delimiter=',')
        # close files
        cam_mat_file.close()
        dist_coeff_file.close()
        self.fps = fps

        self.square_width = square_width
        self.board_size = board_size
        self.corners_world = np.array([[square_width, square_width, 0],
                                       [square_width, board_size * square_width, 0],
                                       [board_size * square_width, square_width, 0],
                                       [board_size * square_width, board_size * square_width, 0]], dtype=np.float32)
        self.corners_ortho = np.array([[100, 100],
                                       [100 * board_size, 100],
                                       [100, 100 * board_size],
                                       [100 * board_size, 100 * board_size]], dtype=np.float32)
        self.outer_corners = None
        self.squares = np.chararray((board_size + 1, board_size + 1, 2), itemsize=2)
        self.gen_spaces()

        self.cam_height = cam_height
        self.cam_width = cam_width
        self.write_video = write_video
        if write_video:
            fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
            self.videoWriter = cv2.VideoWriter(output_video, fourcc=fourcc, fps=30.0,
                                          frameSize=(cam_width, cam_height))
        if webcam:
            self.video_capture = cv2.VideoCapture(cam_number)  # Open video capture object
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, cam_width)  # set cam width
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)  # set cam height
        else:
            self.video_capture = cv2.VideoCapture(input_video)  # Open video capture object

        self.bgr_image = None
        self.bgr_display = None
        self.next_frame()
        if not self.got_video:
            print("Cannot read video source")

    def next_frame(self):
        if self.bgr_display is not None:
            if self.write_video:
                self.videoWriter.write(self.bgr_display)

        self.got_video, self.bgr_image = self.video_capture.read()
        self.bgr_display = np.copy(self.bgr_image)

        if not self.got_video:
            return None
        else:
            gotHomography, H = self.find_board_homography()  # Returns homography from camera to world coordinates if chess board and aruco marker are detected
            if gotHomography:
                return H[0:3][:]
            else:
                return None

    def find_pose(self, pts):
        pose_found, rvec, tvec = cv2.solvePnP(objectPoints=self.corners_world, imagePoints=pts, cameraMatrix=self.K,
                                             distCoeffs=None)  # Finds r and t vectors for homography
        if pose_found:
            return True, rvec, tvec
        else:
            return False, None, None

    def find_board_homography(self):
        global outerCorners
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
        aruco_corners, ids, _ = cv2.aruco.detectMarkers(
            image=self.bgr_image,
            dictionary=aruco_dict
        )
        ret_val, corners = cv2.findChessboardCorners(image=self.bgr_image, patternSize=(self.board_size, self.board_size))

        if ret_val and ids is not None:
            corners = order_points(corners, aruco_corners[0])
            self.outer_corners = np.array(
                [[corners[0][0][0], corners[0][0][1]],  # Finds the outer corners of the findChessBoardCorners points
                 [corners[self.board_size - 1][0][0], corners[self.board_size - 1][0][1]],
                 [corners[self.board_size ** 2 - self.board_size][0][0], corners[self.board_size ** 2 - self.board_size][0][1]],
                 [corners[self.board_size ** 2 - 1][0][0], corners[self.board_size ** 2 - 1][0][1]]], dtype=np.float32)

            gotPose, rvec, tvec = self.find_pose(self.outer_corners)  # Find homography and draw
            if gotPose:
                R = cv2.Rodrigues(rvec)
                return True, np.block([[R[0], tvec], [0, 0, 0, 1]])
            else:
                return False, None
        else:
            return False, None

    # Generates a 2D array of board spaces A1-H8
    def gen_spaces(self):
        for i in range(self.board_size + 1):
            for j in range(self.board_size + 1):
                self.squares[i][j][0] = str(chr(65 + j)) + str(i + 1)

    def draw_spaces_and_origin(self, Mext):
        if self.bgr_display is not None:
            for i in range(self.board_size + 1):
                for j in range(self.board_size + 1):
                    pos = np.array([self.square_width / 2 + i * self.square_width,
                                    self.square_width / 2 + j * self.square_width, 0], dtype=np.float32)
                    p = self.K @ Mext @ (np.block([pos, 1]).T)
                    point = (int(p[0] / p[2]), int(p[1] / p[2]))
                    cv2.putText(self.bgr_display, text=str(self.squares[i][j][0].decode("utf-8")), org=point,
                                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                                fontScale=0.5, color=(0, 0, 255), thickness=2)
                    cv2.drawMarker(self.bgr_display, position=point, color=(0, 0, 255), markerType=cv2.MARKER_CROSS)
            if self.outer_corners is not None:
                found_pose, rvec, tvec = self.find_pose(self.outer_corners)
                if found_pose:
                    W = np.amax(self.corners_world, axis=0) - np.amin(self.corners_world, axis=0)
                    L = np.linalg.norm(W)
                    d = L / 5
                    p_axes = np.float32([[0, 0, 0], [d, 0, 0], [0, d, 0], [0, 0, d]])
                    p_img, J = cv2.projectPoints(objectPoints=p_axes, rvec=rvec, tvec=tvec, cameraMatrix=self.K, distCoeffs=None)
                    p_img = p_img.reshape(-1, 2)
                    cv2.line(self.bgr_display, tuple(np.int32(p_img[0])), tuple(np.int32(p_img[1])), (0, 0, 255), 2,
                             lineType=cv2.LINE_AA)
                    cv2.line(self.bgr_display, tuple(np.int32(p_img[0])), tuple(np.int32(p_img[2])), (0, 255, 0), 2,
                             lineType=cv2.LINE_AA)
                    cv2.line(self.bgr_display, tuple(np.int32(p_img[0])), tuple(np.int32(p_img[3])), (255, 0, 0), 2,
                             lineType=cv2.LINE_AA)

    def click(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.outer_corners is not None:
                H, _ = cv2.findHomography(self.outer_corners, self.corners_ortho)  # Finds orthophoto homography
                point = H @ [x, y, 1]  # Calculates position of mouse click point on orthophoto
                point[0] = point[0] / point[2]
                point[1] = point[1] / point[2]

                if point[0] < ((self.board_size + 1) * 100) and point[0] > 0 and point[1] < ((self.board_size + 1) * 100) and point[1] > 0:
                    param.append(str(self.squares[int(point[1] / 100)][int(point[0] / 100)][0].decode("utf-8")))
                else:
                    param.append("Not on Board")

def closest(lst, K):
    return lst[min(range(len(lst)), key=lambda i: abs(lst[i] - K))]

def order_points(corners, aruco_location):
    aruco_center = np.array([np.average(aruco_location[0, :, 0]), np.average(aruco_location[0, :, 1])])

    corners_reshape = corners.reshape((49, 2)) # reshape to 40x2 array
    corner_dist = [np.sqrt((corner[0] - aruco_center[0])**2 + (corner[1] - aruco_center[1])**2) for corner in corners_reshape]

    closest_val = closest([0, 6, 42, 48], np.argmin(corner_dist))
    if closest_val == 6:
        corners_reshape = corners.reshape((7, 7, 2))
        corners_reshape = np.rot90(corners_reshape, 1, axes=(0, 1))
    elif closest_val == 42:
        corners_reshape = corners.reshape((7, 7, 2))
        corners_reshape = np.rot90(corners_reshape, 3, axes=(0, 1))
    elif closest_val == 48:
        corners_reshape = corners.reshape((7, 7, 2))
        corners_reshape = np.rot90(corners_reshape, 2, axes=(0, 1))

    return corners_reshape.reshape((49, 1, 2))