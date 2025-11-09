import cv2
import cv2.aruco as aruco

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
marker_img = aruco.drawMarker(aruco_dict, 0, 200)
cv2.imwrite("marker_0.png", marker_img)
print("Saved marker_0.png")
