import arcpy
import requests
import json
import csv

def get_pxw_field_list(in_csv_file):
    try:
        with open(in_csv_file) as csvfile:
            reader = csv.DictReader(csvfile)
            return reader.fieldnames
    except csv.Error as e:
        return [f'{e}']

class ToolValidator(object):
        
    """Class for validating a tool's parameter values and controlling
    the behavior of the tool's dialog."""

    def __init__(self):
        """Setup arcpy and the list of tool parameters.""" 
        self.params = arcpy.GetParameterInfo()

    def initializeParameters(self):
        """Refine the properties of a tool's parameters. This method is 
        called when the tool is opened."""
        
        if self.params[0].value:
            self.params[1].filter.list = []
            fields = get_pxw_field_list(self.params[0].value.value)
            if fields:
                self.params[1].filter.list = fields
                self.params[1].value = fields[0]
            else:
                self.params[0].setErrorMessage('Unable to parse fields from PxWeb CSV file.')


        self.params[7].category = 'Additional Options'
        self.params[8].category = 'Additional Options'
        self.params[9].category = 'Additional Options'
        self.params[10].category = 'Additional Options'

        self.params[9].enabled = False

    def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""

        if self.params[0].altered and not self.params[0].hasBeenValidated:
            self.params[1].filter.list = []
            fields = get_pxw_field_list(self.params[0].value.value)
            if fields:
                self.params[1].filter.list = fields
                self.params[1].value = fields[0]
            else:
                self.params[0].setErrorMessage('Unable to parse fields from PxWeb CSV file.')

        if self.params[8].value == True:
            self.params[9].enabled = True
        else:
            self.params[9].enabled = False

    def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True