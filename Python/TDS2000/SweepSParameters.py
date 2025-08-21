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
    parser.add_argument("--dsp", "-s", type=str, help='DSP Mode (e.g. "Off" or "Differential" or "sweep")')
    parser.add_argument("--accomp", "-m", type=str, help='AC compensation (e.g. "0" or "sweep")')
    parser.add_argument("--s11","-1", action='store_true',help='Run S11 analysis')
    parser.add_argument("--s21","-2", action='store_true',help='Run S21 analysis')

    args = parser.parse_args()

    if (not args.s11) and (not args.s21):
        print("Need to select \"--s11\" and/or \"--s21\" on the command-line")
        exit(0)

    ip_address = args.ip
    if ip_address is None:
        ip_address = input("Enter STEPScope IP address? ")

    if args.verbose:
        print(f"ip_address:[{ip_address}]")

    stepscope.Connect(ip_address)
    serial_number = stepscope.Const.getSN()
    arch = stepscope.Sys.getArchitecture()
    ip = stepscope.Sys.getIP()
    print("Stepscope: " + serial_number + ", " + arch + ", " + ip)

    if args.verbose:
        stepscope.progress = True
        stepscope.timing = True

    if args.debug:
         stepscope.debug = True

    # ============

    dsp_value = args.dsp
    if dsp_value is None:
        dsp_value = input('Enter DSP type(s) (e.g. "Differential", "Off", "Off Differential" or "sweep")? ')

    dsp_values_list = consider_dsp_list(dsp_value, SWEEP_DSP_TYPES)
    if args.verbose:
        print(f"dsp_values_list:[{dsp_values_list}]")

    # ============

    accomp_value = args.accomp
    if accomp_value is None:
        accomp_value = input(
            'Enter AC Compensation value(s) (e.g. "0", "True", "0 1", or "sweep")? ')  # print(f"entered:[{accomp_value}]")

    accomp_values_list = consider_accomp_list(accomp_value, SWEEP_ACCOMP_TYPES)
    if args.verbose:
        print(f"accomp_values_list:[{accomp_values_list}]")
    # ============

    pulse_length_value = args.length
    if pulse_length_value is None:
        pulse_length_value = input(
            'Enter pulse length W value(s) (e.g. "1", "8 16 32", or "sweep")? ')  # print(f"entered:[{pulse_length_value}]")

    if args.verbose:
        print(f"pulse_length_value:[{pulse_length_value}]")
    # ============

    amplitude_value = args.amplitude
    if amplitude_value is None:
        amplitude_value = input(
            'Enter amplitude setting mV value(s) (e.g. "350", "200 250 300", or "sweep")? ')  # print(f"entered:[{amplitude_value}]")

    if args.verbose:
        print(f"amplitude_value:[{amplitude_value}]")

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

    # ============
    attenuator_values_list=[]

    attenuator_value = args.attenuator
    if attenuator_value is None:

    try:
        attenuator_value = abs(float(attenuator_value.strip()))
    except ValueError:
        sys.exit("Error: Missing numeric dB attenuator value")

    # ========================================================================
    NeedsCalibrationS11=bool(False)
    NeedsCalibrationS21=bool(False)

    while True:
        attenuator_value = input(
            "Enter DUT attenuator dB value or \"exit\" (e.g. \"0\" or \"12\")? ")

        if args.verbose:
            print(f"attenuator_value:[{attenuator_value}]")

        if attenuator_value.upper()=="EXIT":
            break

        if args.s21:
            pulser_mode = stepscope.Pulse.Mode.Accessory
            using_accessory_flag = bool( pulser_mode == stepscope.Pulse.Mode.Accessory)

            run_count = decide_run_count(
                            accomp_values_list,
                            dsp_values_list,
                            pulse_length_value,
                            using_accessory_flag,
                            SWEEP_ACCESSORY_PULSES,
                            SWEEP_OTHER_PULSES,
                            amplitude_value,
                            SWEEP_ACCESSORY_AMPLITUDES,
                            SWEEP_OTHER_AMPLITUDES)

            stepscope.setup_channel()
            Error = False

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
            stepscope.Pulse.setMode(pulser_mode)

            


            try:
                for pulse_length in pulse_lengths_w:
                    for amplitude in amplitudes_mv:
                        print("run calibration if needed")



                        for ac_enabled in accomp_values_list:
                            for dsp_mode in dsp_values_list:

                            run_progress += 1

                            print(
                                f"Working on {run_progress}-of-{run_count}: Pulser {pulser_mode.name}, ACComp {ac_enabled}, DSP {dsp_mode.name}, W{pulse_length:.0f}, {amplitude:.0f} mV")

                            stepscope.Calib.setACEnabled(ac_enabled)
                            stepscope.Step.Cfg.setDSPMode(dsp_mode)

                            if using_accessory_flag:
                                stepscope.Acc.PUL.setNegEnabled(True)
                                stepscope.Acc.PUL.setPosEnabled(True)
                            else:
                                stepscope.Acc.PUL.setNegEnabled(False)
                                stepscope.Acc.PUL.setPosEnabled(False)

                            if using_accessory_flag:
                                stepscope.Pulse.setAccAmplMV(amplitude)
                                stepscope.Pulse.setAccWidth(map2accessoryLen(pulse_length))
                                time.sleep(0.5)
                            else:
                                stepscope.Pulse.setAmplMV(amplitude)
                                stepscope.Pulse.setLength(pulse_length)
                                time.sleep(0.5)









                            # jpg_file_name = file_prefix + "_w" + str(pulse_length) + "_" + str(amplitude) + "mV.jpg"
                            jpg_file_name = str(f"{file_prefix}_w{pulse_length:.0f}_{amplitude:.0f}mV.jpg")
                            print(f"Jpeg file: {jpg_file_name}")

                            plt.xlabel("Time (" + waveform.x_units + ")")
                            plt.ylabel("Voltage (" + waveform.y_units + ")")

                            plt.suptitle(
                                f"{waveform.name} - {serial_number}\n{pulser_mode.name}, Atten {attenuator_value:.0f}dB, DSP {dsp_mode.name[:4]}, AC{int(ac_enabled)}, W{pulse_length:.0f}, {amplitude:.0f} mV")
                            plt.title(f"Amplitude {amplitude_measurement:.3f} {waveform.y_units}")
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

                            good_count += 1

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
