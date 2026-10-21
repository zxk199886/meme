#!/bin/bash
# Runs on every boot of a rented Vast.ai instance (sent as the "onstart" script).
# Settings come from env vars set by the controller: PRL_WALLET PRL_POOL MINER_URL
# MINER_SHA256 MINER_EXTRA MAX_LIFETIME_HOURS VAST_BASE.
# Vast injects CONTAINER_ID and CONTAINER_API_KEY, which let the instance destroy itself.

LOG=/root/pearl-miner.log

self_destroy() {
  echo "[pearl] $(date -u) destroying instance ${CONTAINER_ID:-?}"
  curl -fsS -X DELETE -H "Authorization: Bearer ${CONTAINER_API_KEY:-}" \
    -H "Content-Type: application/json" -d '{}' \
    "${VAST_BASE:-https://console.vast.ai}/api/v0/instances/${CONTAINER_ID:-0}/"
}

# Hard lifetime, counted from the first boot so restarts don't extend it.
# This is the safety net for when the controller on the user's PC is offline.
lifetime_watchdog() {
  [ -f /root/.pearl_born ] || date +%s > /root/.pearl_born
  local deadline=$(( $(cat /root/.pearl_born) + ${MAX_LIFETIME_HOURS:-12} * 3600 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do sleep 60; done
  until self_destroy; do sleep 300; done
}

main() {
  echo "[pearl] $(date -u) boot, instance ${CONTAINER_ID:-?}"
  if ! command -v curl >/dev/null; then
    apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates
  fi
  lifetime_watchdog &

  mkdir -p /root/miner && cd /root/miner || exit 1
  if [ ! -x ./SRBMiner-MULTI ]; then
    curl -fsSL -o miner.tgz "$MINER_URL" || { echo "[pearl] miner download failed"; exit 1; }
    sum=$(sha256sum miner.tgz | cut -d' ' -f1)
    echo "[pearl] miner sha256 $sum"
    if [ -n "${MINER_SHA256:-}" ] && [ "$sum" != "$MINER_SHA256" ]; then
      echo "[pearl] sha256 mismatch, expected $MINER_SHA256 - refusing to run"
      self_destroy
      exit 1
    fi
    tar xzf miner.tgz --strip-components=1
  fi

  local worker="vast${CONTAINER_ID:-unknown}"
  while true; do
    # shellcheck disable=SC2086  # MINER_EXTRA is a list of flags
    ./SRBMiner-MULTI --disable-cpu --algorithm pearlhash \
      --pool "$PRL_POOL" --wallet "${PRL_WALLET}.${worker}" ${MINER_EXTRA:-}
    echo "[pearl] $(date -u) miner exited ($?), restarting in 10s"
    sleep 10
  done
}

main >>"$LOG" 2>&1 &
disown
