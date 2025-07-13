# PulserCharacterization.py
import os
import shutil
import sys
import time
import csv
import argparse
import tkinter as tk
from tkinter import filedialog

from OscilloscopeDevice import OscilloscopeDevice
from pyBitwiseAutomation import StepscopeDevice, BranchPulse
import matplotlib.pyplot as plt

scope = OscilloscopeDevice()
stepscope = StepscopeDevice()


def map2accessoryLen(length) -> BranchPulse.AccWidth:
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

    return BranchPulse.AccWidth.W8


try:
    # Create parser object
    parser = argparse.ArgumentParser(description="Command-line parser")

    # Add parameters
    parser.add_argument('--ip', "-i", type=str, help='STEPScope IP Address')
    parser.add_argument('--usb', "-u", type=str, default="/dev/usbtmc0", help='USB TMC device path')
    parser.add_argument('--verbose', "-v", action='store_true', help='Enable progress display')
    parser.add_argument("--length", "-l", type=str, help='Pulse length W value or \"sweep\"')
    parser.add_argument("--amplitude", "-a", type=str, help='Pulser amplitude mV value or \"sweep\"')
    parser.add_argument("--attenuator", "-t", type=str, help='Attenuator numeric value (e.g. \"6\")')
    parser.add_argument("--directory", "-d", type=str, help='Results directory path')
    parser.add_argument("--clear", "-c", action='store_true', help='Clear directory before beginning')
    parser.add_argument("--mode", "-m", type=str, help='Pulser mode (e.g. \"Local\" or \"Accessory\")')
    parser.add_argument("--flat", "-f", type=int, default=20, help='Flat spot count of consecutive samples')
    args = parser.parse_args()

    usb_connect = args.usb
    if usb_connect is None:
        usb_connect = input("Enter USB connection (e.g. \"/dev/usbtmc0\")? ")
        print(f"entered:[{usb_connect}]")

    ip_address = args.ip
    if ip_address is None:
        ip_address = input("Enter STEPScope IP address? ")
        print(f"entered:[{ip_address}]")

    if args.verbose:
        scope.progress = True

    scope.connect(usb_connect)
    scope.setup_channel("CH1")
    print("Scope ID:", scope.get_id())

    stepscope.Connect(ip_address)
    serial_number = stepscope.Const.getSN()
    arch = stepscope.Sys.getArchitecture()
    ip = stepscope.Sys.getIP()
    print("Stepscope: " + serial_number + ", " + arch + ", " + ip)

    if args.mode:
        if args.mode.upper() == "ACCESSORY":
            stepscope.Pulse.setMode(stepscope.Pulse.Mode.Accessory)
        elif args.mode.upper() == "LOCAL":
            stepscope.Pulse.setMode(stepscope.Pulse.Mode.Local)
        elif args.mode.upper() == "REMOTE":
            stepscope.Pulse.setMode(stepscope.Pulse.Mode.Remote)
        elif args.mode.upper() == "TRIGGERED":
            stepscope.Pulse.setMode(stepscope.Pulse.Mode.Triggered)

    pulser_mode = stepscope.Pulse.getMode()
    print("STEPScope pulser mode: " + str(pulser_mode))

    using_accessory_flag = bool(pulser_mode == stepscope.Pulse.Mode.Accessory)

    if using_accessory_flag:
        sweep_pulse_lengths_w = [1, 2, 4, 8, 16]
        sweep_amplitudes_mv = [200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700]
    else:
        sweep_amplitudes_mv = [200, 225, 250, 275, 300, 325, 350]
        sweep_pulse_lengths_w = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18,
                                 20, 22, 24, 26, 28, 30, 32]

    pulse_length_value = args.length
    if pulse_length_value is None:
        pulse_length_value = input("Enter pulse length W value (e.g. \"1\" or \"sweep\")? ")
        print(f"entered:[{pulse_length_value}]")

    if pulse_length_value.strip().upper() == "SWEEP":
        pulse_lengths_w = sweep_pulse_lengths_w
    else:
        try:
            number = abs(float(pulse_length_value.strip()))
            pulse_lengths_w = [number]
        except ValueError:
            sys.exit("Error: Missing numeric pulse length value")

    amplitude_value = args.amplitude
    if amplitude_value is None:
        amplitude_value = input("Enter amplitude setting mV value (e.g. \"350\" or \"sweep\")? ")
        print(f"entered:[{amplitude_value}]")

    if amplitude_value.strip().upper() == "SWEEP":
        amplitudes_mv = sweep_amplitudes_mv
    else:
        try:
            number = abs(float(amplitude_value.strip()))
            amplitudes_mv = [number]
        except ValueError:
            sys.exit("Error: Missing numeric mV amplitude value")

    attenuator_value = args.attenuator
    if attenuator_value is None:
        attenuator_value = input("Enter attenuator dB value (e.g. \"0\" or \"12\")? ")
        print(f"entered:[{attenuator_value}]")

    try:
        attenuator_value = abs(float(attenuator_value.strip()))
    except ValueError:
        sys.exit("Error: Missing numeric dB attenuator value")

    results_path = args.directory
    if results_path is None:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        results_path = filedialog.askdirectory(title="Select or Create a Folder for the Results")
        if results_path:
            print(f"entered:[{results_path}]")

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
    # ================================================

    date_time = time.strftime("%y%m%d_%H%M%S")
    file_prefix = results_path + serial_number + "_" + pulser_mode.name
    csv_file_name = file_prefix + ".csv"

    results_ampl_setting = []
    results_length_setting = []
    results_ampl_measurement = []

    run_count = len(pulse_lengths_w) * len(amplitudes_mv)
    run_progress = 0

    for pulse_length in pulse_lengths_w:
        for amplitude in amplitudes_mv:
            # jpg_file_name = file_prefix + "_w" + str(pulse_length) + "_" + str(amplitude) + "mV.jpg"
            jpg_file_name = str(f"{file_prefix}_w{pulse_length:.0f}_{amplitude:.0f}mV.jpg")

            run_progress = run_progress + 1
            print(f"Working on W={pulse_length:.0f}, {amplitude:.0f} mV, {run_progress}-of-{run_count}")
            print(f"Jpeg file: {jpg_file_name}")

            if using_accessory_flag:
                stepscope.Pulse.setAccAmplMV(amplitude)
                stepscope.Pulse.setAccWidth(map2accessoryLen(pulse_length))
            else:
                stepscope.Pulse.setAmplMV(amplitude)
                stepscope.Pulse.setLength(pulse_length)

            scope.align_and_center_single_pulse("CH1")
            waveform = scope.get_waveform_data("CH1", name="CH1 Pulse")

            print(f"Acquire waveform for W={pulse_length:.0f}, {amplitude} mV, {waveform.count} samples")

            plt.figure()
            plt.plot(waveform.generate_x_values(), waveform.y_values, color='blue', linewidth=2, label='Waveform')

            midlevel, minimum, maximum = waveform.get_mid_min_max()
            print(f"Levels: vMin {minimum:.3f}, vMid {midlevel:.3f}, vMax {maximum:.3f}")

            falling = waveform.find_edge_crossing(midlevel, "falling", "last")
            if falling is None:
                print("No falling edge found")
                continue

            falling_n = waveform.calc_index_of_x(falling)
            falling_y = waveform.get_y_value(falling_n)
            print(f"Falling edge: X={falling:.6f}, Y[{falling_n}]={falling_y:.6f}")

            rising = waveform.find_edge_crossing(midlevel, "rising", "last")
            if rising is None:
                print("No rising edge found")
                continue

            rising_n = waveform.calc_index_of_x(rising)
            rising_y = waveform.get_y_value(rising_n)
            print(f"Rising edge: X={rising:.6f}, Y[{rising_n}]={rising_y:.6f}")

            high_flat = waveform.search_flat(falling_n, -1, args.flat, 1.0)
            if high_flat is None:
                print("High flat spot not found")
                continue

            vhigh = waveform.get_y_value(high_flat)
            xhigh = waveform.get_x_value(high_flat)
            print(f"High n={high_flat:.0f}, X={xhigh:.6f}, Y={vhigh:.6f}")
            plt.scatter([xhigh], [vhigh], s=80, color='red', marker='o')

            low_flat = waveform.search_flat(rising_n, -1, args.flat, 1.0)
            if low_flat is None:
                print("Low flat spot not found")
                continue

            vlow = waveform.get_y_value(low_flat)
            xlow = waveform.get_x_value(low_flat)
            print(f"Low n={low_flat:.1f}, X={xlow:.6f}, Y={vlow:.6f}")
            plt.scatter([xlow], [vlow], s=80, color='red', marker='o')

            amplitude_measurement = float(vhigh - vlow)
            print(f"Final amplitude is {amplitude_measurement:.3f}")

            plt.xlabel("Time (" + waveform.x_units + ")")
            plt.ylabel("Voltage (" + waveform.y_units + ")")

            plt.suptitle(
                f"{waveform.name}\n({serial_number}, Pulser {pulser_mode.name}, W={pulse_length:.0f}, {amplitude:.0f} mV)")
            plt.title(f"Amplitude {amplitude_measurement:.3f} " + waveform.y_units)
            plt.grid(True)
            # plt.legend()
            plt.tight_layout()
            plt.savefig(jpg_file_name, format="jpg", dpi=300)
            plt.show()

            results_ampl_setting.append(float(amplitude))
            results_length_setting.append(float(pulse_length))
            results_ampl_measurement.append(float(amplitude_measurement))

    # write results to csv file

    # Open the file explicitly
    print(f"Write results to file: {csv_file_name}")

    file = open(csv_file_name, mode="w", newline='')
    try:
        writer = csv.writer(file)
        writer.writerow(["SN", "DateTime", "Mode", "LenW", "LenNS", "AmplSet", "Meas", "Atten", "MeasNoAtten", ])

        for i in range(len(results_ampl_measurement)):
            without_attenuator = results_ampl_setting[i] / pow(10.0, float(attenuator_value) / 20.0)
            writer.writerow([serial_number, date_time, pulser_mode.name,
                             str(f"{results_length_setting[i]:.0f}"),
                             str(f"{(results_length_setting[i] * 12.8):.3f}"),
                             str(f"{results_ampl_setting[i]:.0f}"),
                             str(f"{results_ampl_measurement[i]:.3f}"),
                             str(f"{attenuator_value:.0f}"),
                             str(f"{without_attenuator:.2f}")]
                            )
    finally:
        file.close()

finally:
    scope.disconnect()
    stepscope.Disconnect()
