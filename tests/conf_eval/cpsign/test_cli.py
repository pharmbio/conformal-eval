from pytest_console_scripts import ScriptRunner

# Simple test that it works
def test_cli_manual(script_runner: ScriptRunner) -> None:
    result = script_runner.run(['cpsign-report','-h'])
    assert result.returncode == 0