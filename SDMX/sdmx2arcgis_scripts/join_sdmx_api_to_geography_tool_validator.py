import arcpy
import requests
import json

def parse_fields_and_lookups(dimension_props, attribute_props):
    fields = []
    for obs in dimension_props:
        fields.append({
            'name': '{}_CODE'.format(obs['id']),
            'alias': '{}_CODE'.format(obs['id']),
            'type': 'String'
        })
        
        # arcpy.AddMessage(obs)
        if obs['name'] is None and obs['name']['en'] is None:
            obs['name'] = {'en': obs['name']}

        
        fields.append({
            'name': obs['name']['en'].replace(' ', '_').upper(),
            'alias': obs['name']['en'],
            'type': 'String'
        })
    
    for obs in attribute_props:
        fields.append({
            'name': '{}_CODE'.format(obs['id']),
            'alias': '{}_CODE'.format(obs['id']),
            'type': 'String'
        })
        
        if obs['name'] is None and obs['name']['en'] is None:
            obs['name'] = {'en': obs['name']}

        fields.append({
            'name': obs['id'],
            'alias': obs['name']['en'],
            'type': 'String'
        })

    return fields

def get_sdmx_field_list(in_url):
    response = requests.get(
        in_url, 
        headers={'accept': 'application/vnd.sdmx.data+json;version=1.0.0-wd'}
    )

    if not response:
        return ['Unable to parse SDMX response. Check URL.']
    else:
        res_json = response.json()
        dimension_props = res_json['data']['structure']['dimensions']['observation']
        attribute_props = res_json['data']['structure']['attributes']['observation']
        field_info = parse_fields_and_lookups(dimension_props, attribute_props)
        fields = [f['name'] for f in field_info]
        return fields

class ToolValidator(object):
        
    """Class for validating a tool's parameter values and controlling
    the behavior of the tool's dialog."""

    def __init__(self):
        """Setup arcpy and the list of tool parameters.""" 
        self.params = arcpy.GetParameterInfo()

    def initializeParameters(self):
        """Refine the properties of a tool's parameters. This method is 
        called when the tool is opened."""

        self.params[5].parameterDependencies = [4]

        self.params[2].category = 'Additional Options'
        self.params[3].category = 'Additional Options'
        self.params[4].category = 'Additional Options'
        self.params[5].category = 'Additional Options'
        self.params[9].category = 'Additional Options'
        self.params[10].category = 'Additional Options'

        self.params[10].enabled = False

    def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""

        if self.params[0].altered and not self.params[0].hasBeenValidated:
            self.params[1].filter.list = []
            fields = get_sdmx_field_list(self.params[0].value)
            if fields:
                self.params[1].filter.list = fields
                self.params[1].value = fields[0]
                
                self.params[10].filter.list = fields
                self.params[10].value = fields[0]
            else:
                self.params[0].setErrorMessage('Unable to parse fields from SDMX API. Please make sure your API Query URL is valid')

        if self.params[9].value == True:
            self.params[10].enabled = True
        else:
            self.params[10].enabled = False

    def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True