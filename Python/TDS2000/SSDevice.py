import time

from TDS2000.Waveform import Waveform
from pyBitwiseAutomation import StepscopeDevice, BranchStep, BranchStepCfg


class SSDevice(StepscopeDevice):
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
    def also_set_base_class(self, value: bool):
        self._also_set_base_class = bool(value)

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = bool(value)
        if self._also_set_base_class:
            super().setDebugging(value)

    @property
    def timing(self):
        return self._timing

    @timing.setter
    def timing(self, value: bool):
        self._timing = bool(value)

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value: bool):
        self._progress = bool(value)

    def _debug_print(self, msg):
        if self.debug:
            print("[DEBUG]", msg)

    def _progress_print(self, msg):
        if self.progress:
            print("[PROGRESS]", msg)

    def setup_channel(self):
        self._progress_print("Setup STEPScope Step response view")

        self.Stop()  # just to make sure not already running
        # self.RestoreConfiguration('[Factory]')

        self.App.setTab("STEP")
        self.Step.Cfg.setBaseAxis(BranchStepCfg.BaseAxis.Nanoseconds)
        self.Step.Cfg.setReclen(1250)  # same as Tek scope
        self.Step.Cfg.setAvg(3)
        self.WaitForRunToComplete()


    def align_and_center_single_pulse(self):
        self._progress_print("Align and center single pulse")
        if self.timing:
            start = time.perf_counter()

        self.App.Stop()
        self.Step.Align(BranchStep.AlignMode.align0101)
        self.App.Run(runOnceFlag=True)
        self.WaitForRunToStart()
        self.WaitForRunToComplete()
        self.Step.Fit()


        if self.timing:
            elapsed = time.perf_counter() - start
            print(f"[TIMING] align_and_center_single_pulse took {elapsed:.3f} sec")

    def get_waveform_data(self, name="no_name"):
        self._progress_print("Acquiring waveform data")
        if self.timing:
            start = time.perf_counter()

        offset_ns = self.Step.Cfg.getOffsetPS()
        span_ns = self.Step.Cfg.getSpanPS()
        record_length = self.Step.Cfg.getReclen()
        data_mv = self.Step.getBinary()

        wf = Waveform(name)
        wf.progress = self.progress
        wf.set_y_values(data_mv)
        wf.offset = offset_ns
        wf.span = span_ns
        wf.x_units = "ns"
        wf.y_units = "mV"

        if self.timing:
            elapsed = time.perf_counter() - start
            print(f"[TIMING] get_waveform_data took {elapsed:.3f} sec")

        if self.debug:
            print(f"[DEBUG] Retrieved {record_length} samples over {wf.span:.3f} " + wf.x_units)
            print(f"[DEBUG] First 5 Y values: {[f'{y:.3f}' for y in data_mv[:5]]}")
            print(f"[DEBUG] First 5 X values: {[f'{x:.6f}' for x in wf.generate_x_values()[:5]]}")

        return wf
