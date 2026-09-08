#Requires -Version 5.1
[CmdletBinding()]
param(
    [int]$PollSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($PollSeconds -lt 5) { throw 'PollSeconds must be at least 5.' }

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$LogDir = Join-Path $ProjectDir 'logs\docker-auto'
$LogFile = Join-Path $LogDir 'keep-awake.log'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class AirflowPowerState {
    [StructLayout(LayoutKind.Sequential)]
    public struct SystemPowerStatus {
        public byte ACLineStatus;
        public byte BatteryFlag;
        public byte BatteryLifePercent;
        public byte SystemStatusFlag;
        public int BatteryLifeTime;
        public int BatteryFullLifeTime;
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint executionState);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetSystemPowerStatus(out SystemPowerStatus status);
}
'@

$ES_SYSTEM_REQUIRED = [uint32]0x00000001
$ES_CONTINUOUS = [Convert]::ToUInt32('80000000', 16)
$lastState = ''

function Write-Log {
    param([string]$Message)
    $line = '{0}  keep-awake: {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}

try {
    Write-Log "started; poll_seconds=$PollSeconds"
    while ($true) {
        $powerStatus = New-Object AirflowPowerState+SystemPowerStatus
        if (-not [AirflowPowerState]::GetSystemPowerStatus([ref]$powerStatus)) {
            throw "GetSystemPowerStatus failed with Win32 error $([Runtime.InteropServices.Marshal]::GetLastWin32Error())."
        }

        if ($powerStatus.ACLineStatus -eq 1) {
            $result = [AirflowPowerState]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)
            if ($result -eq 0) { throw 'SetThreadExecutionState failed while requesting SYSTEM_REQUIRED.' }
            $state = 'AC: system sleep blocked; display may turn off'
        }
        else {
            $result = [AirflowPowerState]::SetThreadExecutionState($ES_CONTINUOUS)
            if ($result -eq 0) { throw 'SetThreadExecutionState failed while releasing SYSTEM_REQUIRED.' }
            $state = 'battery: system sleep allowed'
        }

        if ($state -ne $lastState) {
            Write-Log $state
            $lastState = $state
        }
        Start-Sleep -Seconds $PollSeconds
    }
}
catch {
    Write-Log "FAILED; $($_.Exception.Message)"
    throw
}
finally {
    [void][AirflowPowerState]::SetThreadExecutionState($ES_CONTINUOUS)
    Write-Log 'stopped; system sleep request released'
}
