import os
import struct
import time
import array
import fcntl
import select
from fcntl import F_GETFL, F_SETFL

from TDS2000.Helper import MEDIUM_PAUSE, LONG_PAUSE, VERY_LONG_PAUSE, SCOPE_AVERAGING
from Waveform import Waveform  # Ensure the Waveform class is available

class TDS2000:
    def __init__(self):
        self.scope_path = None
        self.fd = None
        self._debug = False
        self._timing = False
        self._progress = False

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = bool(value)

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

    def connect(self, the_scope_path="/dev/usbtmc0"):
        self.scope_path = the_scope_path
        self._progress_print(f'Connecting to scope at "{self.scope_path}"')
        try:
            self.fd = os.open(self.scope_path, os.O_RDWR)
            # time.sleep(0.2)
            # self.flush_input()
            self._progress_print("Connected to: "+self.query("*IDN?"))
            self.write("*RST")
            time.sleep(0.2)
            self.write("HEAD OFF")
            self.flush_input()
            self.query("*OPC?")
        except PermissionError:
            raise PermissionError(f'Cannot open oscilloscope, check permissions: "chmod a+rw {self.scope_path}"')
        except FileNotFoundError:
            raise FileNotFoundError(f"{self.scope_path} not found. Is the scope connected?")
        return True

    def disconnect(self):
        if self.fd is not None:
            self._progress_print("Disconnecting from scope")
            os.close(self.fd)
            self.fd = None
        return True

    def write(self, cmd):
        if self.fd is None:
            raise ConnectionError("Oscilloscope not connected.")

        start_s = time.perf_counter()

        self._debug_print(f"Writing: {cmd.strip()}")
        os.write(self.fd, cmd.encode())

        elapsed_s = (time.perf_counter() - start_s)
        if self.timing:
            print(f"[TIMING] \"{cmd.strip()}\" took {elapsed_s:.3f}s")

    def query(self, cmd, delay=0.0, readlen=1024):
        """Send a SCPI query and return the response."""
        if self.fd is None:
            raise ConnectionError("Oscilloscope not connected.")

        start_s = time.perf_counter()
        # self.flush_input()
        # time.sleep(5.0)

        flush_s = time.perf_counter() - start_s
        start_s = time.perf_counter()

        clean_cmd = cmd.strip()
        self._debug_print(f"Querying: {clean_cmd}")
        os.write(self.fd, (clean_cmd + "").encode())

        write_completed_s = (time.perf_counter() - start_s)
        start_s = time.perf_counter()

        time.sleep(delay)
        response = os.read(self.fd, readlen).decode(errors='ignore').strip()
        respond_s = (time.perf_counter() - start_s)
        if self.timing:
            print(f"[TIMING] \"{clean_cmd}\" took {flush_s:.3f}s to flush, {write_completed_s:.3f}s to write query, {respond_s:.3f}s to respond")

        self._debug_print(f"Response: {response}")
        return response

    def flush_input(self, max_attempts=1):
        # self._debug_print("Flushing input buffer")
        start_s = time.perf_counter()
        try:
            for _ in range(max_attempts):
                data = os.read(self.fd, 512)
                if not data:
                    break
        except (BlockingIOError, TimeoutError):
            pass

        flush_s = time.perf_counter() - start_s
        if self.timing:
            print(f"[TIMING] flush_input() took {flush_s:.3f} sec")

    def get_id(self):
        self._progress_print("Getting scope ID")
        return self.query("*IDN?")

    def set_averaging(self, count=128):
        self._progress_print(f"Setting averaging to {count}")
        if count <= 1:
            self.write("ACQUIRE:MODE SAMPLE")
        elif 2 <= count <= 512:
            self.write("ACQUIRE:MODE AVERAGE")
            self.write(f"ACQUIRE:NUMAVG {int(count)}")
        else:
            raise ValueError("Averaging count must be between 2 and 512 (or <=1 to disable).")

    def set_time_cursors(self, channel="CH1", pos1_pct=0.20, pos2_pct=0.70):
        self._progress_print(f"Setting time cursors at {pos1_pct * 100:.1f}% and {pos2_pct * 100:.1f}% of view")
        self.write("CURSOR:FUNCTION VBARS")
        self.write("CURSOR:SELECT:SOURCE " + channel)
        self.write("CURSOR:TYPE TIME")
        self.write("CURSOR:SELECT BOTH")
        center_sec = float(self.query("HORIZONTAL:POSITION?").strip())
        scale_sec = float(self.query("HORIZONTAL:SCALE?").strip())
        full_width = 10.0 * scale_sec
        left_edge = center_sec - full_width / 2.0
        time1 = left_edge + pos1_pct * full_width
        time2 = left_edge + pos2_pct * full_width
        self.write(f"CURSOR:VBARS:POSITION1 {time1:.6e}")
        self.write(f"CURSOR:VBARS:POSITION2 {time2:.6e}")

    def get_cursor_voltages(self):
        self._progress_print("Reading voltage at cursor positions")
        self.write("CURSOR:TYPE TIME")
        self.write("CURSOR:SELECT BOTH")
        v1_str = self.query("CURSOR:VBARS:HPOS1?").strip()
        v2_str = self.query("CURSOR:VBARS:HPOS2?").strip()
        v1 = float(v1_str)
        v2 = float(v2_str)
        return v1, v2

    def calc_fit_vpd(self,ch_vpp:float)->float:
        VOLTS_PER_DIVISION = [0.005, 0.010, 0.020, 0.050, 0.100, 0.200, 0.500, 1.000, 2.000, 5.000]

        scale = 5.0
        for vpd in VOLTS_PER_DIVISION:
            entire_range = 8 * vpd
            if ch_vpp/0.90 < entire_range:
                scale = vpd
                break

        return scale

    def calc_fit_tpd(self,span:float)->float:
        TIME_PER_DIVISION = [2.5E-9,5E-9,10e-9,2.5E-8,5E-8,10E-8,2.5E-7,5E-7,10E-7]

        #self._progress_print(f"calc_fit_tps(), span={span}")
        scale = 5.0
        for tpd in TIME_PER_DIVISION:
            entire_range = 10 * tpd
            #self._progress_print(f"test {tpd} (compare span/0.9={span/0.90} with entire_range={entire_range}")

            if span/0.99 < entire_range:
                #self._progress_print(f"select")
                scale = tpd
                break

        #self._progress_print(f"return {scale}")
        return scale

    def get_waveform_data(self, channel="CH1", name="no_name"):
        self._progress_print(f"Acquiring waveform from {channel}")
        if self.timing:
            start = time.perf_counter()

        self.write(f"DATA:SOURCE {channel}")
        self.write("DATA:ENCdg RIBinary")  # Signed integer, MSB first
        self.write("DATA:WIDTH 1")  # 1 byte per sample
        self.write("WFMPRE:BYTE_NR 1")
        # time.sleep(SHORT_PAUSE)

        xincr = float(self.query("WFMPRE:XINCR?"))
        xzero = float(self.query("WFMPRE:XZERO?"))
        ymult = float(self.query("WFMPRE:YMULT?"))
        yzero = float(self.query("WFMPRE:YZERO?"))
        yoff = float(self.query("WFMPRE:YOFF?"))

        self._debug_print(f"XINCR: {xincr}, XZERO: {xzero}")
        self._debug_print(f"YMULT: {ymult}, YZERO: {yzero}, YOFF: {yoff}")

        self.write("CURVE?")
        initial = os.read(self.fd, 2)  # Read the '#' and the header length digit
        if not initial.startswith(b'#'):
            raise RuntimeError("Invalid CURVE? response header")

        header_len = int(initial[1:2])
        self._debug_print(f"Header length field: {header_len}")

        header_rest = os.read(self.fd, header_len)
        num_bytes = int(header_rest.decode("ascii"))
        self._debug_print(f"Number of waveform bytes: {num_bytes}")

        # Read the waveform data in chunks until fully received
        raw_data = bytearray()
        while len(raw_data) < num_bytes:
            chunk = os.read(self.fd, num_bytes - len(raw_data))
            if not chunk:
                raise RuntimeError("Unexpected end of data while reading waveform")
            raw_data.extend(chunk)

        self._debug_print(f"Actual bytes read: {len(raw_data)}")

        count = len(raw_data)
        if count != num_bytes:
            print(f"Warning: Expected {num_bytes} bytes, got {count} bytes")
            # raise RuntimeError(f"Expected {num_bytes} bytes, got {count} bytes")

        # Decode as signed 8-bit integers
        y_raw = struct.unpack(f">{count}b", raw_data)
        y_values = [((val - yoff) * ymult + yzero)*1000.0 for val in y_raw]

        wf = Waveform(name)
        wf.progress = self.progress
        wf.set_y_values(y_values)
        wf.offset = xzero * 1e9
        wf.span = (xincr * (count - 1))*1e9
        wf.x_units = "ns"
        wf.y_units = "mV"

        if self.timing:
            elapsed = time.perf_counter() - start
            print(f"[TIMING] get_waveform_data took {elapsed:.3f} sec")

        if self.debug:
            print(f"[DEBUG] Retrieved {count} samples over {wf.span * 1e6:.6f} "+wf.x_units)
            print(f"[DEBUG] First 5 Y values: {[f'{y:.3f}' for y in y_values[:5]]}")
            print(f"[DEBUG] First 5 X values: {[f'{x:.6f}' for x in wf.generate_x_values()[:5]]}")

        return wf


    def set_trigger(self,channel:str, vhigh:float, vlow:float):
        self._progress_print(f"Executing set_trigger {channel}, vhigh={vhigh}, vlow={vlow}")
        self.write(f"TRIGGER:MAIN:MODE NORMAL")

        # omit:
        # set trigger level very close to bottom so if Even cells and significantly different
        # then odd cells, only one will trigger.  This has been observed on short "W" with
        # low p-p amplitude tests.

        RATIO_FM_LOW_TO_HIGH = 0.50
        trigger_level = vlow + RATIO_FM_LOW_TO_HIGH * abs(vhigh-vlow)
        self._debug_print("Set trigger level to: {trigger_level}")
        self.write(f"TRIGGER:MAIN:LEVEL {trigger_level}")
        return trigger_level

    def set_math(self,ch_vhigh:float, ch_vlow:float):
        self._progress_print(f"Executing set_math, ch_vlow={ch_vlow}, ch_vhigh={ch_vhigh}")

        math_position=0.0
        math_scale = self.calc_fit_vpd(2.0*abs(ch_vhigh-ch_vlow))
        self._debug_print(f"Set math vertical scale to {math_scale} V/Div")
        self.write(f"MATH:DEFINE \"CH1-CH2\"")  # set once?
        self.write(f"MATH:VERTICAL:SCALE {math_scale}")
        self.write(f"MATH:VERTICAL:POSITION {math_position/math_scale}")

        return math_position, math_scale

    def set_horizontal_scale(self, time_extent:float):
        self._progress_print(f"Executing set_horizontal_scale, time_extent is: {time_extent}")
        time_position = 0.0
        time_scale = self.calc_fit_tpd(time_extent)

        self._debug_print("==========================")
        self._debug_print(f"Set horizontal scale to {time_scale} Sec/Div")

        self.write(f"HOR:DEL:MODE OFF")
        self.write(f"HOR:MAI:POS {time_position}")
        self.write(f"HOR:MAI:SCA {time_scale}")


        return time_scale

    def align_channel_vertically(self, channel:str ):
        self._progress_print(f"Executing align_channel_vertically, channel is: {channel}")
        SEARCH_VPD = [0.500, 0.200, 0.100, 0.050, 0.020, 0.010, 0.005 ]
        # don't use 2 mv/div because BW changes

        ch_position=0.0
        step=0
        ch_scale=SEARCH_VPD[step]

        self.write(f"{channel}:SCALE {ch_scale}")
        self.write(f"{channel}:POSITION {ch_position/ch_scale}")
        time.sleep(LONG_PAUSE)

        vmin = float(self.query("MEASUREMENT:MEAS1:VALUE?"))
        vmax = float(self.query("MEASUREMENT:MEAS2:VALUE?"))
        vpp = abs(vmax - vmin)
        vmid = (vmin+vmax)/2.0
        self._debug_print(f"SX scale={ch_scale}, vmax={vmax}, vmin={vmin}, vmid={vmid}, vpp={vpp}, pos={ch_position}")

        ch_position = -vmid
        self.write(f"{channel}:POSITION {ch_position/ch_scale}")

        self._debug_print(f"S{step} scale={ch_scale}, vmax={vmax}, vmin={vmin}, vmid={vmid}, vpp={vpp}, pos={ch_position}")

        while step+1<len(SEARCH_VPD) and vpp < (SEARCH_VPD[step+1] * 8.0) * 0.80:
            step +=1

            ch_scale = SEARCH_VPD[step]
            self.write(f"{channel}:SCALE {ch_scale}")
            time.sleep(LONG_PAUSE)

            vmin = float(self.query("MEASUREMENT:MEAS1:VALUE?"))
            vmax = float(self.query("MEASUREMENT:MEAS2:VALUE?"))
            vpp = abs(vmax - vmin)
            vmid = (vmin + vmax) / 2.0

            ch_position = -vmid
            self.write(f"{channel}:POSITION {ch_position/ch_scale}")

            self._debug_print(
                f"S{step} scale={ch_scale}, vmax={vmax}, vmin={vmin}, vmid={vmid}, vpp={vpp}, pos={ch_position}")

        self._debug_print(f"Final scale={ch_scale},  position={ch_position}")
        return ch_position, ch_scale, vmax, vmin

    def autoalign_on_pulse(self, channel,pulse_length_time:float,pulse_count:float):
        self._progress_print("Executing autoalign_on_pulse")

        self.set_horizontal_scale(pulse_length_time * pulse_count)
        time.sleep(MEDIUM_PAUSE)

        self.write(f"TRIGGER:MAIN:MODE AUTO")
        self.write(f"TRIGGER:MAIN:TYPE EDGE")  # one-time?
        self.write(f"TRIGGER:MAIN:EDGE:COUPLING DC")  # one-time?
        self.write("TRIGGER:MAIN:EDGE:SLOPE RISING")  # one-time?
        # time.sleep(SHORT_PAUSE)

        if channel.upper()=="MATH":
            self.write("TRIGGER:MAIN:EDGE:SOURCE CH1")
            self.write("SELECT:CH1 ON")
            self.write("SELECT:CH2 OFF")
            self.write("SELECT:MATH OFF")
            self.write(f"MEASUREMENT:MEAS1:SOURCE CH1")
            self.write(f"MEASUREMENT:MEAS1:TYPE MINIMUM")
            self.write(f"MEASUREMENT:MEAS2:SOURCE CH1")
            self.write(f"MEASUREMENT:MEAS2:TYPE MAXIMUM")
            # time.sleep(SHORT_PAUSE)

            ch_position, ch_scale, vhigh, vlow = self.align_channel_vertically( "CH1" )
            self._progress_print(f"Mirror CH2: pos={ch_position:.3f}, scale={ch_scale:.3f} V/Div")

            self.write("SELECT:CH2 ON")
            self.write(f"CH2:SCALE {ch_scale}")
            self.write(f"CH2:POSITION {ch_position/ch_scale}")
            time.sleep(MEDIUM_PAUSE)

            self.write("SELECT:MATH ON")
            self.set_math(vhigh, vlow)
            self.set_trigger("CH1",vhigh,vlow)
            time.sleep(MEDIUM_PAUSE)
        else:
            self.write("TRIGGER:MAIN:EDGE:SOURCE {channel}")
            self.write(f"SELECT:{channel} ON")
            self.write(f"MEASUREMENT:MEAS1:SOURCE {channel}")
            self.write(f"MEASUREMENT:MEAS1:TYPE MINIMUM")
            self.write(f"MEASUREMENT:MEAS2:SOURCE {channel}")
            self.write(f"MEASUREMENT:MEAS2:TYPE MAXIMUM")
            # time.sleep(SHORT_PAUSE)

            vpos, vscale, vhigh, vlow = self.align_channel_vertically(channel)
            self.set_trigger(channel, vhigh, vlow)

        self.write("ACQUIRE:MODE AVERAGE")
        self.write(f"ACQUIRE:NUMAVG {SCOPE_AVERAGING}")
        time.sleep(VERY_LONG_PAUSE)
