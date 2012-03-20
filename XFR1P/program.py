#!/bin/env python3

import serial

ser=serial.Serial('/dev/ttyUSB0',19200)
print(ser.portstr)

