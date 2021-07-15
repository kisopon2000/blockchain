#====================
# utils.py
#====================

import collections
import config.defines as const
import datetime
import hashlib
import json
import os
import random
import re
import socket
import string
import subprocess
import sys
import xml.etree.ElementTree as xmlparser

RE_IP = re.compile('(?P<prefix_host>^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.)(?P<last_ip>\\d{1,3}$)')

class Utils(object):
    @staticmethod
    def sorted_dict_by_key(unsorted_dict):
        return collections.OrderedDict(
            sorted(unsorted_dict.items(), key=lambda d:d[0]))
    @staticmethod
    def pprint(chains):
        for i, chain in enumerate(chains):
            print(f'{"="*25} Chain {i} {"="*25}')
            for k, v in chain.items():
                if k == 'transactions':
                    print(k)
                    for d in v:
                        print(f'{"-"*40}')
                        for kk, vv in d.items():
                            print(f'{kk:30}{vv}')
                else:
                    print(f'{k:15}{v}')
        print(f'{"*"*25}')
    @staticmethod
    def is_found_host(target, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect((target, port))
                return True
            except Exception as ex:
                print(ex)
                return False
    @staticmethod
    def find_neighbours(my_host, my_port, start_ip_range, end_ip_range, start_port, end_port):
        address = f'{my_host}:{my_port}'
        m = RE_IP.search(my_host)
        if not m:
            return None
        prefix_host = m.group('prefix_host')
        last_ip = m.group('last_ip')
        neighbours = []
        for guess_port in range(start_port, end_port):
            for ip_range in range(start_ip_range, end_ip_range):
                guess_host = f'{prefix_host}{int(last_ip)+int(ip_range)}'
                guess_address = f'{guess_host}:{guess_port}'
                if Utils.is_found_host(guess_host, guess_port) and not guess_address == address:
                    neighbours.append(guess_address)
        return neighbours
    @staticmethod
    def get_host():
        #try:
        #    return socket.gethostbyname(socket.gethostname())
        #except Exception as ex:
        #    print(ex)
        return '127.0.0.1'
    @staticmethod
    def hash(block):
        sorted_block = json.dumps(block, sort_keys=True)
        return hashlib.sha256(sorted_block.encode()).hexdigest()
    @staticmethod
    def randomname(n):
        randlst = [random.choice(string.ascii_letters + string.digits) for i in range(n)]
        return ''.join(randlst)


class SystemConfigApi():
    #--------------------
    # private
    #--------------------
    m_init = False
    m_configpath = os.path.dirname(__file__) + '\..\config\config.xml'
    m_xmlroot = None
    def __init(self):
        self.xmlroot = xmlparser.parse(self.m_configpath)
        self.m_xmlroot = self.xmlroot.getroot()
        self.m_init = True
    #--------------------
    # public
    #--------------------
    def getLogMaxFileCycle(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('log/maxfilecycle').text
    def getLogMaxFileSize(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('log/maxfilesize').text
    def getLogLevel(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('log/level').text
    def getDBDriver(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('db/driver').text
    def getDBServer(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('db/server').text
    def getDBName(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('db/dbname').text
    def getDBUid(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('db/uid').text
    def getDBPwd(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('db/pwd').text
    def getLevelDBDir(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('db/leveldb/dir').text
    def getBaseIp(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('host/base_ip').text
    def getIpNum(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('host/ip_num').text
    def getBasePort(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('host/base_port').text
    def getPortNum(self):
        if not self.m_init:
            self.__init()
        return self.m_xmlroot.find('host/port_num').text
    def save(self):
        self.xmlroot.write(self.m_configpath)
        self.m_init = False


class LogApi():
    #--------------------
    # private
    #--------------------
    m_init = False
    m_outputpath = ''
    m_maxfilecycle = 0
    m_maxfilesize = 0
    m_level = 0
    def __init(self):
        outputdir = os.path.dirname(__file__) + '\..\log'
        outputpath = os.path.dirname(__file__) + '\..\log\log.000'
        if not os.path.exists(outputdir):
            os.mkdir(outputdir)
        self.m_outputpath = outputpath
        config = SystemConfigApi()
        self.m_maxfilecycle = int(config.getLogMaxFileCycle())
        self.m_maxfilesize = int(config.getLogMaxFileSize())
        level = config.getLogLevel()
        if level == 'ERR':
            self.m_level = const.LOG_LEVEL_ERR
        elif level == 'WAR':
            self.m_level = const.LOG_LEVEL_WAR
        elif level == 'INF':
            self.m_level = const.LOG_LEVEL_INF
        elif level == 'DBG':
            self.m_level = const.LOG_LEVEL_DBG
        else:
            self.m_level = const.LOG_LEVEL_OTH
        self.m_init = True
    def __renameRecurse(self, in_cycle):
        if in_cycle == 0:
            return 0
        else:
            cycle = in_cycle - 1
            if in_cycle == self.m_maxfilecycle:
                outputpath = os.path.dirname(__file__) + '\..\log\log.' + format(cycle, '03d')
                if os.path.exists(outputpath):
                    # ç≈ëÂê¢ë„ÇÕíPèÉçÌèú
                    os.remove(outputpath)
            else:
                oldpath = os.path.dirname(__file__) + '\..\log\log.' + format(cycle, '03d')
                newpath = os.path.dirname(__file__) + '\..\log\log.' + format(in_cycle, '03d')
                if os.path.exists(oldpath):
                    # íÜä‘ê¢ë„ÇÕÉäÉlÅ[ÉÄ
                    os.rename(oldpath, newpath)
            self.__renameRecurse(cycle)
    def __log(self, in_type, in_level, in_message):
        if in_level < self.m_level:
            return
        if os.path.exists(self.m_outputpath):
            if os.path.getsize(self.m_outputpath) > self.m_maxfilesize:
                self.__renameRecurse(self.m_maxfilecycle)
        date = '[' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '] '
        message = date + '<' + in_type + '> ' + in_message
        file = open(self.m_outputpath, 'a')
        file.write(message + '\n')
        file.close()
    #--------------------
    # public
    #--------------------
    def log(self, in_message):
        if not self.m_init:
            self.__init()
        self.__log('INF', const.LOG_LEVEL_INF, in_message)
    def warning(self, in_message):
        if not self.m_init:
            self.__init()
        self.__log('WAR', const.LOG_LEVEL_WAR, in_message)
    def debug(self, in_message):
        if not self.m_init:
            self.__init()
        self.__log('DBG', const.LOG_LEVEL_DBG, in_message)
    def error(self, in_message):
        if not self.m_init:
            self.__init()
        self.__log('ERR', const.LOG_LEVEL_ERR, in_message)


class RequestApi():
    #--------------------
    # private
    #--------------------
    m_init = False
    def __init(self):
        self.m_init = True
    #--------------------
    # public
    #--------------------
    def parseToken(self, in_token):
        if not self.m_init:
            self.__init()
        cwd = os.getcwd()
        os.chdir("../../system/cmd")
        handle = subprocess.run(["./adcrypt.exe", "-decode", "-in", in_token], stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin=subprocess.DEVNULL)
        os.chdir(cwd)
        val = handle.stdout.decode("utf8")
        val = val.replace('\n','')
        if '[ERROR]' in val:
            return None
        else:
            val = json.loads(val)
            return val
    def createToken(self, in_token_base):
        if not self.m_init:
            self.__init()
        token_base = json.dumps(in_token_base, ensure_ascii=False)
        cwd = os.getcwd()
        os.chdir("../../system/cmd")
        handle = subprocess.run(["./adcrypt.exe", "-encode", "-in", token_base], stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin=subprocess.DEVNULL)
        os.chdir(cwd)
        val = handle.stdout.decode("utf8")
        val = val.replace('\n','')
        if '[ERROR]' in val:
            return None
        else:
            return val
