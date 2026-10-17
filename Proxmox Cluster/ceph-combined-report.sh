#!/usr/bin/env bash
set -u
set -o pipefail
umask 077

BASE_DIR=${1:-/var/log/ceph-validation}
OUT=${2:-$BASE_DIR/reports/ceph_combined_report_$(date +%F_%H-%M-%S).txt}
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

mkdir -p "$(dirname "$OUT")"
shopt -s nullglob
LOGS=("$BASE_DIR"/ceph_validation_*.log)

if (( ${#LOGS[@]} == 0 )); then
    echo "No Ceph validation logs found in $BASE_DIR" >&2
    exit 1
fi

extract_last() {
    local pattern=$1 file=$2
    grep -E "$pattern" "$file" | tail -n 1 | sed -E 's/^[[:space:]]+//'
}

{
    echo "======================================================================"
    echo "                  COMBINED CEPH VALIDATION REPORT"
    echo "======================================================================"
    echo "Generated       : $(date)"
    echo "Host            : $(hostname -f 2>/dev/null || hostname)"
    echo "Source directory: $BASE_DIR"
    echo "Log files       : ${#LOGS[@]}"
    echo

    echo "EXECUTIVE SUMMARY"
    echo "----------------------------------------------------------------------"
    printf "%-20s %-11s %-8s %-8s %-8s %-20s\n" \
           "RUN" "MODE" "PASS" "FAIL" "SKIP" "OVERALL"
    printf "%-20s %-11s %-8s %-8s %-8s %-20s\n" \
           "--------------------" "-----------" "--------" "--------" "--------" "--------------------"

    total_pass=0
    total_fail=0
    total_skip=0
    successful_runs=0
    attention_runs=0

    for log in "${LOGS[@]}"; do
        run=$(basename "$log" .log | sed 's/^ceph_validation_//')
        mode=$(grep -E '^Mode:' "$log" | tail -1 | awk '{print $2}')
        [[ -n ${mode:-} ]] || mode=$(grep -E 'Starting Ceph Validation Suite' "$log" >/dev/null && echo "unknown" || echo "unknown")
        pass_count=$(grep -E '^PASS:' "$log" | tail -1 | awk '{print $2}')
        fail_count=$(grep -E '^FAIL:' "$log" | tail -1 | awk '{print $2}')
        skip_count=$(grep -E '^SKIP:' "$log" | tail -1 | awk '{print $2}')
        overall=$(grep -E '^Overall:' "$log" | tail -1 | cut -d: -f2- | sed 's/^[[:space:]]*//')

        [[ ${pass_count:-} =~ ^[0-9]+$ ]] || pass_count=$(grep -c '\[PASS\]' "$log" || true)
        [[ ${fail_count:-} =~ ^[0-9]+$ ]] || fail_count=$(grep -c '\[FAIL\]' "$log" || true)
        [[ ${skip_count:-} =~ ^[0-9]+$ ]] || skip_count=$(grep -c '\[SKIP\]' "$log" || true)
        [[ -n ${overall:-} ]] || { (( fail_count == 0 )) && overall="SUCCESS" || overall="ATTENTION REQUIRED"; }

        total_pass=$((total_pass + pass_count))
        total_fail=$((total_fail + fail_count))
        total_skip=$((total_skip + skip_count))
        if [[ $overall == SUCCESS ]]; then
            successful_runs=$((successful_runs + 1))
        else
            attention_runs=$((attention_runs + 1))
        fi

        printf "%-20s %-11s %-8s %-8s %-8s %-20s\n" \
               "$run" "$mode" "$pass_count" "$fail_count" "$skip_count" "$overall"
    done

    echo
    echo "Aggregate PASS   : $total_pass"
    echo "Aggregate FAIL   : $total_fail"
    echo "Aggregate SKIP   : $total_skip"
    echo "Successful runs  : $successful_runs"
    echo "Attention runs   : $attention_runs"
    echo

    echo "DETAILED RUNS"
    echo "======================================================================"

    run_no=0
    for log in "${LOGS[@]}"; do
        run_no=$((run_no + 1))
        echo
        echo "[$run_no] $(basename "$log")"
        echo "----------------------------------------------------------------------"

        start=$(grep -m1 -E '^\[[0-9]{4}-[0-9]{2}-[0-9]{2} ' "$log" | sed -E 's/^\[([^]]+)\].*/\1/')
        mode=$(grep -E '^Mode:' "$log" | tail -1 | awk '{print $2}')
        pool=$(grep -E '^Pool:' "$log" | tail -1 | cut -d: -f2- | sed 's/^[[:space:]]*//')
        baseline=$(awk '/^Baseline health:/{getline; print; exit}' "$log")
        final=$(awk '/^Final health:/{getline; print; exit}' "$log")
        runtime=$(grep -E '^Runtime:' "$log" | tail -1 | cut -d: -f2- | sed 's/^[[:space:]]*//')
        overall=$(grep -E '^Overall:' "$log" | tail -1 | cut -d: -f2- | sed 's/^[[:space:]]*//')

        echo "Start time      : ${start:-not recorded}"
        echo "Mode            : ${mode:-not recorded}"
        echo "Pool            : ${pool:-N/A}"
        echo "Baseline health : ${baseline:-not recorded}"
        echo "Final health    : ${final:-not recorded}"
        echo "Runtime         : ${runtime:-not recorded}"
        echo "Overall         : ${overall:-not recorded}"

        echo
        echo "Test results:"
        grep -E '\[(PASS|FAIL|SKIP)\]' "$log" | sed 's/^/  /' || true

        echo
        echo "Performance results:"
        perf=$(grep -E 'Bandwidth \(MB/sec\)|Average IOPS:|write: IOPS=|Average Latency\(s\):|clat \(usec\):' "$log" || true)
        if [[ -n $perf ]]; then
            printf '%s\n' "$perf" | sed 's/^/  /'
        else
            echo "  No performance benchmark in this run."
        fi

        echo
        echo "Health/recovery observations:"
        health_lines=$(grep -E 'Baseline health:|Recovery pending|Recovery wait timed out|returned to baseline|health: HEALTH_|Slow OSD heartbeats|active\+clean\+laggy|mons down|osds down' "$log" | tail -n 40 || true)
        if [[ -n $health_lines ]]; then
            printf '%s\n' "$health_lines" | sed 's/^/  /'
        else
            echo "  No additional health observations recorded."
        fi
    done

    echo
    echo "FINAL RECOVERY EVIDENCE"
    echo "======================================================================"
    latest=${LOGS[${#LOGS[@]}-1]}
    echo "Latest log: $latest"
    awk '/^Baseline health:/{getline; print "Latest baseline health: " $0} /^Final health:/{getline; print "Latest final health   : " $0}' "$latest"
    awk '/^Final PG summary:/{getline; print "Latest final PG state : " $0}' "$latest"
    echo
    echo "SOURCE LOGS"
    echo "----------------------------------------------------------------------"
    printf '%s\n' "${LOGS[@]}"
    echo
    echo "======================================================================"
    echo "END OF COMBINED REPORT"
    echo "======================================================================"
} | tee "$OUT"

chmod 600 "$OUT"
echo
echo "Combined report created: $OUT"
