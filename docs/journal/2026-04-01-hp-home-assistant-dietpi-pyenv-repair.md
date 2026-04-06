# 2026-04-01 — HP Home Assistant DietPi pyenv repair

## Why this exists
The HP DietPi host (`ryans-place`) stopped serving Home Assistant after a host
update and subsequent Home Assistant update. This entry records the concrete
failure mode, the minimal repair, and the post-fix runtime state so upcoming
Home Assistant work has a stable starting point.

## Environment
- Host: HP all-in-one (`ryans-place`)
- OS: Debian GNU/Linux 13 (`trixie`) on DietPi
- Home Assistant install style: DietPi-managed Home Assistant Core
- Active runtime after the update:
  - user: `homeassistant`
  - Python: `3.14.3`
  - pyenv root: `/home/homeassistant/.pyenv`
  - config dir: `/mnt/dietpi_userdata/homeassistant`
- Home Assistant target version: `2026.4.0`

## Observed failure
- `home-assistant.service` was failing through DietPi's generated wrapper:
  `/home/homeassistant/homeassistant-start.sh`
- The service used the new pyenv activation script
  `/home/homeassistant/pyenv-activate.sh`, then executed:
  `hass -c /mnt/dietpi_userdata/homeassistant`
- `home-assistant.log` showed startup aborting before normal config load with:
  `ModuleNotFoundError: No module named 'aiohasupervisor'`

## Root cause
- DietPi rebuilt Home Assistant into a fresh pyenv-backed Python `3.14.3`
  runtime.
- `homeassistant==2026.4.0` was installed successfully in that runtime.
- The Home Assistant `hassio` component shipped in that install declares
  `aiohasupervisor==0.4.3` in its `manifest.json`, but that package was missing
  from the rebuilt environment.
- Because Home Assistant imports `homeassistant.components.hassio` during base
  system-info/bootstrap work, the service died before custom integrations were
  the active blocker.

## Minimal repair applied
- Installed the missing package directly into the active DietPi pyenv as the
  `homeassistant` user:

```bash
ssh hp 'sudo -u homeassistant -H bash -lc ". /home/homeassistant/pyenv-activate.sh >/dev/null 2>&1; python -m pip install aiohasupervisor==0.4.3"'
```

- Restarted the service:

```bash
ssh hp 'sudo systemctl restart home-assistant.service'
```

## Validation
- `systemctl status home-assistant.service` returned `active (running)`.
- The live process is now:
  `/home/homeassistant/.pyenv/versions/3.14.3/bin/python3.14 /home/homeassistant/.pyenv/versions/3.14.3/bin/hass -c /mnt/dietpi_userdata/homeassistant`
- `python -m pip show aiohasupervisor homeassistant` under the same pyenv
  showed:
  - `aiohasupervisor 0.4.3`
  - `homeassistant 2026.4.0`
- `ss -ltnp | grep 8123` confirmed Home Assistant listening on:
  - `0.0.0.0:8123`
  - `[::]:8123`
- `curl -sSI http://127.0.0.1:8123/` returned `HTTP/1.1 405 Method Not Allowed`,
  which is sufficient proof that the web server is up.

## Post-fix notes
- Home Assistant needed extra startup time after the restart because it resumed
  dependency installation and recorder recovery before binding `:8123`.
- Recorder logged the expected unclean-shutdown recovery warnings against
  `home-assistant_v2.db`, then continued.
- Custom integrations still produce the usual unsupported warnings, but they
  were not the cause of this outage.

## Known follow-up risk
- Static manifest inspection showed some custom integrations may still need
  follow-up package work in the new pyenv if they become the next blocker:
  - `ai_automation_suggester`: `anthropic>=0.8.0`
  - `icloud3`: `srp`, `fido2`
  - `tapo`: `plugp100==5.1.5`
  - `tapo_control`: `pytapo==3.4.11`, `python-kasa[speedups]==0.10.2`
- Do not preinstall all of these blindly. Repair only the exact package named by
  the next real startup/import failure if one appears.

## Locked takeaway
- The April 1, 2026 outage was caused by an incomplete DietPi/Home Assistant
  pyenv rebuild, not by HACS or a custom integration at first failure.
- The lowest-risk repair is to patch the active pyenv package set first before
  considering any broader DietPi reinstall or migration work.
