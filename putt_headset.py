"""PuttVision AI — AR putting headset foundation for Raspberry Pi 5.

Combines a BNO055 9-DOF IMU (UART) with an ArduCam IMX708 camera to display
a live camera feed with an orientation-aware HUD overlay.
"""

# NOTE: This script uses synchronous execution despite the project preference
# for async/await. OpenCV's cv2.imshow() and cv2.waitKey() must run on the
# main thread and block the event loop, making asyncio counterproductive here.
# The tight capture-read-draw-display loop is inherently sequential — there is
# no I/O concurrency to exploit. If future features need async (e.g., network
# streaming), the camera/IMU reads can be moved to a thread executor.

import math
import time
from typing import Optional

import cv2
import numpy as np
import serial
import adafruit_bno055
from gpiozero import OutputDevice
from picamera2 import Picamera2

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RST_PIN: int = 18
UART_PORT: str = "/dev/ttyAMA0"
UART_BAUD: int = 115200

FRAME_WIDTH: int = 640
FRAME_HEIGHT: int = 480

# BGR colors for OpenCV
GREEN: tuple[int, int, int] = (0, 255, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)
RED: tuple[int, int, int] = (0, 0, 255)

CROSSHAIR_SIZE: int = 20
ROLL_LINE_LENGTH: int = 100

# ---------------------------------------------------------------------------
# IMU
# ---------------------------------------------------------------------------


def reset_imu(rst_pin: int) -> None:
    """Hardware-reset the BNO055 via its RST pin.

    Uses gpiozero.OutputDevice (not RPi.GPIO) because RPi.GPIO does not
    support the Raspberry Pi 5's RP1 GPIO controller.
    """
    rst = OutputDevice(rst_pin, initial_value=True)
    try:
        rst.off()           # pull RST low
        time.sleep(0.1)     # 100 ms reset pulse
        rst.on()            # release RST
        time.sleep(1.0)     # wait for BNO055 boot sequence
    finally:
        rst.close()         # release GPIO so it's not "busy" on next run


def init_imu() -> adafruit_bno055.BNO055_UART:
    """Reset the BNO055, open the UART, and return the sensor object."""
    reset_imu(RST_PIN)

    uart = serial.Serial(UART_PORT, UART_BAUD, timeout=1)
    sensor = adafruit_bno055.BNO055_UART(uart)

    print(f"BNO055 initialized — calibration: {sensor.calibration_status}")
    return sensor

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------


def init_camera() -> Picamera2:
    """Configure and start the ArduCam IMX708 via picamera2.

    Requires dtoverlay=imx708,cam0 and camera_auto_detect=0
    in /boot/firmware/config.txt.
    """
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (FRAME_WIDTH, FRAME_HEIGHT)},
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(2.0)  # allow auto-exposure to settle

    print("Camera started")
    return picam2

# ---------------------------------------------------------------------------
# IMU data reading
# ---------------------------------------------------------------------------


def read_imu_data(
    sensor: adafruit_bno055.BNO055_UART,
) -> tuple[
    Optional[tuple[float, float, float]],
    Optional[tuple[float, float, float]],
    Optional[tuple[int, int, int, int]],
]:
    """Safely read euler angles, acceleration, and calibration status.

    Returns (euler, acceleration, calibration).  Any element may be None if
    the sensor has not yet calibrated or if a communication error occurs.
    """
    try:
        euler = sensor.euler           # (heading, roll, pitch) or None
        accel = sensor.acceleration    # (x, y, z) or None
        calibration = sensor.calibration_status  # (sys, gyro, accel, mag)
        return euler, accel, calibration
    except (OSError, RuntimeError):
        return None, None, None

# ---------------------------------------------------------------------------
# HUD overlay
# ---------------------------------------------------------------------------


def draw_hud(
    frame: np.ndarray,
    euler: Optional[tuple[float, float, float]],
    calibration: Optional[tuple[int, int, int, int]],
    fps: float,
) -> np.ndarray:
    """Draw the heads-up display onto the camera frame (mutates in place)."""
    cx: int = FRAME_WIDTH // 2
    cy: int = FRAME_HEIGHT // 2

    # --- Center crosshair ---
    cv2.line(frame, (cx - CROSSHAIR_SIZE, cy), (cx + CROSSHAIR_SIZE, cy), GREEN, 2)
    cv2.line(frame, (cx, cy - CROSSHAIR_SIZE), (cx, cy + CROSSHAIR_SIZE), GREEN, 2)

    # --- Euler angles (top-left) ---
    if euler is not None and euler[0] is not None:
        heading, roll, pitch = euler
        cv2.putText(frame, f"Heading: {heading:6.1f} deg", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN, 2)
        cv2.putText(frame, f"Roll:    {roll:6.1f} deg", (10, 60),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN, 2)
        cv2.putText(frame, f"Pitch:   {pitch:6.1f} deg", (10, 90),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN, 2)
    else:
        cv2.putText(frame, "IMU: No Data", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

    # --- Calibration status ---
    if calibration is not None:
        sys_cal, gyro_cal, accel_cal, mag_cal = calibration
        cal_color = GREEN if all(v == 3 for v in calibration) else WHITE
        cv2.putText(
            frame,
            f"Cal S:{sys_cal} G:{gyro_cal} A:{accel_cal} M:{mag_cal}",
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, cal_color, 2,
        )

    # --- FPS counter (bottom-left) ---
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, FRAME_HEIGHT - 20),
                 cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN, 2)

    # --- Roll indicator line ---
    if euler is not None and euler[1] is not None:
        roll_rad: float = math.radians(euler[1])
        dx: int = int(ROLL_LINE_LENGTH * math.cos(roll_rad))
        dy: int = int(ROLL_LINE_LENGTH * math.sin(roll_rad))
        cv2.line(frame, (cx - dx, cy + dy), (cx + dx, cy - dy), RED, 2)

    return frame

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    """Initialize hardware, run the frame loop, and clean up on exit."""
    sensor = init_imu()
    picam2 = init_camera()

    prev_time: float = time.monotonic()
    fps: float = 0.0

    try:
        while True:
            frame: np.ndarray = picam2.capture_array()

            euler, _accel, calibration = read_imu_data(sensor)

            current_time: float = time.monotonic()
            dt: float = current_time - prev_time
            fps = 1.0 / dt if dt > 0 else 0.0
            prev_time = current_time

            frame = draw_hud(frame, euler, calibration, fps)

            cv2.imshow("PuttVision", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        pass
    finally:
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
