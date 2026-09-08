# Windows Docker + Airflow daily automation

This folder is the Windows replacement for the former macOS `launchd` automation. The main Airflow DAG runs at 00:00 UTC / 07:00 Asia/Bangkok.

| Task | Windows local time | Behavior |
|---|---:|---|
| `AirflowFabric-Start` | 06:40 | Requires Windows network availability, verifies Windows DNS/HTTPS, starts Docker Desktop and Compose, waits for all 8 services, verifies DNS/HTTPS from the Airflow worker, confirms there are no active runs, then unpauses IoT and Retail DAGs. |
| `AirflowFabric-SafeStop` | 08:00 | Requires today's scheduled Retail success, expected IoT DAG and `pause_fabric_capacity` success, no active DAG run, and F2 `Paused`; pauses IoT/Retail and rechecks activity before stopping. Failed gates leave Docker running and retry every 10 minutes up to 6 times. |
| `AirflowFabric-KeepAwakeOnAC` | User logon | Continuously blocks system sleep/Modern Standby while the user is signed in and AC power is connected. The display may still turn off. On battery, the sleep request is released. |

All three tasks run as the current Windows user with an interactive logon token, so the user must remain signed in. The keep-awake task starts at user logon and prevents idle sleep while the laptop is on AC power. The start task is also registered with `WakeToRun` and `RunOnlyIfNetworkAvailable`; its script waits up to 15 minutes for Windows connectivity and up to 5 minutes for connectivity from the Airflow worker before it can unpause the DAG.

Do not hard-code public DNS servers in `docker-compose.yaml`. Docker Desktop should forward container DNS through the active Windows network so home Wi-Fi, VPN, and managed networks continue to work.

## Install and inspect

Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\docker-auto\Install-WindowsTasks.ps1` from the project root.

Inspect with `Get-ScheduledTask -TaskName 'AirflowFabric-*'`.

Logs are written to `logs\docker-auto\windows-task-scheduler.log` and remain Git-ignored.

## Safe manual tests

Start the stack with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\docker-auto\Start-Airflow.ps1`.

Check the stop gates without changing Docker or DAG state with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\docker-auto\Stop-AirflowIfSafe.ps1 -RunId windows-fabric-validation-20260904T145100Z -CheckOnly`.

Do not run the stop script without `-CheckOnly` during development unless Docker Desktop should really be closed.

## Uninstall

Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\docker-auto\Uninstall-WindowsTasks.ps1`.

Uninstalling removes only the three scheduled tasks. It does not delete project files, Docker data, or logs.

## Files

| File | Role |
|---|---|
| `Start-Airflow.ps1` | Verify host connectivity, start Docker/Compose, wait for health, verify worker connectivity, and safely unpause the main DAG. |
| `Stop-AirflowIfSafe.ps1` | Verify the DAG/F2 shutdown gates, pause the DAG, stop Compose, and stop Docker Desktop. |
| `Keep-AwakeOnAC.ps1` | Hold a Windows system-required power request on AC power and release it on battery. |
| `Install-WindowsTasks.ps1` | Register or update the two daily tasks and the startup keep-awake task. |
| `Uninstall-WindowsTasks.ps1` | Remove only those three tasks. |
