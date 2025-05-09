# TestStepscopeResets.py
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


def extract_value(data: str, target_key: str) -> str:
    """
    Extracts the value associated with a given key from a newline-separated string of key-value pairs.

    Parameters:
        data (str): The input string containing key-value pairs separated by newline characters.
        target_key (str): The key whose associated value is to be extracted.

    Returns:
        str: The value corresponding to the specified key, or None if the key is not found.
    """
    lines = data.splitlines()
    for line in lines:
        if '=' in line:
            key, value = line.split('=', 1)
            if key.strip() == target_key:
                return value.strip()
    return "Key_Not_Found"


def test_StepscopeResets(ip_address: str, stopOnError: bool, repeat: int, verbose: bool):
    Stepscope = StepscopeDevice()
    try:
        Stepscope.Connect(ip_address)

        serialNumber = Stepscope.Const.getSN()

        print("Stepscope TEST")
        print("IP Address........" + ip_address)
        print("Serial number....." + serialNumber)
        print("Build............." + Stepscope.Sys.getBuild())
        print("Architecture......" + Stepscope.Sys.getArchitecture())
        print("StopOnError......." + str(stopOnError))
        print("Repeat............" + str(repeat))
        print("Verbose..........." + str(verbose))

        Stepscope.Stop()
        # Stepscope.RestoreConfiguration("[factory]")
        # if verbose:
        #     print("Configuration restore is complete")

        Stepscope.Pulse.setAmplMV(300.0)
        Stepscope.Pulse.setMode(BranchPulse.Mode.Local)
        Stepscope.Pulse.setLength(8)

        Stepscope.App.setTab("STEP")

        Stepscope.Step.Cfg.setReclen(1024)

        if verbose:
            print("Perform alignment")

        Stepscope.Step.Align(BranchStep.AlignMode.align0101)
        Stepscope.WaitForRunToComplete(90)
        Stepscope.App.Stop()
        Stepscope.Step.Fit()
        n=0

        while n<repeat:
            stats = Stepscope.Step.PulseStats()
            answer = extract_value(stats, "RiseTransitionPS")
            int_answer = int(float(answer))
            print("Answer["+str(n)+"] is: " + str(int_answer))
            time.sleep(1.0)
            Stepscope.Pulse.Reset()
            n = n + 1

        # while repeat > 0:
        #     time.sleep(3.0)
        #     # Stepscope.Pulse.Reset()
        #     Stepscope.App.Run(True)
        #     Stepscope.WaitForRunToComplete(90)
        #     Stepscope.App.Stop()
        #
        #     stats = Stepscope.Step.PulseStats()
        #     answer = extract_value(stats, "RiseTransitionPS")
        #     print("Answer is: " + answer)
    finally:
        Stepscope.Disconnect()
        Stepscope = None
    return None


if __name__ == '__main__':
    print("TestStepscopeResets, Version 1.0\n")

    # Version 1.0 ... 04-24-2025 ... original

    stopOnError = False
    verbose = False
    ip_address = None
    repeat = 1

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "-stop":
            stopOnError = True
        elif sys.argv[i] == "-verbose":
            verbose = True
        elif sys.argv[i] == "-repeat":
            repeat = int(sys.argv[i + 1])
            i = i + 1
        elif sys.argv[i] == "-ip":
            ip_address = sys.argv[i + 1]
            i = i + 1
        else:
            print("Unknown argument: " + sys.argv[i])
            exit()

        i = i + 1

    if ip_address is None or repeat < 1:
        print("Usage:  TestStepscopeResets [options]")
        print("Options:  -stop ......... stop on first error")
        print("          -verbose ...... more debugging messages")
        print("          -repeat N...... number of tests for each IP")
        print("          -ip ip_addr ... ip address");
        exit()

    try:
        test_StepscopeResets(ip_address, stopOnError, repeat, verbose)

    except KeyboardInterrupt:
        print("\nCtrl-C encountered")

# EOF
