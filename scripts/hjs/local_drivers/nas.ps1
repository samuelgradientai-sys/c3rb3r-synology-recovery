param(
  [Parameter(Mandatory=$true)][string]$Script,   # local python file to run remotely
  [string[]]$Argv = @(),
  [int]$TimeoutSec = 60
)
$ErrorActionPreference = 'Continue'
$env:SSH_ASKPASS = "$env:TEMP\dsh_askpass.exe"
$env:SSH_ASKPASS_REQUIRE = 'force'
$env:DISPLAY = 'localhost:0'
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path $Script)))
$quoted = ($Argv | ForEach-Object { "'" + ($_ -replace "'", "'\''") + "'" }) -join ' '
$remote = "echo $b64 | base64 -d > /tmp/_dsh_run.py; timeout $TimeoutSec python3 -u /tmp/_dsh_run.py $quoted"
ssh -T -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ConnectTimeout=15 -o ServerAliveInterval=10 -p 22 hjs@NAS_IP $remote 2>&1
