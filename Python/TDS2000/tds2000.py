import os
import struct
import time
import array
import fcntl
import select
from fcntl import F_GETFL, F_SETFL

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
            time.sleep(0.2)
            # self.flush_input()
            self._progress_print("Connected to: "+self.query("*IDN?"))
            self.write("*RST")
            time.sleep(0.2)
            self.write("HEAD OFF")
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
        self.flush_input()

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


    def flush_input_new(self, max_wait_s=0.05, poll_step_s=0.005, chunk_size=16384):
        """Drain pending bytes from /dev/usbtmc* without blocking. Returns total bytes flushed."""
        start = time.perf_counter()
        total = 0

        # temporarily put fd in non-blocking mode
        flags = fcntl.fcntl(self.fd, F_GETFL)
        try:
            fcntl.fcntl(self.fd, F_SETFL, flags | os.O_NONBLOCK)

            deadline = start + max_wait_s
            while True:
                # is the fd readable right now?
                r, _, _ = select.select([self.fd], [], [], 0)
                if not r:
                    if time.perf_counter() >= deadline:
                        break
                    time.sleep(poll_step_s)
                    continue

                try:
                    data = os.read(self.fd, chunk_size)
                except BlockingIOError:
                    # readable edge but no bytes yet; try again shortly
                    time.sleep(poll_step_s)
                    continue

                if not data:
                    # EOF or nothing more
                    break
                total += len(data)

        finally:
            # restore original flags
            fcntl.fcntl(self.fd, F_SETFL, flags)

        if self.timing:
            print(f"[TIMING] flush_input() drained {total} bytes in {time.perf_counter() - start:.3f}s")

        return total

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

    def autoset(self,channel="MATH"):
        self._progress_print("Running AutoSet")
        time.sleep(0.100)
        self.write("AUTOSET EXECUTE")
        time.sleep(0.100)
        self.write(f"TRIGGER:MAIN:EDGE:COUPLING DC")

    def next_lower_VPD(self,ch_scale:float)->float:
        VOLTS_PER_DIVISION = [0.005, 0.010, 0.020, 0.050, 0.100, 0.200, 0.500, 1.000, 2.000, 5.000]
        previous = 5.0
        for vpd in VOLTS_PER_DIVISION:
            self._progress_print(f"Search vpd={vpd:.3f}, ch_scale={ch_scale:.3f}")

            if vpd == ch_scale:
                self._progress_print(f"Found using previous={previous}")
                break
            previous = vpd

        return previous

        time_per_division = float((pulse_length_time * pulse_count ) / 10.0)
        time_per_division = self.calc_fit_tpd(pulse_length_time*pulse_count)

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

            if span/0.90 < entire_range:
                #self._progress_print(f"select")
                scale = tpd
                break

        #self._progress_print(f"return {scale}")
        return scale







    def poll_completed(self):
        # self.query("*OPC?")
        # print(f'ALLEV={self.query("ALLEV?")}')

        s=str("DONE")
        tsec=30
        while tsec > 0:
            state = self.query("TRIGGER:STATE?").strip().upper()
            self._debug_print(f"ST={state}")
            if state == "TRIGGER" : # actual sentinel is 9.9e37
                s=str("ST=FOUND")
                break
            time.sleep(0.25)
            tsec -= 0.25

        if tsec == 0:
            s=("ST=TIMEOUT")

        self._debug_print(s)
        time.sleep(0.25) # one extra 250 ms after trigger to settle

    def autoalign_on_pulse(self, channel,pulse_length_time:float,pulse_count:float):
        self._progress_print("Executing autoalign_on_pulse")
        self.autoset(channel)

        #VOLTS_PER_DIVISION = [0.005, 0.010, 0.020, 0.050, 0.100, 0.200, 0.500, 1.000, 2.000, 5.000]

        if channel.upper() == "MATH" :
            # double scale waveform height to ensure triggering

            ch_scale = float(self.query("CH1:SCALE?"))
            ch_position = float(self.query("CH1:POSITION?"))

            ch_scale = self.next_lower_VPD(ch_scale)

            self._progress_print(f"Prep CH1: pos={ch_position:.3f}, scale={ch_scale:.3f} V/Div")
            self.write(f"CH1:SCALE {ch_scale}")

            self._progress_print(f"Prep CH2: pos={ch_position:.3f}, scale={ch_scale:.3f} V/Div")
            self.write(f"CH2:POSITION {ch_position}")
            self.write(f"CH2:SCALE {ch_scale}")

            self.write("ACQUIRE:MODE AVERAGE")
            self.write(f"ACQUIRE:NUMAVG 64")


            self.write("SELECT:CH1 ON")
            self.write("SELECT:CH2 ON")
            self.write("SELECT:MATH ON")
            self.write("TRIGGER:MAIN:EDGE:SOURCE CH1")
            self.write(f"TRIGGER:MAIN:EDGE:COUPLING DC")
            self.write(f"MEASUREMENT:MEAS1:SOURCE CH1")
            self.write(f"MEASUREMENT:MEAS1:TYPE MINIMUM")
            self.write(f"MEASUREMENT:MEAS2:SOURCE CH1")
            self.write(f"MEASUREMENT:MEAS2:TYPE MAXIMUM")
            self.write(f"MEASUREMENT:MEAS3:SOURCE CH2")
            self.write(f"MEASUREMENT:MEAS3:TYPE MINIMUM")
            self.write(f"MEASUREMENT:MEAS4:SOURCE CH2")
            self.write(f"MEASUREMENT:MEAS4:TYPE MAXIMUM")

            self.poll_completed()

            ch1_vmin = float(self.query("MEASUREMENT:MEAS1:VALUE?"))
            ch1_vmax = float(self.query("MEASUREMENT:MEAS2:VALUE?"))
            ch2_vmin = float(self.query("MEASUREMENT:MEAS3:VALUE?"))
            ch2_vmax = float(self.query("MEASUREMENT:MEAS4:VALUE?"))

            ch1_vpp = ch1_vmax-ch1_vmin
            ch1_center = (ch1_vmin+ch1_vmax)/2.0
            ch1_scale = float(self.query("CH1:SCALE?"))
            ch1_position = float(self.query("CH1:POSITION?"))

            self._progress_print(f"Start CH1: vmin={ch1_vmin:.1f}, vmax={ch1_vmax:.1f}, center={ch1_center:.1f}, vpp={ch1_vpp:.1f}")
            #self._progress_print(f"Start CH1: pos={ch1_position:.3f}, scale={ch1_scale:.3f}")

            ch2_vpp = ch2_vmax - ch2_vmin
            ch2_center = (ch2_vmin + ch2_vmax) / 2.0
            ch2_scale = float(self.query("CH2:SCALE?"))
            ch2_position = float(self.query("CH2:POSITION?"))

            self._progress_print(f"Start CH2: vmin={ch2_vmin:.1f}, vmax={ch2_vmax:.1f}, center={ch2_center:.1f}, vpp={ch2_vpp:.1f}")
            #self._progress_print(f"Start CH2:  pos={ch2_position:.3f}, scale={ch2_scale:.3f}")

            max_vpp = max(ch1_vpp,ch2_vpp)
            #self._progress_print(f"CH search for vpd to accommodate {max_vpp/0.90} V")

            scale = self.calc_fit_vpd(max_vpp)

            position_1 = -ch1_center/scale
            position_2 = -ch2_center/scale

            self._progress_print(f"Set CH1: pos={position_1:.3f}, scale={scale:.3f} V/Div")
            self.write(f"CH1:POSITION {position_1}")
            self.write(f"CH1:SCALE {scale}")

            ch1_scale = float(self.query("CH1:SCALE?"))
            ch1_position = float(self.query("CH1:POSITION?"))
            self._progress_print(f"Actual CH1: pos={position_1:.3f}, scale={ch1_scale:.3f} V/Div")


            self._progress_print(f"Set CH2: pos={position_2:.3f}, scale={scale:.3f} V/Div")
            self.write(f"CH2:POSITION {position_2}")
            self.write(f"CH2:SCALE {scale}")


            ch2_scale = float(self.query("CH2:SCALE?"))
            ch2_position = float(self.query("CH2:POSITION?"))
            self._progress_print(f"Actual CH2: pos={position_2:.3f}, ch2_scale={scale:.3f} V/Div")

            math_position = ch1_position - ch2_position
            math_vpp = ch1_vpp + ch2_vpp

            math_scale = self.calc_fit_vpd(math_vpp)

            self._progress_print(f"Set MATH to: pos={math_position:.3f}, scale={math_scale:.3f} V/Div")
            self.write(f"MATH:VERTICAL:POSITION {math_position}")
            self.write(f'MATH:VERTICAL:SCALE {math_scale}')

            math_position = float(self.query(f'MATH:VERTICAL:POSITION?'))
            math_scale = float(self.query(f'MATH:VERTICAL:SCALE?'))
            self._progress_print(f"Actual MATH settings: pos={math_position:.3f}, scale={math_scale:.3f} V/Div")
        else:

            ch_scale = float(self.query(f"{channel}:SCALE?"))
            #ch_position = float(self.query(f"{channel}:POSITION?"))

            ch_scale = self.next_lower_VPD(ch_scale)


                    ## doubling height after AUTOSET helps ensure triggering
            self._progress_print(f"Prep {channel}: scale={ch_scale:.3f} V/Div")
            self.write(f"{channel}:SCALE {ch_scale}")

            self.write("ACQUIRE:MODE AVERAGE")
            self.write(f"ACQUIRE:NUMAVG 64")


            self.write(f"SELECT:{channel} ON")
            self.write(f"TRIGGER:MAIN:EDGE:SOURCE {channel}")
            self.write(f"TRIGGER:MAIN:EDGE:COUPLING DC")
            self.write(f"MEASUREMENT:MEAS1:SOURCE {channel}")
            self.write(f"MEASUREMENT:MEAS1:TYPE MINIMUM")
            self.write(f"MEASUREMENT:MEAS2:SOURCE {channel}")
            self.write(f"MEASUREMENT:MEAS2:TYPE MAXIMUM")

            self.poll_completed_ex()

            ch_vmin = float(self.query("MEASUREMENT:MEAS1:VALUE?"))
            ch_vmax = float(self.query("MEASUREMENT:MEAS2:VALUE?"))
            ch_vpp = ch_vmax-ch_vmin
            ch_center = (ch_vmin+ch_vmax)/2.0
            ch_scale = float(self.query(f"{channel}:SCALE?"))
            ch_position = float(self.query(f"{channel}:POSITION?"))
            self._progress_print(f"Start {channel}: vmin={ch_vmin:.1f}, vmax={ch_vmax:.1f}, center={ch_center:.1f}, vpp={ch_vpp:.1f}")
            self._progress_print(f"Start {channel}: pos={ch_position:.3f}, scale={ch_scale:.3f}")

            scale = self.calc_fit_vpd(ch_vpp)
            position = -ch_center/scale

            self._progress_print(f"Set {channel} position {position:.3f}, scale {scale:.3f}")
            self.write(f"{channel}:POSITION {position}")
            self.write(f"{channel}:SCALE {scale}")

            ch_scale = float(self.query(f"{channel}:SCALE?"))
            ch_position = float(self.query(f"{channel}:POSITION?"))
            self._progress_print(f"Actual CH: pos={ch_position:.3f}, scale={ch_scale:.3f} V/Div")

        #time_per_division = float((pulse_length_time * pulse_count ) / 10.0)
        time_per_division = self.calc_fit_tpd(pulse_length_time*pulse_count)

        self._progress_print(f"Set horizontal scale to: {time_per_division}")
        self.write(f'HORIZONTAL:MAIN:SCALE {time_per_division}')

        actual_time_per_division = float(self.query(f'HORIZONTAL:MAIN:SCALE?'))
        self._progress_print(f"Actual HSCALE is {actual_time_per_division}")
        self._progress_print(f"Actual PULSES is {float((actual_time_per_division*10.0)/pulse_length_time):.3f}")

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
