"This Python file defines functions for reading values from a DataFrame from an Excel Sheet."
import pandas as pd
import numpy as np


def import_variable(excel_data, row, column):
    
    return excel_data.iloc[row, column]

def import_list(excel_data, row, column):
    num_cols = excel_data.shape[1]
    values_list = []
    for col in range(column, 100):
        value = excel_data.iloc[row, col]
        values_list.append(value)

        if col + 1 >= num_cols or pd.isna(excel_data.iloc[row, col + 1]):
            break

    
    return values_list