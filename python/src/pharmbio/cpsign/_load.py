"""Utility functions for loading and converting datasets
"""

import numpy as np
from sklearn.utils import Bunch
import pandas as pd
import re
from sklearn.utils import check_consistent_length


def load_calib_stats(f,
                     sep=',',
                     # Calibration metrics
                     overall_accuracy_regex = r'^accuracy$',
                     overall_accuracy_sd_regex = r'^accuracy_SD$',
                     accuracy_regex = r'^accuracy\((.*?)\)$',
                     accuracy_sd_regex = r'^accuracy\((.*?)\)_SD$'
                     ):
    '''
    Read a CSV formatted file with overall statistics (e.g. from CPSign)

    Parameters
    ----------
    f : file or file path

    sep : column-separator, str, default ','
        Character that separate columns in the CSV

    Returns
    -------
        (sign_vals, error_rates, error_rates_SD, labels)
    '''
    # Convert to regex if not already given
    overall_accuracy_regex = __get_regex_or_None(overall_accuracy_regex)
    overall_accuracy_sd_regex = __get_regex_or_None(overall_accuracy_sd_regex)
    accuracy_regex = __get_regex_or_None(accuracy_regex)
    accuracy_sd_regex = __get_regex_or_None(accuracy_sd_regex)

    df = pd.read_csv(f,sep=sep)
    sign_vals = 1 - df.iloc[:,0].to_numpy()
    n_rows = len(sign_vals)

    # Create two lists, to make sure they are in the same order 
    labels = [] 
    sd_labels = []
    accuracies = np.empty((n_rows,0))
    accuracies_sd = np.empty((n_rows,0))

    for i, c in enumerate(df.columns):
        if __matches(overall_accuracy_regex,c):
            overall = df.iloc[:,i].to_numpy().reshape((n_rows,1))
        elif __matches(overall_accuracy_sd_regex,c):
            overall_sd = df.iloc[:,i].to_numpy().reshape((n_rows,1))
        elif __matches(accuracy_regex,c):
            accuracies = np.hstack((accuracies, df.iloc[:,i].to_numpy().reshape(n_rows,1)))
            # Add label for this value
            labels.append(accuracy_regex.match(c).group(1))
        elif __matches(accuracy_sd_regex, c):
            accuracies_sd = np.hstack((accuracies_sd, df.iloc[:,i].to_numpy().reshape(n_rows,1)))
            # Add label for this value
            sd_labels.append(accuracy_sd_regex.match(c).group(1))
    # Overall stuff
    check_consistent_length(sign_vals,overall)

    # Only in case several accuracies (i.e. one per label)
    if accuracies.shape[1]>0:
        check_consistent_length(sign_vals,accuracies)
        if len(sd_labels)>0:
            check_consistent_length(sign_vals, accuracies_sd, overall_sd)
        if sd_labels is not None and sd_labels != labels:
            raise ValueError('Inconsistent input file, different labels for accuracies and SD versions')
            
        accuracies = np.hstack((overall, accuracies))
        accuracies_sd = np.hstack((overall_sd,accuracies_sd))
        labels = ['Overall'] + labels # pre-pend the overall label

        return sign_vals, 1 - accuracies, accuracies_sd, labels
    else:
        # Only overall accuracy given
        return sign_vals, 1-overall, overall_sd, ['Overall']


def load_reg_efficiency_stats(f, 
                              sep=',',
                              median_regex = r'.*median.*prediction.*interval.*width.*(?<!_sd)$',
                              mean_regex = r'.*mean.*prediction.*interval.*width.*(?<!_sd)$',
                              median_sd_regex = r'.*median.*prediction.*interval.*width.*_sd$',
                              mean_sd_regex = r'.*mean.*prediction.*interval.*width.*_sd$'
                              ):
    '''
    
    Returns
    -------
        (sign_vals, median_widths, mean_widths)
        or
        (sign_vals, median_widths, mean_widths, median_widths_sd, mean_widths_sd)
    '''

    df = pd.read_csv(f, sep=sep)
    median_regex = __get_regex_or_None(median_regex)
    mean_regex = __get_regex_or_None(mean_regex)
    # Standard deviation variants
    median_sd_regex = __get_regex_or_None(median_sd_regex)
    mean_sd_regex = __get_regex_or_None(mean_sd_regex)

    sign_regex = re.compile(r'^significance',re.IGNORECASE)
    conf_regex = re.compile(r'^confidence', re.IGNORECASE)
    # Init all values, so they are None if they are missing
    sign_vals = None
    conf_vals = None
    mean_vals = None
    mean_vals_sd = None
    median_vals = None
    median_vals_sd = None

    for i, c in enumerate(df.columns):
        if __matches(sign_regex, c):
            sign_vals = df.iloc[:,i]
        elif __matches(conf_regex,c):
            conf_vals = df.iloc[:,i]
        elif __matches(median_regex, c):
            median_vals = df.iloc[:,i]
        elif __matches(mean_regex, c):
            mean_vals = df.iloc[:,i]
        elif __matches(median_sd_regex, c):
            median_vals_sd = df.iloc[:,i]
        elif __matches(mean_sd_regex, c):
            mean_vals_sd = df.iloc[:,i]
    
    if sign_vals is None and conf_vals is None:
        raise ValueError('No significance or confidence levels given, invalid input')

    # Convert confidence levels into significance levels     
    sign_vals = 1 - conf_vals.to_numpy() if sign_vals is None else sign_vals

    if median_vals_sd is None and mean_vals_sd is None:
        return sign_vals, median_vals, mean_vals
    else:
        return sign_vals,  median_vals, mean_vals, median_vals_sd, mean_vals_sd

def load_reg_predictions(f,
    y_true_col,
    sep = ',',
    lower_regex=r'^prediction.*interval.*lower.*\d+',
    upper_regex=r'^prediction.*interval.*upper.*\d+',
    specifies_significance=None):
    """Loads a CSV file with predictions and converts to the format used by Plot_utils

    The required format is that the csv has;
    - A header
    - Specifies significance or confidence in the header names of the 'lower' and 'upper' columns
    - Those headers must only contain a single number

    Note that there is no requirement for a true label to exist, the `y_true_col` can be set to None and no y-labels will be returned

    Parameters
    ----------
    f : str or buffer
        File path or buffer that `Pandas.read_csv` can read
    
    y_true_col : str or None
        The (case insensitive) column header of the true labels, or None if it should not be loaded
    
    sep : str, default ','
        Delimiter that is used in the CSV between columns
    
    lower_regex, upper_regex : str or re.Pattern
        Regex used for finding columns of the lower and upper interval limits. Must match the column headers
    
    specifies_significance : bool or None, default None
        If the numbers in the headers are significance level (True) or confidence (False). If None, the first column-header found by `lower_regex` will be used to check for occurrences of 'significance' or 'conf' to try to infer what is used

    Returns
    -------
    (y, pred_matrix, sign_values)
    """

    lower_regex = __get_regex_or_None(lower_regex)
    upper_regex = __get_regex_or_None(upper_regex)
    num_pattern = re.compile('\d*\.\d*')
    y_col_lc = None if y_true_col is None else y_true_col.lower()
    y_true_ind = None
    
    df = pd.read_csv(f,sep=sep)
    low_ind, upp_ind, sign_low, sign_upp = [], [], [], []
    for i, c in enumerate(df.columns):
        if lower_regex.match(c) is not None:
            low_ind.append(i)
            sign_low.append(float(num_pattern.findall(c)[0]))
        elif upper_regex.match(c) is not None:
            upp_ind.append(i)
            sign_upp.append(float(num_pattern.findall(c)[0]))
        elif y_col_lc is not None and c.lower() == y_col_lc:
            y_true_ind = i

    # Some validation
    assert sign_low == sign_upp
    assert len(low_ind) == len(upp_ind)
    if not isinstance(specifies_significance,bool):
        col_lc = df.columns[low_ind[0]].lower()
        contains_sign =col_lc.__contains__('significance')
        contains_conf = col_lc.__contains__('confidence')

        if (contains_sign and contains_conf) or (not contains_sign and not contains_conf):
            raise ValueError('Parameter \'specifies_significance\' not set, could not deduce if significance or confidence is used. Explicitly set this parameter and try again')
        
        specifies_significance = True if contains_sign else False

    sign_vals = np.array(sign_low) if specifies_significance else 1 - np.array(sign_low)
    
    y, p = convert_regression(df,y_true_ind,low_ind,upp_ind)
    return y, p, sign_vals


def convert_regression(data,
    y_true_index,
    min_index,
    max_index):
    """
    Converts a 2D input matrix to a 3D ndarray that
    is required by the metrics and plotting functions
    
    Parameters
    ----------
    data : 2d array like
        Data matrix that must be convertible to 2D ndarray
    
    y_true_index : int or None
        Column index that the ground truth values are, or None if no 
        y values should be generated. Output `y` will then be None
    
    min_index, max_index : list or array of int
        Column indices for min and max values for prediction intervals
    
    Returns
    -------
    (y, predictions)
        y : 1D ndarray
            The y_true values or None if `y_true_index` is None
        
        predictions : 3D ndarray
            matrix of shape (n_examples, 2, n_significance_levels), where the second
            dimension is [min, max] of the prediction intervals
    """
    if not isinstance(data,np.ndarray):
        data = np.asarray(data)
    if data.ndim != 2:
        raise ValueError('Input must be a 2D array type')
    
    ys = data[:,y_true_index].astype(np.float64) if y_true_index is not None else None

    if len(min_index) != len(max_index):
        raise ValueError('min_index and max_index must be of same length')
    
    # Allocate matrix
    preds = np.zeros((len(data),2,len(min_index)),dtype=np.float64)

    for s, (min,max) in enumerate(zip(min_index,max_index)):
        preds[:,0,s] = data[:,min]
        preds[:,1,s] = data[:,max]

    # Return tuple
    return (ys, preds)




def load_clf_efficiency_stats(f,
                              sep=',',
                              prop_s_regex=r'prop.*single.*sets$',
                              prop_m_regex=r'prop.*multi.*sets$',
                              prop_e_regex=r'prop.*empty.*sets$',
                              prop_s_sd_regex=r'prop.*single.*_SD$',
                              prop_m_sd_regex=r'prop.*multi.*_SD$',
                              prop_e_sd_regex=r'prop.*empty.*_SD$'
                              ):
    '''
    Returns
    -------
        (sign_vals, prop_single, prop_multi, prop_empty) or
        (sign_vals, prop_single, prop_multi, prop_empty, prop_single_sd, prop_multi_sd, prop_empty_sd)
    '''
    df = pd.read_csv(f, sep=sep)
    prop_s_regex = __get_regex_or_None(prop_s_regex)
    prop_m_regex = __get_regex_or_None(prop_m_regex)
    prop_e_regex = __get_regex_or_None(prop_e_regex)
    # Standard deviation variants
    prop_s_sd_regex = __get_regex_or_None(prop_s_sd_regex)
    prop_m_sd_regex = __get_regex_or_None(prop_m_sd_regex)
    prop_e_sd_regex = __get_regex_or_None(prop_e_sd_regex)

    sign_regex = re.compile(r'^significance',re.IGNORECASE)
    conf_regex = re.compile(r'^confidence', re.IGNORECASE)
    # Init all values, so they are None if they are missing
    sign_vals = None
    conf_vals = None
    prop_single = None
    prop_single_sd = None
    prop_multi = None
    prop_multi_sd = None
    prop_empty = None
    prop_empty_sd = None


    for i, c in enumerate(df.columns):
        if __matches(sign_regex, c):
            sign_vals = df.iloc[:,i]
        elif __matches(conf_regex,c):
            conf_vals = df.iloc[:,i]
        elif __matches(prop_s_regex, c):
            prop_single = df.iloc[:,i]
        elif __matches(prop_m_regex, c):
            prop_multi = df.iloc[:,i]
        elif __matches(prop_e_regex, c):
            prop_empty = df.iloc[:,i]
        elif __matches(prop_s_sd_regex, c):
            prop_single_sd = df.iloc[:,i]
        elif __matches(prop_m_sd_regex, c):
            prop_multi_sd = df.iloc[:,i]
        elif __matches(prop_e_sd_regex, c):
            prop_empty_sd = df.iloc[:,i]
    
    if sign_vals is None and conf_vals is None:
        raise ValueError('No significance or confidence levels given, invalid input')

    # Convert confidence levels into significance levels     
    sign_vals = 1 - conf_vals.to_numpy() if sign_vals is None else sign_vals

    if prop_single_sd is None and prop_multi_sd is None and prop_empty_sd is None:
        return sign_vals, prop_single, prop_multi, prop_empty
    else:
        return sign_vals, prop_single, prop_multi, prop_empty, prop_single_sd, prop_multi_sd, prop_empty_sd


    



def load_clf_predictions(f, y_true_col, sep=',', pvalue_regex=r'p-value\s+\[label=(?P<label>[^\]]+)\]'):
    '''
    Parameters
    ----------
    f : str or buffer
        File path or buffer that `Pandas.read_csv` can read
    
    y_true_col : str or None
        The (case insensitive) column header of the true labels, or None if it should not be loaded

    sep : str, default ','
        Delimiter that is used in the CSV between columns

    pvalue_regex : str, re.Pattern
        A regular expression for getting column headers matching those that should contain p-values, and that 
        retrieves the textual label for the p-value

    Returns
    -------
        (y_true, p_values, labels)
        
        
    '''
    df = pd.read_csv(f, sep=sep)
    n_rows = len(df)

    pvalue_regex = __get_regex_or_None(pvalue_regex)
    y_label_lc = None if y_true_col is None else y_true_col.lower()

    y = None
    pvals = np.empty((n_rows,0))
    labels = []

    for i, c in enumerate(df.columns):
        if y_label_lc is not None and c.lower() == y_label_lc:
            y = df.iloc[:,i]
        elif __matches(pvalue_regex,c):
            pvals = np.hstack((pvals,df.iloc[:,i].to_numpy().reshape((n_rows,1))))
            labels.append(pvalue_regex.match(c).group('label'))

    return y, pvals, labels


def __get_regex_or_None(input):
    if input is None:
        return None
    if isinstance(input, re.Pattern):
        # Correct type already
        return input
    # Try to convert into re.Pattern
    return re.compile(input,re.IGNORECASE)
    

def __matches(regex, txt):
    if regex is None:
        return False
    return regex.match(txt) is not None