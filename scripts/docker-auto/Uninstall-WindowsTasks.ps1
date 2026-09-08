#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

foreach ($taskName in @('AirflowFabric-Start', 'AirflowFabric-SafeStop', 'AirflowFabric-KeepAwakeOnAC')) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($null -ne $task) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output "Removed $taskName"
    }
    else {
        Write-Output "$taskName was not installed"
    }
}
