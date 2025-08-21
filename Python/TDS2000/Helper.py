# Helper.py
import sys

from pyBitwiseAutomation import BranchPulse, BranchStepCfg

SWEEP_ACCESSORY_PULSES = [1, 2, 4, 8, 16]
SWEEP_ACCESSORY_AMPLITUDES = [700, 600, 500, 400, 300, 200]
SWEEP_OTHER_PULSES = [1, 2, 4, 8, 16, 32]
SWEEP_OTHER_AMPLITUDES = [350, 300, 250, 200]
SWEEP_PULSER_MODES = [BranchPulse.Mode.Local, BranchPulse.Mode.Accessory]
SWEEP_DSP_TYPES = [BranchStepCfg.DSPMode.Off, BranchStepCfg.DSPMode.Differential]
SWEEP_ACCOMP_TYPES = [True, False]
DEFAULT_FLAT = 12   #20


def consider_accomp_list(arg: str, sweep_list: list) -> list:
    if arg.strip().upper() == "SWEEP":
        return sweep_list
    else:
        tokens = arg.replace(",", " ").split()
        try:
            answer = [
                tok.strip().lower() in ("true", "1", "yes", "y", "t")
                for tok in tokens
            ]
        except ValueError:
            sys.exit("Error: Invalid AC Compensation value(s)")
        return answer



def consider_dsp_list(arg: str, sweep_list: list) -> list:
    answer = None
    if arg.strip().upper() == "SWEEP":
        answer = sweep_list
    else:
        try:
            tokens = arg.replace(",", " ").split()
            answer = [map2DSPmode(tok) for tok in tokens]
        except ValueError:
            sys.exit("Error: Invalid DSP value(s)")
    return answer


def consider_mode_list(arg: str, sweep_list: list) -> list:
    answer = None
    if arg.strip().upper() == "SWEEP":
        answer = sweep_list
    else:
        try:
            tokens = arg.replace(",", " ").split()
            answer = [map2PulserMode(tok) for tok in tokens]
        except ValueError:
            sys.exit("Error: Invalid mode value(s)")
    return answer


def consider_sweep_int_list(title: str, arg: str, using_acc: bool, accessory_list: list, other_list: list) -> list:
    answer = None
    if arg.strip().upper() == "SWEEP":
        answer = accessory_list if using_acc else other_list
    else:
        try:
            tokens = arg.replace(",", " ").split()
            answer = [int(abs(float(tok))) for tok in tokens]
            if not answer:
                raise ValueError
        except ValueError:
            sys.exit(f"Error: Invalid numeric {title} value(s)")
    return answer


def map2accessoryLen(length: int) -> BranchPulse.AccWidth:
    if length is not None:
        if length == 1:
            return BranchPulse.AccWidth.W1
        if length == 2:
            return BranchPulse.AccWidth.W2
        if length == 4:
            return BranchPulse.AccWidth.W4
        if length == 8:
            return BranchPulse.AccWidth.W8
        if length == 16:
            return BranchPulse.AccWidth.W16
    raise ValueError


def map2DSPmode(value: str) -> BranchStepCfg.DSPMode:
    if value is not None:
        if value.strip().upper() == "DIFFERENTIAL":
            return BranchStepCfg.DSPMode.Differential
        if value.strip().upper() == "SEPOSITIVE":
            return BranchStepCfg.DSPMode.SEPositive
        if value.strip().upper() == "SENEGATIVE":
            return BranchStepCfg.DSPMode.SENegative
        if value.strip().upper() == "OFF":
            return BranchStepCfg.DSPMode.Off
    raise ValueError


def map2PulserMode(value: str) -> BranchPulse.Mode:
    if value is not None:
        if value.strip().upper() == "ACCESSORY":
            return BranchPulse.Mode.Accessory
        if value.strip().upper() == "REMOTE":
            return BranchPulse.Mode.Remote
        if value.strip().upper() == "TRIGGERED":
            return BranchPulse.Mode.Triggered
        if value.strip().upper() == "LOCAL":
            return BranchPulse.Mode.Local
    raise ValueError

def decide_run_count(
    x_accomp_values_list:list,
    x_dsp_values_list:list,
    x_pulse_length_value:str,
    x_using_accessory_flag,
    x_SWEEP_ACCESSORY_PULSES:list,
    x_SWEEP_OTHER_PULSES:list,
    x_amplitude_value:str,
    x_SWEEP_ACCESSORY_AMPLITUDES:list,
    x_SWEEP_OTHER_AMPLITUDES:list) -> int:

    run_count = 0
    for ac_enabled in x_accomp_values_list:
        for dsp_mode in x_dsp_values_list:
            pulse_lengths_w = consider_sweep_int_list("pulse length", x_pulse_length_value, x_using_accessory_flag,
                                                      x_SWEEP_ACCESSORY_PULSES, x_SWEEP_OTHER_PULSES)

            amplitudes_mv = consider_sweep_int_list("amplitude", x_amplitude_value, x_using_accessory_flag,
                                                    x_SWEEP_ACCESSORY_AMPLITUDES, x_SWEEP_OTHER_AMPLITUDES)

            run_count += len(amplitudes_mv) * len(pulse_lengths_w)

    return run_count