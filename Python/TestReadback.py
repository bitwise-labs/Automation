# TestReadback.py
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
import random


def test_Readback(ip_address: str, stopOnError: bool, verboseMode: bool, loop_count: int = 10000):
    Bw = BitwiseDevice()
    Bw.setDebugging(verboseMode)

    try:
        Bw.Connect(ip_address)
        print("TEST READBACK REGISTER")
        print("IP Address........" + ip_address)
        print("Serial number....." + Bw.Const.getSN())
        print("Nickname.........." + Bw.Sys.getNickname())
        print("Build............." + Bw.Sys.getBuild())
        print("Architecture......" + Bw.Sys.getArchitecture())
        print("StopOnError......." + str(stopOnError))
        print("verboseMode......." + str(verboseMode))
        print("Loop count........" + str(loop_count))

        Bw.Stop()

        error_count = 0
        for ii in range(loop_count):
            random_number = random.randint(0, 0xffffffff)

            Bw.Hw.setReadback(random_number)
            read_back = Bw.Hw.getReadback()
            if read_back != random_number:
                error_count = error_count + 1

                print(f"\n{ii}, write {random_number:#08x}, read {read_back:#08x}")

                if stopOnError:
                    break

            print(f"{ii}, {error_count} error(s)      ", end="\r")

        print(f"\nDone.  {error_count} error(s), out of {loop_count} attempts")

    finally:
        Bw.Disconnect()
        Bw = None

    return None


if __name__ == '__main__':
    print("TestReadback, Version 1.0\n")

    verbose = False
    stop_on_error = False
    loop = 10000
    ip = ""

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "-loop":
            loop = int(sys.argv[i + 1])
            i = i + 1
        elif sys.argv[i] == "-stop":
            stop_on_error = True
        elif sys.argv[i] == "-verbose":
            verbose = True
        elif ip == "":
            ip = sys.argv[i]
        else:
            print("Unknown argument: " + sys.argv[i])
            exit()

        i = i + 1

    if ip == "":
        print("Usage:  TestReadback [options] IP")
        print("Options:  -loop N ..... Specify loop count (dflt 10000)")
        print("          -stop ....... Stop on error")
        print("          -verbose .... Verbose")

        exit()

    try:
        test_Readback(ip, stop_on_error, verbose, loop)

    except KeyboardInterrupt:
        print("\nCtrl-C encountered")

# EOF