import arcpy
import os
import shutil
import json
import csv
import requests
from datetime import datetime
from dateutil import parser
from pathlib import Path

def create_working_directory():
    now_ts = datetime.now().strftime('%Y%m%d%H%M%S')
    
    current_wd = Path(os.path.dirname(os.path.realpath(__file__)))
    
    job_ws_foldername = f'job_tmp_files_{now_ts}'

    full_job_path = current_wd.joinpath(job_ws_foldername)
    full_job_path.mkdir()

    return [full_job_path, now_ts]

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

def query_and_parse_sdmx(in_url):
    response = requests.get(
        in_url, 
        headers={'accept': 'application/vnd.sdmx.data+json;version=1.0.0-wd'}
    )

    if response:
        res_json = response.json()

        try:
            dimension_props = res_json['data']['structure']['dimensions']['observation']
            attribute_props = res_json['data']['structure']['attributes']['observation']
            fields = parse_fields_and_lookups(dimension_props, attribute_props)
            obs = res_json['data']['dataSets'][0]['observations']
            res_count = len(obs.keys())
        except:
            arcpy.AddError('unable to parse SDMX response from \'{}\''.format(in_url))
            raise arcpy.ExecuteError

        return { 
            'dimension_props': dimension_props,
            'attribute_props': attribute_props, 
            'obs': obs, 
            'fields': fields,
            'res_count': res_count 
        }

def convert_sdmx_json_to_csv(sdmx_response):
    observations = sdmx_response['obs']
    dimension_props = sdmx_response['dimension_props']
    attribute_props = sdmx_response['attribute_props']

    features = []

    for obs in observations:
        feature = {}

        dim_splits = obs.split(':')
        attributes = observations[obs]

        for i, current_key_str in enumerate(dim_splits):
            current_key_int = int(current_key_str)
            found_dim = [dim for dim in dimension_props if dim['keyPosition'] == i][0]
            
            if found_dim is not None:
                if found_dim['id'] == 'TIME_PERIOD':
                    tv = parser.parse(found_dim['values'][current_key_int]['name']['en'])
                    feature['{}_CODE'.format(found_dim['id'])] = datetime.strftime(tv, '%Y-%m')
                    feature['{}'.format(found_dim['name']['en'].upper().replace(' ', '_'))] = datetime.strftime(tv, '%Y-%m')
                else:
                    feature['{}_CODE'.format(found_dim['id'])] = found_dim['values'][current_key_int]['id']
                    feature['{}'.format(found_dim['name']['en'].upper().replace(' ', '_'))] = found_dim['values'][current_key_int]['name']['en']

        obs_value = attributes[0]
        feature['OBS_VALUE'] = obs_value
    
        attributes.pop(0)

        for j, attValue in enumerate(attributes):
            att_value = attributes[j]
            found_att = attribute_props[j]

            if att_value is None:
                feature['{}_CODE'.format(found_att['id'])] = None
                feature[found_att['id'].upper().replace(' ', '_')] = None
            else:
                feature['{}_CODE'.format(found_att['id'])] = found_att['values'][att_value]['id']
                feature[found_att['id'].upper().replace(' ', '_')] = found_att['values'][att_value]['name']['en']

        features.append(feature)
    
    return features

def create_csv_file(sdmx_csv_rows, sdmx_field_names, full_job_path):
    file_name = 'fromSDMXapi.csv'
    full_path_to_file = full_job_path.joinpath(file_name)

    with open(full_path_to_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sdmx_field_names)
        writer.writeheader()

        for row in sdmx_csv_rows:
            writer.writerow(row)
    
    return full_path_to_file.resolve()

def get_geom(geo_field, geo_value, join_field_type):
    global geom_cache
    global geo_fl

    # if join_field_type == 'TEXT':
    #     geo_value = f"'{geo_value}'"

    wc = """{0} = '{1}'""".format(arcpy.AddFieldDelimiters(geo_fl, geo_field), geo_value)
    # arcpy.AddMessage(wc)
    if geo_value in geom_cache:
        # arcpy.AddMessage(f'got from cache for {geo_value}')
        return geom_cache[geo_value]
    else:
        geom = None
        row = next(arcpy.da.SearchCursor(geo_fl, ['SHAPE@', geo_field],where_clause=wc))
        if row and len(row) > 0:
            # arcpy.AddMessage(row)
            geom = row[0]
            geo_val_to_add = row[1]
            geom_cache[geo_val_to_add] = geom
        else:
            arcpy.AddMessage(f'Unable to get geometry from Geography layer. The where_clause, {wc} did not return results.')

        return geom

################
# SCRIPT START #
################

# get input parameters
in_sdmx_api_url = arcpy.GetParameterAsText(0)
in_sdmx_join_field = arcpy.GetParameterAsText(1)

in_should_replace_codes_with_values = arcpy.GetParameter(2)
in_should_update_field_aliases_on_output = arcpy.GetParameter(3)
in_api_has_alias_information = arcpy.GetParameter(4)
in_codelists_file = arcpy.GetParameter(5)

in_geo_table = arcpy.GetParameter(6)
in_geo_join_field = arcpy.GetParameterAsText(7)

global geom_cache
geom_cache = {}
global geo_fl
geo_fl = 'geo_fl'
arcpy.MakeFeatureLayer_management(in_geo_table, geo_fl)

in_geo_fl_desc = arcpy.Describe(geo_fl)
in_geo_field_info = in_geo_fl_desc.fieldInfo

in_output_workspace = arcpy.GetParameterAsText(8)
in_use_field_value_for_outputname = arcpy.GetParameter(9)
in_sdmx_field_for_outputname = arcpy.GetParameterAsText(10)
in_output_filename = arcpy.ValidateTableName(arcpy.GetParameterAsText(11))

# in_save_temp_files = arcpy.GetParameter(13)

arcpy.SetProgressor('default', 'Creating working directory ...')
# create working directory
wd_res = create_working_directory()
full_job_path = wd_res[0]
now_ts = wd_res[1]

arcpy.SetProgressor('default', 'Querying SDMX API ...')
# get sdmx api response 
sdmx_response = query_and_parse_sdmx(in_sdmx_api_url)

arcpy.SetProgressor('default', 'Converting SDMX JSON to CSV ...')
# convert sdmx json to csv
sdmx_csv_rows = convert_sdmx_json_to_csv(sdmx_response)

# write csv to temp file location
sdmx_field_names = [f['name'] for f in sdmx_response['fields']]
sdmx_field_names.append('OBS_VALUE')
path_to_csv_file = create_csv_file(sdmx_csv_rows, sdmx_field_names, full_job_path)

arcpy.SetProgressor('default', 'Converting CSV file to Table in memory ...')
# write csv to temp table in output workspace - will be deleted later
tmp_stats_tbl = 'tbl_tmp'
arcpy.TableToTable_conversion(str(path_to_csv_file), 'memory', tmp_stats_tbl)
in_mem_stats_tbl = f'memory\\{tmp_stats_tbl}'

# set the output filename to be a value from the sdmx table, if user selects
if in_use_field_value_for_outputname:
    row = next(arcpy.da.SearchCursor(in_mem_stats_tbl, [in_sdmx_field_for_outputname]))
    in_output_filename = arcpy.ValidateTableName(row[0])

# build path to newly created output feature class 
final_output_fc_path = os.path.join(in_output_workspace, in_output_filename)

# check if the filename for the output fc already exists, if so, add the now_ts (timestamp) to the end
if arcpy.Exists(final_output_fc_path):
    in_output_filename = f'{in_output_filename}_{now_ts}' 
    final_output_fc_path = os.path.join(in_output_workspace, in_output_filename)

arcpy.SetProgressor('default', 'Creating output Feature Class ...')
# create output feature class
geo_layer_feature_type = in_geo_fl_desc.shapeType
geo_layer_sr = in_geo_fl_desc.spatialReference
arcpy.CreateFeatureclass_management(in_output_workspace, in_output_filename, geo_layer_feature_type, '#', '#', '#', geo_layer_sr)

# get field alias info
if in_should_update_field_aliases_on_output:
    arcpy.SetProgressor('default', 'Collecting field alias information ...')
    alias_info = None
    if in_api_has_alias_information:
        alias_info = sdmx_response['fields']
    else:
        arcpy.AddMessage('TODO :: IMPLEMENT Load from codelists file')
        arcpy.AddError('load field alias info from codelist file not yet implemented')
        raise arcpy.ExecuteError
        # alias_info = parse_fields_from_codelists_file(in_codelists_file)

arcpy.SetProgressor('default', 'Building fields to add to output feature class ...')
# build list of fields to add
add_field_type_map = {
    'Integer': 'LONG',
    'String': 'TEXT',
    'SmallInteger': 'SHORT'
}
stats_tbl_fields = []
join_field_type = 'text'
stats_table_fields = arcpy.ListFields(in_mem_stats_tbl)
for f in stats_table_fields:
    if not f.required:
        alias = f.aliasName
        if in_should_update_field_aliases_on_output:
            found_field = [ff for ff in alias_info if ff['name'] == f.name]
            if found_field and len(found_field) > 0:
                found_field = found_field[0]
                alias = found_field['alias']
            
        field_type = f.type
        if f.type in add_field_type_map.keys():
            field_type = add_field_type_map[f.type]

        stats_tbl_fields.append([f.name, field_type, alias, f.length])

        if f.name == in_sdmx_join_field:
            join_field_type = field_type

arcpy.SetProgressor('default', 'Adding fields to output feature class ...')
# add the fields
arcpy.AddFields_management(final_output_fc_path, stats_tbl_fields)

stats_table_fields_list = [f.name for f in stats_table_fields]
stats_table_fields_list.insert(0, 'SHAPE@')
# final_outfc_fields = ','.join(stats_table_fields_list)

cnt = int(arcpy.GetCount_management(in_mem_stats_tbl)[0])
arcpy.SetProgressor('step', f'Inserting {cnt} rows into output feature class ...', 0, cnt, 1)
# add features with geometry to the output feature class
counter = 1
with arcpy.da.SearchCursor(in_mem_stats_tbl, '*') as cursor:
    for row in cursor:
        arcpy.SetProgressorPosition(counter)
        arcpy.SetProgressorLabel(f'Inserting row {counter} of {cnt} ...')

        stats_cursor_fields = cursor.fields
        search_val = row[stats_cursor_fields.index(in_sdmx_join_field)]
        geom = get_geom(in_geo_join_field, search_val, join_field_type)

        row_list = list(row)
        row_list.insert(0, geom)
        insert_row = tuple(row_list)
        # arcpy.AddMessage(insert_row)

        with arcpy.da.InsertCursor(final_output_fc_path, stats_table_fields_list) as ic:
            try:
                ic.insertRow(insert_row)
                counter = counter + 1
            except:
                arcpy.AddMessage(ic.fields)
                arcpy.AddError('Error inserting rows')
                raise arcpy.ExecuteError

arcpy.ResetProgressor()

# replace SDMX codes with values
if in_should_replace_codes_with_values:
    arcpy.SetProgressor('default', 'Replacing SDMX codes with values ...')
    arcpy.AddMessage('TODO :: IMPLEMENT replace SDMX codes with values')

# set the output parameter
arcpy.SetParameter(12, final_output_fc_path)

arcpy.SetProgressor('default', 'Cleaning up temporary files ...')
# delete the in memory workspace
arcpy.Delete_management(in_mem_stats_tbl)

# clean up geometry cache variable
del geom_cache

# delete tmp directory
# if not in_save_temp_files:
#     pth = Path(full_job_path)
#     if pth.exists():
#         shutil.rmtree(pth)
# else:
#     arcpy.AddMessage(f'Temp files saved at {full_job_path}')