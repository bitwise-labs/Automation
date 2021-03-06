# BitwiseDevice.py
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
import time
from pyBitwiseAutomation.SocketDevice import SocketDevice
from pyBitwiseAutomation.autogenCommon import *

class BitwiseDevice(SocketDevice):
    """Bitwise device class."""

    def __init__(self):
        super().__init__()
        self.App = BranchApp(self, "App:")
        self.File = BranchFile(self, "File:")
        self.Sys = BranchSys(self, "Sys:")
        self.Const = BranchConst(self, "Const:")

    def __del__(self):
        super().__del__()
        return None

    # Override
    def SendCommand(self, command:str ):
        """Send command (ending with '\n') to socket device, with error handling."""

        super().SendCommand( "stc;"+command)
        statusResponse = super().QueryResponse( "st?\n")

        if statusResponse != "[none]" :
            raise Exception("["+statusResponse+"]")

        return None

    #Override
    def QueryResponse( self, command:str, maxLength:int = 4096 ) -> str:
        """Query response from command (ending with '\n') from socket device, with error handling."""

        if not isinstance(command,str):
            raise Exception("[Command_Must_Be_String]")

        if not isinstance(maxLength,int):
            raise Exception("[MaxLen_Must_Be_Int]")

        response = super().QueryResponse( "stc;"+command, maxLength)
        statusResponse = super().QueryResponse( "st?\n")

        if statusResponse != "[none]":
            raise Exception("[" + statusResponse + "]")

        return response

    def SaveConfiguration(self, configuration:str ):
        """Restore configuration file and optionally pause while operation completes.

        specifying configurations:
        [recent]  ...  most recent settings
        [factory]  ... factory settings
        [startup]  ... settings from selectable startup configuration file
        full-path-name ... settings from fully-specified configuration file path
        filename-only ... settings from file located in configuration folder
        """

        super().SendCommand( "stc;"+"save \"" + configuration + "\"\n" )
        super().SendCommand( "stc\n")
        return None

    def RestoreConfiguration(self, configuration:str, waitToComplete:bool = True ):
        """Restore configuration file and optionally pause while operation completes.

        specifying configurations:
        [recent]  ...  most recent settings
        [factory]  ... factory settings
        [startup]  ... settings from selectable startup configuration file
        full-path-name ... settings from fully-specified configuration file path
        filename-only ... settings from file located in configuration folder
        """

        self.App.Stop() # just to make sure

        super().SendCommand( "stc;"+"restore \"" + configuration + "\"\n" )

        if waitToComplete:
            self.WaitForRestoreToComplete()

        return None


    def WaitForRestoreToComplete(self):
        """Wait for restore configuration operation completes."""

        now = SocketDevice.timestamp()
        timeout = now + 30.0
        begin_time = now

        while now < timeout:
            time.sleep(0.5)
            now = SocketDevice.timestamp()

            if self.getDebugging():
                print("Restoring configuration " + "{:.1f}".format(now - begin_time) )

            response = super().QueryResponse("inprogress\n")
            if response == "F" or response == "0":
                break

        if now >= timeout:
            raise Exception("[Timeout_Restoring_Configuration]")

        super().SendCommand( "stc\n")
        return None


    def getIsRunning(self) ->bool :
        response = self.QueryResponse("App:RunState?\n")
        if len(response) < 2:
            raise Exception("[Invalid_RunState_Response]")

        tokens = response[1:-1].split(",")
        return_value = False
        for itm in tokens:
            if itm != "Stop":
                return_value = True
                break

        return return_value

    def Run(self):
        """Initiate run operation and wait until started."""

        self.App.Run(False)

        now = SocketDevice.timestamp()
        timeout = now + 30.0

        while now < timeout:
            time.sleep(0.5)
            now = SocketDevice.timestamp()
            if getIsRunning():
                break

        if now >= timeout:
            raise Exception("[Run_Timeout]")

        return None

    def RunSingle(self):
        """Initiate run once operation and wait until started."""

        self.App.Run(True)

        now = SocketDevice.timestamp()
        timeout = now + 30.0

        while now < timeout:
            time.sleep(0.5)
            now = SocketDevice.timestamp()
            if self.getIsRunning():
                break

        if now >= timeout:
            raise Exception("[Run_Single_Timeout]")

        return None

    def Stop(self, ):
        self.App.Stop()
        return None

    def WaitForRunToComplete(self, timeoutSec: float):
        """Wait for device to stop running."""

        now = SocketDevice.timestamp()
        timeout = now + timeoutSec

        while now < timeout and self.getIsRunning():
            time.sleep(0.5)

            now = SocketDevice.timestamp()

        self.Stop()
        return None

    @staticmethod
    def unpackValueByKey(string: str, key: str) -> str:
        lines = string.split("\n")
        retn = None
        for tok in lines:
            if tok.startswith(key+" ") or tok.startswith(key+"=") or tok.startswith(key+"\t") or tok.startswith(key+",") :
                retn = tok[len(key)+1:]

        if retn == None:
            raise Exception("[Key_Not_Found]")

        return retn

    @staticmethod
    def unpackDoubleByKey(string: str, key: str) -> float:
        return float(BitwiseDevice.unpackValueByKey(string, key))

    @staticmethod
    def unpackIntegerByKey(string: str, key: str) -> float:
        value = BitwiseDevice.unpackValueByKey(string,key)
        if value.startswith("0x") or value.startswith("0X"):
            retn = int(value[2:], 16)
        else:
            retn = int(value)
        return retn


    def Clear(self):
        self.App.Clear()
        return None

# EOF