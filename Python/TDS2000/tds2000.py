import os
import struct
import time
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

    def connect(self, scope_path="/dev/usbtmc0"):
        self.scope_path = scope_path
        self._progress_print(f"Connecting to scope at {scope_path}")
        try:
            self.fd = os.open(self.scope_path, os.O_RDWR)
            self.write("*RST\n")
            self.write("HEAD OFF\n")
            self.query("*OPC?\n")
        except PermissionError:
            raise PermissionError(f"Cannot open {scope_path}: check permissions.")
        except FileNotFoundError:
            raise FileNotFoundError(f"{scope_path} not found. Is the scope connected?")
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

        if self.timing:
            start = time.perf_counter()

        self._debug_print(f"Writing: {cmd.strip()}")
        os.write(self.fd, cmd.encode())

        if self.timing:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"[TIMING] \"{cmd.strip()}\" took {elapsed_ms:.2f} ms")

    def query(self, cmd, delay=0.0, readlen=1024):
        """Send a SCPI query and return the response."""
        if self.fd is None:
            raise ConnectionError("Oscilloscope not connected.")
        self.flush_input()

        clean_cmd = cmd.strip()
        self._debug_print(f"Querying: {clean_cmd}")

        if self.timing:
            start = time.perf_counter()

        os.write(self.fd, (clean_cmd + "\n").encode())
        time.sleep(delay)
        response = os.read(self.fd, readlen).decode(errors='ignore').strip()

        if self.timing:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"[TIMING] \"{clean_cmd}\" took {elapsed_ms:.2f} ms")

        self._debug_print(f"Response: {response}")

        return response

    def flush_input(self, max_attempts=5):
        self._debug_print("Flushing input buffer")
        try:
            for _ in range(max_attempts):
                data = os.read(self.fd, 512)
                if not data:
                    break
        except (BlockingIOError, TimeoutError):
            pass

    def autoset(self):
        self._progress_print("Running AutoSet")
        self.write("AUTOSET EXECUTE\n")
        self.query("*OPC?\n")
        return True

    def get_id(self):
        self._progress_print("Getting scope ID")
        return self.query("*IDN?\n")

    def set_averaging(self, count=128):
        self._progress_print(f"Setting averaging to {count}")
        if count <= 1:
            self.write("ACQUIRE:MODE SAMPLE\n")
        elif 2 <= count <= 512:
            self.write("ACQUIRE:MODE AVERAGE\n")
            self.write(f"ACQUIRE:NUMAVG {int(count)}\n")
        else:
            raise ValueError("Averaging count must be between 2 and 512 (or <=1 to disable).")

    def show_single_pulse_after_autoset(self, multiplier=5):
        self._progress_print("Executing show_single_pulse_after_autoset")
        self.autoset()
        horiz = self.query("HORIZONTAL:SCALE?\n").strip()
        current_scale = float(horiz)
        new_scale = current_scale / multiplier
        self.write(f"HORIZONTAL:SCALE {new_scale:.6e}\n")
        position = self.query("HORIZONTAL:POSITION?\n").strip()
        current_position = float(position)
        new_position = current_position - 2.5 * new_scale
        self.write(f"HORIZONTAL:POSITION {new_position:.6e}\n")
        return new_scale

    def scale_vertical_and_recenter(self, channel="CH1", gain=2.0):
        self._progress_print(f"Scaling {channel} by gain factor: {gain}")
        scale_str = self.query(f"{channel}:SCALE?\n").strip()
        current_scale = float(scale_str)
        trig_str = self.query("TRIGGER:MAIN:LEVEL?\n").strip()
        trigger_voltage = float(trig_str)
        new_scale = max(current_scale / gain, 2e-3)
        self.write(f"{channel}:SCALE {new_scale:.6e}\n")
        new_position = -trigger_voltage / new_scale
        self.write(f"{channel}:POSITION {new_position:.6f}\n")
        return new_scale, new_position

    def set_time_cursors(self, channel="CH1", pos1_pct=0.20, pos2_pct=0.70):
        self._progress_print(f"Setting time cursors at {pos1_pct * 100:.1f}% and {pos2_pct * 100:.1f}% of view")
        self.write("CURSOR:FUNCTION VBARS\n")
        self.write("CURSOR:SELECT:SOURCE " + channel)
        self.write("CURSOR:TYPE TIME\n")
        self.write("CURSOR:SELECT BOTH\n")
        center_sec = float(self.query("HORIZONTAL:POSITION?\n").strip())
        scale_sec = float(self.query("HORIZONTAL:SCALE?\n").strip())
        full_width = 10.0 * scale_sec
        left_edge = center_sec - full_width / 2.0
        time1 = left_edge + pos1_pct * full_width
        time2 = left_edge + pos2_pct * full_width
        self.write(f"CURSOR:VBARS:POSITION1 {time1:.6e}\n")
        self.write(f"CURSOR:VBARS:POSITION2 {time2:.6e}\n")

    def get_cursor_voltages(self):
        self._progress_print("Reading voltage at cursor positions")
        self.write("CURSOR:TYPE TIME\n")
        self.write("CURSOR:SELECT BOTH\n")
        v1_str = self.query("CURSOR:VBARS:HPOS1?\n").strip()
        v2_str = self.query("CURSOR:VBARS:HPOS2?\n").strip()
        v1 = float(v1_str)
        v2 = float(v2_str)
        return v1, v2

    def get_waveform_data(self, channel="CH1", name="no_name"):
        self._progress_print(f"Acquiring waveform from {channel}")
        if self.timing:
            start = time.perf_counter()

        self.write(f"DATA:SOURCE {channel}")
        self.write("DATA:ENCdg RIBinary")  # Signed integer, MSB first
        self.write("DATA:WIDTH 1")  # 1 byte per sample
        self.write("WFMPRE:BYTE_NR 1")

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
