# Installe une tâche planifiée Windows : vérifie le bot toutes les minutes et le relance s'il est mort.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Watchdog = Join-Path $Root "tools\watchdog.ps1"
$TaskName = "WhatsAppBot-Watchdog"

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Watchdog`" -Restart"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.Repetition.Interval = "PT1M"
$trigger.Repetition.Duration = "P3650D"

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Vérifie le bot WhatsApp et le relance s'il ne tourne plus." `
  -Force | Out-Null

Write-Host "Tâche installée : $TaskName (toutes les 1 min)"
Write-Host "Vérifier : Get-ScheduledTask -TaskName $TaskName"
Write-Host "Retirer  : Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
