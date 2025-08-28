# SweepPulserTek.py
import argparse
import csv
import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog

import matplotlib.pyplot as plt

from OscilloscopeDevice import OscilloscopeDevice
from Helper import *
from pyBitwiseAutomation import StepscopeDevice

scope = OscilloscopeDevice()
stepscope = StepscopeDevice()

try:

    # Create parser object
    parser = argparse.ArgumentParser(description="Command-line parser")

    # Add parameters
    parser.add_argument('--ip', "-i", type=str, help='STEPScope IP Address')
    parser.add_argument('--usb', "-u", type=str, default="/dev/usbtmc0", help='USB TMC device path')
    parser.add_argument('--verbose', "-v", action='store_true', help='Enable progress display')
    parser.add_argument('--debug', "-g", action='store_true', help='Enable debugging display')
    parser.add_argument("--length", "-l", type=str, help='Pulse length W value or "sweep"')
    parser.add_argument("--amplitude", "-a", type=str, help='Pulser amplitude mV value or "sweep"')
    parser.add_argument("--attenuator", "-t", type=str, help='Attenuator numeric value (e.g. "6")')
    parser.add_argument("--directory", "-d", type=str, help='Results directory path')
    parser.add_argument("--clear", "-c", action='store_true', help='Clear directory before beginning')
    parser.add_argument("--pulser", "-p", type=str, help='Pulser mode (e.g. "Local" or "Accessory")')
    parser.add_argument("--flat", "-f", type=int, default=DEFAULT_FLAT, help='Flat spot count of consecutive samples')
    parser.add_argument("--diff", action='store_true', help='Use Ch1-Ch2 Differential')
    parser.add_argument("--xgain", "-x", type=float, default=1.0, help='Gain multiplied by readings')
    parser.add_argument("--histogram", "-s", action='store_true',  help='Force histogram level detection')

    args = parser.parse_args()

    usb_connect = args.usb
    if usb_connect is None:
        usb_connect = input("Enter USB connection (e.g. \"/dev/usbtmc0\")? ")  # print(f"entered:[{usb_connect}]")

    ip_address = args.ip
    if ip_address is None:
        ip_address = input("Enter STEPScope IP address? ")  # print(f"entered:[{ip_address}]")

    if args.verbose:
        scope.progress = True

    if args.debug:
        scope.debug = True
        scope.timing = True

    scope.connect(usb_connect)

    waveform_channel = "MATH"
    if args.diff is None:
        args.diff=bool(False)
        waveform_channel = "CH1"

    scope.setup_channel(waveform_channel)

    stepscope.Connect(ip_address)
    serial_number = stepscope.Const.getSN()
    arch = stepscope.Sys.getArchitecture()
    ip = stepscope.Sys.getIP()
    print("Stepscope: " + serial_number + ", " + arch + ", " + ip)

    # ============

    if args.pulser is not None:
        stepscope.Pulse.setMode(map2PulserMode(args.pulser))

    pulser_mode = stepscope.Pulse.getMode()
    print("STEPScope pulser mode: " + str(pulser_mode))

    # ============

    using_accessory_flag = bool(pulser_mode == stepscope.Pulse.Mode.Accessory)

    pulse_length_value = args.length
    if pulse_length_value is None:
        pulse_length_value = input(
            'Enter pulse length W value(s) (e.g. "1", "1 4 8", or "sweep")? ')  # print(f"entered:[{pulse_length_value}]")

    pulse_lengths_w = consider_sweep_int_list("pulse length", pulse_length_value, using_accessory_flag,
                                              SWEEP_ACCESSORY_PULSES, SWEEP_OTHER_PULSES)
    # ============

    amplitude_value = args.amplitude
    if amplitude_value is None:
        amplitude_value = input(
            'Enter amplitude setting mV value(s) (e.g. "350", "200 250 300", or "sweep")? ')  # print(f"entered:[{amplitude_value}]")

    amplitudes_mv = consider_sweep_int_list("amplitude", amplitude_value, using_accessory_flag,
                                            SWEEP_ACCESSORY_AMPLITUDES, SWEEP_OTHER_AMPLITUDES)
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

    # ====================

    gain = float(args.xgain)
    print(f"Gain is: {gain:.3f}")

    date_time = time.strftime("%y%m%d_%H%M%S")
    file_prefix = str(f'{results_path}{serial_number}_{pulser_mode.name}_{attenuator_value:.0f}dB')
    csv_file_name = str(f'{file_prefix}.csv')

    results_ampl_setting = []
    results_length_setting = []
    results_ampl_measurement = []

    run_count = len(pulse_lengths_w) * len(amplitudes_mv)
    run_progress = 0
    good_count = 0
    Error = False

    try:
        for pulse_length in pulse_lengths_w:
            for amplitude in amplitudes_mv:
                run_progress += 1
                print(f"Working on {run_progress}-of-{run_count}: W={pulse_length:.0f}, {amplitude:.0f} mV, ")

                if using_accessory_flag:
                    stepscope.Pulse.setAccAmplMV(amplitude)
                    stepscope.Pulse.setAccWidth(map2accessoryLen(pulse_length))
                    time.sleep(0.5)
                else:
                    stepscope.Pulse.setAmplMV(amplitude)
                    stepscope.Pulse.setLength(pulse_length)
                    time.sleep(0.5)

                scope.autoalign_on_pulse(waveform_channel, pulse_length_time=12.8e-9*pulse_length, pulse_count=1.5)
                waveform = scope.get_waveform_data(waveform_channel, name="Scope Pulse")

                print(f"Acquire waveform for W={pulse_length:.0f}, {amplitude} mV, {waveform.count} samples")
                waveform.appy_gain(gain)

                if plt is not None:
                    plt.close()

                plt.figure()
                # plt.plot(waveform.generate_x_values(), waveform.y_values, color='blue', linewidth=2, label='Waveform')

                try:
                    midlevel, minimum, maximum = waveform.get_mid_min_max()
                    print(f"Levels: vMin {minimum:.3f}, vMid {midlevel:.3f}, vMax {maximum:.3f}")

                    # ==========================

                    rising = waveform.find_edge_crossing(midlevel, "rising", "last")
                    if rising is None:
                        raise Exception("[No_Rising_Edge_Found]")

                    rising_n = waveform.calc_index_of_x(rising)
                    rising_y = waveform.get_y_value(rising_n)
                    print(f"Rising edge: X={rising:.6f}, Y[{rising_n}]={rising_y:.6f}")

                    falling = waveform.find_edge_crossing(midlevel, "falling", "last")
                    if falling is None:
                        raise Exception("[No_Falling_Edge_Found]")

                    falling_n = waveform.calc_index_of_x(falling)
                    falling_y = waveform.get_y_value(falling_n)
                    print(f"Falling edge: X={falling:.6f}, Y[{falling_n}]={falling_y:.6f}")

                    # ==========================

                    # one percent, clamped 0.1 to 1.0 mV range
                    tolerance = max(0.1, min(1.0, abs(maximum - minimum) * 0.01))
                    print(f"Tolerance is: {tolerance:.2f}")

                    vhigh=None
                    vlow=None

                    if abs(maximum-minimum)>20.0 or args.histogram:
                        high_flat = waveform.search_flat(falling_n, -1, args.flat, tolerance)
                        if high_flat is not None:
                            vhigh = waveform.get_y_value(high_flat)
                            xhigh = waveform.get_x_value(high_flat)
                            print(f"High n={high_flat:.0f}, X={xhigh:.6f}, Y={vhigh:.6f}")
                            plt.scatter([xhigh], [vhigh], s=80, color='red', marker='o')

                        low_flat = waveform.search_flat(rising_n, -1, args.flat, tolerance)
                        if low_flat is not None:
                            vlow = waveform.get_y_value(low_flat)
                            xlow = waveform.get_x_value(low_flat)
                            print(f"Low n={low_flat:.1f}, X={xlow:.6f}, Y={vlow:.6f}")
                            plt.scatter([xlow], [vlow], s=80, color='red', marker='o')

                    if vhigh is None or vlow is None :
                        print("Try using histogram")
                        counts, values = waveform.histogram()
                        if counts is None:
                            raise Exception( "[Histogram_Levels_Failed]")

                        segm_x = [waveform.get_x_value(0),waveform.get_x_value(waveform.count-1)]

                        for index in range(len(counts)):
                            if values[index]<midlevel:
                                vlow = values[index]
                                print(f"Low Hist index={index}, Y={vlow:.6f}")
                                plt.plot(segm_x, [vlow,vlow], color='red', linewidth=2, label='vLow')
                                break

                        for index in range(len(counts)):
                            if values[index]>midlevel:
                                vhigh = values[index]
                                print(f"High Hist index={index}, Y={vhigh:.6f}")
                                plt.plot(segm_x, [vhigh,vhigh], color='red', linewidth=2, label='vHigh')
                                break

                    if vhigh is None or vlow is None:
                        raise Exception("[Unable_To_Locate_Levels]")

                    # ==========================

                    amplitude_measurement = float(vhigh - vlow)
                    print(f"Final amplitude is {amplitude_measurement:.3f}")

                    good_count += 1
                    message=""

                except Exception as e:
                    print(f'Error during processing: {str(e)}')
                    message=str(e)
                finally:
                    # jpg_file_name = file_prefix + "_w" + str(pulse_length) + "_" + str(amplitude) + "mV.jpg"
                    jpg_file_name = str(f"{file_prefix}_w{pulse_length:.0f}_{amplitude:.0f}mV.jpg")
                    print(f"Jpeg file: {jpg_file_name}")

                    plt.plot(waveform.generate_x_values(), waveform.y_values, color='blue', linewidth=2,
                             label='Waveform')
                    plt.xlabel("Time (" + waveform.x_units + ")")
                    plt.ylabel("Voltage (" + waveform.y_units + ")")

                    plt.suptitle(
                        f"{waveform.name} - {serial_number}\n{pulser_mode.name}, Atten {attenuator_value:.0f}dB, W{pulse_length:.0f}, {amplitude:.0f} mV")
                    plt.title(f"Amplitude {amplitude_measurement:.3f} {waveform.y_units} {message}")
                    plt.grid(True)
                    # plt.legend()
                    plt.tight_layout()

                    plt.savefig(jpg_file_name, format="jpg", dpi=300)
                    plt.show(block=False)
                    plt.pause(0.25)
                    #plt.close()

                results_ampl_setting.append(float(amplitude))
                results_length_setting.append(float(pulse_length))
                results_ampl_measurement.append(float(amplitude_measurement))

    except Exception as e:
        Error = True
        print(f"Exception encountered: {e}")
    finally:
        print(f"Write results to file: {csv_file_name}")

        if len(results_ampl_measurement) > 0:
            file = open(csv_file_name, mode="w", newline='')
            try:
                writer = csv.writer(file)
                writer.writerow(["SN", "DateTime", "Mode", "LenW", "AmplSet", "Meas", "Atten"])

                for i in range(len(results_ampl_measurement)):
                    writer.writerow(
                        [serial_number, date_time, pulser_mode.name, str(f"{results_length_setting[i]:.0f}"),
                         str(f"{results_ampl_setting[i]:.0f}"), str(f"{results_ampl_measurement[i]:.3f}"),
                         str(f"{attenuator_value:.0f}")])
            finally:
                file.close()

        print(f'Completed.  {good_count}-of-{run_count} Okay')

finally:
    scope.disconnect()
    stepscope.Disconnect()
