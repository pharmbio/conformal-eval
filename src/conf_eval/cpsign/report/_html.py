from typing import Optional

import shutil
import zipfile
import json
from pathlib import Path
from typing import Union

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    raise ImportError("The 'report' extras are required to generate a report. Install them with 'pip install conformal-eval[report]'.")
    


_static_sub_dir_name = "_static"
_static_output_dir_name = "static"

_default_page_name = "model-report.html"
_package_dir = Path(__file__).absolute().parent
_template_dir = _package_dir /"_templates"
_figsize = (6,4)

def generate_html(model_file: Union[str, Path],
                  output_file: Union[str, Path] = _default_page_name,
                  validation_file: Optional[Union[str, Path]] = None,
                  info_file: Optional[Union[str, Path]] = None,
                  template_file: Optional[Union[str, Path]] = None,
                  validation_template: Optional[Union[str, Path]] = None) -> None:
    # convert to correct format
    model_file = __resolve_path(model_file)
    output_file = __resolve_path(output_file)
    if validation_file is not None:
        validation_file = __resolve_path(validation_file)
    if info_file is not None:
        info_file = __resolve_path(info_file)
    if template_file is not None:
        template_file = __resolve_path(template_file)
    if validation_template is not None:
        validation_template = __resolve_path(validation_template)

    output_dir, page_name = _setup_output_dir_and_file(output_file)
    static_output_dir = output_dir /_static_output_dir_name
    
    # Validate model_file being a valid path
    if not model_file.exists() or not model_file.is_file():
        raise FileNotFoundError(f"Parameter model_file \"{model_file}\" does not exist or is not a file")
    # Load the meta data about the model
    model_data = {}
    with zipfile.ZipFile(model_file, 'r') as zip_ref:
        # Check if the JSON file exists in the archive
        if 'cpsign.json' in zip_ref.namelist():
            # Extract the JSON file content
            with zip_ref.open('cpsign.json') as json_file:
                # Load the JSON content into a Python dictionary
                model_data = json.load(json_file)
        else:
            raise Exception(f"Parameter model_file \"{model_file}\" is not a valid CPSign model")
               
    
    param_section = model_data['parameters']
    
    
    # Set up data to replace in the template
    cpsign_version = model_data['info']['cpsignVersion'] if model_data['info']['cpsignVersion'] is not None else '<b>Unknown</b>'
    data = {
        'title': 'Model report',
        'heading': 'Model report: {}'.format(param_section['modelName']),
        'cpsign_build_version': cpsign_version,
        'pt_type' : __get_pt_type(param_section['predictor']['mlPredictorType']),
        'n_observations': param_section['data']['nrObservations'],
        'n_features': param_section['data']['nrFeatures'],
        'if_clf': __get_clf_extra_info(param_section['data'])
    }
    # Add hyper-parameter table
    ml_settings_matrix = []
    for key,val in param_section['predictor'].items():
        if key.endswith('Name') and "mlImplementationName" not in key:
            ml_settings_matrix.append([key,val])
    data['ml_settings_table'] = ml_settings_matrix
    
    # Check if custom intro section is present
    if info_file is not None:
        with open(info_file,'r') as info_file:
            data['intro'] = info_file.read()
    
    # Set up the Jinja2 environment
    if template_file is None:
        # this is our default template, should be in the same directory
        env = Environment(loader=FileSystemLoader(_template_dir))
        template = env.get_template('template.html')
    else:
        # Custom template 
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template(template_file)

    ##### MODEL EVALUATION SECTION 
    if validation_file is not None:
        is_cvap = param_section['predictor']['mlPredictorType'] == 5
        # Should add a validation section
        if validation_template is not None:
            # Custom template 
            metrics_env = Environment(loader=FileSystemLoader('.'))
            val_temp = metrics_env.get_template(validation_template)
        else:
            # Fallback default template
            metrics_env = Environment(loader=FileSystemLoader(_template_dir))
            if is_cvap:
                # Venn-ABERS
                val_temp = metrics_env.get_template('vap_metrics_template.html')
            else:
                # Conformal model
                val_temp = metrics_env.get_template('cp_metrics_template.html')
        
        if is_cvap:
            val_html = __generate_cvap_validation_section(validation_file, val_temp, static_output_dir)
        else:
            val_html = __generate_cp_validation_section(validation_file, val_temp, static_output_dir)
        if val_html is not None:
            data['validation_section'] = val_html
            

    # Render the template with the provided data
    html_content = template.render(data)

    # Save the generated HTML to a file
    with (output_dir /page_name).open(mode='w') as file:
        file.write(html_content)
    # Copy all static files for nice output
    shutil.copytree(_package_dir/_static_sub_dir_name, static_output_dir,dirs_exist_ok=True)


def __resolve_path(input_path: Union[str, Path]) -> Path:
    if isinstance(input_path, Path):
        return input_path.expanduser()
    elif isinstance(input_path,str):
        return Path(input_path).expanduser().resolve()
    else:
        raise ValueError('Input was neither a string or Path instance: ' + str(input_path))

def __clear_directory_contents(dir: Path):
    def is_dangerous_path(dir: Path) -> bool:
        # List of paths that should not be cleared
        dangerous_paths = [
            Path.home(),  # User's home directory
            Path("/"),  # Root directory
            # Add any other directories you want to protect
        ]
        
        # Resolve the absolute path and compare with dangerous paths
        dir = dir.resolve()
        # Check if the path or any of its parents is in the dangerous_paths list
        return dir in dangerous_paths or any(dir.parent == path for path in dangerous_paths)

    # make sure to not delete anything important by mistake 
    if is_dangerous_path(dir):
        raise ValueError(f"Refusing to clear directory contents of {dir} due to safety constraints.")
    
    for child in dir.iterdir():  # Replaces dir.walk()
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            __clear_directory_contents(child)  # Recursively clear and delete directories
            child.rmdir()

def __get_pt_type(pt_id) -> str:
    """
    From CPSign:
    (1) ACP_Classification
    (2) ACP_Regression
    (3) TCP_Classification
    (5) VAP_Classification
    """
    if pt_id == 1:
        return "Inductive Conformal Classifier"
    elif pt_id == 2:
        return "Inductive Conformal Regressor"
    elif pt_id == 3:
        return "Transductive Conformal Classifier"
    elif pt_id == 5:
        return "Cross Venn-ABERS Predictor"
    else:
        return "Unknown type"

def __get_clf_extra_info(data_dict):
    labels = data_dict.get('classLabels')
    if labels is None:
        return ""
    labels_lst = ', '.join(list(labels.keys()))
    return f" The dataset contains {len(labels)} classes with the following names: {labels_lst}."
    
def _setup_output_dir_and_file(file_or_dir: Path) -> tuple[str, str]:
    if not isinstance(file_or_dir, Path):
        raise ValueError('Input of incorrect')
    # Decide the output directory of where a directory of where to save things
    if file_or_dir.suffix =='.html':
        # Create output file directory
        # Extract the directory part of the output path
        output_dir = file_or_dir.absolute().parent
        # If empty - use the current working directory
        if output_dir is None:
            output_dir = Path.cwd()
        # set the html file name
        page_name = file_or_dir.name
    else:
        # Otherwise 
        output_dir = file_or_dir
        # Use the default file-name
        page_name = _default_page_name
    
    # Create the dir and static-output dirs if needed
    static_out_dir = output_dir / _static_output_dir_name
    try:
        # Ensure the directory exists
        static_out_dir.mkdir(parents=True,exist_ok=True)
    except Exception as e:
        raise Exception(f'Error when creating output directory: {e}')
    
    # Clear any contents of the static dir
    __clear_directory_contents(static_out_dir)
    
    return output_dir,page_name



def __generate_cp_validation_section(validation_file, validation_template, static_output_dir: str):
    if validation_file is None:
        return None
    
    import conf_eval.cpsign as cpsign
    from conf_eval import plot
    from csv import Sniffer
    
    plot.update_plot_settings(font_scale=1.25)
    
    # Find the delimiter of the CSV
    with open(validation_file, newline='') as csvfile:
        first_mb = csvfile.read(1024).lower()
        dialect = Sniffer().sniff(first_mb)
        # Check if input is regression or classification
        is_regression = "rmse" in first_mb
    
    ### CALIBRATION PLOT
    (sign_vals, error_rates, error_rates_SD, labels) = cpsign.load_calib_stats(validation_file, sep=dialect.delimiter)
    # Validate the standard deviations
    error_rates_SD = error_rates_SD if error_rates_SD is not None and  error_rates.shape == error_rates_SD.shape else None
    calib_fig = plot.plot_calibration(sign_vals=sign_vals, error_rates=error_rates,
                                      error_rates_sd=error_rates_SD, labels=labels,
                                      figsize=_figsize, flip_x=True, flip_y=True, tight_layout=True) 
    calib_fig.savefig(static_output_dir / 'calibration_fig.svg')
    
    ### EFFICIENCY PLOT
    if is_regression:
        # Here define how to read and plot efficiency for a regression output
        (sign_vals, median_widths, mean_widths, median_widths_sd, mean_widths_sd) = cpsign.load_reg_efficiency_stats(validation_file,sep=dialect.delimiter)
        eff_fig = plot.plot_pred_widths(sign_vals = sign_vals, 
                                        pred_widths = median_widths,
                                        pred_widths_sd = median_widths_sd if median_widths_sd is not None and len(median_widths_sd)>0 else None,
                                        flip_x=True,
                                        figsize=_figsize,
                                        tight_layout=True)
        eff_caption = 'Median prediction interval width with respect to confidence level.'
    else:
        # Label distribution is more informative for classification
        res = cpsign.load_clf_efficiency_stats(validation_file,sep=dialect.delimiter)
        if len(res)>4:
            (sign_vals, prop_single, prop_multi, prop_empty, prop_single_sd, prop_multi_sd, prop_empty_sd) = res
        else:
            (sign_vals, prop_single, prop_multi, prop_empty) = res
        eff_fig = plot.plot_label_distribution(sign_vals=sign_vals, prop_single=prop_single, prop_multi = prop_multi, prop_empty=prop_empty, figsize=_figsize, tight_layout=True)
        eff_caption = 'Label distribution plot'
        
    eff_fig.savefig(static_output_dir /'efficiency_fig.svg')
    
    # Generate a table of the other metrics
    metric_dict = cpsign.load_conf_independent_metrics(validation_file,sep=dialect.delimiter)
    metric_table = [[key, value] for key, value in metric_dict.items()]
    
    val_html = validation_template.render({'calib_src' : _static_output_dir_name+'/calibration_fig.svg',
                                           'eff_src' : _static_output_dir_name+'/efficiency_fig.svg',
                                           'eff_caption' : eff_caption,
                                           'metric_table' : metric_table})
    
    return val_html
    
def __generate_cvap_validation_section(validation_file,validation_template,output_dir: str):
    if validation_file is None:
        return None
    
    from .. import load_conf_independent_metrics
    from csv import Sniffer
    
    # Find the delimiter of the CSV
    with open(validation_file, newline='') as csvfile:
        dialect = Sniffer().sniff(csvfile.read(1024))
    
    # Generate a table of the other metrics
    metric_dict = load_conf_independent_metrics(validation_file,sep=dialect.delimiter)
    metric_table = [[key, value] for key, value in metric_dict.items()]
    
    val_html = validation_template.render({'metric_table' : metric_table})
    
    return val_html
    

