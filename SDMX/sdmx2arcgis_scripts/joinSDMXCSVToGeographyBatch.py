import arcpy
import os
import shutil
import json
import csv
import requests
from datetime import datetime
from dateutil import parser
from pathlib import Path
import glob

def write_log(msg):
    global full_log_path
    with open(full_log_path, 'a') as lf:
        wr = csv.writer(lf)        
        ts = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        wr.writerow([ts, msg])

def create_working_directory():
    now_ts = datetime.now().strftime('%Y%m%d%H%M%S')
    
    current_wd = Path(os.path.dirname(os.path.realpath(__file__)))
    
    job_ws_foldername = f'batch_job_tmp_files_{now_ts}'

    full_job_path = current_wd.joinpath(job_ws_foldername)
    full_job_path.mkdir()

    return [full_job_path, now_ts]

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
        row = None
        try:
            row = next(arcpy.da.SearchCursor(geo_fl, ['SHAPE@', geo_field],where_clause=wc))
            geom = row[0]
            geo_val_to_add = row[1]
            geom_cache[geo_val_to_add] = geom
            return geom
        except:
            write_log(f'Unable to find or get geometry when where clause is :: {wc}')
            # arcpy.AddMessage(f'Unable to find or get geometry when where clause is :: {wc}')            

        return geom

################
# SCRIPT START #
################

# get input parameters
in_sdmx_csv_folder = arcpy.GetParameterAsText(0)
in_sdmx_join_field = arcpy.GetParameterAsText(1)

in_should_replace_codes_with_values = arcpy.GetParameter(2)
in_should_update_field_aliases_on_output = arcpy.GetParameter(3)
in_codelists_file = arcpy.GetParameter(4)

in_geo_table = arcpy.GetParameter(5)
in_geo_join_field = arcpy.GetParameterAsText(6)

global geom_cache
geom_cache = {}
global geo_fl
geo_fl = 'geo_fl'
arcpy.MakeFeatureLayer_management(in_geo_table, geo_fl)

in_geo_fl_desc = arcpy.Describe(geo_fl)
in_geo_field_info = in_geo_fl_desc.fieldInfo

in_output_workspace = arcpy.GetParameterAsText(7)
in_use_field_value_for_outputname = arcpy.GetParameter(8)
in_sdmx_field_for_outputname = arcpy.GetParameterAsText(9)
in_output_filename_pattern = arcpy.GetParameterAsText(10)

# in_save_temp_files = arcpy.GetParameter(12)

arcpy.SetProgressor('default', 'Creating working directory ...')
# create working directory
wd_res = create_working_directory()
full_job_path = wd_res[0]
now_ts = wd_res[1]

# setup logging
global full_log_path
full_log_path = full_job_path.joinpath('sdmx_job.log').resolve()

with open(full_log_path, 'w') as lf:
    wr = csv.writer(lf)
    wr.writerow(['DATETIME', 'MESSAGE'])
    
write_log('Job Started')

for fname in glob.glob(f'{in_sdmx_csv_folder}/*.csv'):
    # use the incoming filename to as the default for the output
    in_output_filename = arcpy.ValidateTableName(os.path.splitext(os.path.basename(fname))[0])

    arcpy.SetProgressor('default', f'Converting CSV file \'{fname}\' to Table in memory ...')
    # write csv to temp table in output workspace - will be deleted later
    tmp_stats_tbl = 'tbl_tmp'
    arcpy.TableToTable_conversion(fname, 'memory', tmp_stats_tbl)
    in_mem_stats_tbl = f'memory\\{tmp_stats_tbl}'

    ### TODO
    # use the output filename pattern if there is a value
    if in_output_filename_pattern:
        arcpy.AddMessage('TODO :: file name pattern for output name not yet implemented')

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

    arcpy.SetProgressor('default', f'Creating output Feature Class :: {in_output_filename} ...')
    # create output feature class
    geo_layer_feature_type = in_geo_fl_desc.shapeType
    geo_layer_sr = in_geo_fl_desc.spatialReference
    arcpy.CreateFeatureclass_management(in_output_workspace, in_output_filename, geo_layer_feature_type, '#', '#', '#', geo_layer_sr)

    # get field alias info
    alias_info = []
    if in_should_update_field_aliases_on_output:
        arcpy.SetProgressor('default', 'Collecting field alias information ...')
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
            arcpy.SetProgressorLabel(f'Feature Class \'{in_output_filename}\' -- Inserting row {counter} of {cnt} ...')

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
    arcpy.SetParameter(11, final_output_fc_path)

    arcpy.SetProgressor('default', 'Cleaning up temporary files ...')
    # finally, delete the in memory workspace
    arcpy.Delete_management(in_mem_stats_tbl)
    arcpy.Delete_management(tmp_stats_tbl)
    del in_mem_stats_tbl
    del tmp_stats_tbl

# clean up geometry cache variable
del geom_cache

    # delete tmp directory
    # if not in_save_temp_files:
    #     pth = Path(full_job_path)
    #     if pth.exists():
    #         shutil.rmtree(pth)
    # else:
    #     arcpy.AddMessage(f'Temp files saved at {full_job_path}')