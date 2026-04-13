"""Standalone script to test and calibrate the BallDetector."""

import cv2
from src.ball_detector import BallDetector


def main_test() -> None:
    """Run the video stream with ball detection overlaid for debugging."""
    # 1. Load camera and the new detector
    # Replace 0 with a video path (e.g., 'af742e30-7e71-4082-a980-94aa61225ed8.MP4')
    # if testing on your recording
    cap = cv2.VideoCapture(0)
    detector = BallDetector()

    print("Starting vision test... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video stream or cannot read from camera.")
            break

        # 2. Pass frame to detector
        ball_pos = detector.detect(frame)

        # Draw ball if found
        if ball_pos:
            cv2.circle(
                frame,
                (int(ball_pos.x), int(ball_pos.y)),
                10,
                (0, 255, 0),
                2
            )
            cv2.putText(
                frame,
                "BALL",
                (int(ball_pos.x) + 15, int(ball_pos.y)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        # 3. Show the original image
        cv2.imshow("Camera Original", frame)

        # Exit condition
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main_test()