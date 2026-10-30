from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = PROJECT_ROOT / "installer" / "Invoke-ViGEmBusInstall.ps1"


def _powershell() -> Path:
    return Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


@pytest.fixture
def orchestration_runner(tmp_path):
    if sys.platform != "win32":
        pytest.skip("ViGEmBus installer orchestration is Windows-specific")
    powershell = _powershell()
    if not powershell.is_file():
        pytest.skip("Windows PowerShell is not installed")

    state_file = tmp_path / "state counter with spaces.txt"
    detector = tmp_path / "mock detector with spaces.ps1"
    detector.write_text(
        """param([string]$ProductCode)
$StateFile = $env:VIGEM_TEST_STATE_FILE
$InitialState = [int]$env:VIGEM_TEST_INITIAL_STATE
$FinalState = [int]$env:VIGEM_TEST_FINAL_STATE
$count = 0
if (Test-Path -LiteralPath $StateFile) {
    $count = [int](Get-Content -LiteralPath $StateFile -Raw)
}
$count++
Set-Content -LiteralPath $StateFile -Value $count -NoNewline
if ($count -eq 1) { exit $InitialState }
exit $FinalState
""",
        encoding="utf-8",
    )

    def run(initial, final, installer_arguments=None):
        args = [
            str(powershell),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ORCHESTRATOR),
            "-DriverInstaller",
            os.environ["ComSpec"],
            "-DetectionScript",
            str(detector),
            "-ProductCode",
            "{9C581C76-2D68-40F8-AA6F-94D3C5215C05}",
            "-PowerShellPath",
            str(powershell),
        ]
        if installer_arguments is not None:
            args.extend(["-InstallerArguments", installer_arguments])
        env = os.environ.copy()
        env["VIGEM_TEST_STATE_FILE"] = str(state_file)
        env["VIGEM_TEST_INITIAL_STATE"] = str(initial)
        env["VIGEM_TEST_FINAL_STATE"] = str(final)
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=20, env=env
        )
        return result, state_file

    return run


def test_orchestrator_skips_a_working_driver(orchestration_runner):
    result, state_file = orchestration_runner(0, 1)

    assert result.returncode == 0
    assert state_file.read_text(encoding="utf-8") == "1"


def test_orchestrator_runs_driver_once_and_verifies_success(orchestration_runner):
    result, state_file = orchestration_runner(1, 0, "/c exit 0")

    assert result.returncode == 0
    assert state_file.read_text(encoding="utf-8") == "2"


def test_orchestrator_reports_driver_failure_without_retrying(orchestration_runner):
    result, state_file = orchestration_runner(1, 1, "/c exit 1603")

    assert result.returncode == 1603
    assert state_file.read_text(encoding="utf-8") == "2"


def test_orchestrator_reports_restart_without_restarting_windows(orchestration_runner):
    result, state_file = orchestration_runner(1, 1, "/c exit 3010")

    assert result.returncode == 10
    assert state_file.read_text(encoding="utf-8") == "2"
