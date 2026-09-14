#!/usr/bin/env bash
# Start an image as the webserver and wait for its Docker HEALTHCHECK to report healthy.
# Usage: scripts/check_docker_health.sh <image>

set -euo pipefail

MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

image="$1"
name="archivepodcast-healthcheck"

echo_magenta "Healthcheck ${image}"

docker rm -f "$name" >/dev/null 2>&1 || true
docker run --detach --name "$name" "$image" >/dev/null
trap 'docker rm -f "$name" >/dev/null' EXIT

for _ in $(seq 1 30); do
    status=$(docker inspect --format '{{if .State.Running}}{{.State.Health.Status}}{{else}}exited{{end}}' "$name")
    echo "${image}: ${status}"
    case "$status" in
    healthy) exit 0 ;;
    unhealthy | exited) break ;;
    esac
    sleep 2
done

docker logs "$name"
echo "${image} did not become healthy" >&2
exit 1
