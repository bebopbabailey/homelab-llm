# Service Spec: optillm-local (deferred)

## Purpose
Local inference backend intended for Jetson Orin experiments (decode-time techniques).

## Status
Deferred. Not currently deployed; Orin has no listener on port `4040`.

## Intended interface (if revived)
- Bind: `0.0.0.0:4040` (LAN)
- Base URL: `http://192.168.1.93:4040/v1`
- Health: `GET /v1/models`
- Auth: bearer token required

## Storage
- Offload mount on Orin: `/mnt/seagate` (sshfs to Mini)

