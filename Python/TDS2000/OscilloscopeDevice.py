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

    def setup_channel(self,channel="CH1"):
        self.write("TRIGGER:MAIN:EDGE:SOURCE "+channel+"\n")
        self.write(channel+":PROBE 1\n")

    def align_and_center_single_pulse(self,channel="CH1"):
        self._progress_print("Align and center single pulse on channel "+channel)

        self.show_single_pulse_after_autoset()
        self.scale_vertical_and_recenter("CH1", 2)
        self.set_averaging(128)