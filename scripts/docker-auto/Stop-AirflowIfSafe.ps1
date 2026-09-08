#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$ProjectDir = '',
    [string]$DagId = 'qr_printing_machine_api_ingestion',
    [string]$RunId = '',
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $ProjectDir) {
    $ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$DockerCli = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
$LogDir = Join-Path $ProjectDir 'logs\docker-auto'
$LogFile = Join-Path $LogDir 'windows-task-scheduler.log'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-Log {
    param([string]$Message)
    $line = '{0}  stop: {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}

function Read-EnvFile {
    $values = @{}
    foreach ($line in Get-Content -LiteralPath (Join-Path $ProjectDir '.env')) {
        if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) { continue }
        $key, $value = $line.Split('=', 2)
        $values[$key] = $value
    }
    return $values
}

function Invoke-DockerCommand {
    param([string[]]$Arguments)
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = @(& $DockerCli @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedPreference
    }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
}

function Test-DockerReady {
    $result = Invoke-DockerCommand -Arguments @('info')
    return ($result.ExitCode -eq 0)
}

function Invoke-PostgresScalar {
    param([string]$Sql)
    $result = Invoke-DockerCommand -Arguments @('compose', 'exec', '--no-TTY', 'postgres', 'psql', '-U', 'airflow', '-d', 'airflow', '-tAqc', $Sql)
    if ($result.ExitCode -ne 0) {
        throw "PostgreSQL gate query failed: $($result.Output -join ' ')"
    }
    $lastLine = $result.Output | Where-Object { $_ -and $_.ToString().Trim() } | Select-Object -Last 1
    if ($null -eq $lastLine) { return '' }
    return $lastLine.ToString().Trim()
}

function Get-CapacityState {
    param([hashtable]$Settings)
    $required = @(
        'AZURE_TENANT_ID',
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET',
        'AZURE_SUBSCRIPTION_ID',
        'AZURE_RESOURCE_GROUP',
        'FABRIC_CAPACITY_NAME'
    )
    $missing = $required | Where-Object { -not $Settings[$_] -or $Settings[$_] -eq 'replace_me' }
    if ($missing) { throw "Missing capacity settings: $($missing -join ', ')" }

    $tokenUri = "https://login.microsoftonline.com/$($Settings['AZURE_TENANT_ID'])/oauth2/v2.0/token"
    $body = @{
        client_id     = $Settings['AZURE_CLIENT_ID']
        client_secret = $Settings['AZURE_CLIENT_SECRET']
        scope         = 'https://management.azure.com/.default'
        grant_type    = 'client_credentials'
    }
    $token = (Invoke-RestMethod -Method Post -Uri $tokenUri -Body $body -TimeoutSec 30).access_token
    $capacityUri = 'https://management.azure.com/subscriptions/{0}/resourceGroups/{1}/providers/Microsoft.Fabric/capacities/{2}?api-version=2023-11-01' -f (
        $Settings['AZURE_SUBSCRIPTION_ID'],
        $Settings['AZURE_RESOURCE_GROUP'],
        $Settings['FABRIC_CAPACITY_NAME']
    )
    $capacity = Invoke-RestMethod -Method Get -Uri $capacityUri -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 30
    return [string]$capacity.properties.state
}

try {
    Write-Log "begin; project=$ProjectDir; checkOnly=$CheckOnly"

    if (-not (Test-Path -LiteralPath $DockerCli)) { throw 'Docker CLI is missing.' }
    if (-not (Test-DockerReady)) { throw 'Docker engine is not running; no shutdown action was taken.' }

    if (-not $RunId) {
        $utcDate = [DateTime]::UtcNow.ToString('yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
        $RunId = "scheduled__${utcDate}T00:00:00+00:00"
    }

    $safeDagId = $DagId.Replace("'", "''")
    $safeRunId = $RunId.Replace("'", "''")

    Push-Location $ProjectDir
    try {
        $runState = Invoke-PostgresScalar "SELECT state FROM dag_run WHERE dag_id='$safeDagId' AND run_id='$safeRunId' ORDER BY id DESC LIMIT 1;"
        if ($runState -ne 'success') {
            throw "Required DAG run is not successful; run_id=$RunId state=$runState"
        }

        $pauseTaskState = Invoke-PostgresScalar "SELECT state FROM task_instance WHERE dag_id='$safeDagId' AND run_id='$safeRunId' AND task_id='pause_fabric_capacity' LIMIT 1;"
        if ($pauseTaskState -ne 'success') {
            throw "pause_fabric_capacity is not successful; state=$pauseTaskState"
        }

        $activeRuns = [int](Invoke-PostgresScalar "SELECT count(*) FROM dag_run WHERE state IN ('queued','running');")
        if ($activeRuns -ne 0) {
            throw "$activeRuns DAG run(s) are still queued/running."
        }

        # Do not shut down before today's 07:30 Bangkok Retail schedule completes.
        $retailState = Invoke-PostgresScalar "SELECT state FROM dag_run WHERE dag_id='retail_dbt_daily' AND run_type='scheduled' AND (run_after AT TIME ZONE 'Asia/Bangkok')::date = (now() AT TIME ZONE 'Asia/Bangkok')::date ORDER BY run_after DESC LIMIT 1;"
        if ($retailState -ne 'success') { throw "Today's scheduled Retail run is not successful; state=$retailState" }

        $settings = Read-EnvFile
        $capacityState = Get-CapacityState -Settings $settings
        if ($capacityState -ne 'Paused') {
            throw "Fabric capacity is not Paused; state=$capacityState"
        }

        Write-Log "safety gates passed; run_id=$RunId; IoT=success; Retail=success; pause task=success; active runs=0; F2=Paused."

        if ($CheckOnly) {
            Write-Log 'check-only success; Docker and DAG state were not changed.'
            exit 0
        }

        $pause = Invoke-DockerCommand -Arguments @('compose', 'exec', '--no-TTY', 'airflow-scheduler', 'airflow', 'dags', 'pause', '-y', $DagId)
        if ($pause.ExitCode -ne 0) { throw "DAG pause failed: $($pause.Output -join ' ')" }
        $isPaused = Invoke-PostgresScalar "SELECT is_paused FROM dag WHERE dag_id='$safeDagId';"
        if ($isPaused -ne 't') { throw "DAG pause verification failed; database value=$isPaused" }

        $retailPause = Invoke-DockerCommand -Arguments @('compose', 'exec', '--no-TTY', 'airflow-scheduler', 'airflow', 'dags', 'pause', '-y', 'retail_dbt_daily')
        if ($retailPause.ExitCode -ne 0) { throw 'Retail DAG pause failed.' }
        if ((Invoke-PostgresScalar "SELECT is_paused FROM dag WHERE dag_id='retail_dbt_daily';") -ne 't') { throw 'Retail DAG pause verification failed.' }
        # Recheck after pausing schedules to close the admission/shutdown race.
        if ([int](Invoke-PostgresScalar "SELECT count(*) FROM dag_run WHERE state IN ('queued','running');") -ne 0) {
            throw 'A DAG run became active while pausing; leave Docker running.'
        }

        $composeStop = Invoke-DockerCommand -Arguments @('compose', 'stop', '--timeout', '30')
        if ($composeStop.ExitCode -ne 0) { throw "docker compose stop failed: $($composeStop.Output -join ' ')" }
    }
    finally {
        Pop-Location
    }

    Write-Log 'containers stopped safely; requesting Docker Desktop stop.'
    $desktopStop = Invoke-DockerCommand -Arguments @('desktop', 'stop')
    if ($desktopStop.ExitCode -ne 0) { throw "docker desktop stop failed after containers stopped: $($desktopStop.Output -join ' ')" }

    Write-Log 'success; Docker Desktop stopped.'
    exit 0
}
catch {
    Write-Log "BLOCKED; $($_.Exception.Message); Docker is intentionally left running."
    exit 2
}
