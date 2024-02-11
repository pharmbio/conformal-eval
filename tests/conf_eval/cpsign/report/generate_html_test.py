from conf_eval.cpsign.report import generate_html
import pytest
import os
from ....context import output_dir
from ....help_utils import  get_resource


report_out_dir = os.path.join(output_dir,'report')

def _get_path(rel_path):
    return os.path.join(report_out_dir,rel_path)

def test_out_path():
    print("report_out_dir:",report_out_dir)

def test_invalid_input_path_model():
    with pytest.raises(Exception) as e:
        generate_html('some-file.zip','output')
    assert 'some-file.zip' in str(e)

def test_invalid_output_dir():
    with pytest.raises(Exception) as e:
        generate_html(get_resource('acp_clf_linear-2.0.0.jar'),'/some/nonexistent/path/file.html')
    assert '/some' in str(e)

def test_with_only_model_file():
    generate_html(get_resource('acp_clf_linear-2.0.0.jar'),_get_path('clf/cp_clf_report.html'))
    generate_html(get_resource('acp_reg_rbf-2.0.0.jar'),_get_path('reg/cp_reg_report.html'))
    generate_html(get_resource('cvap_linear-2.0.0.jar'),_get_path('cvap/'))
    
    
def test_including_metrics():
    generate_html(get_resource('acp_clf_linear-2.0.0.jar'),_get_path('clf_2/cp_clf_report.html'), get_resource('cpsign_clf_stats_excl_sd.csv'))
    generate_html(get_resource('acp_reg_rbf-2.0.0.jar'),_get_path('reg_2'), get_resource('cpsign_reg_stats_incl_sd.csv'))
    generate_html(get_resource('cvap_linear-2.0.0.jar'),_get_path('cvap_2'),info_file=get_resource('custom_model_text.html'))