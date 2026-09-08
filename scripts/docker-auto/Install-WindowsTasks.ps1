#Requires -Version 5.1
[CmdletBinding()]
param(
    [datetime]$StartAt = (Get-Date '06:40'),
    [datetime]$StopAt = (Get-Date '08:00')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$StartTaskName = 'AirflowFabric-Start'
$StopTaskName = 'AirflowFabric-SafeStop'
$KeepAwakeTaskName = 'AirflowFabric-KeepAwakeOnAC'
$StartScript = Join-Path $PSScriptRoot 'Start-Airflow.ps1'
$StopScript = Join-Path $PSScriptRoot 'Stop-AirflowIfSafe.ps1'
$KeepAwakeScript = Join-Path $PSScriptRoot 'Keep-AwakeOnAC.ps1'
$PowerShellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

foreach ($path in @($StartScript, $StopScript, $KeepAwakeScript, $PowerShellExe)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required file is missing: $path" }
}

$principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 6 `
    -RestartInterval (New-TimeSpan -Minutes 10)

$startAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$StartScript`""
$stopAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$StopScript`""
$keepAwakeAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$KeepAwakeScript`""
$startTrigger = New-ScheduledTaskTrigger -Daily -At $StartAt
$stopTrigger = New-ScheduledTaskTrigger -Daily -At $StopAt
$keepAwakeTrigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$keepAwakePrincipal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
$keepAwakeSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([timespan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $StartTaskName -Action $startAction -Trigger $startTrigger -Settings $settings -Principal $principal -Description 'Start Docker Desktop and the Airflow Fabric stack before the 07:00 Bangkok DAG.' -Force | Out-Null
Register-ScheduledTask -TaskName $StopTaskName -Action $stopAction -Trigger $stopTrigger -Settings $settings -Principal $principal -Description 'Stop Docker only after the daily DAG succeeds and Fabric F2 is confirmed Paused.' -Force | Out-Null
Register-ScheduledTask -TaskName $KeepAwakeTaskName -Action $keepAwakeAction -Trigger $keepAwakeTrigger -Settings $keepAwakeSettings -Principal $keepAwakePrincipal -Description 'Prevent Windows system sleep and Modern Standby while connected to AC power and the user is signed in; allow the display to turn off.' -Force | Out-Null
Start-ScheduledTask -TaskName $KeepAwakeTaskName

Get-ScheduledTask -TaskName $StartTaskName, $StopTaskName, $KeepAwakeTaskName | ForEach-Object {
    [pscustomobject]@{
        TaskName = $_.TaskName
        State = $_.State
        User = $_.Principal.UserId
        LogonType = $_.Principal.LogonType
        NetworkRequired = $_.Settings.RunOnlyIfNetworkAvailable
        WakeToRun = $_.Settings.WakeToRun
        NextRun = (Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime
    }
} | Sort-Object TaskName | Format-Table -AutoSize
