$ErrorActionPreference = "Stop"

function Read-DotEnv {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Cannot find env file: $Path"
    }

    $result = @{}
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line -split "=", 2
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        $result[$key] = $value
    }
    return $result
}

function Test-LocalDashboard {
    try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/status" -TimeoutSec 5
        return @{
            Ok = $true
            Status = $status.runner.health.status
            Cycles = $status.runner.state.cycles
            Errors = $status.runner.state.consecutive_errors
        }
    }
    catch {
        return @{ Ok = $false; Error = $_.Exception.Message }
    }
}

$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root ".env.demo"
$envMap = Read-DotEnv $envPath

foreach ($required in @("IP", "USER", "SECRET_KEY")) {
    if (-not $envMap.ContainsKey($required) -or -not $envMap[$required]) {
        throw ".env.demo is missing $required"
    }
}

$keyPath = $envMap["SECRET_KEY"]
if (-not (Test-Path -LiteralPath $keyPath)) {
    throw "SECRET_KEY path does not exist"
}

$target = "$($envMap["USER"])@$($envMap["IP"])"
$ssh = (Get-Command ssh -ErrorAction Stop).Source

Write-Host "[1/4] Checking remote dashboard..."
$remoteScript = @'
set -e
cd ~/codex_trade
mkdir -p logs data reports run
if ! pgrep -af '[r]un_dashboard.py' >/dev/null; then
  nohup .venv/bin/python scripts/run_dashboard.py \
    --host 127.0.0.1 \
    --port 8765 \
    --db data/demo_rebalance_runner.sqlite3 \
    --log-file logs/demo_rebalance_runner_24h.jsonl \
    --summary-file reports/demo_rebalance_runner_24h.json \
    --state-file data/demo_rebalance_runner_state.json \
    > logs/dashboard.stdout.log \
    2> logs/dashboard.stderr.log &
  echo $! > run/dashboard.pid
fi
curl -fsS --max-time 5 http://127.0.0.1:8765/api/status >/dev/null
echo REMOTE_DASHBOARD_OK
'@

$remoteOutput = $remoteScript | & $ssh -i $keyPath -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 $target "bash -s"
if ($LASTEXITCODE -ne 0) {
    throw "Remote dashboard check failed"
}
Write-Host ($remoteOutput | Select-Object -Last 1)

Write-Host "[2/4] Checking local tunnel..."
$localStatus = Test-LocalDashboard
if (-not $localStatus.Ok) {
    $existingTunnel = Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match "8765:127\.0\.0\.1:8765" }

    if (-not $existingTunnel) {
        Write-Host "[3/4] Starting SSH tunnel..."
        $args = @(
            "-i", $keyPath,
            "-N",
            "-L", "8765:127.0.0.1:8765",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
            $target
        )
        Start-Process -FilePath $ssh -ArgumentList $args -WindowStyle Hidden | Out-Null
    }
    else {
        Write-Host "[3/4] SSH tunnel process already exists."
    }

    $deadline = (Get-Date).AddSeconds(12)
    do {
        Start-Sleep -Milliseconds 500
        $localStatus = Test-LocalDashboard
    } while (-not $localStatus.Ok -and (Get-Date) -lt $deadline)
}
else {
    Write-Host "[3/4] Local tunnel already works."
}

if (-not $localStatus.Ok) {
    throw "Local dashboard is still unavailable: $($localStatus.Error)"
}

Write-Host "[4/4] Opening dashboard..."
Write-Host "Dashboard OK: status=$($localStatus.Status), cycles=$($localStatus.Cycles), errors=$($localStatus.Errors)"
Start-Process "http://127.0.0.1:8765"
