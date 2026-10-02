# One-shot YouTube OAuth on Windows → youtube-oauth.json for the VPS
#
# 1) Google Cloud Console → create project → enable "YouTube Data API v3"
# 2) APIs & Services → Credentials → Create OAuth client ID (Desktop app)
# 3) Download JSON as client_secret.json next to this script (or pass -ClientSecrets)
# 4) Run:
#      powershell -ExecutionPolicy Bypass -File tools\youtube-oauth-setup.ps1
# 5) Script uploads token to VPS if -Deploy is set

param(
  [string]$ClientSecrets = "",
  [string]$OutFile = "$PSScriptRoot\..\config\youtube-oauth.json",
  [switch]$Deploy
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $ClientSecrets) {
  $candidates = @(
    (Join-Path $Root "config\youtube-client-secrets.json"),
    (Join-Path $Root "config\client_secret.json"),
    (Join-Path (Get-Location) "client_secret.json")
  )
  foreach ($c in $candidates) {
    if (Test-Path $c) { $ClientSecrets = $c; break }
  }
}

if (-not $ClientSecrets -or -not (Test-Path $ClientSecrets)) {
  Write-Host @"
MISSING client_secret.json

Create it in Google Cloud Console:
  1. https://console.cloud.google.com/
  2. Enable YouTube Data API v3
  3. Credentials → Create OAuth client ID → Desktop
  4. Download JSON → save as:
     $Root\config\youtube-client-secrets.json

Then re-run this script.
"@
  exit 1
}

pip install -q google-auth google-auth-oauthlib google-api-python-client
python "$Root\tools\youtube-oauth-setup.py" --client-secrets "$ClientSecrets" --out "$OutFile"
Write-Host "Wrote $OutFile"

if ($Deploy) {
  $key = "C:\Users\nacim\Documents\projet\vps to\ssh-key-2026-08-22.key"
  scp -i $key -o StrictHostKeyChecking=no "$OutFile" ubuntu@88.96.45.10:/home/ubuntu/zaeldryk/config/youtube-oauth.json
  scp -i $key -o StrictHostKeyChecking=no "$ClientSecrets" ubuntu@88.96.45.10:/home/ubuntu/zaeldryk/config/youtube-client-secrets.json
  ssh -i $key -o StrictHostKeyChecking=no ubuntu@88.96.45.10 "chmod 600 /home/ubuntu/zaeldryk/config/youtube-oauth.json /home/ubuntu/zaeldryk/config/youtube-client-secrets.json"
  Write-Host "Deployed OAuth files to VPS"
}
