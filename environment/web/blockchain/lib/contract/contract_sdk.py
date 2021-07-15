#====================
# contract_sdk.py
#====================

import json
import os
import requests

import config.defines as const

from lib.serverapi import ServerApi
from lib.utils import SystemConfigApi
from lib.utils import Utils

class ContractPoint(object):
    def __set_neighbours(self):
        return Utils.find_neighbours(
            Utils.get_host(), int(os.environ['BLOCKCHAIN_ENV_CONTRACT_PORT']),
            const.BLOCKCHAIN_NEIGHBOURS_IP_RANGE_NUM[0], const.BLOCKCHAIN_NEIGHBOURS_IP_RANGE_NUM[1],
            const.BLOCKCHAIN_PORT_RANGE[0], const.BLOCKCHAIN_PORT_RANGE[1]
        )
    def sendPoint(self, in_original_recipient_blockchain_address, in_rate):
        sender_blockchain_address = os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_SENDER_ADDRESS']
        recipient_blockchain_address = in_original_recipient_blockchain_address
        value = float(os.environ['BLOCKCHAIN_ENV_CONTRACT_VALUE']) * in_rate
        key = os.environ['BLOCKCHAIN_ENV_CONTRACT_KEY']
        secret_key = os.environ['BLOCKCHAIN_ENV_CONTRACT_SECRET_KEY']
        os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_RATE'] = str(in_rate)

        serverapi = ServerApi()
        request_json_template = {}
        request_json_template['sender_blockchain_address'] = sender_blockchain_address
        request_json_template['recipient_blockchain_address'] = recipient_blockchain_address
        request_json_template['value'] = value
        request_json_template['key'] = key
        request_json_template['secret_key'] = secret_key
        request_json = serverapi.createTransactionRequestJson(const.BLOCKCHAIN_TYPE_POINT, request_json_template)
        if request_json is None:
            print('<!> createTransactionRequestJson failed')
            return None
        neighbours = self.__set_neighbours()
        for node in neighbours:
            try:
                print(f'########## contract http://{node}/transactions')
                response = requests.post(
                    f'http://{node}/transactions',
                    json=request_json,
                    timeout=3)
            except Exception as exception:
                print(exception)
        return True
