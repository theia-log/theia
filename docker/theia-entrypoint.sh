#!/bin/sh

theia_process=""

_trap_sigint() {
    kill -SIGINT "$theia_process" 2>/dev/null
}

_trap_sigterm() {
    kill -SIGTERM "$theia_process" 2>/dev/null
}

_trap_sighup() {
    kill -SIGHUP "$theia_process" 2>/dev/null
}

_trap_sigkill() {
    kill -SIGKILL "$theia_process" 2>/dev/null
}


trap _trap_sighup 1
trap _trap_sigint 2
trap _trap_sigkill 9
trap _trap_sigterm 15

theia_args="-P ${THEIA_PORT} -H 0.0.0.0 collect -d ${THEIA_DATA_DIR}"

if [ "${THEIA_DATA_STORE}" = "rdbs" ]; then
    theia_args="$theia_args --rdbs-store --db-url=${THEIA_DB_URL}"
    if [ "${THEIA_STORE_VERBOSE}" ]; then
        theia_args="${theia_args} --verbose"
    fi
fi

echo "theia.cli $theia_args"
python3 -m theia.cli $theia_args &

theia_process=$!

wait "${theia_process}"