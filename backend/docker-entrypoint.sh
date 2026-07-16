#!/bin/sh
set -eu

if [ -n "${MOOTDX_SERVER:-}" ]; then
    case "$MOOTDX_SERVER" in
        *:*) ;;
        *)
            echo "MOOTDX_SERVER must use host:port format" >&2
            exit 1
            ;;
    esac

    mootdx_host=${MOOTDX_SERVER%:*}
    mootdx_port=${MOOTDX_SERVER##*:}
    mkdir -p "$HOME/.mootdx"
    printf '{"BESTIP":{"HQ":["%s",%s]}}\n' \
        "$mootdx_host" "$mootdx_port" > "$HOME/.mootdx/config.json"
fi

exec "$@"
