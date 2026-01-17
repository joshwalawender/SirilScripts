#!python3

## Import General Tools
import sys
import time
from pathlib import Path
import logging
import argparse
import traceback

from alpaca import camera

from PyQt5 import uic, QtWidgets, QtCore, QtGui


##-------------------------------------------------------------------------
## Create logger object
##-------------------------------------------------------------------------
log = logging.getLogger('MyLogger')
log.setLevel(logging.DEBUG)
## Set up console output
LogConsoleHandler = logging.StreamHandler()
LogConsoleHandler.setLevel(logging.DEBUG)
LogFormat = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
LogConsoleHandler.setFormatter(LogFormat)
log.addHandler(LogConsoleHandler)
## Set up file output
# LogFileName = None
# LogFileHandler = logging.FileHandler(LogFileName)
# LogFileHandler.setLevel(logging.DEBUG)
# LogFileHandler.setFormatter(LogFormat)
# log.addHandler(LogFileHandler)


##-------------------------------------------------------------------------
## Define Application MainWindow
##-------------------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, clargs, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        ui_file = Path(__file__).parent / 'AlpacaCamera.ui'
        uic.loadUi(f"{ui_file}", self)

    def setupUi(self):
        self.setWindowTitle("Alpaca Camera GUI")


##-------------------------------------------------------------------------
## Define main()
##-------------------------------------------------------------------------
def main(clargs):
    application = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow(clargs)
    main_window.setupUi()
    main_window.show()
    return application.exec()


##-------------------------------------------------------------------------
## if __name__ == '__main__':
##-------------------------------------------------------------------------
if __name__ == '__main__':
    ## Parse Command Line Arguments
    p = argparse.ArgumentParser(description='''
    ''')
    ## add flags
    p.add_argument("-v", "--verbose", dest="verbose",
        default=False, action="store_true",
        help="Be verbose! (default = False)")
    ## add options
    clargs = p.parse_args()

    try:
        main(clargs)
    except Exception as e:
        print(e)
        print(traceback.format_exc())
    print(f"Exiting GUI")





##-------------------------------------------------------------------------
## Test Script
##-------------------------------------------------------------------------
def test_script(temperature_threshold=0.2):

    if args.ip is None:
        args.ip = '192.168.4.235:80'
    s = camera.Camera(args.ip, 0)
    s.Connect()
    time.sleep(0.5)
    assert s.Name == 'Pegasus Astro SmartEye'

#     print(s.DeviceState)


#     if args.setpoint is not None:
#         s.CoolerOn = True
#         s.SetCCDTemperature = args.setpoint
#     print('Waiting for detector to reach set point temperature')
#     time.sleep(10)
#     ccd_temp = s.CCDTemperature
#     at_100_count = 0
#     at_temp_count = 0
#     while abs(ccd_temp - args.setpoint) > temperature_threshold:
#         cooling_power = s.CoolerPower
#         print(f"  Temperature = {ccd_temp:.2f} C, Power = {cooling_power:.1f} %")
#         time.sleep(10)
#         ccd_temp = s.CCDTemperature
#         if cooling_power > 99:
#             at_100_count += 1
#         if at_100_count > 6:
#             print('Cooler seems unable to reach setpoint')
#             break
#     print(f"Temperature = {ccd_temp:.2f} C, Power = {cooling_power:.1f} %")


    print('Disconnecting')
    s.CoolerOn = False
    ccd_temp = s.CCDTemperature
    for i in range(0,5):
        cooling_power = s.CoolerPower
        print(f"  Temperature = {ccd_temp:.2f} C, Power = {cooling_power:.1f} %")
        time.sleep(10)
        ccd_temp = s.CCDTemperature
    s.Connect = False
