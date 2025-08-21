from tds2000 import TDS2000

class OscilloscopeDevice(TDS2000):
    """
    OscilloscopeDevice extends TDS2000 with support for local timing and debugging flags.
    """

    def __init__(self):
        super().__init__()
        self._debug = False
        self._timing = False
        self._progress = False
        self._also_set_base_class = False

    @property
    def also_set_base_class(self):
        return self._also_set_base_class

    @also_set_base_class.setter
    def also_set_base_class(self, value: bool ):
        self._also_set_base_class = bool(value)

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = bool(value)
        if self._also_set_base_class:
            super().debug=value

    @property
    def timing(self):
        return self._timing

    @timing.setter
    def timing(self, value: bool):
        self._timing = bool(value)
        if self._also_set_base_class:
            super().timing=value

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value: bool):
        self._progress = bool(value)
        if self._also_set_base_class:
            super().progress=value

    def _debug_print(self, msg):
        if self.debug:
            print("[DEBUG]", msg)

    def _progress_print(self, msg):
        if self.progress:
            print("[PROGRESS]", msg)

    def setup_channel(self,channel,trigger_channel="CH1"):
        self._progress_print("Setting up oscilloscope channel "+channel)

        if channel.upper()=="MATH":
            self.write("CH1:PROBE 1")
            self.write("CH2:PROBE 1")
            self.write("CH1:COUP DC")
            self.write("CH2:COUP DC")
            self.write("SELECT:CH1 ON")
            self.write("SELECT:CH2 ON")
            self.write('MATH:DEFINE "CH1 - CH2"')
            self.write("SELECT:MATH ON")
            self.write("TRIGGER:MAIN:EDGE:SOURCE CH1")
            self.write(f"TRIGGER:MAIN:EDGE:COUPLING DC")

        else:
            self.write(f"{channel}:COUP DC")
            self.write(f"PROBE:{channel} 1")
            self.write(f"SELECT:{channel} ON")
            self.write(f"TRIGGER:MAIN:EDGE:SOURCE {trigger_channel}")
            self.write(f"TRIGGER:MAIN:EDGE:COUPLING DC")




