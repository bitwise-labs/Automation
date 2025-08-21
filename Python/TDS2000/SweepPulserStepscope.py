# SweepPulserTek.py
import argparse
import csv
import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog

import matplotlib.pyplot as plt

from Helper import *
from TDS2000.SSDevice import SSDevice

stepscope = SSDevice()

try:
    # Create parser object
    parser = argparse.ArgumentParser(description="Command-line parser")

    # Add parameters
    parser.add_argument('--ip', "-i", type=str, help='STEPScope IP Address')
    parser.add_argument('--verbose', "-v", action='store_true', help='Enable progress display')
    parser.add_argument('--debug', "-g", action='store_true', help='Enable debugging display')
    parser.add_argument("--length", "-l", type=str, help='Pulse length W value or "sweep"')
    parser.add_argument("--amplitude", "-a", type=str, help='Pulser amplitude mV value or "sweep"')
    parser.add_argument("--attenuator", "-t", type=str, help='Attenuator numeric value (e.g. "6")')
    parser.add_argument("--directory", "-d", type=str, help='Results directory path')
    parser.add_argument("--clear", "-c", action='store_true', help='Clear directory before beginning')
    parser.add_argument("--pulser", "-p", type=str, help='Pulser mode (e.g. "Local" or "Accessory" or "sweep")')
    parser.add_argument("--dsp", "-s", type=str, help='DSP Mode (e.g. "Off" or "Differential" or "sweep")')
    parser.add_argument("--accomp", "-m", type=str, help='AC compensation (e.g. "0" or "sweep")')
    parser.add_argument("--flat", "-f", type=int, default=DEFAULT_FLAT, help='Flat spot count of consecutive samples')
    args = parser.parse_args()

    ip_address = args.ip
    if ip_address is None:
        ip_address = input("Enter STEPScope IP address? ")  # print(f"entered:[{ip_address}]")

    stepscope.Connect(ip_address)
    serial_number = stepscope.Const.getSN()
    arch = stepscope.Sys.getArchitecture()
    ip = stepscope.Sys.getIP()
    print("Stepscope: " + serial_number + ", " + arch + ", " + ip)

    if args.verbose:
        stepscope.progress = True
        # stepscope.timing = True

    if args.debug:
         stepscope.debug = True

    # ============

    mode_value = args.pulser
    if mode_value is None:
        mode_value = input(
            'Enter pulser mode(s) (e.g. "Local", "Accessory", "Local Accessory" or "sweep")? ')  # print(f"entered:[{mode_value}]")

    pulser_mode_values_list = consider_mode_list(mode_value, SWEEP_PULSER_MODES)

    # ============

    dsp_value = args.dsp
    if dsp_value is None:
        dsp_value = input('Enter DSP mode(s) (e.g. "Differential", "Off", "Off Differential" or "sweep")? ')

    # print(f"entered:[{dsp_value}]")

    dsp_values_list = consider_dsp_list(dsp_value, SWEEP_DSP_TYPES)

    # ============

    accomp_value = args.accomp
    if accomp_value is None:
        accomp_value = input(
            'Enter AC Compensation value(s) (e.g. "0", "True", "0 1", or "sweep")? ')  # print(f"entered:[{accomp_value}]")

    accomp_values_list = consider_accomp_list(accomp_value, SWEEP_ACCOMP_TYPES)

    # ============

    pulse_length_value = args.length
    if pulse_length_value is None:
        pulse_length_value = input(
            'Enter pulse length W value(s) (e.g. "1", "8 16 32", or "sweep")? ')  # print(f"entered:[{pulse_length_value}]")

    # ============

    amplitude_value = args.amplitude
    if amplitude_value is None:
        amplitude_value = input(
            'Enter amplitude setting mV value(s) (e.g. "350", "200 250 300", or "sweep")? ')  # print(f"entered:[{amplitude_value}]")

    # ============

    attenuator_value = args.attenuator
    if attenuator_value is None:
        attenuator_value = input(
            "Enter attenuator dB value (e.g. \"0\" or \"12\")? ")  # print(f"entered:[{attenuator_value}]")

    try:
        attenuator_value = abs(float(attenuator_value.strip()))
    except ValueError:
        sys.exit("Error: Missing numeric dB attenuator value")

    # ============

    results_path = args.directory
    if results_path is None:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        results_path = filedialog.askdirectory(
            title="Select or Create a Folder for the Results")  # if results_path:  #     print(f"entered:[{results_path}]")

    if results_path:
        if not results_path.endswith('/'):
            results_path += '/'
    else:
        sys.exit("Error: Missing Results folder")

    print(f"Result directory is: {results_path}")

    if args.clear:
        if os.path.exists(results_path):
            print(f"Clearing Result directory")
            shutil.rmtree(results_path)

    os.makedirs(results_path, exist_ok=True)

    # ============

    date_time = time.strftime("%y%m%d_%H%M%S")
    run_count = 0
    run_progress = 0
    good_count = 0

    # ========================================================================

    for pulser_mode in pulser_mode_values_list:
        for ac_enabled in accomp_values_list:
            for dsp_mode in dsp_values_list:
                using_accessory_flag = bool(pulser_mode == stepscope.Pulse.Mode.Accessory)

                pulse_lengths_w = consider_sweep_int_list("pulse length", pulse_length_value, using_accessory_flag,
                                                          SWEEP_ACCESSORY_PULSES, SWEEP_OTHER_PULSES)

                amplitudes_mv = consider_sweep_int_list("amplitude", amplitude_value, using_accessory_flag,
                                                        SWEEP_ACCESSORY_AMPLITUDES, SWEEP_OTHER_AMPLITUDES)

                run_count += len(amplitudes_mv) * len(pulse_lengths_w)

    # ========================================================================

    stepscope.setup_channel()
    Error = False

    for pulser_mode in pulser_mode_values_list:
        for ac_enabled in accomp_values_list:
            for dsp_mode in dsp_values_list:
                stepscope.Pulse.setMode(pulser_mode)
                stepscope.Calib.setACEnabled(ac_enabled)
                stepscope.Step.Cfg.setDSPMode(dsp_mode)

                using_accessory_flag = bool(pulser_mode == stepscope.Pulse.Mode.Accessory)
                if using_accessory_flag:
                    stepscope.Acc.PUL.setNegEnabled(True)
                    stepscope.Acc.PUL.setPosEnabled(True)
                else:
                    stepscope.Acc.PUL.setNegEnabled(False)
                    stepscope.Acc.PUL.setPosEnabled(False)

                # ============

                pulse_lengths_w = consider_sweep_int_list("pulse length", pulse_length_value, using_accessory_flag,
                                                          SWEEP_ACCESSORY_PULSES, SWEEP_OTHER_PULSES)

                amplitudes_mv = consider_sweep_int_list("amplitude", amplitude_value, using_accessory_flag,
                                                        SWEEP_ACCESSORY_AMPLITUDES, SWEEP_OTHER_AMPLITUDES)

                file_prefix = str(
                    f'{results_path}{serial_number}_{pulser_mode.name}_{attenuator_value:.0f}dB_{dsp_mode.name[:4]}_AC{int(ac_enabled)}')
                csv_file_name = str(f'{file_prefix}.csv')

                results_ampl_setting = []
                results_length_setting = []
                results_ampl_measurement = []

                try:
                    for pulse_length in pulse_lengths_w:
                        for amplitude in amplitudes_mv:
                            run_progress += 1

                            print(
                                f"Working on {run_progress}-of-{run_count}: Pulser {pulser_mode.name}, ACComp {ac_enabled}, DSP {dsp_mode.name}, W{pulse_length:.0f}, {amplitude:.0f} mV")

                            for retry in range(2):
                                if using_accessory_flag:
                                    stepscope.Pulse.setAccAmplMV(amplitude)
                                    stepscope.Pulse.setAccWidth(map2accessoryLen(pulse_length))
                                    time.sleep(0.5)
                                else:
                                    stepscope.Pulse.setAmplMV(amplitude)
                                    stepscope.Pulse.setLength(pulse_length)
                                    time.sleep(0.5)

                                amplitude_measurement = 0
                                stepscope.auto_alignment()

                                expected = (pulse_length * 12.8) * 1.2
                                measured = stepscope.Step.Cfg.getSpanPS()

                                err = abs(expected-measured)
                                twenty_percent = expected * 0.20

                                if err<twenty_percent:
                                    break

                                print(f'Span expected {expected}, Measured {measured}')
                                print("Retry acquisition")


                            waveform = stepscope.get_waveform_data(name="Step Response Pulse")

                            print( f"Acquire waveform for W={pulse_length:.0f}, {amplitude} mV, {waveform.count} samples")

                            try:
                                if plt is not None:
                                    plt.close()

                                plt.figure()
                                plt.plot(waveform.generate_x_values(), waveform.y_values, color='blue', linewidth=2,
                                         label='Waveform')

                                midlevel, minimum, maximum = waveform.get_mid_min_max()
                                print(f"Levels: vMin {minimum:.3f}, vMid {midlevel:.3f}, vMax {maximum:.3f}")

                                # one percent, clamped 0.1 to 1.0 mV range

                                tolerance = max(0.1, min(1.0, abs(maximum - minimum) * 0.01))

                                print(f"Tolerance is: {tolerance:.2f}")

                                falling = waveform.find_edge_crossing(midlevel, "falling", "last")
                                if falling is None:
                                    raise Exception("[No_Falling_Edge_Found]")

                                falling_n = waveform.calc_index_of_x(falling)
                                falling_y = waveform.get_y_value(falling_n)
                                print(f"Falling edge: X={falling:.6f}, Y[{falling_n}]={falling_y:.6f}")

                                rising = waveform.find_edge_crossing(midlevel, "rising", "last")
                                if rising is None:
                                    raise Exception("[No_Rising_Edge_Found]")

                                rising_n = waveform.calc_index_of_x(rising)
                                rising_y = waveform.get_y_value(rising_n)
                                print(f"Rising edge: X={rising:.6f}, Y[{rising_n}]={rising_y:.6f}")

                                high_flat = waveform.search_flat(falling_n, -1, args.flat, tolerance)
                                if high_flat is None:
                                    raise Exception ("[High_Flat_Spot_Not_Found]")

                                vhigh = waveform.get_y_value(high_flat)
                                xhigh = waveform.get_x_value(high_flat)
                                print(f"High n={high_flat:.0f}, X={xhigh:.6f}, Y={vhigh:.6f}")
                                plt.scatter([xhigh], [vhigh], s=80, color='red', marker='o')

                                low_flat = waveform.search_flat(rising_n, -1, args.flat, tolerance)
                                if low_flat is None:
                                    raise Exception( "[Low_Flat_Spot_Not_Found]")

                                vlow = waveform.get_y_value(low_flat)
                                xlow = waveform.get_x_value(low_flat)
                                print(f"Low n={low_flat:.1f}, X={xlow:.6f}, Y={vlow:.6f}")
                                plt.scatter([xlow], [vlow], s=80, color='red', marker='o')

                                amplitude_measurement = float(vhigh - vlow)
                                print(f"Final amplitude is {amplitude_measurement:.3f}")
                                good_count += 1

                                plt.title(f"Amplitude {amplitude_measurement:.3f} {waveform.y_units}")

                            except Exception as e:
                                print(f"Exception encountered: {e}")
                                amplitude_measurement = 0.0
                                plt.title(f"Amplitude {amplitude_measurement:.3f} {waveform.y_units} {e}")

                            finally:
                                jpg_file_name = str(f"{file_prefix}_w{pulse_length:.0f}_{amplitude:.0f}mV.jpg")
                                print(f"Jpeg file: {jpg_file_name}")

                                plt.xlabel("Time (" + waveform.x_units + ")")
                                plt.ylabel("Voltage (" + waveform.y_units + ")")

                                plt.suptitle(
                                    f"{waveform.name} - {serial_number}\n{pulser_mode.name}, Atten {attenuator_value:.0f}dB, DSP {dsp_mode.name[:4]}, AC{int(ac_enabled)}, W{pulse_length:.0f}, {amplitude:.0f} mV")

                                plt.grid(True)
                                # plt.legend()
                                plt.tight_layout()
                                plt.savefig(jpg_file_name, format="jpg", dpi=300)
                                plt.show(block=False)
                                plt.draw()
                                plt.pause(1.0)
                                # plt.close()

                            results_ampl_setting.append(float(amplitude))
                            results_length_setting.append(float(pulse_length))
                            results_ampl_measurement.append(float(amplitude_measurement))

                except Exception as e:
                    Error = True
                    print(f"Exception encountered: {e}")
                finally:
                    file = open(csv_file_name, mode="w", newline='')
                    try:
                        writer = csv.writer(file)
                        writer.writerow(["SN", "DateTime", "Mode", "DSP", "ACComp", "LenW", "AmplSet", "Meas", "Atten"])

                        for i in range(len(results_ampl_measurement)):
                            writer.writerow([serial_number, date_time, pulser_mode.name, dsp_mode.name, str(ac_enabled),
                                             str(f"{results_length_setting[i]:.0f}"),
                                             str(f"{results_ampl_setting[i]:.0f}"),
                                             str(f"{results_ampl_measurement[i]:.3f}"), str(f"{attenuator_value:.0f}")])
                        print(f"Write results to file: {csv_file_name}")
                    finally:
                        file.close()
                if Error:
                    break
            if Error:
                break
        if Error:
            break

    print(f'Completed.  {good_count}-of-{run_count} Okay')

finally:
    stepscope.Disconnect()
