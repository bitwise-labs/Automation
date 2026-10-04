# TestPegaDeployLoop.py

from pyBitwiseAutomation import *
import argparse
import time
import math
import statistics
from datetime import datetime


USE_RECOMMENDED_METHOD = False
DEBUG_FLAG = False

# Histogram Y-axis scaling: "log" or "linear"
HISTOGRAM_Y_SCALE = "log"

# Two consecutive empty histogram bins separate timing populations.
# A single empty bin is allowed within a population.
MIN_EMPTY_BINS_BETWEEN_POPULATIONS = 2


# ==============================================================================
# Histogram support
# ==============================================================================

def percentile(values, pct):
    """
    Return an interpolated percentile.
    values must be non-empty.
    """
    data = sorted(values)

    if len(data) == 1:
        return data[0]

    position = (len(data) - 1) * pct
    low = int(math.floor(position))
    high = int(math.ceil(position))

    if low == high:
        return data[low]

    fraction = position - low

    return data[low] + fraction * (data[high] - data[low])


def choose_histogram_bin_width(values):
    """
    Choose a histogram bin width using the Freedman-Diaconis rule,
    with limits to avoid an unreasonable number of bins.
    """
    if len(values) < 2:
        return 0.1

    minimum = min(values)
    maximum = max(values)
    data_range = maximum - minimum

    if data_range <= 0:
        return 0.1

    q1 = percentile(values, 0.25)
    q3 = percentile(values, 0.75)
    iqr = q3 - q1

    if iqr > 0:
        bin_width = 2.0 * iqr / (len(values) ** (1.0 / 3.0))
    else:
        # Fall back to about 20 bins if the distribution
        # has little or no interquartile range.
        bin_width = data_range / 20.0

    # Limit the histogram to no more than about 100 bins
    # and no fewer than about 5 bins.
    minimum_width = data_range / 100.0
    maximum_width = data_range / 5.0

    if minimum_width > 0:
        bin_width = max(bin_width, minimum_width)

    if maximum_width > 0:
        bin_width = min(bin_width, maximum_width)

    # No need for extremely fine timing bins.
    bin_width = max(bin_width, 0.01)

    return bin_width


def build_histogram(values):
    """
    Return:
        bin_edges
        bin_centers
        counts
    """
    if not values:
        return [], [], []

    minimum = min(values)
    maximum = max(values)

    if minimum == maximum:
        width = max(0.01, minimum * 0.01)

        return (
            [minimum - width / 2.0, minimum + width / 2.0],
            [minimum],
            [len(values)]
        )

    width = choose_histogram_bin_width(values)

    start = math.floor(minimum / width) * width
    end = math.ceil(maximum / width) * width

    bin_count = max(
        1,
        int(math.ceil((end - start) / width))
    )

    edges = [
        start + i * width
        for i in range(bin_count + 1)
    ]

    counts = [0] * bin_count

    for value in values:

        index = int((value - start) / width)

        if index >= bin_count:
            index = bin_count - 1

        if index < 0:
            index = 0

        counts[index] += 1

    centers = [
        (edges[i] + edges[i + 1]) / 2.0
        for i in range(bin_count)
    ]

    return edges, centers, counts


def transform_histogram_count(count, y_scale):
    """
    Transform histogram population for display.
    """
    if y_scale == "log":
        return math.log10(count + 1.0)

    return float(count)


def print_ascii_histogram(centers, counts, y_scale):
    """
    Display a rough histogram on the console.
    """
    if not counts:
        return

    print()
    print("Deployment timing histogram:")
    print("Y-axis: " + y_scale)
    print()

    graph_width = 50

    transformed = [
        transform_histogram_count(count, y_scale)
        for count in counts
    ]

    maximum = max(transformed)

    if maximum <= 0:
        maximum = 1.0

    for center, count, transformed_value in zip(
            centers,
            counts,
            transformed
    ):

        if count == 0:
            bar_length = 0
        else:
            bar_length = max(
                1,
                int(round(
                    graph_width
                    * transformed_value
                    / maximum
                ))
            )

        print(
            f"{center:8.3f} s | "
            f"{'#' * bar_length:<50} "
            f"{count:6d}"
        )


# ==============================================================================
# Timing population analysis
# ==============================================================================

def find_timing_populations(values, edges, counts):
    """
    Find separated timing populations in the histogram.

    A timing population begins at a non-empty histogram bin and continues
    until MIN_EMPTY_BINS_BETWEEN_POPULATIONS consecutive empty bins have
    been encountered.  One isolated empty bin is therefore allowed inside
    a population.

    Every population is retained, including populations containing only
    one timing sample.  Statistics are calculated from the original timing
    measurements, not from histogram-bin centers.

    Returns dictionaries containing:
        mean
        stdev
        count
        percent

    sorted by increasing timing.
    """
    if not values or not counts or len(edges) < 2:
        return []

    population_ranges = []
    start_index = None
    last_nonzero_index = None
    empty_run = 0

    # --------------------------------------------------------------------------
    # Identify separated islands of occupied histogram bins.
    # --------------------------------------------------------------------------

    for index, count in enumerate(counts):

        if count > 0:

            if start_index is None:
                start_index = index

            last_nonzero_index = index
            empty_run = 0

        elif start_index is not None:

            empty_run += 1

            if empty_run >= MIN_EMPTY_BINS_BETWEEN_POPULATIONS:

                population_ranges.append(
                    (
                        start_index,
                        last_nonzero_index
                    )
                )

                start_index = None
                last_nonzero_index = None
                empty_run = 0

    # A population can extend through the final histogram bin.
    if start_index is not None:

        population_ranges.append(
            (
                start_index,
                last_nonzero_index
            )
        )

    # --------------------------------------------------------------------------
    # Map each histogram bin to its population.
    # --------------------------------------------------------------------------

    bin_to_population = [None] * len(counts)

    for population_index, (first_bin, last_bin) in enumerate(
            population_ranges
    ):

        for bin_index in range(first_bin, last_bin + 1):
            bin_to_population[bin_index] = population_index

    groups = [
        []
        for _ in population_ranges
    ]

    bin_width = edges[1] - edges[0]

    # --------------------------------------------------------------------------
    # Assign each original timing measurement to its histogram population.
    # --------------------------------------------------------------------------

    for value in values:

        bin_index = int(
            (value - edges[0])
            / bin_width
        )

        if bin_index < 0:
            bin_index = 0

        if bin_index >= len(counts):
            bin_index = len(counts) - 1

        population_index = bin_to_population[bin_index]

        if population_index is not None:
            groups[population_index].append(value)

    # --------------------------------------------------------------------------
    # Calculate statistics from the original timing values.
    # --------------------------------------------------------------------------

    total = len(values)
    populations = []

    for group in groups:

        if not group:
            continue

        mean = statistics.mean(group)

        if len(group) >= 2:
            deviation = statistics.stdev(group)
        else:
            deviation = 0.0

        populations.append(
            {
                "mean": mean,
                "stdev": deviation,
                "count": len(group),
                "percent": (
                    100.0
                    * len(group)
                    / total
                ),
            }
        )

    populations.sort(
        key=lambda item: item["mean"]
    )

    return populations


def report_deployment_timings(values, y_scale):
    """
    Display histogram and numerical timing results.
    """
    print()
    print("============================================================")
    print("Deployment timing analysis")
    print("============================================================")

    if not values:
        print("No successful deployment timing measurements.")
        return

    edges, centers, counts = build_histogram(values)

    # --------------------------------------------------------------------------
    # Histogram first.
    # --------------------------------------------------------------------------

    print_ascii_histogram(
        centers,
        counts,
        y_scale
    )

    # --------------------------------------------------------------------------
    # Overall numerical information.
    # --------------------------------------------------------------------------

    mean = statistics.mean(values)

    if len(values) >= 2:
        stdev = statistics.stdev(values)
    else:
        stdev = 0.0

    print()
    print("Deployment timing statistics:")
    print()
    print(f"Successful timed deployments: {len(values)}")
    print(f"Minimum:                      {min(values):.3f} sec")
    print(f"Maximum:                      {max(values):.3f} sec")
    print(f"Overall mean:                 {mean:.3f} sec")
    print(f"Overall standard deviation:   {stdev:.3f} sec")

    # --------------------------------------------------------------------------
    # Timing populations.
    # --------------------------------------------------------------------------

    populations = find_timing_populations(
        values,
        edges,
        counts
    )

    if populations:

        print()
        print("Timing populations:")
        print()
        print(
            "     Timing                 Population       Percent"
        )
        print(
            "  -------------------       ----------       -------"
        )

        for population in populations:

            print(
                f"  "
                f"{population['mean']:7.3f} +/- "
                f"{population['stdev']:6.3f} sec"
                f"       "
                f"{population['count']:6d}"
                f"          "
                f"{population['percent']:6.2f}%"
            )


# ==============================================================================
# One complete test
# ==============================================================================

def test_the_situation(bitwise_ip, output_source):

    datarate = 18
    ch = 0
    ClkLvl = 300

    first_deploy_success = True
    second_deploy_success = True

    # None means that no valid timing measurement was obtained.
    deploy_elapsed = None

    # Each entry is (attempt_name, local_date_time_string).
    failure_events = []

    Pega = PegaDevice()

    try:

        if DEBUG_FLAG:
            Pega.setDebugging(True)

        Pega.Connect(bitwise_ip)

        serialNumber = Pega.Const.getSN()

        print(
            "Device connected : IP ADDRESS : "
            + str(bitwise_ip)
        )

        print(
            "Device connected : Serial ID  : "
            + str(serialNumber)
        )

        Pega.PG.Amp.setEnabled(
            0,
            0
        )  ## Turn off Ch0 output

        ############## Factory reset

        Pega.RestoreConfiguration("[factory]")

        Pega.Syn.setDataRateGbps(
            10.001
        )  # workaround for "output enabled"

        if USE_RECOMMENDED_METHOD:

            Pega.PG.WaitForClockToSettle(
                10.001 / 2.0
            )

        else:

            time.sleep(2)

        ################ Bitwise basic turn on

        Pega.PG.setLinkMode(
            Pega.PG.LinkMode.Unlinked
        )

        pg_link = Pega.PG.getLinkMode().value

        print(
            "Link mode is  :"
            + str(pg_link)
        )

        Pega.PG.setAllOn(1)

        pg_status = Pega.PG.getAllOn()

        print(
            "Both Ch0 and Ch1 being on is :"
            + str(pg_status)
        )

        Pega.PG.setLinkMode(
            Pega.PG.LinkMode.Unlinked
        )

        ################ Channel Setup

        Pega.PG.Term.setLinkPosNeg(
            ch,
            True
        )

        ch0_link = Pega.PG.Term.getLinkPosNeg(ch)

        print(
            "Ch  link + and - are linked :"
            + str(ch0_link)
        )

        Pega.PG.Term.setType(
            ch,
            Pega.PG.Term.Type.DC
        )

        ch0_term = Pega.PG.Term.getType(ch).value

        print(
            "Ch  termination is:"
            + str(ch0_term)
        )

        Pega.PG.Amp.setAmplMV(
            ch,
            ClkLvl
        )

        Pega.PG.Amp.setCrossPcnt(
            ch,
            50
        )

        Pega.PG.setDelayPS(
            ch,
            0
        )

        Pega.PG.Amp.setOffsMV(
            ch,
            ClkLvl / 2
        )

        ################ Deploy

        # Start timing immediately before the first Deploy attempt.
        #
        # If the first attempt fails and the second attempt succeeds,
        # this timer continues running, so the recorded time represents
        # the combined time required for both attempts.
        #
        # If both attempts fail, deploy_elapsed remains None and the
        # deployment is not included in the timing statistics.

        deploy_start = time.perf_counter()

        try:

            Pega.Patt.Deploy(
                Pega.Patt.PatternChannel.Ch0,
                "Prbs/prbs10.patt",
                0
            )

            # Successful on first attempt.
            deploy_elapsed = (
                time.perf_counter()
                - deploy_start
            )

        except Exception as e:

            first_deploy_success = False
            failure_events.append(
                ("First Deploy", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            print(str(e))
            print("First Deploy ERROR")

            try:

                Pega.Patt.Deploy(
                    Pega.Patt.PatternChannel.Ch0,
                    "Prbs/prbs10.patt",
                    0
                )

                # Successful on second attempt.
                #
                # Note that deploy_start was NOT restarted, so this
                # includes the time consumed by the failed first attempt.
                deploy_elapsed = (
                    time.perf_counter()
                    - deploy_start
                )

            except Exception as e:

                second_deploy_success = False
                failure_events.append(
                    ("Second Deploy", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )

                print(str(e))
                print("Second Deploy ERROR")

                # Complete failure is deliberately not timed.
                deploy_elapsed = None

                return (
                    first_deploy_success,
                    second_deploy_success,
                    deploy_elapsed,
                    failure_events
                )

        ################ Deployment succeeded

        Pega.PG.setPattern(
            ch,
            Pega.PG.Pattern.User
        )

        time.sleep(3)

        ################ Set to external clock source

        # XYZZY - jim's test - there is no ext reference present,
        #         must use internal reference.
        #
        # Pega.Syn.setRefSource(
        #     Pega.Syn.RefSource.ExtRef
        # )

        Pega.Syn.setSource(
            0,
            Pega.Syn.Source.ExtB
        )  # Ch0

        Pega.Syn.setSource(
            1,
            Pega.Syn.Source.ExtB
        )  # Ch1

        Pega.Syn.setSource(
            2,
            Pega.Syn.Source.ExtB
        )  # Calib source

        # Output source is configurable.  Internal preserves Jim's test
        # configuration; ExtB matches the customer configuration.
        if output_source == "extb":
            Pega.Syn.setSource(
                3,
                Pega.Syn.Source.ExtB
            )  # Output source
        else:
            Pega.Syn.setSource(
                3,
                Pega.Syn.Source.Internal
            )  # Output source

        time.sleep(3)

        return (
            first_deploy_success,
            second_deploy_success,
            deploy_elapsed,
            failure_events
        )

    except Exception as e:

        print(
            "ERROR: "
            + str(e)
        )

        return None

    finally:

        Pega.Disconnect()


# ==============================================================================
# Main
# ==============================================================================


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Repeated Pega user-pattern deployment test."
    )

    parser.add_argument(
        "ip_address",
        help="IP address of the Pega device"
    )

    method_group = parser.add_mutually_exclusive_group()

    method_group.add_argument(
        "-original",
        "--original",
        action="store_true",
        help="Use original method: sleep(2) [default]"
    )

    method_group.add_argument(
        "-recommended",
        "--recommended",
        action="store_true",
        help="Use WaitForClockToSettle()"
    )

    parser.add_argument(
        "-hist",
        "--hist",
        choices=("log", "linear"),
        default="log",
        help="Histogram Y-axis scaling (default: log)"
    )

    parser.add_argument(
        "-verbose",
        "--verbose",
        action="store_true",
        help="Display test count, failures and elapsed time"
    )

    parser.add_argument(
        "-debug",
        "--debug",
        action="store_true",
        help="Enable Pega automation debugging"
    )

    parser.add_argument(
        "--output-source",
        type=str.lower,
        choices=("internal", "extb"),
        default="internal",
        help=(
            "Output clock source after deployment: "
            "internal preserves Jim's test configuration; "
            "extb selects ExtB (default: internal)"
        )
    )

    return parser.parse_args()


if __name__ == '__main__':

    args = parse_arguments()

    USE_RECOMMENDED_METHOD = args.recommended
    DEBUG_FLAG = args.debug
    HISTOGRAM_Y_SCALE = args.hist

    ip = args.ip_address
    verbose = args.verbose
    output_source = args.output_source

    print("Configuration:")
    print(
        "  IP Address:              "
        + ip
    )
    print(
        "  Verbose:                 "
        + str(verbose)
    )
    print(
        "  Debug:                   "
        + str(DEBUG_FLAG)
    )
    print(
        "  Use recommended method:  "
        + str(USE_RECOMMENDED_METHOD)
    )
    print(
        "  Histogram Y-axis:        "
        + HISTOGRAM_Y_SCALE
    )
    print(
        "  Output source:           "
        + output_source
    )
    print()

    print("Press Ctrl-C to stop.")
    print()

    total_tests = 0
    first_deploy_failures = 0
    second_deploy_failures = 0

    # Contains one elapsed-time measurement for every deployment
    # that eventually succeeded.
    deployment_timings = []

    # Entries are (test_number, attempt_name, local_date_time_string).
    failure_events = []

    start_time = time.perf_counter()

    try:

        while True:

            result = test_the_situation(
                ip,
                output_source
            )

            if result is None:
                break

            (
                first_success,
                second_success,
                deploy_elapsed,
                test_failure_events
            ) = result

            total_tests += 1

            if not first_success:
                first_deploy_failures += 1

            if not second_success:
                second_deploy_failures += 1

            for attempt_name, failure_time in test_failure_events:
                failure_events.append(
                    (
                        total_tests,
                        attempt_name,
                        failure_time
                    )
                )

            # Only successful deployments contribute timing samples.
            if deploy_elapsed is not None:

                deployment_timings.append(
                    deploy_elapsed
                )

            if verbose:

                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                hours = int(
                    elapsed // 3600
                )

                minutes = int(
                    (elapsed % 3600) // 60
                )

                seconds = elapsed % 60

                print(
                    f"Tests: {total_tests}   "
                    f"First failures: "
                    f"{first_deploy_failures}   "
                    f"Second failures: "
                    f"{second_deploy_failures}   "
                    f"Timed: "
                    f"{len(deployment_timings)}   "
                    f"Elapsed: "
                    f"{hours:02d}:"
                    f"{minutes:02d}:"
                    f"{seconds:05.2f}"
                )

                if deploy_elapsed is not None:

                    print(
                        "Last successful deployment: "
                        f"{deploy_elapsed:.3f} sec"
                    )

                print()

    except KeyboardInterrupt:

        print(
            "\nCtrl-C encountered"
        )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    hours = int(
        elapsed // 3600
    )

    minutes = int(
        (elapsed % 3600) // 60
    )

    seconds = elapsed % 60

    print()
    print("Final results:")

    print(
        f"Tests completed:        "
        f"{total_tests}"
    )

    print(
        f"First Deploy failures:  "
        f"{first_deploy_failures}"
    )

    print(
        f"Second Deploy failures: "
        f"{second_deploy_failures}"
    )

    print(
        f"Timed deployments:      "
        f"{len(deployment_timings)}"
    )

    print(
        f"Elapsed time:           "
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:05.2f}"
    )

    if failure_events:
        print()
        print("Deployment failure times:")
        print()
        print("  Test    Attempt          Local date/time")
        print("  ------  ---------------  -------------------")

        for test_number, attempt_name, failure_time in failure_events:
            print(
                f"  {test_number:6d}  "
                f"{attempt_name:<15}  "
                f"{failure_time}"
            )

    report_deployment_timings(
        deployment_timings,
        HISTOGRAM_Y_SCALE
    )


# EOF