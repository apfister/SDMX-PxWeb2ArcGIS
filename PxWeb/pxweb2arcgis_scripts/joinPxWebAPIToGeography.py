import arcpy
import os
import shutil
import json
import csv
import requests
from datetime import datetime
from dateutil import parser
from pathlib import Path

import jsonstat

def create_working_directory():
    now_ts = datetime.now().strftime('%Y%m%d%H%M%S')
    
    current_wd = Path(os.path.dirname(os.path.realpath(__file__)))
    
    job_ws_foldername = f'job_tmp_files_{now_ts}'

    full_job_path = current_wd.joinpath(job_ws_foldername)
    full_job_path.mkdir()

    return [full_job_path, now_ts]

def get_pxw_field_aliases(dataset):
    fields = []
    for i, d in enumerate(dataset.dimensions()):
        f = {
            'name': d.label,
            'alias': d.did,
            'type': 'String'
        }

        fields.append(f)
    
    fields = fields + [
        { 'name': 'UNITS', 'alias': 'UNITS', 'type': 'String' },
        { 'name': 'DECIMALS', 'alias': 'DECIMALS', 'type': 'Number' }
    ]
    return fields

def query_and_parse_pxw(in_url, in_pxw_body_file_path):
    json_params = None
    # arcpy.AddMessage(in_url)
    # arcpy.AddMessage(in_pxw_body_file_path)
    with open(in_pxw_body_file_path, encoding='utf-8') as json_file:
        json_params = json.load(json_file)
    
    response = requests.post(in_url, json=json_params)
    
    return_dataset = None
    if response:
        res_json = response.json()
        jstat = jsonstat.from_json(res_json)
        return_dataset = jstat.dataset(0)

    return return_dataset

def create_data_frame(dataset, pxw_jf_name, pxw_jf_label):
    area_dim = None
    
    for d in dataset.dimensions():
        if d.label.strip() == pxw_jf_label.strip():
            area_dim = d
            break

    cnt = area_dim.__len__()
    cat_lookups = {}
    for i in range(0, cnt):
        cat = area_dim.category(i)
        cat_lookups[cat.label] = cat.index
    
    def get_code(row):
        return cat_lookups[row[pxw_jf_label]]

    def get_units_decimals(row, f):
        r_info = row['Information']

        for i, d in enumerate(dataset.dimensions()):
            if d.role == 'metric' and d._JsonStatDimension__unit:
                unit_info = d._JsonStatDimension__unit
                
                for j in range(0, 99999):
                    try:
                        cat = d._pos2cat(j)      
                        if cat.label == r_info:                  
                            return unit_info[cat.index][f]                   
                    except:
                        arcpy.AddMessage(f'nothing found at index {j}. exiting ..')
                        break 
                
                return 'UNKNOWN'

    df = dataset.to_data_frame()

    df[f'{pxw_jf_label}_Code'] = df.apply(lambda row: get_code(row), axis=1)
    df['UNITS'] = df.apply(lambda row: get_units_decimals(row, 'base').upper(), axis=1)    
    df['DECIMALS'] = df.apply(lambda row: get_units_decimals(row, 'decimals'), axis=1)

    return df

def convert_dataframe_to_csv_file(dataframe, full_job_path):
    file_name = 'fromPxWebapi.csv'
    full_path_to_file = full_job_path.joinpath(file_name)
    
    dataframe.to_csv(path_or_buf=full_path_to_file, index=None)

    return full_path_to_file.resolve()

def get_geom(geo_field, geo_value, join_field_type):
    global geom_cache
    global geo_fl

    wc = """{0} = '{1}'""".format(arcpy.AddFieldDelimiters(geo_fl, geo_field), geo_value)
    # arcpy.AddMessage(wc)
    if geo_value in geom_cache:
        # arcpy.AddMessage(f'got from cache for {geo_value}')
        return geom_cache[geo_value]
    else:
        geom = None
        row = None
        try:
            row = next(arcpy.da.SearchCursor(geo_fl, ['SHAPE@', geo_field], where_clause=wc))
            # arcpy.AddMessage(row)
            geom = row[0]
            geo_val_to_add = row[1]
            geom_cache[geo_val_to_add] = geom
            return geom
        except:
            arcpy.AddMessage(f'Unable to get geometry from Geography layer. The where_clause, {wc} did not return results.')


################
# SCRIPT START #
################

# get input parameters
in_pxw_api_url = arcpy.GetParameterAsText(0)
in_pxw_post_body = arcpy.GetParameterAsText(1)
in_pxw_join_field_raw = arcpy.GetParameterAsText(2).split('-')
in_pxw_join_field_name = in_pxw_join_field_raw[0].strip()
in_pxw_join_field_label = in_pxw_join_field_raw[1].strip()

in_geo_table = arcpy.GetParameter(3)
in_geo_join_field = arcpy.GetParameterAsText(4)

global geom_cache
geom_cache = {}
global geo_fl
geo_fl = 'geo_fl'
arcpy.MakeFeatureLayer_management(in_geo_table, geo_fl)

in_geo_fl_desc = arcpy.Describe(geo_fl)
in_geo_field_info = in_geo_fl_desc.fieldInfo

in_output_workspace = arcpy.GetParameterAsText(5)

in_pxw_use_calcd_geo_code_field_for_join = arcpy.GetParameter(8)
in_should_update_field_aliases_on_output = arcpy.GetParameter(9)
in_use_wm_sr_for_output = arcpy.GetParameter(10)

in_should_transform_fields = arcpy.GetParameter(11)
in_transform_fields = arcpy.GetParameter(12)

arcpy.SetProgressor('default', 'Creating working directory ...')
# create working directory
wd_res = create_working_directory()
full_job_path = wd_res[0]
now_ts = wd_res[1]

arcpy.SetProgressor('default', 'Querying PxWeb API ...')
# get pxw api response 
pxw_response = query_and_parse_pxw(in_pxw_api_url, in_pxw_post_body)

arcpy.SetProgressor('default', 'Converting PxWeb JSON-Stat to CSV ...')
# convert pxw json-stat to pandas dataframe
pxw_as_dataframe = create_data_frame(pxw_response, in_pxw_join_field_name, in_pxw_join_field_label)

# convert pandas data frame to csv and write to temp file location
path_to_csv_file = convert_dataframe_to_csv_file(pxw_as_dataframe, full_job_path)

arcpy.SetProgressor('default', 'Converting CSV file to Table in memory ...')
# write csv to temp table in output workspace - will be deleted later
tmp_stats_tbl = 'tbl_tmp'
arcpy.TableToTable_conversion(str(path_to_csv_file), 'memory', tmp_stats_tbl)
in_mem_stats_tbl = f'memory\\{tmp_stats_tbl}'

# test write output table to workspace to make sure pxw data came in ok
# arcpy.TableToTable_conversion(in_mem_stats_tbl, in_output_workspace, 'pxw_table')

in_output_filename = arcpy.ValidateTableName('pxweb_output')
if arcpy.GetParameterAsText(6):
    in_output_filename = arcpy.ValidateTableName(arcpy.GetParameterAsText(6))
elif pxw_response.label:
    in_output_filename = arcpy.ValidateTableName(pxw_response.label)

# build path to newly created output feature class 
final_output_fc_path = os.path.join(in_output_workspace, in_output_filename)

# check if the filename for the output fc already exists, if so, add the now_ts (timestamp) to the end
if arcpy.Exists(final_output_fc_path):
    in_output_filename = f'{in_output_filename}_{now_ts}' 
    final_output_fc_path = os.path.join(in_output_workspace, in_output_filename)

arcpy.SetProgressor('default', 'Creating output Feature Class ...')
# create output feature class
geo_layer_feature_type = in_geo_fl_desc.shapeType
geo_layer_sr = arcpy.SpatialReference(102100) if in_use_wm_sr_for_output else in_geo_fl_desc.spatialReference
arcpy.CreateFeatureclass_management(in_output_workspace, in_output_filename, geo_layer_feature_type, '#', '#', '#', geo_layer_sr)

# get field alias info
if in_should_update_field_aliases_on_output:
    arcpy.SetProgressor('default', 'Collecting field alias information ...')
    alias_info = get_pxw_field_aliases(pxw_response)

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

        if f.name == in_pxw_join_field_name:
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
        
        search_field = in_pxw_join_field_label
        if in_pxw_use_calcd_geo_code_field_for_join:
            search_field = f'{in_pxw_join_field_label}_Code'

        search_val = row[stats_cursor_fields.index(search_field)]

        if in_should_transform_fields and in_transform_fields.rowCount > 0:
            for i in range(0, in_transform_fields.rowCount):
                find_val = in_transform_fields.getValue(i, 0)
                rep_val = in_transform_fields.getValue(i, 1)

                if find_val and rep_val == 'None':
                    search_val = search_val.replace(find_val, '')
                elif find_val and rep_val == '':
                    search_val = f'{find_val}{search_val}'
                elif find_val == '' and rep_val:
                    search_val = f'{search_val}{rep_val}'
                elif find_val and rep_val:
                    search_val = f'{find_val}{search_val}{rep_val}'

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

# # replace SDMX codes with values
# if in_should_replace_codes_with_values:
#     arcpy.SetProgressor('default', 'Replacing SDMX codes with values ...')
#     arcpy.AddMessage('TODO :: IMPLEMENT replace SDMX codes with values')

# set the output parameter
arcpy.SetParameter(7, final_output_fc_path)

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