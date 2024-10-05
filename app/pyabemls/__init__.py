from tables import *
import numpy as np
import pathlib
import os.path
import warnings
import sqlite3
from pandas import DataFrame
import pdb
from lxml import etree


# conda install pytables lxml


DATATYPES = dict([
 (1,  {'Name': 'SP',         'Symbol': 'SP',         'Unit': 'V',         'Explanation': 'SP'}),
 (2,  {'Name': 'rho_app',    'Symbol': '\\rho_a',    'Unit': '\\Omega m', 'Explanation': 'Apparent Resistivity value'}),
 (3,  {'Name': 'IP',         'Symbol': 'IP',         'Unit': 'mV/V',      'Explanation': 'One IP window'}),
 (4,  {'Name': 'SNR',        'Symbol': 'SNR',        'Unit': 'dB',        'Explanation': 'Signal to noise ratio'}),
 (5,  {'Name': 'R',          'Symbol': 'R',          'Unit': '\\omega',   'Explanation': 'Resistance'}),
 (6,  {'Name': 'I',          'Symbol': 'I',          'Unit': 'A',         'Explanation': 'Current'}),
 (7,  {'Name': 'delta_U',    'Symbol': '\\deltaU',   'Unit': 'V',         'Explanation': 'ResDeltaVoltage'}),
 (8,  {'Name': 'm',          'Symbol': 'm',          'Unit': 'ms',        'Explanation': 'Chargeability'}),
 (9,  {'Name': 'IP_delta_U', 'Symbol': 'IP\\deltaU', 'Unit': 'V',         'Explanation': 'IPDeltaVoltage'}),
 (10, {'Name': 'Avg',        'Symbol': 'V',          'Unit': 'V',         'Explanation': 'Average'}),
 (11, {'Name': 'Signal',     'Symbol': 'V',          'Unit': 'V',         'Explanation': 'Intermediary result'}),
 (12, {'Name': 'IPSP',       'Symbol': 'V',          'Unit': 'V',         'Explanation': 'SP compensation'}),
 (13, {'Name': 'Temp',       'Symbol': 'T',          'Unit': 'C',         'Explanation': 'Temperature'}),
])


def remove_comments(line, sep):
    for s in sep:
        line = line.split(s)[0]
    return line.strip()


class ABEMLS_project():
    """Class to handle getting data from an ABEM Terrameter LS project file

    """

    # Define sql queries to retrieve different types of data from database.
    GETDATA_SQL = """
        SELECT
            DPV.TaskID,
            DPV.MeasureID,
            DPV.Channel,
            DPV.DatatypeID,
            DP_ABMN.APosX,DP_ABMN.APosY,DP_ABMN.APosZ,
            DP_ABMN.BPosX,DP_ABMN.BPosY,DP_ABMN.BPosZ,
            DP_ABMN.MPosX,DP_ABMN.MPosY,DP_ABMN.MPosZ,
            DP_ABMN.NPosX,DP_ABMN.NPosY,DP_ABMN.NPosZ,
            DPV.DataValue,
            DPV.DataSDev,
            DPV.MCycles,
            Measures.Time,
            Measures.PosLatitude,
            Measures.PosLongitude,
            Measures.PosQuality,
            Measures.IntPowerVolt,
            Measures.ExtPowerVolt,
            Measures.Temp
        FROM DPV, DP_ABMN, Measures
        WHERE
            DPV.MeasureID=Measures.ID AND
            DPV.DPID=DP_ABMN.ID AND
            DPV.DatatypeID=5
    """

    GET_TASK_SQL = """
        SELECT
            Measures.Time,
            DPV.TaskID,
            DPV.MeasureID,
            DPV.Channel,
            DPV.SeqNum,
            DPV.DatatypeID,
            DP_ABMN.APosX,DP_ABMN.APosY,DP_ABMN.APosZ,
            DP_ABMN.BPosX,DP_ABMN.BPosY,DP_ABMN.BPosZ,
            DP_ABMN.MPosX,DP_ABMN.MPosY,DP_ABMN.MPosZ,
            DP_ABMN.NPosX,DP_ABMN.NPosY,DP_ABMN.NPosZ,
            DPV.DataValue,
            DPV.DataSDev,
            DPV.MCycles,
            Measures.SessionID
        FROM DPV, DP_ABMN, Measures
        WHERE
            DPV.TaskID=? AND
            DPV.MeasureID=Measures.ID AND
            DPV.DPID=DP_ABMN.ID
    """

    GET_ELECTRODETESTS = """
        SELECT
               ID
             , TaskID
             , StationID
             , SwitchNumber
             , SwitchAddress
             , PosX
             , PosY
             , PosZ
             , ResistanceValue
             , CurrentValue
             , TestStatus
             , UserSetting
             , TxStatus
             , Time
        FROM ElectrodeTestData
    """

    GET_TASK_ELECTRODETEST = """
        SELECT
               ID
             , TaskID
             , StationID
             , SwitchNumber
             , SwitchAddress
             , PosX
             , PosY
             , PosZ
             , ResistanceValue
             , CurrentValue
             , TestStatus
             , UserSetting
             , TxStatus
             , Time
        FROM ElectrodeTestData
        WHERE TaskID=?
    """


    GET_TASK_INFO_SQL_BACKUP = """
        SELECT
            Tasks.ID,
            Tasks.Name,
            Tasks.PosX, Tasks.PosY, Tasks.PosZ,
            Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
            Tasks.ArrayCode,Tasks.Time,
            COUNT(*) AS ndat
        FROM (
            SELECT TaskID, MeasureID, Channel
            FROM DPV
            WHERE
                Channel>0 AND Channel<13 AND TaskID=?
            GROUP BY
                TaskID, MeasureID, Channel
        ) AS NdatTable, Tasks
        WHERE Tasks.ID=NdatTable.TaskID
    """

    GET_TASK_INFO_SQL = """
        SELECT
            Tasks.ID,
            Tasks.Name,
            Tasks.PosX, Tasks.PosY, Tasks.PosZ,
            Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
            Tasks.ArrayCode,Tasks.Time,
            ts1.Value as ProtocolFile,
            ts2.Value as SpreadFile,
            ts4.Value as BaseReference,
            Log2.PosLatitude, Log2.PosLongitude, Log2.PosQuality,
            COUNT(DISTINCT ndt.ID) as nData,
            COUNT(DISTINCT ndt.DPID) as nDipoles,
            COUNT(DISTINCT e.ID) as nECRdata
        FROM Tasks
        LEFT JOIN ElectrodeTestData as e ON Tasks.ID=e.TaskID
        LEFT JOIN (SELECT * FROM DPV WHERE Channel>0 AND Channel<13)            as ndt ON ndt.TaskID=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="ProtocolFile")     as ts1 ON ts1.key1=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="SpreadFile")       as ts2 ON ts2.key1=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="BaseReference")    as ts4 ON ts4.key1=Tasks.ID
        LEFT JOIN (SELECT DISTINCT PosLatitude, PosLongitude, PosQuality, TaskID FROM Log) as Log2 ON Log2.TaskID=Tasks.ID
        GROUP BY Tasks.ID
    """

    GET_TASK_INFO_NO_COUNT_SQL = """
        SELECT
            Tasks.ID,
            Tasks.Name,
            Tasks.PosX, Tasks.PosY, Tasks.PosZ,
            Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
            Tasks.ArrayCode,Tasks.Time,
            ts1.Value as ProtocolFile,
            ts2.Value as SpreadFile,
            ts4.Value as BaseReference,
            Log2.PosLatitude, Log2.PosLongitude, Log2.PosQuality,
            COUNT(DISTINCT e.ID) as nECRdata
        FROM Tasks
        LEFT JOIN ElectrodeTestData as e ON Tasks.ID=e.TaskID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="ProtocolFile")     as ts1 ON ts1.key1=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="SpreadFile")       as ts2 ON ts2.key1=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="BaseReference")    as ts4 ON ts4.key1=Tasks.ID
        LEFT JOIN (SELECT DISTINCT PosLatitude, PosLongitude, PosQuality, TaskID FROM Log) as Log2 ON Log2.TaskID=Tasks.ID
        GROUP BY Tasks.ID
    """

    GET_TASK_COORDS_SQL = """
        SELECT
            Stations.TaskID,
            Tasks.Name AS TaskName,
            Stations.ID AS StationID,
            AVG(Measures.PosLatitude),
            AVG(Measures.PosLongitude)
        FROM Stations
        LEFT JOIN Measures ON Stations.ID = Measures.StationID
        LEFT JOIN Tasks ON Tasks.ID = Stations.TaskID
        WHERE Stations.TaskID=? AND Measures.PosQuality=3
        GROUP BY StationID 
    """    
    
    
    HAS_MEASUREMENTS_SQL = """
        SELECT
            DPV.TaskID,
            DPV.MeasureID,
            DPV.Channel,
            DPV.DatatypeID,
            DPV.DataValue,
            DPV.DataSDev,
            DPV.MCycles,
            DPV.SeqNum
        FROM DPV
    """
    # Remember to add WHERE clause and LIMIT when querying!

    GET_ACQ_SETTINGS_SQL = """
        SELECT
            acqs.*
        FROM AcqSettings AS acqs, Sessions
    """
    # Rememeber to add "WHERE acqs.key2=" claues when querying

    GET_SESSIONS_SQL = """
        SELECT
            *
        FROM Sessions
    """


    def __init__(self, filename, project_name=None, xml_path=None):
        # Define instance variables
        self.name = project_name
        self.filename = filename
        self.xml_path = xml_path
        self.tasks = None
        self.task_cols = None
        self.spread_files = dict()
        self.datatypes = dict()
        self.settings = dict()

        conn = sqlite3.connect(filename)
        cur = conn.cursor()
        self.get_tasklist(cur=cur, no_count=True)
        self.get_datatypes_from_db(cur=cur)
        self.sessions = self.get_sessions(cur=cur)
        self.settings = self.get_settings_dict()
        cur.close()
        conn.close()
        self.filename = filename

        # read textfile with project name if present
        # it must have the same basename as the db-file,
        # but with '_name.txt' added
        name_filename = os.path.splitext(filename)[0]+'_name.txt'
        if os.path.exists(name_filename) and project_name is None:
            with open(name_filename, 'r') as f:
                pname = f.read()
            if pname:
                self.name = pname

    def execute_sql(self, sql, cur=None, args=None):
        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        if not args:
            cur.execute(sql)
        else:
            cur.execute(sql, args)

        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

        if temp_cur:
            cur.close()
            conn.close()

        return rows, cols

    def get_datatypes_from_db(self, cur=None):
        """Get datatypes table from the db file

        """
        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        cur.execute("SELECT * FROM Datatype")

        rows = cur.fetchall()
        column_titles = cur.description

        if temp_cur:
            cur.close()
            conn.close()

        self.datatypes = dict()

        for row in rows:
            self.datatypes[row[0]] = {
                    column_titles[1][0]: row[1],
                    column_titles[2][0]: row[2],
                    column_titles[3][0]: row[3]
            }

    def get_data(self):
        """Get data from SQLITE file, return rows and column titles.
        """

        conn = sqlite3.connect(self.filename)
        cur = conn.cursor()

        cur.execute(self.GETDATA_SQL)

        rows = cur.fetchall()
        column_titles = cur.description
        cur.close()
        conn.close()

        return rows, column_titles

    def get_tasklist(self, cur=None, no_count=False):
        """Read tasks table from db file

        """
        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM Tasks")

        try:
            ntasks = cur.fetchall()[0][0]
        except:
            ntasks = 0

        #cur.execute(self.GET_TASK_INFO_SQL)
        if no_count:
            cur.execute(self.GET_TASK_INFO_NO_COUNT_SQL)
        else:
            cur.execute(self.GET_TASK_INFO_SQL)
        tasks = cur.fetchall()
        #tasks = []
        #for n in xrange(1,ntasks+1):
        #    cur.execute(self.GET_TASK_INFO_SQL_2, (n,))
        #    tasks.append(cur.fetchall()[0])

        task_cols = [c[0] for c in cur.description]

        result = DataFrame(tasks, columns=task_cols)

        self.tasks=result

        if temp_cur:
            cur.close()
            conn.close()

        return result


    def list_tasks(self):
        """Print a nice list of the tasks

        """
        if self.tasks is None:
            self.get_tasklist()

        print("Tasks in project:")
        for id, t in self.tasks.iterrows():
            # print ("Task ID: {0}   "
            #        "Name: {1:8}  "
            #        "Edist: {2}   "
            #        "Array: {3}   "
            #        "Datapts: {4}   "
            #        "Time: {5}".format(t[0],t[1],t[5],t[8],t[10],t[9]))
            print("-"*40)
            print(t)

    def get_task(self, task_id=1, condensed=False, cur=None):
        """Read task data from db file

        :param task_id: integer
            The index (1-based) of the task to retrieve. If omitted, TaskID 1 is returned.
        :param condensed: Boolean
            If condensed=True, all parameters for one channel will be collected
            in one row of the resulting array.
        :param cur: sql cursor
            Cursor into the sql database. If omitted, a temporary cursor will be created.

        Returns: tuple of two dataframes
            Returns task measurements and electrode test data in two separate dataframes.
        """

        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        #pdb.set_trace()
        cur.execute(self.GET_TASK_SQL, (int(task_id),))
        task = cur.fetchall()
        task_cols = [c[0] for c in cur.description]

        if task:
            result = DataFrame(task, columns=task_cols)
        else:
            result = DataFrame()

        if self.tasks.nECRdata[self.tasks.ID == task_id].values[0] > 0:
            etest = self.get_electrodetest(task_id=task_id, cur=cur)
        else:
            etest = DataFrame()

        if temp_cur:
            cur.close()
            conn.close()

        if condensed:
            result = condense_measurements(result, self.datatypes)

        return result, etest

    def get_quadrupoles(self, task_id=None, cur=None):
        """Reads the quadrupole information for the task specified (the DP_ABMN table)."""
        sql = """
            SELECT
                *
            FROM DP_ABMN
            WHERE TaskID=?
        """

        rows, cols = self.execute_sql(sql, cur=None, args=(int(task_id),))
        if rows:
            return DataFrame(rows, columns=cols)
        else:
            return DataFrame()

    def get_electrodetest(self, task_id=None, cur=None):
        """Read electrode test data from db file. Test data will be read for
        the task given in task_id. If task_id is None, all test data will be
        read.
        """

        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        #pdb.set_trace()
        if task_id is not None:
            cur.execute(self.GET_TASK_ELECTRODETEST, ('{0}'.format(task_id),))
        else:
            cur.execute(self.GET_ELECTRODETESTS)

        etest = cur.fetchall()
        etest_cols = [c[0] for c in cur.description]

        result = DataFrame(etest, columns=etest_cols)

        if temp_cur:
            cur.close()
            conn.close()

        return result

    def get_settings_dict(self, session_id=None, task_id=None, cur=None):
        """Loads all acquisition settings from project file, and sets the instance settings attribute
        with a dictionary containing dicts of name, value pairs as values and SessionID as key.
        """

        result = dict()
        settings = self.get_acqsettings(session_id=None, task_id=None)

        for session in settings['key2'].unique():
            ses_set = settings[settings['key2'] == session]
            result[session] = dict(ses_set[['Setting','Value']].values)
        return result

    def get_acqsettings(self, session_id=None, task_id=None, cur=None):
        """Returns a dataframe with the acquisition settings of the specified session or task,
        or all settings if session_id and task_id is None. You should pass EITHER seesion_id
        OR task_id, NOT both!

        :param session_id: integer or iterable
            The SessionID of the session to query for settings. If None is specified (default)
            the method will retrieve all registered settings.

        :param task_id: integer
            The TaskID of the task to query for settings. If None is specified (default)
            the method will retrieve all registered settings. A task may relate to several
            sessions, if settings were changed during acquisition (or during electrode
            testing).

        :param cur: sql cursor
            Cursor into the sql database. If omitted, a temporary cursor will be created.

        :return: dataframe
            Dataframe containing the acquisition settings.
        """

        args = None
        if session_id is not None:
            args = (session_id,)
            if hasattr(session_id, '__iter__'):
                sql = self.GET_ACQ_SETTINGS_SQL + " WHERE acqs.key2 in ?".format(session_id)
            else:
                sql = self.GET_ACQ_SETTINGS_SQL + " WHERE acqs.key2=?".format(session_id)

        elif task_id is not None:
            args = (int(task_id),)
            sql = self.GET_ACQ_SETTINGS_SQL + \
                  " WHERE acqs.key2=Sessions.ID " + \
                  " AND Sessions.TaskID=?"
        else:
            # Fetch all acquisition settings
            sql = self.GET_ACQ_SETTINGS_SQL

        rows, cols = self.execute_sql(sql, args=args)

        if rows:
            return DataFrame(rows, columns=cols)
        else:
            return None

    def get_sessions(self, session_id=None, task_id=None, cur=None):
        """Returns a dataframe with the acquisition settings of the specified session or task,
        or all settings if session_id and task_id is None. You should pass EITHER seesion_id
        OR task_id, NOT both!

        :param session_id: integer or iterable
            The SessionID of the session to query for settings. If None is specified (default)
            the method will retrieve all registered settings.

        :param task_id: integer
            The TaskID of the task to query for settings. If None is specified (default)
            the method will retrieve all registered settings. A task may relate to several
            sessions, if settings were changed during acquisition (or during electrode
            testing).

        :param cur: sql cursor
            Cursor into the sql database. If omitted, a temporary cursor will be created.

        :return: dataframe
            Dataframe containing the acquisition settings.
        """

        args = None
        if session_id is not None:
            args = (session_id,)
            if hasattr(session_id, '__iter__'):
                sql = self.GET_SESSIONS_SQL + " WHERE ID in ?".format(session_id)
            else:
                sql = self.GET_SESSIONS_SQL + " WHERE ID=?".format(session_id)

        elif task_id is not None:
            args = (int(task_id),)
            sql = self.GET_SESSIONS_SQL + \
                  " WHERE Sessions.TaskID=?"
        else:
            # Fetch all acquisition settings
            sql = self.GET_SESSIONS_SQL

        rows, cols = self.execute_sql(sql, args=args)

        if rows:
            return DataFrame(rows, columns=cols)
        else:
            return None

            
    def get_task_coords(self, task_id=1, cur=None):
        """Get the station coordinates of the specified task

        :param task_id: integer
            The index (1-based) of the task to retrieve. If omitted, TaskID 1 is returned.
        :param cur: sql cursor
            Cursor into the sql database. If omitted, a temporary cursor will be created.

        Returns: dataframe
            Returns a dataframe with information about each station in the task .
        """

        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        #pdb.set_trace()
        cur.execute(self.GET_TASK_COORDS, (int(task_id),))
        task = cur.fetchall()
        task_cols = [c[0] for c in cur.description]

        if task:
            result = DataFrame(task, columns=task_cols)
        else:
            result = DataFrame()

        if temp_cur:
            cur.close()
            conn.close()

        return result
            


    def has_measurements(self, task_id=None, cur=None):
        """Evaluate whether the task has any measurement data available.

        :param task_id: integer
            The TaskID of the task to query for measurements. If None is specified (default)
            the method will query whether the project has data in any task.

        :param cur: sql cursor
            Cursor into the sql database. If omitted, a temporary cursor will be created.

        :return: boolean
            True if data is present in task (or project if task_id is None), or False
            if data is not present.
        """

        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        if task_id is not None:
            cur.execute(self.HAS_MEASUREMENTS_SQL +
                        " WHERE DPV.TaskID=? " +
                        " LIMIT 10",
                        (int(task_id),))
        else:
            cur.execute(self.HAS_MEASUREMENTS_SQL + " LIMIT 10")

        task = cur.fetchall()

        if temp_cur:
            cur.close()
            conn.close()

        if task:
            return True
        else:
            return False


    def get_spreadfile(self, fname, path=""):
        if not fname:
            raise ValueError('No valid filename passed to get_spreadfile.')
        basename = os.path.basename(fname)
        if basename in list(self.spread_files.keys()):
            tree = self.spread_files[basename]
        else:
            if not path:
                path = self.xml_path
            filename = os.path.join(path,basename)
            try:
                tree = etree.parse(filename)
                self.spread_files[basename] = tree
            except:
                warnings.warn("Spread file not found... ({0})".format(filename))
                return None
        return tree


    def get_electrode_id(self, posx=None, posy=None, posz=None,
                         switch_number=1, switch_address=None,
                         spreadfile="", path="", task_id=None):

        if not spreadfile and task_id is not None:
            spreadfile = os.path.basename(self.tasks.SpreadFile[self.tasks.ID==task_id].values[0])
        tree = self.get_spreadfile(spreadfile, path)
        #pdb.set_trace()
        if posx is not None:
            xpstring = ".//Electrode[X//text()=' {0:.0f} '".format(posx)
            if posy is not None:
                xpstring += " and Y//text()=' {0:.0f} '".format(posy)
            #if posz is not None:
            #    xpstring += " and Z//text()=' {0:.0f} '".format(posz)
        elif switch_address is not None:
            if switch_number != 1:
                raise NotImplementedError('Support for more than one switch is not implemented.')
            xpstring = ".//Electrode[SwitchAddress//text()=' {0:.0f} '".format(switch_address)

        xpstring += "]//Id//text()"

        try:
            return int(tree.xpath(xpstring)[0])
        except:
            print("Could not find electrode: " + xpstring)
            return None

    def export_dat(self, task_id=1, filename=None, out_path=None, exclude_negative=True, datatype='resistivity'):
        
        tasklist = self.get_tasklist()
        task_info = tasklist.set_index('ID').loc[task_id]
    
        data, ecr_data = self.get_task(task_id=task_id)
        
        if datatype == 'resistivity':
            resistivity = data[data['DatatypeID']==2]    # get measured resistivities
            #dat = resistivity[['MeasureID','Channel','APosX','APosZ','BPosX','BPosZ','MPosX','MPosZ','NPosX','NPosZ','DataValue','Time']].copy()
            dat = resistivity[['APosX','APosZ','BPosX','BPosZ','MPosX','MPosZ','NPosX','NPosZ','DataValue']].copy()
        else:
            resistance = data[(data['DatatypeID']==5) & (data['Channel']>0)]     # get measured resistances
            #dat = resistance[['MeasureID','Channel','APosX','APosZ','BPosX','BPosZ','MPosX','MPosZ','NPosX','NPosZ','DataValue','Time']].copy()
            dat = resistance[['APosX','APosZ','BPosX','BPosZ','MPosX','MPosZ','NPosX','NPosZ','DataValue']].copy()
            
        if exclude_negative:
            dat = dat[dat['DataValue']>=0]

        dat.insert(loc=0, column='n_elec', value=4)

        xspc = task_info['SpacingX']
        dat.loc[:,['APosX','BPosX','MPosX','NPosX']] = dat[['APosX','BPosX','MPosX','NPosX']]*xspc

        if filename is None:
            filename = pathlib.Path(self.filename).parent.stem
        
        if out_path is None:
            out_path = pathlib.Path(self.filename).parent
        else:
            out_path = pathlib.Path(out_path)
        
        outlist = []
        outlist.append(self.filename)
        outlist.append('{0:.2f}'.format(xspc))
        outlist.append('11')
        outlist.append('{0:.0f}'.format(task_info['ArrayCode']))
        outlist.append('Type of measurement (0=app.resistivity, 1=resistance)')
        if datatype == 'resistivity':
            outlist.append('0')
        else:
            outlist.append('1')
            
        outlist.append('{0:.0f}'.format(len(dat)))
        outlist.append('2')   # type of x-location, 1=True horizontal, 2=distance along ground surface
        outlist.append('0')   # IP data included, 0=No, 1=Yes
        outlist.append(dat[dat['DataValue']>=0][::-1].to_string(header=None, index=False, index_names=False))
        outlist.append('0\n0\n0\n0\n0\n0\n0\n0\n0\n0\n0\n0')
        
        with open((out_path/filename).with_suffix('.dat'), 'w') as f:
            f.write('\n'.join(outlist))




def condense_measurements(data, datatype_dict):
    """Condense measurements such that all measurement values for a specific
    channel and MeasureID is in the same row

    data:           a DataFrame as returned by ABEMLS_project.get_task()
    datatype_dict:  a dictionary of datatypes as stored in ABEMLS_project.datatypes
    """

    # raise NotImplementedError('condense_measurements method not yet finished!')

    rep_dict = {'\u03c1': r'rho_',
                '\u0394': r'd',
                '\u03a9': r'Ohm'}


    MeasureIDs = data.MeasureID.unique()
    channels = data.Channel.unique()

    result = None

    for mid in MeasureIDs:

        # Here we should get out the Current:

        # Ivalue = ....
        # Isdev = ....

        # So that we can add it below...

        for c in channels:
            if (c<1) or (c>12):
                # only handle data channels
                continue

            dat = data[(data.MeasureID==mid) & (data.Channel==c)]

            if len(dat) == 0:
                continue

            # Prepare new DataFrame
            tmp = dat.ix[dat.index[0]].copy()
            tmp = tmp.drop(['DataValue', 'DataSDev', 'SeqNum',
                            'DatatypeID'])
            df = DataFrame(data=np.atleast_2d(tmp.values),
                           columns=tmp.index)

            for dtid in sorted(dat.DatatypeID.unique()):
                d = dat[dat.DatatypeID==dtid]
                if len(d.SeqNum)==0:
                    # No data with this datatype
                    continue
                elif len(d.SeqNum)>1:
                    # Loop over all sequence numbers and add a subscript when
                    # adding the name
                    for sn in d.SeqNum.unique():
                        pass
                else:
                    # We have only one item with this datatype, add it...
                    n = datatype_dict[dtid]['Name']

                    # Replace known non-ascii unicode chars from names
                    for k,v in list(rep_dict.items()):
                        n = n.replace(k,v)

                    df[n] = np.array(d.DataValue, dtype=float)[0]
                    df[n+'_SDev'] = np.array(d.DataSDev, dtype=float)[0]

            if result is None:
                result = df.copy()
            else:
                result = result.append(df, ignore_index=True)


    return result



