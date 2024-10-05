import pyabemls
import pathlib
import pandas as pd
from xml.dom.minidom import parseString
import ipdb as pdb
import re
import dateutil as du
import datetime as dt

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


task_info_file = info_db_file = pathlib.Path('./QEQ-ERT-02_task_info.ftr')
#supply_dat_file = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\home_root\scripts\io_scripts\supply_voltage.dat')
#ls_log_file = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\from_terrameter\home_root\logfile')
supply_dat_file = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\home_root\scripts\io_scripts\supply_voltage.dat')
ls_log_file = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\from_terrameter\home_root\logfile')

# Definition of paths
#protocols_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\from_terrameter\home_root\protocols')
#project_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\from_terrameter\projects')
protocols_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\from_terrameter\home_root\protocols')
project_path = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\from_terrameter\projects')


info_db_file = pathlib.Path('./QEQ-ERT-02_task_info.ftr')
force_reprocessing = False   # Set this to True to reprocess all files!

# Get expected measures of protocol files used
# and create a lookup dictionary
nm_dipdip = get_expected_measure_nb(str(protocols_path/'DipoleDipole64_DISKO.xml'))
nm_grad = get_expected_measure_nb(str(protocols_path/'GradientXL_64_DISKO.xml'))

nominal_measures = {'2x32gradientXL_1': nm_grad,
                    '2x32dipdip_1': nm_dipdip}

# Imoprt topography - at this stage it is a simplified topography and only for pygimli
# NOT NEEDED NOW, ONLY FOR EXPORT OF TOPOGRAPHY IN DAT FILES IN MARCOS VERSION
#topo = pd.read_csv("topography_DISKO.txt",sep="\t",header=None)

# Get db files in test_data folder
db_files = list(project_path.rglob('*.db'))
#print(db_files)

# import database of task info, if it exists
if info_db_file.exists() and not force_reprocessing:
    task_df = pd.read_feather(info_db_file)
else:
    task_df = None

#pdb.set_trace()


# Loop to process all db files and extract information
task_info_export = []
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

    # Did we already process this file?
    if task_df is not None:
        if project_name in task_df['proj_name'].values:
            print('File {0} was previously processed, skipping.'.format(rel_file))
            continue
    
    print('Reading file: {0}'.format(rel_file))
    
    # Read project file
    try:
        alsp = pyabemls.ABEMLS_project(str(file)) # Get db file
    except:
        print('Could not open project!')
        continue
        
    # Get all task information, including data counts
    task_list = alsp.get_tasklist(no_count=False) # get task list
    
    #pdb.set_trace()
    
    if len(task_list) == 0:
        # project is empty
        continue

    log_info = alsp.execute_sql('SELECT * FROM Log')
    log_df = pd.DataFrame(log_info[0], columns=log_info[1])    

    for rid, row in task_list.iterrows():
        
        #tmp = alsp.execute_sql('SELECT * FROM AcqSettings WHERE key1 == {0} AND key2 == {0}'.format(row['ID']))
        #acq_settings = pd.DataFrame(tmp[0], columns=tmp[1])
        acq_settings = alsp.settings[row['ID']]
        
        if 'ecr' in row['Name'].lower():
            config = 'ecr'
        elif 'gradient' in row['Name'].lower():
            config = 'gradient'
        elif 'gradient' in row['Name'].lower():
            config = 'gradient'
        
        # store all standard parameters
        task_info = dict(proj_name=project_name,
                         proj_date=proj_date,
                         task_name=row['Name'],
                         task_id=row['ID'],
                         protocol=pathlib.Path(row['ProtocolFile']).name,
                         configuration=config,
                         time_created=row['Time'],
                         nECRdata=row['nECRdata'],
                         nDipoles=row['nDipoles'],
                         nominal=0,
                         completed_pct=0,
                         Started=None,
                         Completed=None,
                         Quit=None,
                         )
        
        # This is the full list of available settings from the Terrameter LS:
        # ['AGC_TimeSec', 'Acq_DelaySec', 'Acq_TimeSec', 'AutoStack',
        #     'BaseFreqHz', 'BoreholeStepDown', 'BoreholeStepUp',
        #     'CurrentLimitHighAmpere', 'CurrentLimitLowAmpere', 'DoInitialAGC',
        #     'ElectrodeResistanceBadLimitHighOhm',
        #     'ElectrodeResistanceBadLimitLowOhm', 'ElectrodeTest',
        #     'ElectrodeTestCurrentAmpere', 'ErrorLimit', 'Fullwaveform',
        #     'IPSP_TimeSec', 'IP_MinOffTimeSec', 'IP_OffTimeSec',
        #     'IP_WindowSecList', 'LogFluidResistivity', 'LogLateral18foot',
        #     'LogLongNormal', 'LogSelfPotential', 'LogShortNormal',
        #     'LogTemperature', 'MarginLimitHigh', 'MeasureMode', 'Measure_SNR',
        #     'PowerLimitHighWatt', 'PowerLimitLowWatt',
        #     'PowerLossLimitHighWatt', 'SNR_TimeSec', 'SP_TimeSec',
        #     'SampleRateHz', 'StackLimitsHigh', 'StackLimitsLow', 'StackNorm',
        #     'VoltageLimitHighVolt', 'VoltageLimitLowVolt']
        
        # Fields that we choose to report:
        fields = ['Acq_DelaySec', 
                  'Acq_TimeSec', 
                  'CurrentLimitHighAmpere',
                  'CurrentLimitLowAmpere', 
                  'ElectrodeResistanceBadLimitHighOhm',
                  'ElectrodeResistanceBadLimitLowOhm', 
                  'ElectrodeTest',
                  'ElectrodeTestCurrentAmpere', 
                  'Fullwaveform',
                  'IP_OffTimeSec',  # Treated separately, to set to 0 if in resistivity mode
                  'MeasureMode'     # This is treated separately, to make it human readable
                  ]
                  
        float_fields =  ['Acq_DelaySec', 
                         'Acq_TimeSec', 
                         'CurrentLimitHighAmpere',
                         'CurrentLimitLowAmpere', 
                         'ElectrodeResistanceBadLimitHighOhm',
                         'ElectrodeResistanceBadLimitLowOhm', 
                         'ElectrodeTestCurrentAmpere', 
                         'IP_OffTimeSec',  # Treated separately, to set to 0 if in resistivity mode
                         ]
        # Add acquisition settings
        for f in fields:
            #task_info[f] = acq_settings[acq_settings['Setting'] == f]['Value'].values[0]
            if f in float_fields:
                task_info[f] = float(acq_settings[f])
            else:
                task_info[f] = acq_settings[f]
            
        # Convert MeasureMode to human readable
        if task_info['MeasureMode'] == '2':
            task_info['MeasureMode'] = 'Resistivity'
        else:
            raise ValueError('Check MeasureMode conversions from numbers to human readable... is this IP or SP measurements?')
        
        # If Measuremode is IP, add the off time, otherwise set it to 0 sec
        if task_info['MeasureMode'] != 'IP':
            task_info['IP_OffTimeSec'] = 0

        # Calculate ON_time and OFF_time of waveform
        if task_info['MeasureMode'] != 'SP':
            # Here for Resistivity and IP waveforms
            task_info['ON_time_sec'] = task_info['Acq_DelaySec'] + task_info['Acq_TimeSec']
            task_info['OFF_time_sec'] = task_info['IP_OffTimeSec']
        else:
            # Here for SP measurements
            task_info['ON_time_sec'] = 0
            task_info['OFF_time_sec'] = acq_settings['SP_TimeSec']

        # Add information about nominal number of measurements in the protocol
        if task_info['task_name'] in nominal_measures.keys():
            task_info['nominal'] = nominal_measures[task_info['task_name']]
            
        # Calculate the percentage of measurements completed
        if task_info['nominal'] >0:
            task_info['completed_pct'] = task_info['nDipoles']/task_info['nominal']*100
        
        # add timestamps for log events when "Measurements Started", "Measurements Completed", and "Quit".
        for lid, logitem in log_df[log_df['TaskID']==row['ID']].iterrows():
            if 'Measuring Started' in logitem['What']:
                task_info['Started'] = du.parser.parse(logitem['Time'], yearfirst=True, dayfirst=False)
            
            if 'Measuring done' in logitem['What']:
                task_info['Completed'] = du.parser.parse(logitem['Time'], yearfirst=True, dayfirst=False)
            
            if 'Quit' in logitem['What']:
                task_info['Quit'] = du.parser.parse(logitem['Time'], yearfirst=True, dayfirst=False)

        task_info['first_log_event'] = log_df[log_df['TaskID']==row['ID']].iloc[0]['Time']
        task_info['last_log_event'] = log_df[log_df['TaskID']==row['ID']].iloc[-1]['Time']
        # Add the task info to the list of tasks...
        task_info_export.append(task_info)

    continue

#pdb.set_trace()

if task_df is None:
    task_df = pd.DataFrame(task_info_export)
else:
    if len(task_info_export) > 0:
        tmp = pd.DataFrame(task_info_export)
        task_df = task_df.append(tmp, ignore_index=True)

task_df.to_feather(info_db_file)

with open(pathlib.Path('D:/vapp/log.txt'), 'a') as f:
    f.write('{0}\n'.format(dt.datetime.now()))
    


#    
#    if task_list['ID'].size == 1: # sometimes the instrument only runs electrode test
#        print("No resistivity measurement performed!")
#        write_projectInfos(str(file).split(".")[0]+"_infos.inf","No protocol","0")
#        continue
#    my_protocol = task_list['Name'][1] # Get the protocol used for resisitivity
#    print('Electrode contact resistance : {0}'.format(task_list['Name'][0]))
#    print('Protocol : {0}'.format(my_protocol))
#    # Assing the expected number of measures based on protocol
#    if my_protocol == "2x32gradientXL_1":
#            expected_nm = nm_grad
#    elif my_protocol == "2x32dipdip_1":
#            expected_nm = nm_dipdip
#    else:
#        print("ERROR - PROTOCOL NOT FOUND!")
#        break
#    data, ecr_data = alsp.get_task(task_id=task_id) # Import actual data
#    if data.empty:
#        print("WARNING : var data is empty")
#    else:
#        resistivity = data[data['DatatypeID']==2] #Get resistivity
#        # Evaluate % of completede measures
#        completed = resistivity['Time'].size/expected_nm*100
#        # Diagnostic messages
#        print('Started:{0}'.format(data['Time'][0]), ' - Ended:{0}'.format(data['Time'].iloc[-1]))
#        print('Total measurements : {0}'.format(data['Time'].size))
#        print('Total resisitivity data  : {0}'.format(resistivity['Time'].size), 'out of {0}'.format(expected_nm))
#        print('{0} % Completed measurements'.format(completed))
#        print('Negative resisitivity values:{0}'.format(sum(resistivity['DataValue']<0)))
#        # Write dat file for res2inv
#        print('Writing dat-file (task_id: {0}) ... '.format(task_id), end='')
#        alsp.export_dat(task_id=task_id) # Export to dat file for res2inv
#        dat = resistivity[['APosX','BPosX','MPosX','NPosX','DataValue']].copy()
#        # Write ohm file for gimli
#        print("Writing .ohm file ...")
#        dat2ohm(dat,topo,str(file).split(".")[0]+".ohm") # Convert to .ohm for gimli
#        print("... Done!")
#        # Write project infors to text file
#        write_projectInfos(str(file).split(".")[0]+"_infos.inf",my_protocol,completed)
#    print()
#