#!/usr/bin/env bash

###############################################################################
# CEPH VALIDATION SUITE
# Author: Nishu Saini
# Version: 3.0
#
# Safe defaults:
# - Auto-detects a non-.mgr pool when no pool is supplied.
# - Refuses performance tests for a missing pool.
# - Records the baseline cluster state and never waits forever for HEALTH_OK.
# - Destructive tests are disabled unless --allow-destructive is supplied.
# - Network rules are automatically removed by EXIT/INT/TERM cleanup traps.
# - Full-disk test uses a bounded file size; it does not try to fill an OSD.
###############################################################################

set -u
set -o pipefail
umask 077

PROGRAM=${0##*/}
VERSION="3.0"
DATE=$(date +%F_%H-%M-%S)

BASE_DIR="/var/log/ceph-validation"
METRIC_DIR="$BASE_DIR/metrics"
REPORT_DIR="$BASE_DIR/reports"
BACKUP_DIR="/var/backups/ceph-validation/$DATE"
LOGFILE="$BASE_DIR/ceph_validation_$DATE.log"
REPORT="$REPORT_DIR/report_$DATE.txt"

POOL=""
MODE="validate"
ALLOW_DESTRUCTIVE=0
CONTINUE_DEGRADED=0
WAIT_TIMEOUT=300
INTERVAL=10
BENCH_SECONDS=30
RBD_SIZE="5G"
FIO_SIZE="1G"
FIO_JOBS=4
FIO_IODEPTH=32
OSD_ID=""
MON_ID=""
PARTITION_SUBNET=""
PARTITION_SECONDS=30
FULL_PATH=""
FULL_TEST_MIB=1024

PASS=0
FAIL=0
SKIP=0
TEST_START=$(date +%s)
INITIAL_HEALTH_STATUS=""
INITIAL_HEALTH_CODE=""
INITIAL_PG_SUMMARY=""
CREATED_RBD=""
MAPPED_DEVICE=""
ADDED_IPTABLES_RULE=0
FULL_TEST_FILE=""
NOOUT_WAS_SET=0
SCRIPT_RC=0

usage() {
    cat <<EOF
Usage:
  $PROGRAM [pool]
  $PROGRAM [options]

Modes:
  --mode validate           Run environment, health, metrics, PG, RADOS and RBD tests
  --mode health             Run non-destructive health and environment checks only
  --mode osd-failure        Controlled single OSD stop/start test
  --mode mon-failure        Controlled single MON stop/start test
  --mode network-partition  Temporary INPUT drop for one subnet
  --mode disk-space         Create and remove a bounded test file on a supplied path

Parameters:
  --pool NAME               Ceph pool. If omitted, first pool except .mgr is selected
  --continue-degraded       Permit benchmarks while baseline health is not HEALTH_OK
  --timeout SEC             Recovery/baseline wait timeout (default: 300)
  --interval SEC            Health polling interval (default: 10)
  --bench-seconds SEC       RADOS/FIO runtime (default: 30)
  --rbd-size SIZE           Temporary RBD image size (default: 5G)
  --fio-size SIZE           FIO working size (default: 1G)
  --fio-jobs N              FIO jobs (default: 4)
  --fio-iodepth N           FIO queue depth (default: 32)

Destructive-test parameters:
  --allow-destructive       Required for every destructive mode
  --osd ID                  OSD ID for --mode osd-failure
  --mon ID                  MON ID for --mode mon-failure
  --subnet CIDR             Source subnet for --mode network-partition
  --partition-seconds SEC   Rule duration (default: 30; maximum: 300)
  --path DIRECTORY          Test directory for --mode disk-space
  --test-mib N              Bounded file size in MiB (default: 1024; maximum: 10240)

Examples:
  $PROGRAM --mode health
  $PROGRAM --pool vm-rbd --continue-degraded
  $PROGRAM --mode osd-failure --osd 32 --allow-destructive
  $PROGRAM --mode mon-failure --mon prox23 --allow-destructive
  $PROGRAM --mode network-partition --subnet 10.31.122.23/32 --partition-seconds 30 --allow-destructive
  $PROGRAM --mode disk-space --path /var/lib/ceph/osd/ceph-32 --test-mib 1024 --allow-destructive
EOF
}

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOGFILE"
}

pass() {
    PASS=$((PASS + 1))
    log "[PASS] $*"
}

fail() {
    FAIL=$((FAIL + 1))
    log "[FAIL] $*"
}

skip() {
    SKIP=$((SKIP + 1))
    log "[SKIP] $*"
}

is_positive_integer() {
    [[ ${1:-} =~ ^[1-9][0-9]*$ ]]
}

run_cmd() {
    local description=$1
    shift

    {
        printf '\n==================================================\n'
        printf '%s\n' "$description"
        printf 'Command:'
        printf ' %q' "$@"
        printf '\n==================================================\n'
    } | tee -a "$LOGFILE"

    "$@" 2>&1 | tee -a "$LOGFILE"
    local rc=${PIPESTATUS[0]}

    if (( rc == 0 )); then
        pass "$description"
        return 0
    fi

    fail "$description (exit code $rc)"
    return "$rc"
}

current_health() {
    ceph health 2>&1 | sed -E 's/[[:space:]]+/ /g; s/[[:space:]]+$//'
}

health_code() {
    current_health | awk '{print $1}'
}

current_pg_summary() {
    ceph pg stat 2>&1 | sed -E 's/[[:space:]]+/ /g; s/[[:space:]]+$//'
}

capture_baseline() {
    INITIAL_HEALTH_STATUS=$(current_health)
    INITIAL_HEALTH_CODE=$(printf '%s\n' "$INITIAL_HEALTH_STATUS" | awk '{print $1}')
    INITIAL_PG_SUMMARY=$(current_pg_summary)

    log "Baseline health: $INITIAL_HEALTH_STATUS"
    log "Baseline PGs: $INITIAL_PG_SUMMARY"
}

wait_for_baseline_or_better() {
    local start now elapsed current code
    start=$(date +%s)
    log "Waiting up to ${WAIT_TIMEOUT}s for baseline health code '$INITIAL_HEALTH_CODE' or HEALTH_OK"

    while true; do
        current=$(current_health)
        code=$(printf '%s\n' "$current" | awk '{print $1}')

        if [[ $code == "HEALTH_OK" || $current == "$INITIAL_HEALTH_STATUS" ]]; then
            elapsed=$(( $(date +%s) - start ))
            pass "Cluster returned to baseline or better in ${elapsed}s"
            return 0
        fi

        now=$(date +%s)
        elapsed=$((now - start))
        if (( elapsed >= WAIT_TIMEOUT )); then
            fail "Recovery wait timed out after ${elapsed}s; current health: $current"
            return 1
        fi

        log "Recovery pending (${elapsed}s): $current"
        sleep "$INTERVAL"
    done
}

require_root() {
    if (( EUID != 0 )); then
        echo "Run this script as root." >&2
        exit 1
    fi
}

precheck() {
    local missing=0 cmd
    log "Running precheck"

    for cmd in ceph rados rbd fio awk grep sed tee date; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            fail "Required command not found: $cmd"
            missing=1
        fi
    done

    if ! ceph -s >/dev/null 2>&1; then
        fail "Cannot communicate with the Ceph cluster"
        missing=1
    fi

    if (( missing != 0 )); then
        exit 1
    fi

    pass "Precheck completed"
}

select_and_validate_pool() {
    local pools
    pools=$(ceph osd pool ls 2>/dev/null || true)

    if [[ -z $POOL ]]; then
        POOL=$(printf '%s\n' "$pools" | grep -v '^\.mgr$' | sed '/^[[:space:]]*$/d' | head -n 1)
    fi

    if [[ -z $POOL ]]; then
        fail "No usable pool was found"
        return 1
    fi

    if ! printf '%s\n' "$pools" | grep -Fxq -- "$POOL"; then
        fail "Pool '$POOL' does not exist"
        printf 'Available pools:\n%s\n' "$pools" | tee -a "$LOGFILE"
        return 1
    fi

    pass "Pool exists: $POOL"
}

warn_if_degraded() {
    if [[ $INITIAL_HEALTH_CODE == "HEALTH_OK" ]]; then
        pass "Baseline cluster health is HEALTH_OK"
        return 0
    fi

    log "[WARNING] Cluster was already degraded before testing"
    log "[WARNING] $INITIAL_HEALTH_STATUS"

    if [[ $MODE == "validate" && $CONTINUE_DEGRADED -ne 1 ]]; then
        skip "Performance tests blocked on degraded baseline; use --continue-degraded to override"
        return 1
    fi

    return 0
}

collect_environment() {
    {
        printf '\n########## HOST ##########\n'
        hostnamectl 2>&1 || true
        printf '\n########## KERNEL ##########\n'
        uname -a
        printf '\n########## CEPH VERSION ##########\n'
        ceph version
        printf '\n########## CEPH STATUS ##########\n'
        ceph -s
        printf '\n########## HEALTH DETAIL ##########\n'
        ceph health detail
        printf '\n########## MON STATUS ##########\n'
        ceph mon stat
        printf '\n########## OSD TREE ##########\n'
        ceph osd tree
        printf '\n########## OSD DF ##########\n'
        ceph osd df
        printf '\n########## FILESYSTEM STATUS ##########\n'
        ceph fs status 2>&1 || true
        printf '\n########## CAPACITY ##########\n'
        ceph df
    } >>"$LOGFILE" 2>&1
    pass "Environment and capacity collected"
}

collect_metrics() {
    local collected=0
    log "Collecting local system metrics"

    if command -v iostat >/dev/null 2>&1; then
        iostat -xm 2 5 >"$METRIC_DIR/iostat_$DATE.txt" 2>&1 &
        collected=1
    else
        skip "iostat is not installed"
    fi

    if command -v vmstat >/dev/null 2>&1; then
        vmstat 2 5 >"$METRIC_DIR/vmstat_$DATE.txt" 2>&1 &
        collected=1
    else
        skip "vmstat is not installed"
    fi

    if command -v mpstat >/dev/null 2>&1; then
        mpstat -P ALL 2 5 >"$METRIC_DIR/mpstat_$DATE.txt" 2>&1 &
        collected=1
    else
        skip "mpstat is not installed"
    fi

    wait
    if (( collected == 1 )); then
        pass "Available metrics collected"
    fi
}

rados_test() {
    local prefix="ceph-validation-$DATE"
    local write_ok=0

    if run_cmd "RADOS write benchmark" rados -p "$POOL" bench "$BENCH_SECONDS" write --no-cleanup --run-name "$prefix"; then
        write_ok=1
    fi

    if (( write_ok == 1 )); then
        run_cmd "RADOS sequential read benchmark" rados -p "$POOL" bench "$BENCH_SECONDS" seq --run-name "$prefix" || true
        run_cmd "RADOS random read benchmark" rados -p "$POOL" bench "$BENCH_SECONDS" rand --run-name "$prefix" || true
        run_cmd "RADOS benchmark object cleanup" rados -p "$POOL" cleanup --run-name "$prefix" || true
    else
        skip "RADOS read tests skipped because write benchmark failed"
    fi
}

rbd_test() {
    CREATED_RBD="ceph_validation_$DATE"

    if ! run_cmd "Create temporary RBD image" rbd create "$CREATED_RBD" --size "$RBD_SIZE" --pool "$POOL"; then
        CREATED_RBD=""
        skip "RBD mapping and FIO skipped because image creation failed"
        return 1
    fi

    if ! run_cmd "Map temporary RBD image" rbd map "$CREATED_RBD" --pool "$POOL"; then
        fail "RBD mapping failed"
        return 1
    fi

    MAPPED_DEVICE=$(rbd showmapped --format json 2>/dev/null | python3 -c '
import json,sys
name=sys.argv[1]
pool=sys.argv[2]
try:
    data=json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
items=data.values() if isinstance(data,dict) else data
for item in items:
    if item.get("name")==name and item.get("pool")==pool:
        print(item.get("device", ""))
        break
' "$CREATED_RBD" "$POOL" 2>/dev/null || true)

    if [[ -z $MAPPED_DEVICE || ! -b $MAPPED_DEVICE ]]; then
        fail "Mapped block device could not be identified"
        return 1
    fi

    run_cmd "RBD FIO random-write benchmark" fio \
        --name=ceph-rbd-randwrite \
        --filename="$MAPPED_DEVICE" \
        --rw=randwrite \
        --bs=4k \
        --size="$FIO_SIZE" \
        --iodepth="$FIO_IODEPTH" \
        --numjobs="$FIO_JOBS" \
        --runtime="$BENCH_SECONDS" \
        --time_based=1 \
        --direct=1 \
        --group_reporting || true

    cleanup_rbd
}

backup_cluster_state() {
    mkdir -p "$BACKUP_DIR"
    ceph -s >"$BACKUP_DIR/ceph-status.txt" 2>&1 || true
    ceph health detail >"$BACKUP_DIR/health-detail.txt" 2>&1 || true
    ceph osd tree >"$BACKUP_DIR/osd-tree.txt" 2>&1 || true
    ceph osd dump >"$BACKUP_DIR/osd-dump.txt" 2>&1 || true
    ceph quorum_status --format json-pretty >"$BACKUP_DIR/quorum-status.json" 2>&1 || true
    if command -v iptables-save >/dev/null 2>&1; then
        iptables-save >"$BACKUP_DIR/iptables.rules" 2>&1 || true
    fi
    pass "Cluster evidence saved to $BACKUP_DIR"
}

confirm_destructive() {
    local phrase expected
    expected="RUN-$MODE"

    if (( ALLOW_DESTRUCTIVE != 1 )); then
        fail "Destructive mode requires --allow-destructive"
        return 1
    fi

    cat <<EOF

############################################################
WARNING: CONTROLLED DISRUPTIVE CEPH TEST
Mode: $MODE
Baseline: $INITIAL_HEALTH_STATUS

This can affect client I/O and cluster availability.
Type exactly: $expected
############################################################
EOF
    read -r phrase
    if [[ $phrase != "$expected" ]]; then
        skip "Destructive test cancelled"
        return 1
    fi
    return 0
}

osd_failure_test() {
    [[ $OSD_ID =~ ^[0-9]+$ ]] || { fail "--osd requires a numeric OSD ID"; return 1; }
    ceph osd find "$OSD_ID" >/dev/null 2>&1 || { fail "OSD.$OSD_ID does not exist"; return 1; }

    confirm_destructive || return 1
    backup_cluster_state

    if ceph osd dump | grep -q 'flags.*noout'; then
        NOOUT_WAS_SET=1
        log "noout was already set before the test"
    else
        run_cmd "Set Ceph noout flag" ceph osd set noout || return 1
    fi

    run_cmd "Mark osd.$OSD_ID out" ceph osd out "$OSD_ID" || return 1
    run_cmd "Stop osd.$OSD_ID" systemctl stop "ceph-osd@$OSD_ID" || return 1
    sleep "$INTERVAL"
    run_cmd "Capture cluster status with osd.$OSD_ID stopped" ceph -s || true
    run_cmd "Start osd.$OSD_ID" systemctl start "ceph-osd@$OSD_ID" || return 1
    run_cmd "Mark osd.$OSD_ID in" ceph osd in "$OSD_ID" || return 1

    if (( NOOUT_WAS_SET == 0 )); then
        run_cmd "Unset Ceph noout flag" ceph osd unset noout || true
    fi

    wait_for_baseline_or_better
}

mon_failure_test() {
    [[ -n $MON_ID ]] || { fail "--mon requires a monitor ID"; return 1; }
    ceph mon dump 2>/dev/null | grep -q "mon\.$MON_ID" || { fail "Monitor '$MON_ID' does not exist"; return 1; }

    confirm_destructive || return 1
    backup_cluster_state

    run_cmd "Stop monitor $MON_ID" systemctl stop "ceph-mon@$MON_ID" || return 1
    sleep "$INTERVAL"
    run_cmd "Capture quorum while monitor $MON_ID is stopped" ceph quorum_status --format json-pretty || true
    run_cmd "Start monitor $MON_ID" systemctl start "ceph-mon@$MON_ID" || return 1
    wait_for_baseline_or_better
}

network_partition_test() {
    [[ -n $PARTITION_SUBNET ]] || { fail "--subnet is required"; return 1; }
    command -v iptables >/dev/null 2>&1 || { fail "iptables is not installed"; return 1; }

    if ! is_positive_integer "$PARTITION_SECONDS" || (( PARTITION_SECONDS > 300 )); then
        fail "--partition-seconds must be 1 to 300"
        return 1
    fi

    confirm_destructive || return 1
    backup_cluster_state

    if iptables -C INPUT -s "$PARTITION_SUBNET" -m comment --comment ceph-validation -j DROP >/dev/null 2>&1; then
        fail "Matching ceph-validation iptables rule already exists"
        return 1
    fi

    run_cmd "Add temporary network partition rule" iptables -I INPUT 1 -s "$PARTITION_SUBNET" -m comment --comment ceph-validation -j DROP || return 1
    ADDED_IPTABLES_RULE=1
    log "Partition active for ${PARTITION_SECONDS}s"
    sleep "$PARTITION_SECONDS"
    remove_partition_rule
    run_cmd "Capture cluster status after network rule removal" ceph -s || true
    wait_for_baseline_or_better
}

disk_space_test() {
    [[ -n $FULL_PATH ]] || { fail "--path is required"; return 1; }
    [[ -d $FULL_PATH ]] || { fail "Directory does not exist: $FULL_PATH"; return 1; }

    if ! is_positive_integer "$FULL_TEST_MIB" || (( FULL_TEST_MIB > 10240 )); then
        fail "--test-mib must be 1 to 10240"
        return 1
    fi

    local avail_mib required_mib
    avail_mib=$(df -Pm "$FULL_PATH" | awk 'NR==2 {print $4}')
    required_mib=$((FULL_TEST_MIB + 1024))
    if [[ ! $avail_mib =~ ^[0-9]+$ ]] || (( avail_mib < required_mib )); then
        fail "Insufficient safety headroom: need test size plus 1024 MiB free"
        return 1
    fi

    confirm_destructive || return 1
    backup_cluster_state

    FULL_TEST_FILE="$FULL_PATH/.ceph-validation-$DATE.test"
    run_cmd "Create bounded ${FULL_TEST_MIB} MiB test file" dd if=/dev/zero of="$FULL_TEST_FILE" bs=1M count="$FULL_TEST_MIB" conv=fsync status=progress || return 1
    run_cmd "Capture health after bounded disk-space test" ceph health detail || true
    run_cmd "Remove bounded disk-space test file" rm -f -- "$FULL_TEST_FILE" || return 1
    FULL_TEST_FILE=""
    wait_for_baseline_or_better
}

remove_partition_rule() {
    if (( ADDED_IPTABLES_RULE == 1 )); then
        iptables -D INPUT -s "$PARTITION_SUBNET" -m comment --comment ceph-validation -j DROP >/dev/null 2>&1 || true
        ADDED_IPTABLES_RULE=0
        log "Temporary network partition rule removed"
    fi
}

cleanup_rbd() {
    if [[ -n $MAPPED_DEVICE ]]; then
        rbd unmap "$MAPPED_DEVICE" >>"$LOGFILE" 2>&1 || true
        MAPPED_DEVICE=""
    fi
    if [[ -n $CREATED_RBD ]]; then
        rbd rm "$CREATED_RBD" --pool "$POOL" >>"$LOGFILE" 2>&1 || true
        CREATED_RBD=""
    fi
}

cleanup() {
    local rc=$?
    remove_partition_rule

    if [[ -n $FULL_TEST_FILE && -f $FULL_TEST_FILE ]]; then
        rm -f -- "$FULL_TEST_FILE" >/dev/null 2>&1 || true
        log "Emergency cleanup removed $FULL_TEST_FILE"
    fi

    cleanup_rbd

    if (( NOOUT_WAS_SET == 0 )) && command -v ceph >/dev/null 2>&1; then
        if ceph osd dump 2>/dev/null | grep -q 'flags.*noout'; then
            ceph osd unset noout >>"$LOGFILE" 2>&1 || true
            log "Emergency cleanup attempted to unset noout"
        fi
    fi

    return "$rc"
}

extract_performance_summary() {
    {
        printf '\nPERFORMANCE EXTRACT\n'
        grep -E 'Bandwidth \(MB/sec\)|Average IOPS|IOPS=|BW=' "$LOGFILE" | tail -n 30 || true
    } >>"$REPORT"
}

generate_report() {
    local end runtime final_health final_pg overall
    end=$(date +%s)
    runtime=$((end - TEST_START))
    final_health=$(current_health)
    final_pg=$(current_pg_summary)

    if (( FAIL == 0 )); then
        overall="SUCCESS"
    else
        overall="ATTENTION REQUIRED"
        SCRIPT_RC=1
    fi

    cat >"$REPORT" <<EOF
==================================================
CEPH VALIDATION REPORT
==================================================
Date: $(date)
Host: $(hostname -f 2>/dev/null || hostname)
Suite version: $VERSION
Mode: $MODE
Pool: ${POOL:-N/A}

Baseline health:
$INITIAL_HEALTH_STATUS

Final health:
$final_health

Baseline PG summary:
$INITIAL_PG_SUMMARY

Final PG summary:
$final_pg

PASS: $PASS
FAIL: $FAIL
SKIP: $SKIP
Runtime: ${runtime}s
Overall: $overall

Log: $LOGFILE
Metrics: $METRIC_DIR
Backup evidence: $BACKUP_DIR
==================================================
EOF

    extract_performance_summary
    cat "$REPORT"
}

parse_args() {
    if (( $# > 0 )) && [[ $1 != --* ]]; then
        POOL=$1
        shift
    fi

    while (( $# > 0 )); do
        case "$1" in
            --pool) POOL=${2:?Missing value for --pool}; shift 2 ;;
            --mode) MODE=${2:?Missing value for --mode}; shift 2 ;;
            --continue-degraded) CONTINUE_DEGRADED=1; shift ;;
            --allow-destructive) ALLOW_DESTRUCTIVE=1; shift ;;
            --timeout) WAIT_TIMEOUT=${2:?Missing value for --timeout}; shift 2 ;;
            --interval) INTERVAL=${2:?Missing value for --interval}; shift 2 ;;
            --bench-seconds) BENCH_SECONDS=${2:?Missing value for --bench-seconds}; shift 2 ;;
            --rbd-size) RBD_SIZE=${2:?Missing value for --rbd-size}; shift 2 ;;
            --fio-size) FIO_SIZE=${2:?Missing value for --fio-size}; shift 2 ;;
            --fio-jobs) FIO_JOBS=${2:?Missing value for --fio-jobs}; shift 2 ;;
            --fio-iodepth) FIO_IODEPTH=${2:?Missing value for --fio-iodepth}; shift 2 ;;
            --osd) OSD_ID=${2:?Missing value for --osd}; shift 2 ;;
            --mon) MON_ID=${2:?Missing value for --mon}; shift 2 ;;
            --subnet) PARTITION_SUBNET=${2:?Missing value for --subnet}; shift 2 ;;
            --partition-seconds) PARTITION_SECONDS=${2:?Missing value for --partition-seconds}; shift 2 ;;
            --path) FULL_PATH=${2:?Missing value for --path}; shift 2 ;;
            --test-mib) FULL_TEST_MIB=${2:?Missing value for --test-mib}; shift 2 ;;
            -h|--help) usage; exit 0 ;;
            *) echo "Unknown parameter: $1" >&2; usage >&2; exit 2 ;;
        esac
    done

    case "$MODE" in
        validate|health|osd-failure|mon-failure|network-partition|disk-space) ;;
        *) echo "Invalid mode: $MODE" >&2; exit 2 ;;
    esac

    for value in "$WAIT_TIMEOUT" "$INTERVAL" "$BENCH_SECONDS" "$FIO_JOBS" "$FIO_IODEPTH"; do
        is_positive_integer "$value" || { echo "Numeric parameters must be positive integers" >&2; exit 2; }
    done
}

main() {
    parse_args "$@"
    require_root
    mkdir -p "$BASE_DIR" "$METRIC_DIR" "$REPORT_DIR"
    touch "$LOGFILE"
    trap cleanup EXIT INT TERM

    log "Starting Ceph Validation Suite v$VERSION"
    precheck
    capture_baseline
    collect_environment

    case "$MODE" in
        health)
            collect_metrics
            ;;
        validate)
            select_and_validate_pool || { generate_report; exit 1; }
            if warn_if_degraded; then
                collect_metrics
                rados_test
                rbd_test || true
            else
                collect_metrics
            fi
            ;;
        osd-failure)
            osd_failure_test || true
            ;;
        mon-failure)
            mon_failure_test || true
            ;;
        network-partition)
            network_partition_test || true
            ;;
        disk-space)
            disk_space_test || true
            ;;
    esac

    run_cmd "Final Ceph status" ceph -s || true
    generate_report
    exit "$SCRIPT_RC"
}

main "$@"
