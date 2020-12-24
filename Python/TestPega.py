# TestPega.py
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

def test_Pega(ip_address: str, stopOnError: bool, run: int, fromGHz: float = 1, toGHz: float = 28, stepGHz: float = 0.5 ):
    Pega = PegaDevice()
    try:
        Pega.Connect(ip_address)

        serialNumber = Pega.Const.getSN()

        print("PEGA FREQUENCY SWEEP");
        print("IP Address........"+ip_address)
        print("Serial number....."+serialNumber)
        print("Build............."+Pega.Sys.getBuild())
        print("StopOnError......."+ str(stopOnError))
        print("From GHz.........."+str(fromGHz))
        print("To GHz............"+str(toGHz))
        print("Step GHz.........."+str(stepGHz))

        Pega.Stop();

        Pega.RestoreConfiguration("[factory]")
        Pega.PG.Amp.setAmplMV(0, 500.0)
        Pega.PG.Amp.setAmplMV(1, 500.0)

        Pega.PG.setPattern(0, BranchPG.Pattern.Prbs7)
        Pega.PG.setPattern(1, BranchPG.Pattern.Prbs31)

        Pega.Syn.setSource(0, BranchSyn.Source.Internal)
        Pega.Syn.setSource(1, BranchSyn.Source.Internal)
        Pega.PG.setAllOn(True)

        Pega.ED.setEnabled(True)
        Pega.ED.Sampler.setMode(BranchEDSampler.Mode.CalInput)
        Pega.ED.setEyeSubrate(BranchED.EyeSubrate.DivBy1)
        Pega.ED.setAutoResync(True)
        Pega.ED.setPatt(BranchED.Patt.Auto)

        Pega.Tub.setResolutionPS(0.25)

        print("=================================================================================");
        print("SN,Run,DegreeC,Gbps,CalDiv,Align,Thresh,Delay,Sync,Errors,Resyncs,BER,LogBER,RJ,EWC,TubStatus");

        dataRateGbps = fromGHz
        while dataRateGbps <= toGHz:
            clockRateGHz = dataRateGbps / 2.0
            Pega.Syn.setClockRateGHz(clockRateGHz)

            divider = Pega.ED.findBestCalibDivider(dataRateGbps)
            Pega.Syn.setDivCalib(divider)
            Pega.PG.WaitForClockToSettle(clockRateGHz)
            degrees = Pega.getTemperatureC();

            Pega.ED.AlignData(BranchED.AlignBy.All)

            alignStatus=Pega.ED.getAlignDataMsg()

            print(serialNumber, end='')
            print(","+str(run), end='')
            print("," + "{:.2f}".format(degrees), end='')
            print("," + "{:.2f}".format(dataRateGbps), end='')
            print("," + divider.name, end='')
            print(",\"" + alignStatus+ "\"" , end='')
            print("," + "{:.2f}".format(Pega.ED.Sampler.getVoltsMV()), end='')
            print("," + "{:.2f}".format(Pega.ED.Sampler.getTimePS()), end='')

            if stopOnError and alignStatus.upper().startswith("SUCCESS"):
                raise Exception("[Stop_On_No_Alignment]")

            #= == == == == == == == == == == == == == == == == ==== == == == == == == == == == == == == == =

            Pega.App.Stop()
            Pega.App.setTab("BERT")
            Pega.App.Clear()

            inSyncFlag = Pega.ED.getInSync()

            Pega.App.Run()
            time.sleep(5)
            Pega.App.Stop()

            ERRS = Pega.Err.getErrors()
            RC = Pega.Err.getResyncCount()
            BER = Pega.Err.getABER()
            logBER = 0.0 if BER == 0.0 else math.log10(BER)

            print(","+str(inSyncFlag), end='')
            print(","+str(ERRS), end='')
            print("," + str(RC), end='')
            print("," + "{:.2e}".format(BER), end='')
            print("," + "{:.2f}".format(logBER), end='')

            if stopOnError and (not inSyncFlag):
                raise Exception("[Stop_On_No_Sync]")

            if stopOnError and (RC > 0 or ERRS > 0.0):
                raise Exception("[Stop_On_Errors]")

            #= == == == == == == == == == == == == == == == == ==== == == == == == == == == == == == == == =

            Pega.App.Stop()
            Pega.App.setTab("TUB")
            Pega.App.Clear()

            Pega.RunSingle()
            Pega.WaitForRunToComplete(300.0)

            tubStatusMessage = Pega.Tub.getStatusMsg()

            results = Pega.Tub.FetchResults()
            RJ = BitwiseDevice.unpackDoubleByKey(results, "RJ")
            EWC = BitwiseDevice.unpackDoubleByKey(results, "EWC")

            print(","+"{:.3f}".format(RJ), end='')
            print(","+"{:.3f}".format(EWC), end='')
            print(",\"" + tubStatusMessage + "\"")

            if stopOnError and (RJ == 0.0) and dataRateGbps >= 4.0:
                raise Exception("[Stop_On_Bad_Tub]")

                # = == == == == == == == == == == == == == == == == ==== == == == == == == == == == == == == == =
            dataRateGbps = dataRateGbps + stepGHz

    finally:
        Pega.Disconnect()
        Pega = None
    return None


if __name__ == '__main__':
    print("TestPega, Version 1.0\n")

    stopOnError = False
    fromGHz = 1.0
    toGHz = 28.0
    stepGHz = 0.5
    ipCount = 0
    repeat = 1
    ip = [32]

    i = 1
    while i<len(sys.argv):
        if sys.argv[i] == "-stop" :
            stopOnError = True
        elif sys.argv[i] == "-step":
            stepGHz = float(sys.argv[i+1])
            i = i+1
        elif sys.argv[i] == "-from":
            fromGHz = float(sys.argv[i+1])
            i = i+1
        elif sys.argv[i] == "-to":
            toGHz = float(sys.argv[i + 1])
            i = i+1
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

    if ipCount == 0 or stepGHz <= 0.0 or repeat < 1 or fromGHz <= 0.0 or toGHz > 32.0 or fromGHz >= toGHz:
        print("Usage:  TestPega [options] IP0 IP1 ... IPn")
        print("Options:  -stop ..... stop on first error")
        print("          -from X ... set starting Gbps (dflt 1.0)")
        print("          -to X ..... set ending Gbps (dflt 28.0)")
        print("          -step X ... set step-size Gbps (dflt 0.5)")
        print("          -repeat N.. number of tests for each IP")
        exit()


    for ip_address in ip:
        for k in range(1,repeat+1):
            test_Pega( ip_address, stopOnError, k, fromGHz, toGHz, stepGHz )

# EOF