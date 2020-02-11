import arcpy
import json
import os
import csv
import glob

def has_csv_files(in_csv_folder):
    files = glob.glob(f'{in_csv_folder}/*.csv')
    if len(files) == 0:
        return {'found': False, 'message': f'No CSV files found in \'{in_csv_folder}\''}

    return {'found': True}

def peek_pxw_fields(in_csv_folder, in_field):
    for fname in glob.glob(f'{in_csv_folder}/*.csv'):
        try:
            with open(fname) as csvfile:
                reader = csv.DictReader(csvfile)
                if in_field not in reader.fieldnames:
                    return {'found': False, 'message': f'Field \'{in_field}\' was not found in file \'{fname}\''}
        except:
            return {'found': False, 'message': f'unable to open file \'{fname}\''}
    
    return {'found': True}

class ToolValidator(object):
        
    """Class for validating a tool's parameter values and controlling
    the behavior of the tool's dialog."""

    def __init__(self):
        """Setup arcpy and the list of tool parameters.""" 
        self.params = arcpy.GetParameterInfo()

    def initializeParameters(self):
        """Refine the properties of a tool's parameters. This method is 
        called when the tool is opened."""

        self.params[4].parameterDependencies = [3]

        self.params[6].category = 'Additional Options'
        self.params[7].category = 'Additional Options'
        self.params[8].category = 'Additional Options'
        self.params[9].category = 'Additional Options'

        self.params[8].enabled = False

    def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""

        if not self.params[0].hasBeenValidated:
            self.params[1].value = ''      

        if self.params[7].value == True:
            self.params[8].enabled = True
        else:
            self.params[8].enabled = False
        
    def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        
        if self.params[0].value:
            check = has_csv_files(self.params[0].value)
            if not check['found']:
                self.params[0].setErrorMessage(check['message'])

        if self.params[0].value and self.params[1].value:
            check = peek_pxw_fields(self.params[0].value, self.params[1].value)
            if not check['found']:
                self.params[1].setErrorMessage(check['message'])

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True