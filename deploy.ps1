<#
  deploy.ps1 - copy a FWFS601T.BIN to an SD card for the Reflecta DigitDia Evolution (run from SD, never flashes).

  Usage:  .\deploy.ps1 -Drive E [-Bin out\pldr\FWFS601T.BIN] [-Label MYCARD]

  Guards:
    - the drive exists and is FAT32 (the bootloader can't read exFAT); with -Label, the volume label must match
    - the file starts with "BCL1" and its size is a multiple of 4 (otherwise the bootloader hangs)
    - refuses if FWFS601A.BIN or LDFS601A.BIN is on the card (those names WRITE the flash)
    - verifies the copy by SHA256 and flushes the write cache
  Then: eject the card, insert it into the powered-off scanner, power on. Delete the file to return to stock.
#>
param(
  [Parameter(Mandatory=$true)][string]$Drive,
  [string]$Bin = "",
  [string]$Label = ""
)
$ErrorActionPreference = "Stop"
function Die([string]$m){ Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
$Drive = $Drive.TrimEnd(':','\')
if(-not $Bin){ $Bin = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "out\pldr\FWFS601T.BIN" }  # PS 5.1: no $PSScriptRoot in param defaults

if(-not (Test-Path $Bin)){ Die "$Bin not found (build it with: python make_pldr.py)" }
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Bin))
if([System.Text.Encoding]::ASCII.GetString($bytes,0,4) -ne "BCL1"){ Die "$Bin is not a BCL1 firmware file" }
if($bytes.Length % 4 -ne 0){ Die "$Bin size $($bytes.Length) is not a multiple of 4 - the bootloader would hang" }

if(-not (Test-Path "${Drive}:\")){ Die "drive ${Drive}: not present" }
$vol = Get-Volume -DriveLetter $Drive
if($Label -and $vol.FileSystemLabel -ne $Label){ Die "${Drive}: is labelled '$($vol.FileSystemLabel)', expected '$Label'" }
if($vol.FileSystem -ne "FAT32"){ Die "${Drive}: is $($vol.FileSystem); the bootloader only reads FAT32" }
foreach($bad in @("FWFS601A.BIN","LDFS601A.BIN")){
  if(Test-Path "${Drive}:\$bad"){ Die "${Drive}:\$bad is on the card - that file makes the bootloader WRITE flash. Remove it first." }
}

$dst = "${Drive}:\FWFS601T.BIN"
Copy-Item $Bin $dst -Force
$h1 = (Get-FileHash $Bin -Algorithm SHA256).Hash
$h2 = (Get-FileHash $dst -Algorithm SHA256).Hash
if($h1 -ne $h2){ Die "copy verification failed" }
Write-VolumeCache -DriveLetter $Drive -ErrorAction SilentlyContinue
Write-Host "deployed -> $dst ($($bytes.Length) bytes, SHA256 $($h1.Substring(0,16))..., cache flushed)"
Write-Host "Now eject the card, insert it into the powered-OFF scanner, power on."
