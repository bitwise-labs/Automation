# TestPegaStartup.py
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

def test_PegaStartup(ip_address: str, verboseFlag: bool = False, loopCount: int = 1):
    Pega = PegaDevice()
    try:

        Pega.Connect(ip_address)

        print("PEGA STARTUP TEST")
        print("IP Address........"+ip_address)
        print("Serial number....."+Pega.Const.getSN())
        print("Build............."+Pega.Sys.getBuild())
        print("Loop.............."+str(loopCount))
        print("Verbose..........."+str(verboseFlag))

        Pega.setDebugging(verboseFlag)

        for counter in range(0,loopCount):
            print("Loop counter is: "+str(counter))

            # Pega.Syn.setClockRateGHz(5.5)
            # Pega.PG.WaitForClockToSettle(5.5)
            # print("Operating rate is now: "+str(Pega.PG.getOperatingRateGHz()))

            Pega.RestoreConfiguration("[factory]")
            Pega.Syn.setDataRateGbps(10.001)

            # print("Read rate immediately after restore is: "+str(Pega.PG.getReadRateGHz()))
            # print("Operating rate immediately after restore is: "+str(Pega.PG.getOperatingRateGHz()))
            #
            # Pega.PG.WaitForClockToSettle(5.0)
            # print("Read rate after pause is: "+str(Pega.PG.getReadRateGHz()))
            # print("Operating rate after pause is: "+str(Pega.PG.getOperatingRateGHz()))

            Pega.PG.setLinkMode(Pega.PG.LinkMode.Unlinked)  # set it to unlinked

            pg_link = Pega.PG.getLinkMode().value  ## check the link
            print("Link mode is: " + str(pg_link))

            Pega.PG.setAllOn(1)

            pg_status = Pega.PG.getAllOn()
            print("Both Ch0 and Ch1 being on is: " + str(pg_status))

            print(">>>>>>> Data rate after restore and AllOn is:" + str(Pega.Syn.getDataRateGbps()))
            print(">>>>>>> Read rate after restore and AllOn is: " + str(Pega.PG.getReadRateGHz()))
            print(">>>>>>> Operating rate after restore and AllOn is:" + str(Pega.PG.getOperatingRateGHz()))

            # startup initialization from Sreela
            Pega.Syn.setDataRateGbps(18)

            # time.sleep(1)
            Pega.setDebugging(True)
            Pega.PG.WaitForClockToSettle(9)
            Pega.setDebugging(False)

            print(">>>>>>> Data rate after set(18) with 1 second delay is:" + str(Pega.Syn.getDataRateGbps()))
            print(">>>>>>> Read rate after set(18) with 1 second delay is: " + str(Pega.PG.getReadRateGHz()))
            print(">>>>>>> Operating rate after set(18) with 1 second delay is:" + str(Pega.PG.getOperatingRateGHz()))

            pg_clk = Pega.Syn.getDataRateGbps()

            print("Clock source data rate is (in Gbps) :" + str(pg_clk))

            Pega.Syn.setDivOutput(Pega.Syn.DivCalib.Div2)

            pg_clkdiv = Pega.Syn.getDivOutput().value

            print("Clock source Div output is  :" + str(pg_clkdiv))

            ###############Ch0

            Pega.PG.Term.setLinkPosNeg(0, True)  ## Link + and - termination

            ch0_link = Pega.PG.Term.getLinkPosNeg(0)

            print("Ch0  link + and - are linked :" + str(ch0_link))

            Pega.PG.Term.setType(0, Pega.PG.Term.Type.DC)  ### set termination as Dc

            ch0_term = Pega.PG.Term.getType(0).value

            print("Ch0  termination is:" + str(ch0_term))

            Pega.PG.Amp.setAmplMV(0, 200)  # single ended amplitude

            Pega.PG.Amp.setCrossPcnt(0, 50)  # duty cycle

            Pega.PG.setDelayPS(0, 0)

            Pega.PG.Amp.setOffsMV(0, 200)  # offset

            ###############Ch1

            Pega.PG.Term.setLinkPosNeg(1, True)  ## Link + and - termination

            ch1_link = Pega.PG.Term.getLinkPosNeg(1)

            print("Ch1  link + and - are linked :" + str(ch1_link))

            Pega.PG.Term.setType(1, Pega.PG.Term.Type.DC)  ### set termination as Dc

            ch1_term = Pega.PG.Term.getType(1).value

            print("Ch1  termination is:" + str(ch1_term))

            Pega.PG.Amp.setAmplMV(1, 200)  # single ended amplitude

            Pega.PG.Amp.setCrossPcnt(1, 50)  # duty cycle

            Pega.PG.setDelayPS(1, 0)

            Pega.PG.Amp.setOffsMV(1, 200)  # offset

            ##############Send user defined patterns to Ch0 and Ch1

            Pega.PG.setPattern(0, Pega.PG.Pattern.User)

            Pega.PG.setPattern(1, Pega.PG.Pattern.User)

            Pega.Patt.Deploy(Pega.Patt.PatternChannel.Ch0, "10.patt", 0)

            Pega.Patt.Deploy(Pega.Patt.PatternChannel.Ch1, "10.patt", 0)


    finally:
        Pega.Disconnect()
        Pega = None

    return None


if __name__ == '__main__':
    print("TestPegaStartup, Version 1.1\n")

    ipCount = 0
    loop = 1
    ip = ""
    verboseFlag = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "-loop":
            loop = int(sys.argv[i + 1])
            i = i+1
        elif sys.argv[i] == "-verbose":
            verboseFlag = True
        elif ip == "":
            ip = sys.argv[i]

        i = i+1

    if ip == "" or loop < 1:
        print("Usage:  TestPegaStartup [options] <ip-address>")
        print("Options:  -loop N ... set looping count (dflt 1)")
        print("          -verbose ... set verbose mode for debugging")
        exit()

    try:
        test_PegaStartup(ip, verboseFlag, loop)

    except KeyboardInterrupt:
        print("\nCtrl-C encountered")

# EOF