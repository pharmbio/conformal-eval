from pytest_console_scripts import ScriptRunner
import os
from ....context import output_dir
from ....help_utils import  get_resource

report_out_dir = os.path.join(output_dir,'report')

def _get_path(rel_path):
    return os.path.join(report_out_dir,rel_path)

# Simple test that it works
def test_cli_manual(script_runner: ScriptRunner) -> None:
    result = script_runner.run(['cpsign-report','-h'])
    assert result.returncode == 0
    
def test_incl_custom_cvap(script_runner: ScriptRunner):
    result = script_runner.run(['cpsign-report',
                                '--model-file',get_resource('cvap_linear-2.0.0.jar'),
                                '--info-file',get_resource('custom_model_text.html'),
                                '-of',_get_path('cli_cvap_2')])
    assert result.returncode == 0
    
def test_incl_acp_clf(script_runner: ScriptRunner):
    result = script_runner.run(['cpsign-report',
                                '--model-file',get_resource('acp_clf_linear-2.0.0.jar'),
                                "--output-file", _get_path('cli_clf_2/cp_clf_report.html'),
                                '--validation-file',get_resource('cpsign_clf_stats_excl_sd.csv')])
    assert result.returncode == 0

def test_incl_cp_reg(script_runner: ScriptRunner):
    result = script_runner.run(['cpsign-report',
                                '--model-file',get_resource('acp_reg_rbf-2.0.0.jar'),
                                "--output-file", _get_path('cli_reg_2/cp_clf_report.html'),
                                '--validation-file',get_resource('cpsign_reg_stats_incl_sd.csv')])
    assert result.returncode == 0
    
# Absolute path - cannot be run other than with a specific machine. but it works!
# def test_abs_paths(script_runner: ScriptRunner):
#     result = script_runner.run(['cpsign-report',
#                                 '--model-file',"~/git/cplogd-v2.0/generate_service/trained-model.jar",
#                                 "--output-file", "~/Desktop/model-report-cplogd_v2/model-report-cplod.html",
#                                 '--validation-file',"~/git/cplogd-v2.0/train_and_evaluate_model/output/validation_stats.csv"])
#     assert result.returncode == 0