#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$ProjectDir = '',
    [string]$DagId = 'qr_printing_machine_api_ingestion',
    [int]$NetworkWaitSeconds = 900,
    [int]$DockerWaitSeconds = 240,
    [int]$StackWaitSeconds = 240,
    [int]$ContainerNetworkWaitSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $ProjectDir) {
    $ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$DockerCli = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
$DockerDesktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$ConnectivityHost = 'login.microsoftonline.com'
$ConnectivityUri = 'https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration'
$LogDir = Join-Path $ProjectDir 'logs\docker-auto'
$LogFile = Join-Path $LogDir 'windows-task-scheduler.log'
$ExpectedServices = @(
    'airflow-apiserver',
    'airflow-dag-processor',
    'airflow-scheduler',
    'airflow-triggerer',
    'airflow-worker',
    'machine-api',
    'postgres',
    'redis'
)

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-Log {
    param([string]$Message)
    $line = '{0}  start: {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
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

function Test-HostNetworkReady {
    try {
        $addresses = [System.Net.Dns]::GetHostAddresses($ConnectivityHost)
        if ($addresses.Count -eq 0) { return $false }
        $response = Invoke-WebRequest -Uri $ConnectivityUri -UseBasicParsing -TimeoutSec 10
        return ($response.StatusCode -eq 200)
    }
    catch {
        return $false
    }
}

function Wait-HostNetworkReady {
    $deadline = (Get-Date).AddSeconds($NetworkWaitSeconds)
    $waitingLogged = $false
    while (-not (Test-HostNetworkReady)) {
        if (-not $waitingLogged) {
            Write-Log "waiting for Windows DNS/HTTPS connectivity to $ConnectivityHost before starting Docker."
            $waitingLogged = $true
        }
        if ((Get-Date) -ge $deadline) {
            throw "Windows network preflight failed; cannot resolve or reach $ConnectivityHost within $NetworkWaitSeconds seconds."
        }
        Start-Sleep -Seconds 10
    }
    Write-Log "Windows network preflight passed; $ConnectivityHost is reachable over HTTPS."
}

function Test-ContainerNetworkReady {
    $python = "import socket, urllib.request; socket.getaddrinfo('$ConnectivityHost', 443); print(urllib.request.urlopen('$ConnectivityUri', timeout=10).status)"
    $result = Invoke-DockerCommand -Arguments @('compose', 'exec', '--no-TTY', 'airflow-worker', 'python', '-c', $python)
    if ($result.ExitCode -ne 0) { return $false }
    $lastLine = $result.Output | Where-Object { $_ -and $_.ToString().Trim() } | Select-Object -Last 1
    return ($null -ne $lastLine -and $lastLine.ToString().Trim() -eq '200')
}

function Wait-ContainerNetworkReady {
    $deadline = (Get-Date).AddSeconds($ContainerNetworkWaitSeconds)
    $waitingLogged = $false
    while (-not (Test-ContainerNetworkReady)) {
        if (-not $waitingLogged) {
            Write-Log "waiting for Airflow worker DNS/HTTPS connectivity to $ConnectivityHost before unpausing the DAG."
            $waitingLogged = $true
        }
        if ((Get-Date) -ge $deadline) {
            throw "Airflow worker network preflight failed; cannot resolve or reach $ConnectivityHost within $ContainerNetworkWaitSeconds seconds."
        }
        Start-Sleep -Seconds 10
    }
    Write-Log "Airflow worker network preflight passed; $ConnectivityHost is reachable over HTTPS."
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

try {
    Write-Log "begin; project=$ProjectDir"

    if (-not (Test-Path -LiteralPath $DockerCli) -or -not (Test-Path -LiteralPath $DockerDesktop)) {
        throw 'Docker Desktop is not installed at the expected Windows path.'
    }

    $envValues = Read-EnvFile
    if ($envValues['FABRIC_MODE'] -ne 'fabric' -or
        $envValues['FABRIC_CAPACITY_AUTO_RESUME'] -ne 'true' -or
        $envValues['FABRIC_CAPACITY_AUTO_PAUSE'] -ne 'true') {
        throw 'Daily automation requires FABRIC_MODE=fabric and both capacity automation flags=true.'
    }

    Wait-HostNetworkReady

    if (-not (Test-DockerReady)) {
        Write-Log 'Docker engine is down; requesting Docker Desktop start.'
        $desktopStart = Invoke-DockerCommand -Arguments @('desktop', 'start')
        if ($desktopStart.ExitCode -ne 0) { throw "docker desktop start failed: $($desktopStart.Output -join ' ')" }
    }

    $dockerDeadline = (Get-Date).AddSeconds($DockerWaitSeconds)
    while (-not (Test-DockerReady)) {
        if ((Get-Date) -ge $dockerDeadline) { throw 'Docker engine did not become ready before timeout.' }
        Start-Sleep -Seconds 5
    }

    Push-Location $ProjectDir
    try {
        $composeUp = Invoke-DockerCommand -Arguments @('compose', 'up', '-d')
        if ($composeUp.ExitCode -ne 0) { throw "docker compose up failed: $($composeUp.Output -join ' ')" }

        $stackDeadline = (Get-Date).AddSeconds($StackWaitSeconds)
        while ($true) {
            $composePs = Invoke-DockerCommand -Arguments @('compose', 'ps', '--format', 'json')
            if ($composePs.ExitCode -ne 0) { throw "docker compose ps failed: $($composePs.Output -join ' ')" }
            $raw = $composePs.Output

            $containers = @()
            foreach ($item in $raw) {
                try { $containers += ($item | ConvertFrom-Json) } catch { }
            }

            $notReady = @()
            foreach ($service in $ExpectedServices) {
                $container = $containers | Where-Object { $_.Service -eq $service } | Select-Object -First 1
                if ($null -eq $container -or $container.State -ne 'running' -or $container.Health -ne 'healthy') {
                    $notReady += $service
                }
            }

            if ($notReady.Count -eq 0) { break }
            if ((Get-Date) -ge $stackDeadline) {
                throw "Stack health timeout; not ready: $($notReady -join ', ')"
            }
            Start-Sleep -Seconds 5
        }

        Wait-ContainerNetworkReady

        $activeRuns = [int](Invoke-PostgresScalar "SELECT count(*) FROM dag_run WHERE state IN ('queued','running');")
        if ($activeRuns -ne 0) {
            throw "Refusing to unpause a new schedule while $activeRuns DAG run(s) are active."
        }

        $unpause = Invoke-DockerCommand -Arguments @('compose', 'exec', '--no-TTY', 'airflow-scheduler', 'airflow', 'dags', 'unpause', '-y', $DagId)
        if ($unpause.ExitCode -ne 0) { throw "DAG unpause failed: $($unpause.Output -join ' ')" }

        $safeDagId = $DagId.Replace("'", "''")
        $isPaused = Invoke-PostgresScalar "SELECT is_paused FROM dag WHERE dag_id='$safeDagId';"
        if ($isPaused -ne 'f') { throw "DAG unpause verification failed; database value=$isPaused" }

        $retailUnpause = Invoke-DockerCommand -Arguments @('compose', 'exec', '--no-TTY', 'airflow-scheduler', 'airflow', 'dags', 'unpause', '-y', 'retail_dbt_daily')
        if ($retailUnpause.ExitCode -ne 0) { throw 'Retail DAG unpause failed.' }
        if ((Invoke-PostgresScalar "SELECT is_paused FROM dag WHERE dag_id='retail_dbt_daily';") -ne 'f') {
            throw 'Retail DAG unpause verification failed.'
        }
    }
    finally {
        Pop-Location
    }

    Write-Log 'success; Windows and worker connectivity passed, all 8 services are healthy; IoT and Retail DAGs are unpaused.'
    exit 0
}
catch {
    Write-Log "FAILED; $($_.Exception.Message); Docker is intentionally left running for recovery."
    exit 1
}
