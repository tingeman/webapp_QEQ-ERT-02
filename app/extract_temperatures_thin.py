import pyabemls
import pathlib
import pandas as pd
from xml.dom.minidom import parseString
import ipdb as pdb
import re
import dateutil as du
import datetime as dt
import numpy as np

# Please install pyarrow
# conda install -c conda-forge pyarrow


################################################################

# Function to convert from dat to ohm
def dat2ohm(dat,topo, filename):
    nsensors = topo[0].size
    temp = dat[dat['DataValue']>=0] # Save only positive resistivities
    file1 = open(filename,"w")
    file1.write(str(nsensors))
    file1.write("# Number of sensors\n")
    file1.write("#x z\n")
    file1.write(topo.to_string(header=None, index = False, index_names = False))
    file1.write("\n")
    file1.write(str(temp['DataValue'].size))
    file1.write("# Number of data\n")
    file1.write("#a b m n R\n")
    file1.write(dat[dat['DataValue']>=0][::-1].to_string(header=None, index=False, index_names=False))
    file1.close()

# Function to get the total expected number of measures based on xml protocol file
def get_expected_measure_nb(protocol):
    file = open(protocol,"r")
    data = file.read()
    file.close()
    dom = parseString(data)
    return len(dom.getElementsByTagName('Rx'))

# Function to write some project informations to .inf file
def write_projectInfos(filename,protocol,completed):
    file = open(filename,'w')
    file.write(filename)
    file.write("\n")
    file.write(protocol)
    file.write("\n")
    file.write(str(completed))
    file.close()

################################################################


# Definition of paths
#protocols_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\from_terrameter\home_root\protocols')
#project_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\from_terrameter\projects')
#ls_log_file = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\from_terrameter\home_root\logfile')
protocols_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\from_terrameter\home_root\protocols')
project_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\from_terrameter\projects')
ls_log_file = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\from_terrameter\home_root\logfile')


info_db_file = pathlib.Path('./QEQ-ERT-02_task_info.ftr')
temp_db_file = pathlib.Path('./QEQ-ERT-02_temperature_info.ftr')
force_reprocessing = False   # Set this to True to reprocess all files!


# Get expected measures of protocol files used
# and create a lookup dictionary
nm_dipdip = get_expected_measure_nb(str(protocols_path/'DipoleDipole64_DISKO.xml'))
nm_grad = get_expected_measure_nb(str(protocols_path/'GradientXL_64_DISKO.xml'))

nominal_measures = {'2x32gradientXL_1': nm_grad,
                    '2x32dipdip_1': nm_dipdip}

# Get db files in test_data folder
db_files = list(project_path.rglob('*.db'))
#print(db_files)

# import database of task info, if it exists
if info_db_file.exists() and not force_reprocessing:
    task_df = pd.read_feather(info_db_file)
else:
    task_df = None

# import database of temperature info, if it exists
if temp_db_file.exists() and not force_reprocessing:
    temp_df = pd.read_feather(temp_db_file)
else:
    temp_df = None
    

# Loop to process all db files and extract information

info = {}
info['Time'] = []
info['Temp'] = []
info['ExtPowerVolt'] = []

for file in db_files:
    
    # Extract information from project folder name
    rel_file = file.relative_to(project_path)
    project_name = str(rel_file.parent)
    pattern = r'[^_0-9]'
    if re.search(pattern, project_name):
        # invalid characters present (anything other than _ and 0-9)
        continue
    proj_date = du.parser.parse(project_name[0:6], yearfirst=True, dayfirst=False)
    
    if proj_date < dt.datetime(2021,6,26):
        # We launched the system on 2021-06-27, skip everything before
        continue

    ## Did we already process this file?
    #if task_df is not None:
    #    if project_name in task_df['proj_name'].values:
    #        print('File {0} was previously processed, skipping.'.format(rel_file))
    #        continue
    
    print('Reading file: {0}'.format(rel_file))
    
    # Read project file
    try:
        alsp = pyabemls.ABEMLS_project(str(file)) # Get db file
    except:
        print('Could not open project!')
        continue
        
    # Get all task information, including data counts
    task_list = alsp.get_tasklist(no_count=False) # get task list
        
    if len(task_list) == 0:
        # project is empty
        continue
    
    log_info = alsp.execute_sql('SELECT * FROM Log')
    log_df = pd.DataFrame(log_info[0], columns=log_info[1])    

    info['Time'].extend(log_df['Time'].values.tolist())
    info['ExtPowerVolt'].extend(log_df['ExtPowerVolt'].values.tolist())
    info['Temp'].extend(log_df['Temp'].values.tolist())
    
    for rid, row in task_list.iterrows():
        
        acq_settings = alsp.settings[row['ID']]
        
        if 'ecr' in row['Name'].lower():
            config = 'ecr'
            continue
        elif 'gradient' in row['Name'].lower():
            config = 'gradient'
        elif 'gradient' in row['Name'].lower():
            config = 'gradient'
        
        data, ecr_data = alsp.get_task(task_id=row['ID'])
        
        if len(data)==0:
            continue
        
        temperatures = data[(data['DatatypeID']==13)]
        
        if len(temperatures)==0:
            continue
                
        info['Time'].extend(temperatures['Time'].values.tolist())
        info['Temp'].extend(temperatures['DataValue'].values.tolist())
        info['ExtPowerVolt'].extend((np.zeros(len(temperatures))*np.nan).tolist())
    
    
temp_df = pd.DataFrame(info)
temp_df['Time'] = pd.to_datetime(temp_df['Time'])
temp_df['Temp'] = temp_df['Temp'].apply(pd.to_numeric, errors='coerce')
temp_df['ExtPowerVolt'] = temp_df['ExtPowerVolt'].apply(pd.to_numeric, errors='coerce')

temp_df = temp_df.sort_values(by='Time')
temp_df = temp_df.reset_index()
temp_df = temp_df.drop(columns='index')

temp_df.to_feather(temp_db_file)

