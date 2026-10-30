param(
    [string]$ProductCode = '{9C581C76-2D68-40F8-AA6F-94D3C5215C05}'
)

$ErrorActionPreference = 'Stop'

try {
    $driverPath = Join-Path $env:SystemRoot 'System32\drivers\ViGEmBus.sys'
    $service = Get-CimInstance -ClassName Win32_SystemDriver `
        -Filter "Name='ViGEmBus'" -ErrorAction Stop
    $device = Get-CimInstance -ClassName Win32_PnPEntity `
        -Filter "Service='ViGEmBus'" -ErrorAction Stop

    $registered = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$ProductCode",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$ProductCode"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

    $driverFilePresent = Test-Path -LiteralPath $driverPath -PathType Leaf
    $servicePresent = $null -ne $service
    $deviceReady = @($device | Where-Object {
        $_.ConfigManagerErrorCode -eq 0
    }).Count -gt 0

    # Require the live PnP device and running kernel service. Product
    # registration is additional evidence, never the sole test.
    if ($driverFilePresent -and $servicePresent -and
        $service.State -eq 'Running' -and $deviceReady) {
        exit 0
    }

    # A staged driver may need a reboot. Do not run the retired driver's
    # installer a second time against an existing installation.
    if ($driverFilePresent -and ($servicePresent -or $registered)) {
        exit 10
    }

    exit 1
}
catch {
    exit 1
}
