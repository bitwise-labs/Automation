from math import floor, ceil


class Waveform:
    def __init__(self, name="no_name"):
        self._name = name
        self._offset = 0.0
        self._span = 0.0
        self._y_values = []
        self._debug = False
        self._progress = False
        self._x_units = ""
        self._y_units = ""

    @property
    def x_units(self):
        return self._x_units

    @x_units.setter
    def x_units(self, value: bool):
        self._x_units = str(value)

    @property
    def y_units(self):
        return self._y_units

    @y_units.setter
    def y_units(self, value: bool):
        self._y_units = str(value)

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = bool(value)

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

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        self._name = str(val)

    @property
    def count(self):
        return len(self._y_values)

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, val):
        self._offset = float(val)
        self._debug_print("Waveform offset={self._offset:.6e}")

    @property
    def span(self):
        return self._span

    @span.setter
    def span(self, val):
        self._span = float(val)
        self._debug_print("Waveform span={self._span:.6e}")

    @property
    def y_values(self):
        return self._y_values.copy()

    def get_y_value(self, index):
        index = floor(index)
        index = min(self.count - 1, index)
        index = max(0, index)
        return float(self._y_values[index])

    def get_x_value(self, index):
        index = min(self.count - 1, index)
        index = max(0, index)
        index = floor(index)
        dx = self._span / (self.count - 1)
        return float(self._offset + index * dx)

    def set_y_values(self, arr):
        self._y_values = list(map(float, arr))

    def print(self, pre_message="Waveform:"):
        if pre_message is not None:
            print(pre_message)

        print(f" Name: {self.name}")
        print(f" Offset: {self.offset:.3f} {self.x_units}")
        print(f" Span: {self.span:.6f} {self.x_units}")
        print(f" Count: {len(self.y_values)}")
        print(f" Y-units: {self.y_units}")

    def generate_x_values(self):
        self._debug_print("generate_x_values")

        count = len(self._y_values)
        if count <= 1 or self._span <= 0.0:
            return []

        dx = self._span / (count - 1)
        self._debug_print(f"count={count}, offset={self.offset:.6f}, span={self.span:.6f}, dx={dx:.6f}")

        return [self._offset + i * dx for i in range(count)]

    def generate_x_indexes(self):
        self._debug_print("generate_x_indexes")
        count = len(self._y_values)
        if count <= 1 or self._span <= 0.0:
            return []
        return list(range(count))

    def get_mid_min_max(self):
        self._progress_print("Find minimum, midpoint, maximum")
        if not self._y_values:
            raise ValueError("Waveform has no data")
        min_val = min(self._y_values)
        max_val = max(self._y_values)
        mid_val = 0.5 * (min_val + max_val)
        self._debug_print(f"Min: {min_val}, Max: {max_val}, Mid: {mid_val}")
        return mid_val, min_val, max_val

    def find_edge_crossing(self, threshold, edge_type="falling", direction="first"):

        self._progress_print(f"Find {direction} {edge_type} edge at threshold {threshold:.6f}")

        if edge_type not in ("falling", "rising"):
            raise ValueError("edge_type must be 'falling' or 'rising'")
        if direction not in ("first", "last"):
            raise ValueError("direction must be 'first' or 'last'")

        y = self._y_values
        x = self.generate_x_values()
        indices = range(len(y))
        first_flag = True
        prior_i = 0
        if direction == "last":
            indices = reversed(indices)

        for i in indices:
            self._debug_print(f" y[{i}]={y[i]:.6f}, x[{i}]={x[i]:.6e}")

            if first_flag:
                first_flag = False
                prior_i = i
                continue

            prev = y[prior_i]
            curr = y[i]

            if direction == "first" and edge_type == "falling" and prev > threshold >= curr:
                edge_label = "falling"
            elif direction == "last" and edge_type == "falling" and prev < threshold <= curr:
                edge_label = "falling"
            elif direction == "first" and edge_type == "rising" and prev < threshold <= curr:
                edge_label = "rising"
            elif direction == "last" and edge_type == "rising" and prev > threshold >= curr:
                edge_label = "rising"
            else:
                prior_i = i
                continue

            dy = curr - prev
            dx = x[i] - x[prior_i]

            if dy != 0:
                x_val = x[prior_i] + ((threshold - prev) * dx) / dy
            else:
                x_val = (x[i] + x[prior_i]) / 2.0

            self._debug_print(f"Interpolated {edge_label} edge X: {x_val:.6e}")
            return x_val

        self._debug_print(" Warning: None found")
        return None

    def calc_x_of_index(self, index):
        count = len(self._y_values)
        index = max(0, min(index, count - 1))
        x_val = self._offset + index * (self._span / (count - 1))
        self._debug_print(f"Index {index} maps to X = {x_val:.6e}")
        return x_val

    def calc_index_of_x(self, x_value):
        count = len(self._y_values)
        if count < 2 or self._span == 0:
            return 0
        delta_x = self._span / (count - 1)
        index = int(round((x_value - self._offset) / delta_x))
        index = max(0, min(index, count - 1))
        self._debug_print(f"X {x_value:.6e} maps to index = {index}")
        return index

    def search_flat(self, start_index, direction, required_count=20, tolerance=1e-6):
        """
        Search for a flat region starting at `start_index` and moving in `direction` (+1 or -1),
        where `required_count` successive samples are within `tolerance` of each other.

        Returns the index of the first sample in the flat region, or None if not found.
        """
        self._progress_print(
            f"Searching flat from index {start_index}, direction {direction}, count {required_count}, tolerance {tolerance}")

        if direction not in (+1, -1):
            raise ValueError("Direction must be +1 or -1")

        y = self._y_values
        n = len(y)

        i = start_index

        while 0 <= i < n - (required_count - 1) * abs(direction):
            flat = True
            base_value = y[i]

            for j in range(1, required_count):
                neighbor_index = i + j * direction
                if not (0 <= neighbor_index < n):
                    flat = False
                    break

                diff = abs(y[neighbor_index] - base_value)

                if j > 1:
                    self._debug_print(f" Y[{neighbor_index}]={y[neighbor_index]:.6f}, diff={diff:.6f}")

                if diff > tolerance:
                    flat = False
                    self._debug_print(
                        f" Break at i={i}, j={j}, y[{neighbor_index}]={y[neighbor_index]:.6f}, diff={diff:.6f}")
                    break

            if flat:
                self._debug_print(f"Found flat region starting at index {i}")
                i = max(0, min(n - 1, floor(i + direction * required_count / 2)))
                return i

            i += direction

        self._debug_print("No flat region found")
        return None
