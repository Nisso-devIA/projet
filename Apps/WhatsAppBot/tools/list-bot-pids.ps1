$ids = @()
Get-CimInstance Win32_Process | ForEach-Object {
  if ($_.CommandLine -and $_.CommandLine -like "*WhatsAppBot*" -and $_.CommandLine -like "*index.js*") {
    $ids += $_.ProcessId
  }
}
$ids -join ","
