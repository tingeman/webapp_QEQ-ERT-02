import io
import re
import pandas as pd
import numpy as np
import datetime as dt
import dateutil as du
import pathlib
import json
import ipdb as pdb
import chardet


class DataFile(io.BytesIO):
    """Defines a common interface to reading data files stored in directories and inside zip-files.
    Reads and holds the data from the file in memory. 
    Consider deleting the instance when it is no longer needed, if memory usage is an issue.
    """
    def __init__(self, filename, path=None):
        super().__init__()

        self._enc = None
        self.encoding = None
        self.encoding_confidence = None

        if path is None:
            self._filename = pathlib.Path(filename)
        else:
            self._filename = pathlib.Path(path) / filename
        
        if self._filename.parent.suffix == '.zip':
            self._read_zipped_data()
        else:
            self._read_plain_data()
        self.get_encoding()

    def _read_zipped_data(self):
        """Reads the contents of a file inside a zip-file and place it
        in the StringIO buffer. 
        Currently only files in the root of the zip file can be handled."""
        if not self._filename.parent.exists():
            raise FileNotFoundError('File does not exist: {0}'.format(self._filename.parent))

        zf = zipfile.ZipFile(self._filename.parent)

        if not self._filename.name in zf.namelist():
            raise FileNotFoundError('File does not exist: {0}'.format(self._filename))

        with zf.open(self._filename.name, 'rb') as file:
            data = file.read()
            data = self._clean(data)
            self.write(data)

    def _read_plain_data(self):
        """Reads the contents of a regular file and place it in the BytesIO buffer."""
        if not self._filename.exists():
            raise FileNotFoundError('File does not exist: {0}'.format(self._filename))
        
        with open(self._filename, 'rb') as file:
            data = file.read()
            data = self._clean(data)
            self.write(data)


    def _clean(self, data):
        return data.replace(b'\x00', b'')

    def get_encoding(self, count=300):
        """Detect the encoding of the file."""
    
        # If we passed an open file
        self.seek(0)
        dat = self.read(count)
        self.seek(0)
    
        self._enc = chardet.detect(dat)
        self.encoding = self._enc['encoding']
        self.encoding_confidence = self._enc['confidence']
    

#SUPPLY_DAT_FILE = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-PC\home_root\scripts\io_scripts\supply_voltage.dat')
SUPPLY_DAT_FILE = pathlib.Path(r'D:\data\artek\stations\QEQ-ERT-02-RPi2\logs\supply_voltage_combined.dat')

SUPPLY_FTR = pathlib.Path(r'.\supply_voltage.ftr')
BATT_STATS_FTR = pathlib.Path(r'.\battery_stats.ftr')


datf = DataFile(SUPPLY_DAT_FILE)

custom_date_parser = lambda x: dt.datetime.strptime(x, "%Y-%m-%d %H:%M:%S(%z)")
df = pd.read_csv(datf, sep=';', parse_dates=['DateTime'], 
                 date_parser=custom_date_parser, 
                 names=['DateTime', 'Voltage','Unit', 'relay state', 'Comment'])

#df2 = df.set_index('DateTime')
df2 = df

# This we do to correct for when two log entries were written 
# so fast that the 1 second resolution shows no time difference
# We move the last duplicates by 1 ms, until there are no more duplicates.
idx = df2['DateTime'].duplicated(keep='last')
while any(idx):
    datetimes = df2['DateTime'].values
    datetimes[idx] = datetimes[idx] + np.timedelta64(1, 'ms')
    df2['DateTime'] = datetimes
    idx = df2['DateTime'].duplicated(keep='last')

# Prepare voltage
df2.loc[df2['Voltage'] < -90, 'Voltage'] = np.nan

# Prepare "Power on" column
power = df2[~df2['relay state'].isin([-1])]['relay state'].copy()
power[power==1] = np.nan
power.name = 'Power on'
df2['Power on'] = power

df2.reset_index()
df2.to_feather(SUPPLY_FTR)

# Extract voltage stats on a daily basis
daily_voltage_stats = df2.groupby(df2['DateTime'].dt.date).agg({'Voltage':['min', 'max', 'mean', 'std']})

# in order to be able to save as Feather...
daily_voltage_stats = daily_voltage_stats.reset_index()  # make DateTime index a normal column
daily_voltage_stats.columns = [("_".join(a)).strip('_') for a in daily_voltage_stats.columns.to_flat_index()]   # Flatten the multiindex columns
daily_voltage_stats.to_feather(BATT_STATS_FTR)




