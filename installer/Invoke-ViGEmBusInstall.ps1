param(
    [Parameter(Mandatory = $true)]
    [string]$DriverInstaller,

    [Parameter(Mandatory = $true)]
    [string]$DetectionScript,

    [Parameter(Mandatory = $true)]
    [string]$ProductCode,

    [string]$PowerShellPath = (Join-Path $env:SystemRoot 'WindowsPowerShell\v1.0\powershell.exe'),

    [string]$InstallerArguments = '/exenoui /qn /norestart'
)

$ErrorActionPreference = 'Stop'

function Get-DriverState {
    & $PowerShellPath -NoProfile -NonInteractive -ExecutionPolicy Bypass `
        -File $DetectionScript -ProductCode $ProductCode
    return $LASTEXITCODE
}

try {
    $state = Get-DriverState
    if ($state -eq 0) {
        exit 0
    }
    if ($state -eq 10) {
        # The driver is staged but may need a reboot. Never rerun this retired
        # package in a loop or as an in-place repair.
        exit 10
    }

    $process = Start-Process -FilePath $DriverInstaller `
        -ArgumentList $InstallerArguments -Wait -PassThru -WindowStyle Hidden
    $installerExitCode = [int]$process.ExitCode

    $state = Get-DriverState
    if ($state -eq 0) {
        exit 0
    }

    if ($state -eq 10 -or $installerExitCode -in @(3010, 1641)) {
        exit 10
    }

    if ($installerExitCode -ne 0) {
        exit $installerExitCode
    }

    # The installer returned success, but the service/PnP checks did not
    # confirm a working bus and Windows did not report a reboot requirement.
    exit 20
}
catch {
    exit 21
}
