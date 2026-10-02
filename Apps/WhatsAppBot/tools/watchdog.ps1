# Vérifie le bot WhatsApp. Avec -Restart, le relance s'il est mort.
param(
  [switch]$Restart,
  [switch]$Loop,
  [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Check {
  & node "$Root\tools\check-bot.js"
  return $LASTEXITCODE
}

function Start-Bot {
  Write-Host "Relance du bot…"
  $hbPath = Join-Path $Root "state\heartbeat.json"
  if (Test-Path $hbPath) {
    try {
      $hb = Get-Content $hbPath -Raw | ConvertFrom-Json
      if ($hb.pid) {
        Stop-Process -Id ([int]$hb.pid) -Force -ErrorAction SilentlyContinue
      }
    } catch { }
  }
  Start-Process -FilePath "npm.cmd" -ArgumentList "start" -WorkingDirectory $Root -WindowStyle Hidden
}

function Invoke-Once {
  $code = Invoke-Check
  if ($Restart -and $code -eq 1) {
    Start-Bot
    Start-Sleep -Seconds 8
    return Invoke-Check
  }
  return $code
}

if ($Loop) {
  while ($true) {
    Invoke-Once | Out-Null
    Start-Sleep -Seconds $IntervalSeconds
  }
} else {
  exit (Invoke-Once)
}
