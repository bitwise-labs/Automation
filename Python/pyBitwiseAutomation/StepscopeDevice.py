# StepscopeDevice.py
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

from pyBitwiseAutomation.BitwiseDevice import *
from pyBitwiseAutomation.autogenStepscope import *
from pyBitwiseAutomation.autogenAccessory import *
from pyBitwiseAutomation.autogenCommon import *

class StepscopeDevice(BitwiseDevice):
    """Stepscope device class."""

    def __init__(self):
        super().__init__()

        self.Acc = BranchAcc(self, "Acc:")
        self.Calib = BranchCalib(self, "Calib:")
        self.Pulse = BranchPulse(self, "Pulse:")
        self.S11 = BranchS11(self, "S11:")
        self.S21 = BranchS21(self, "S21:")
        self.Step = BranchStep(self, "Step:")
        self.Tdr = BranchTdr(self, "Tdr:")
        self.Tdt = BranchTdt(self, "Tdt:")

    def __del__(self):
        # # turn off amplifiers upon every Stepscope object deletion
        # if self.getIsConnected():
        #     self.PG.setAllOn(False)

        super().__del__()
        return None

# EOF