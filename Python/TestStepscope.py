# TestStepscope.py
# ================================================================================
# BOOST SOFTWARE LICENSE
#
# Copyright 2020 BitWise Laboratories Inc.
# Original Author.......Jim Waschura
# Contact...............info@bitwiselabs.com
#
# Permission is hereby granted, free of charge, to any person or organization
# obtaining a copy of the software and accompanying documentation covered by
# this license (the "Software") to use, reproduce, display, distribute,
# execute, and transmit the Software, and to prepare derivative works of the
# Software, and to permit third-parties to whom the Software is furnished to
# do so, all subject to the following:
#
# The copyright notices in the Software and this entire statement, including
# the above license grant, this restriction and the following disclaimer,
# must be included in all copies of the Software, in whole or in part, and
# all derivative works of the Software, unless such copies or derivative
# works are solely in the form of machine-executable object code generated by
# a source language processor.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
# SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
# FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
# ================================================================================

from pyBitwiseAutomation import *
import sys
import math

def test_Stepscope(ip_address: str, stopOnError: bool, run: int ):
    Stepscope = StepscopeDevice()
    try:
        Stepscope.Connect(ip_address)

        serialNumber = Stepscope.Const.getSN()

        print("Stepscope TEST");
        print("IP Address........"+ip_address)
        print("Serial number....."+serialNumber)
        print("Build............."+Stepscope.Sys.getBuild())
        print("StopOnError......." + str(stopOnError))

        Stepscope.Stop()
        Stepscope.RestoreConfiguration("[factory]")

        Stepscope.Pulse.setAmplMV(300.0)
        Stepscope.Pulse.setMode(BranchPulse.Mode.Local)
        Stepscope.Pulse.setLength(8)

        Stepscope.App.setTab("STEP")

        Stepscope.Step.Cfg.setReclen(1024)

        Stepscope.Step.Align(BranchStep.AlignMode.align0101)

        Stepscope.WaitForRunToComplete(90)
        Stepscope.App.Stop()
        Stepscope.Step.Fit()

        data = Stepscope.Step.getBinary()

        if len(data)>0:
            minimum = data[0]
            maximum = data[0]

            for n in range(1,len(data)):
                if data[n] < minimum:
                    minimum = data[n]
                if data[n] > maximum:
                    maximum = data[n]

            print("Minimum....." + "{:.2f}".format(minimum))
            print("Maximum....." + "{:.2f}".format(maximum))
            print("Amplitude..." + "{:.2f}".format(maximum-minimum))
        else:
            print("No step response data returned")
            pass
    finally:
        Stepscope.Disconnect()
        Stepscope = None
    return None


if __name__ == '__main__':
    print("TestStepscope, Version 1.0\n")

    stopOnError = False
    ipCount = 0
    repeat = 1
    ip = [32]

    i = 1
    while i<len(sys.argv):
        if sys.argv[i] == "-stop" :
            stopOnError = True
        elif sys.argv[i] == "-repeat":
            repeat = int(sys.argv[i + 1])
            i = i+1
        elif ipCount<32:
            ip[ipCount] = sys.argv[i]
            ipCount = ipCount+1
        else:
            print( "Too many IP addresses, maximum is 32");
            exit()

        i = i+1

    if ipCount == 0 or repeat < 1 :
        print("Usage:  TestStepscope [options] IP0 IP1 ... IPn")
        print("Options:  -stop ..... stop on first error")
        print("          -repeat N.. number of tests for each IP")
        exit()

    for ip_address in ip:
        for k in range(1,repeat+1):
            test_Stepscope( ip_address, stopOnError, k)

# EOF
