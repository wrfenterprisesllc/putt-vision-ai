# PuttVision AI

AR putting headset foundation running on Raspberry Pi 5 with a BNO055 9-DOF IMU and ArduCam IMX708 camera.

## Hardware

### Components

- Raspberry Pi 5
- Adafruit BNO055 9-DOF Absolute Orientation IMU
- ArduCam IMX708 Wide 120-degree (CSI camera)

### Wiring — BNO055 IMU (UART Mode)

| BNO055 Pin | Pi Pin  | Description         |
|------------|---------|---------------------|
| Vin        | Pin 1   | 3.3V Power          |
| GND        | Pin 6   | Ground              |
| SDA (TX)   | Pin 10  | RXD (UART receive)  |
| SCL (RX)   | Pin 8   | TXD (UART transmit) |
| PS1        | Pin 17  | 3.3V (UART mode)    |
| RST        | Pin 12  | GPIO 18 (reset)     |

### Camera

ArduCam IMX708 Wide 120-degree connected to the CSI connector (cam0).

### Boot Config

Add to `/boot/firmware/config.txt`:

```
camera_auto_detect=0
dtoverlay=imx708,cam0
```

Ensure UART is enabled:

```
enable_uart=1
dtparam=uart0=on
```

Disable the serial console via `sudo raspi-config` > Interface Options > Serial Port (say No to login shell, Yes to hardware enabled).

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python putt_headset.py
```

Press `q` to quit.

## HUD Elements

- **Euler angles** — heading, roll, pitch (top-left)
- **Calibration status** — sys, gyro, accel, mag from 0 to 3 (green when fully calibrated)
- **FPS counter** — bottom-left
- **Center crosshair** — green cross at screen center
- **Roll indicator** — red line through center that rotates with headset tilt
