# TestPegaRateChange.py
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
import time
import math

def runOnePatternTest( pega: PegaDevice, ch: int, pch: BranchPatt.PatternChannel, ghz: float, \
             pegaPattern: BranchPG.Pattern, fname: str, grablen: int, \
             detpatt: BranchED.DetPatt, autoAlignFlag: bool, \
             stopOnErrorFlag: bool = True) -> int :

    errors = 0

    try:
        print("Set data rate to: " + str(ghz) )
        pega.Syn.setClockRateGHz(ghz / 2.0)

        print("Wait for clock to settle");
        pega.PG.WaitForClockToSettle(ghz / 2.0)

        # print("Step 1: Detecting: "+str(pega.ED.getDetPatt().value))

        if pegaPattern == BranchPG.Pattern.User:
            print("Deploy " + fname + " to " + str(pch.value))
            pega.Patt.Deploy(pch, fname)

            print("Set grab length to " + str(grablen) )
            pega.ED.setGrabLen(grablen)

        print("Set Pega pattern to: " + str(pegaPattern.value))
        pega.PG.setPattern(ch, pegaPattern)

        # print("Step 2: Detecting: "+str(pega.ED.getDetPatt().value))

        if autoAlignFlag:
            print("Perform auto-align")

            pega.ED.AlignData(BranchED.AlignBy.All)
            alignStatus = pega.ED.getAlignDataMsg()
            print("Auto-align status is: " + str(alignStatus))

            if stopOnErrorFlag and (not alignStatus.upper().startswith("SUCCESS")):
                print("Error: Alignment failed");
                errors = errors + 1
                # raise Exception("[Stop_On_No_Alignment]")

                if stopOnErrorFlag:
                    raise Exception("[Auto_Alignment_Not_Successful]")

        print("Wait for pattern to settle");

        x = pega.ED.WaitForDetPattToSettle()
        print("Detected pattern: "+str(x.value))

        if x != detpatt:
            print("Error: Detected pattern does not match")
            errors = errors + 1

            if stopOnErrorFlag:
                raise Exception("[Detected_Pattern_Does_Not_Match]")

    except Exception as e:
        print("Problem building pivot file contents: ", e)
        errors = 1;
        # raise e

    return errors

def test_rate_change(ip_address: bool, stopOnErrorFlag: bool = True, loopFlag: bool = False, autoAlignFlag: bool = False ):
    Pega = PegaDevice()
    try:
        # Pega.setDebugging(True)

        CH = 0
        PCH = BranchPatt.PatternChannel.Ch0
        AMPL = 500.0


        print("PEGA TEST DATA RATE CHANGING")
        print("IP Address........"+ip_address)

        Pega.Connect(ip_address)

        serialNumber = Pega.Const.getSN()

        print("Serial number....."+serialNumber)
        print("Build............."+Pega.Sys.getBuild())
        print("Architecture......" + Pega.Sys.getArchitecture())
        print("Temperature......" + str(Pega.getTemperatureC()))
        print("Channel to test..." + str(CH))
        print("Channel Amplitude " + str(AMPL))

        Pega.Stop()

        Pega.RestoreConfiguration("[factory]")

        Pega.PG.Amp.setAmplMV(CH, 500.0)
        Pega.Syn.setSource(CH, BranchSyn.Source.Internal)
        Pega.Syn.setDivOutput(BranchSyn.DivOutput.Div2)
        Pega.Syn.setDivCalib(BranchSyn.DivCalib.Div4)
        Pega.PG.setAllOn(True)
        Pega.ED.setPatt(BranchED.Patt.Auto)
        Pega.ED.setAutoResync(True)
        Pega.ED.Sampler.setMode(BranchEDSampler.Mode.CalInput)
        Pega.ED.setEnabled(True)

        errors = 0
        errors = runOnePatternTest(Pega, CH, PCH, 10.0, BranchPG.Pattern.Prbs7, "", BranchED.GrabLen._32,
                                  BranchED.DetPatt.Prbs7, True, stopOnErrorFlag)

        first = True
        tests = 0
        while first or loopFlag:

            errors += runOnePatternTest(
                Pega, CH, PCH,  10.0,
                BranchPG.Pattern.Prbs7, "", BranchED.GrabLen._32,
                BranchED.DetPatt.Prbs7, True, stopOnErrorFlag
                )
            tests = tests + 1
            errors += runOnePatternTest(
                Pega, CH, PCH,  10.0,
                BranchPG.Pattern.User, "16-1s-16-0s.patt", BranchED.GrabLen._32,
                BranchED.DetPatt.Grab, False, stopOnErrorFlag
                )
            tests = tests + 1
            errors += runOnePatternTest(
                Pega, CH, PCH,  10.0,
                BranchPG.Pattern.User, "111000.patt", BranchED.GrabLen._192,
                BranchED.DetPatt.Grab, False, stopOnErrorFlag
                )
            tests = tests + 1
            print(str(errors)+" Errors, " + str(tests) + " Tests.");

            errors += runOnePatternTest(
                Pega, CH, PCH, 9.0,
                BranchPG.Pattern.Prbs15, "",
                BranchED.GrabLen._32, BranchED.DetPatt.Prbs15, True, stopOnErrorFlag
                )
            tests = tests + 1
            errors += runOnePatternTest(
                Pega, CH, PCH, 9.0,
                BranchPG.Pattern.User, "16-1s-16-0s.patt",
                BranchED.GrabLen._32, BranchED.DetPatt.Grab, False, stopOnErrorFlag
                )
            tests = tests + 1
            errors += runOnePatternTest(
                Pega, CH, PCH, 9.0,
                BranchPG.Pattern.User, "111000.patt",
                BranchED.GrabLen._192, BranchED.DetPatt.Grab, False, stopOnErrorFlag
                )
            tests = tests + 1
            print(str(errors)+" Errors, " + str(tests) + " Tests.");

            first = False

    except Exception as e:
        print( "Exception encountered: " + str(e) )

    finally:
        Pega.Disconnect()
        Pega = None

    return None


if __name__ == '__main__':
    print("TestPegaRateChange, Version 1.1\n")

    stopOnErrorFlag = False
    ipAddress = ""
    loopFlag = False
    autoAlignFlag = False;

    i = 1
    while i<len(sys.argv):
        if sys.argv[i] == "-stop" :
            stopOnErrorFlag = True
        elif sys.argv[i] == "-aa":
            autoAlignFlag = True
        elif sys.argv[i] == "-loop":
            loopFlag = True
        elif ipAddress == "" :
            ipAddress = sys.argv[i]
        else:
            print( "Unrecognized command line token: " + sys.argv[i])
            exit()

        i = i+1

    if ipAddress == "":
        print("Usage:  TestPegaRateChange [options] ip-address")
        print("Options:  -stop ..... stop on first error")
        print("          -aa   ..... enable auto align during test")
        print("          -loop ..... never-ending loop, use ctrl-c to stop")
        exit()

    try:
        test_rate_change( ipAddress, stopOnErrorFlag, loopFlag, autoAlignFlag )

    except KeyboardInterrupt:
        print("\nCtrl-C encountered")

# EOF
