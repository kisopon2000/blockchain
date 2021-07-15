#--------------------
# serverapi.py
#--------------------

import config.defines as const
import datetime
import random
import urllib.parse

from lib.utils import RequestApi
from lib.utils import SystemConfigApi
from lib.wallet import Transaction

class ServerApi(object):
    #--------------------
    # private
    #--------------------
    m_cConfig = None
    m_cRequestApi = None
    def __init__(self):
        self.m_cConfig = SystemConfigApi()
        self.m_cRequestApi = RequestApi()
    def __getRequestUrl(self, in_hosts, in_url_rsc):
        if len(in_hosts) == 0:
            print('<!> in_hosts is empty')
            return None
        index = random.randint(0, len(in_hosts) - 1)    # ƒ‰ƒ“ƒ_ƒ€‚É‘I‘ð
        protocol = in_hosts[index]['protocol']
        host = in_hosts[index]['host']
        port = in_hosts[index]['port']
        gateway = f'{protocol}://{host}:{port}'
        url = urllib.parse.urljoin(gateway, in_url_rsc)
        return url
    #--------------------
    # public
    #--------------------
    def getDBInfo(self):
        return self.m_cConfig.getDBDriver(), self.m_cConfig.getDBServer(), self.m_cConfig.getDBName(), self.m_cConfig.getDBUid(), self.m_cConfig.getDBPwd()
    def parseToken(self, in_token):
        token = self.m_cRequestApi.parseToken(in_token)
        if token == None:
            print("<!> Token parse error")
            return None
        else:
            self.m_cToken = token
            return token
    def createToken(self, in_token_base):
        token = self.m_cRequestApi.createToken(in_token_base)
        if token == None:
            print("<!> Token create error")
            return None
        else:
            return token
    def createSignature(self, in_type, in_request_json_template):
        
        if in_type == const.BLOCKCHAIN_TYPE_POINT:
            transaction = Transaction(
                in_type,
                in_request_json_template['secret_key'],
                in_request_json_template['key'],
                in_request_json_template['sender_blockchain_address'],
                in_request_json_template['recipient_blockchain_address'],
                in_request_json_template['value'])
            try:
                return transaction.generate_signature()
            except Exception as exception:
                print(exception)
                return None
        elif in_type == const.BLOCKCHAIN_TYPE_NFT:
            transaction = Transaction(
                in_type,
                in_request_json_template['secret_key'],
                in_request_json_template['key'],
                in_request_json_template['sender_blockchain_address'],
                in_request_json_template['recipient_blockchain_address'],
                in_request_json_template['value'])
            try:
                return transaction.generate_signature()
            except Exception as exception:
                print(exception)
                return None
        else:
            print('<!> not support type:', in_type)
            return None
    def createTransactionRequestJson(self, in_type, in_request_json_template):
        if in_type == const.BLOCKCHAIN_TYPE_POINT:
            signature = self.createSignature(in_type, in_request_json_template)
            if signature is None:
                return None
            else:
                request_json = {
                    'type': in_type,
                    'sender_public_key': in_request_json_template['key'],
                    'sender_blockchain_address': in_request_json_template['sender_blockchain_address'],
                    'recipient_blockchain_address': in_request_json_template['recipient_blockchain_address'],
                    'value': in_request_json_template['value'],
                    'signature': signature,
                }
                return request_json
        elif in_type == const.BLOCKCHAIN_TYPE_NFT:
            signature = self.createSignature(in_type, in_request_json_template)
            if signature is None:
                return None
            else:
                request_json = {
                    'type': in_type,
                    'sender_public_key': in_request_json_template['key'],
                    'sender_blockchain_address': in_request_json_template['sender_blockchain_address'],
                    'recipient_blockchain_address': in_request_json_template['recipient_blockchain_address'],
                    'id': in_request_json_template['id'],
                    'value': in_request_json_template['value'],
                    'url': in_request_json_template['url'],
                    'contract': in_request_json_template['contract'],
                    'signature': signature,
                }
                return request_json
        else:
            print('<!> not support type:', in_type)
            return None
    def getTransactionRequestUrl(self, in_hosts):
        return self.__getRequestUrl(in_hosts, 'transactions')
    def getAmountRequestUrl(self, in_hosts):
        return self.__getRequestUrl(in_hosts, 'amounts')
    def createNftRequestJson(self, in_type, in_request_json_template):
        signature = self.createSignature(in_type, in_request_json_template)
        if signature is None:
            return None
        else:
            request_json = {
                'type': in_type,
                'sender_public_key': in_request_json_template['key'],
                'sender_blockchain_address': in_request_json_template['sender_blockchain_address'],
                'recipient_blockchain_address': in_request_json_template['sender_blockchain_address'],
                'id': in_request_json_template['id'],
                'value': in_request_json_template['value'],
                'url': in_request_json_template['url'],
                'contract': in_request_json_template['contract'],
                'signature': signature,
            }
            return request_json
    def getNftRequestUrl(self, in_hosts):
        return self.__getRequestUrl(in_hosts, 'nfts')
