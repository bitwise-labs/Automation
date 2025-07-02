# TestExampleSS.py

from pyBitwiseAutomation import *
import sys

# create StepscopeDevice as global for shared use

_Stepscope = StepscopeDevice()


def connect_all(ip_address: str):
    # connect to device using TCP/IP socket IP address
    _Stepscope.Connect(ip_address)

    # example fetch of system parameter
    serial_number = _Stepscope.Const.getSN()

    print("Stepscope:")
    print("IP Address: " + ip_address)
    print("Serial number: " + serial_number)

    # restore baseline configuration to begin with
    _Stepscope.Stop()  # just to make sure not already running
    _Stepscope.RestoreConfiguration('[Configurations]/test_baseline.cfg')

    # example set configuration parameters
    _Stepscope.Pulse.setAmplMV(300.0)
    _Stepscope.Pulse.setMode(BranchPulse.Mode.Local)
    _Stepscope.Pulse.setLength(8)
    return None


def terminate_all():
    _Stepscope.Disconnect()
    return None


def invoke_tdr():
    # access the TDR features and user interface
    _Stepscope.App.setTab("TDR")

    # Run TDR analysis and retrieve waveform for subsequent use
    _Stepscope.Tdr.Reset()
    _Stepscope.App.Run(True)  # true=run_once
    _Stepscope.WaitForRunToComplete(90)

    # fetch chart configuration
    offset_ps = _Stepscope.Tdr.Cfg.getOffsetPS()
    span_ps = _Stepscope.Tdr.Cfg.getSpanPS()
    record_length = _Stepscope.Tdr.Cfg.getReclen()

    # fetch floating point data array
    data_mv = _Stepscope.Tdr.getBinary()

    # calculate min, max, variation.
    minimum_mv = data_mv[0]
    maximum_mv = data_mv[0]

    # create array of 2-tuples as coordinates for charting
    chart_coordinates_xy = []

    # for each sample ...
    for n in range(0, len(data_mv)):
        # calc sample's ps value, add (ps,mv) to coordinate array
        ps = offset_ps + (n * span_ps) / record_length
        chart_coordinates_xy.append((ps, data_mv[n]))

        # search for min and max values throughout
        minimum_mv = min(minimum_mv, data_mv[n])
        maximum_mv = max(maximum_mv, data_mv[n])

    print("Minimum: " + "{:.2f}".format(minimum_mv))
    print("Maximum: " + "{:.2f}".format(maximum_mv))
    print("Variation: " + "{:.2f}".format(maximum_mv - minimum_mv))
    print("Length of chart coordinates: " + "{:d}".format(len(chart_coordinates_xy)))

    return None


def invoke_return_loss():
    # access the S11 features and user interface
    _Stepscope.App.setTab("S11")

    # configure auto-cursors and enable
    _Stepscope.S11.Chart.setCursor1(BranchS11Chart.Cursor1.AutoXS11)
    _Stepscope.S11.Chart.setCursor2(BranchS11Chart.Cursor2.AutoYS11)
    _Stepscope.S11.Chart.setCursValue(ChartCursorY1, -20.0)
    _Stepscope.S11.Chart.setCursValue(ChartCursorX2, 1.25)

    # turn on cursors

    _Stepscope.S11.Chart.setCursEnabled(ChartCursorX1, True)
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorX2, True)
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorY1, True)
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorY2, True)


    # run analysis
    _Stepscope.S11.Reset()
    _Stepscope.App.Run(True)  # true=run_once
    _Stepscope.WaitForRunToComplete(90)

    # retrieve auto cursor results
    # auto X(GHz) value associated with Y=-20 dB
    # auto Y(dB) value associated with X=1.25 GHz
    ghz_result = _Stepscope.S11.Chart.getCursValue(ChartCursorX1)
    db_result = _Stepscope.S11.Chart.getCursValue(ChartCursorY2)

    print("db_result: " + "{:.2f}".format(db_result))
    print("ghz_result: " + "{:.2f}".format(ghz_result))

    return None


def invoke_insertion_loss():
    # access the S21 features and user interface
    _Stepscope.App.setTab("S21")

    # configure auto-cursors and enable
    _Stepscope.S21.Chart.setCursor1(BranchS11Chart.Cursor1.AutoXS11)
    _Stepscope.S21.Chart.setCursor2(BranchS11Chart.Cursor1.AutoXS11)
    _Stepscope.S21.Chart.setCursValue(ChartCursorY1, -3.0)
    _Stepscope.S21.Chart.setCursValue(ChartCursorY2, -10.0)

    # turn on cursors
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorX1, True)
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorX2, True)
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorY1, True)
    _Stepscope.S11.Chart.setCursEnabled(ChartCursorY2, True)

    # run analysis
    _Stepscope.S21.Reset()
    _Stepscope.App.Run(True)  # true=run_once
    _Stepscope.WaitForRunToComplete(90)

    # retrieve auto cursor results
    # auto X(GHz) value associated with Y=-3 dB
    # auto X(GHz) value associated with Y=-10 dB
    ghz_3dB_result = _Stepscope.S21.Chart.getCursValue(ChartCursorX1)
    ghz_10dB_result = _Stepscope.S21.Chart.getCursValue(ChartCursorX2)

    print("ghz_3dB_result: " + "{:.2f}".format(ghz_3dB_result))
    print("ghz_10dB_result: " + "{:.2f}".format(ghz_10dB_result))

    return None


if __name__ == '__main__':
    print("TestExampleSS, Version 1.0")

    connect_all('192.168.2.45')
    invoke_tdr()
    invoke_return_loss()
    invoke_insertion_loss()
    terminate_all()
# EOF
