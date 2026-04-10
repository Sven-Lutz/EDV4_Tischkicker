# calibrate_camera.py
import cv2
import numpy as np
import glob

CHECKERBOARD = (9, 6)
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((CHECKERBOARD[0]*CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)

objpoints = []
imgpoints = []

images = glob.glob("calibration/*.jpg")

for img_path in images:
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    if ret:
        corners = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
        objpoints.append(objp)
        imgpoints.append(corners)

ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

np.save("camera_matrix.npy", camera_matrix)
np.save("dist_coeffs.npy", dist_coeffs)