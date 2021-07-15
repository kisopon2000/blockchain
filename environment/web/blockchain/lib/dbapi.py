#--------------------
# dbapi.py
#--------------------

import pyodbc
from lib.utils import LogApi

class DBApi():
    m_cLogApi = None
    m_connection = None
    m_cursor = None
    def connect(self, in_driver, in_server, in_dbname, in_uid, in_pwd):
        if self.m_cLogApi == None:
            self.m_cLogApi = LogApi()
        dburl = 'DRIVER=' + in_driver + ';SERVER=' + in_server + ';DATABASE=' + in_dbname + ';UID=' + in_uid + ';PWD=' + in_pwd
        self.m_connection = pyodbc.connect(dburl)
        self.m_cursor = self.m_connection.cursor()
    def commit(self):
        self.m_connection.commit()
    def rollback(self):
        self.m_connection.rollback()
    def close(self):
        self.m_cursor.close()
        self.m_connection.close()
    def log(self, in_message):
        self.m_cLogApi.log(in_message)
    def warning(self, in_message):
        self.m_cLogApi.warning(in_message)
    def debug(self, in_message):
        self.m_cLogApi.debug(in_message)
    def error(self, in_message):
        self.m_cLogApi.error(in_message)

class DataHandler(DBApi):
    def getCompany(self):
        self.m_cursor.execute("SELECT * FROM companies")
        columns = [column[0] for column in self.m_cursor.description]
        results = []
        for row in self.m_cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
