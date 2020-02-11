import arcpy
import requests
import json
import jsonstat

def load_pxweb_post_params(in_path):
    json_params = None
    with open(in_path, encoding='utf-8') as json_file:
        json_params = json.load(json_file)
    return json_params

def get_pxweb_field_list(in_url, post_body_params):
    return_values = {'success': False, 'fields': []}
    
    response = None
    try:
        response = requests.post(in_url, json=post_body_params)
    except requests.exceptions.RequestException as e:
        return_values['message'] = e
        return return_values
   
    if not response:
        return_values['message'] = response.text
    else:
        res_json = response.json()
        jstat = jsonstat.from_json(res_json)
        dataset = jstat.dataset(0)
        for f in dataset.dimensions():
            list_value = f'{f.did} - {f.label}'
            return_values['fields'].append(list_value)

        return_values['success'] = True

    return return_values

class ToolValidator(object):
        
    """Class for validating a tool's parameter values and controlling
    the behavior of the tool's dialog."""

    def __init__(self):
        """Setup arcpy and the list of tool parameters.""" 
        self.params = arcpy.GetParameterInfo()

    def initializeParameters(self):
        """Refine the properties of a tool's parameters. This method is 
        called when the tool is opened."""

        if self.params[0].value and self.params[1].value:
            self.params[2].filter.list = []
            json_body_params = load_pxweb_post_params(self.params[1].value.value)
            return_values = get_pxweb_field_list(self.params[0].value, json_body_params)
            if return_values['success']:
                self.params[2].filter.list = return_values['fields']
                self.params[2].value = return_values['fields'][0]
            else:
                err_msg = return_values['message']
                self.params[2].filter.list = [f'Unable to parse PxWeb API :: {err_msg}']

        self.params[8].category = 'Additional Options'
        self.params[9].category = 'Additional Options'
        self.params[10].category = 'Additional Options'
        self.params[11].category = 'Additional Options'
        self.params[12].category = 'Additional Options'

    def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""

        if (self.params[0].altered and not self.params[0].hasBeenValidated) or (self.params[1].altered and not self.params[1].hasBeenValidated):
            self.params[2].filter.list = []
            json_body_params = load_pxweb_post_params(self.params[1].value.value)
            return_values = get_pxweb_field_list(self.params[0].value, json_body_params)
            if return_values['success']:
                self.params[2].filter.list = return_values['fields']
                self.params[2].value = return_values['fields'][0]
            else:
                err_msg = return_values['message']
                self.params[2].filter.list = [f'Unable to parse PxWeb API :: {err_msg}']

        # if using calculated area field for join, disable drop-down for selecting pxw join field from table
        if self.params[8].value == True:
            self.params[2].enabled = False
        else:
            self.params[2].enabled = True

        if self.params[11].value == True:
            self.params[12].enabled = True
        else:
            self.params[12].enabled = False

    def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True