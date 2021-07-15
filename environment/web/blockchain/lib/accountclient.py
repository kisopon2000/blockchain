#--------------------
# accountclient.py
#--------------------

from lib.dbapi import DBApi
from lib.utils import RequestApi
from lib.wallet import Wallet

class AccountClient(DBApi):
    #--------------------
    # private
    #--------------------
    def __isExistUserId(self, in_user_id):
        sql = f'SELECT count (*) FROM accounts where user_id = \'{in_user_id}\''
        self.m_cursor.execute(sql)
        rows = self.m_cursor.fetchall()
        count = rows[0][0]
        print('user count is', count)
        if count > 0:
            return True
        else:
            return False
    def __isExistUser(self, in_user_id, in_password):
        sql = f'SELECT count (*) FROM accounts where user_id = \'{in_user_id}\' and password = \'{in_password}\''
        self.m_cursor.execute(sql)
        rows = self.m_cursor.fetchall()
        count = rows[0][0]
        print('user count is', count)
        if count > 0:
            return True
        else:
            return False
    #--------------------
    # public
    #--------------------
    def createAccount(self, in_user_id, in_password):
        if not in_user_id:
            self.error('<!> in_user_id is none')
            return None
        if not in_password:
            self.error('<!> in_password is none')
            return None
        if self.__isExistUserId(in_user_id):
            self.error('<!> in_user_id is already existed')
            return None
        wallet = Wallet()
        public_key = wallet.public_key
        secret_key = wallet.private_key
        blockchain_address = wallet.blockchain_address
        sql = f'INSERT INTO accounts VALUES (\'{in_user_id}\', \'{in_password}\', \'{public_key}\', \'{secret_key}\', \'{blockchain_address}\', NULL)'
        try:
            self.m_cursor.execute(sql)
        except Exception as exception:
            print(exception)
            self.rollback()
            return None
        sql = f'SELECT user_oid FROM accounts where user_id = \'{in_user_id}\''
        try:
            self.m_cursor.execute(sql)
        except Exception as exception:
            print(exception)
            self.rollback()
            return None
        columns = [column[0] for column in self.m_cursor.description]
        accounts = []
        for row in self.m_cursor.fetchall():
            accounts.append(dict(zip(columns, row)))
        if len(accounts) > 0:
            user_oid = accounts[0]['user_oid']
        else:
            print('<!> not found user_oid')
            self.rollback()
            return None
        requestapi = RequestApi()
        token_base = { "company_id": "FB", "user_oid": user_oid }
        token = requestapi.createToken(token_base)
        if token is None:
            print('<!> token is none')
            self.rollback()
            return None
        self.commit()
        return token
    def getAccounts(self, in_user_oid=None):
        if in_user_oid is None:
            sql = 'SELECT public_key AS \'key\', secret_key, blockchain_address FROM accounts'
        else:
            sql = f'SELECT public_key AS \'key\', secret_key, blockchain_address FROM accounts where user_oid = {in_user_oid}'
        self.m_cursor.execute(sql)
        columns = [column[0] for column in self.m_cursor.description]
        results = []
        for row in self.m_cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    def getToken(self, in_user_id, in_password):
        if not in_user_id:
            self.error('<!> in_user_id is none')
            return None
        if not in_password:
            self.error('<!> in_password is none')
            return None
        if self.__isExistUser(in_user_id, in_password) is False:
            self.error('<!> user not found')
            return None
        sql = f'SELECT user_oid FROM accounts where user_id = \'{in_user_id}\' and password = \'{in_password}\''
        self.m_cursor.execute(sql)
        rows = self.m_cursor.fetchall()
        user_oid = rows[0][0]
        requestapi = RequestApi()
        token_base = { "company_id": "FB", "user_oid": user_oid }
        token = requestapi.createToken(token_base)
        if token is None:
            print('<!> token is none')
            return None
        return token
    def getHosts(self, in_id=None):
        if in_id is None:
            sql = 'SELECT * FROM hosts'
        else:
            sql = f'SELECT * FROM hosts where id = {in_id}'
        self.m_cursor.execute(sql)
        columns = [column[0] for column in self.m_cursor.description]
        results = []
        for row in self.m_cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
