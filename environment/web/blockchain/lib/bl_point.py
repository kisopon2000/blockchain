#====================
# bl_point.py
#====================

import config.defines as const
import copy
import datetime
import json
import os
import pickle
import plyvel
import requests
import threading
import time

from lib.block import Block
from lib.utils import SystemConfigApi
from lib.utils import Utils

class BlPoint(Block):
    def __init__(self, id, blockchain_address, port, transaction_pool, chain):
        super().__init__(id, blockchain_address, port, transaction_pool, chain)
    def run(self):
        #self.start_mining()
        print('BlPoint.run()')
    def get_transaction_json(self, in_tx_infos):
        json={
            'type': in_tx_infos['type'],
            'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
            'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address'],
            'value': in_tx_infos['value'],
            'sender_public_key': in_tx_infos['sender_public_key'],
            'signature': in_tx_infos['signature'],
            'transaction_id': in_tx_infos['transaction_id'],
        }
        return json
    def create_transaction_id(self, in_tx_infos):
        now = datetime.datetime.now().isoformat()
        transaction_id = Utils.sorted_dict_by_key({
            'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
            'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address'],
            'value': float(in_tx_infos['value']),
            'datetime': now
        })
        return Utils.hash(transaction_id)
    def get_transaction_core(self, in_tx_infos):
        return Utils.sorted_dict_by_key({
            'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
            'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address'],
            'value': float(in_tx_infos['value']),
        })
    def get_transaction(self, in_transaction_id, in_type, in_tx_infos):
        transaction = Utils.sorted_dict_by_key({
            'transaction_id': in_transaction_id,
            'type': in_type,
            'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
            'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address'],
            'value': float(in_tx_infos['value']),
        })
        print('=============================================')
        print('transaction_id:', in_transaction_id)
        print('type:', in_type)
        print('sender_blockchain_address:', in_tx_infos['sender_blockchain_address'])
        print('recipient_blockchain_address:', in_tx_infos['recipient_blockchain_address'])
        print('value:', in_tx_infos['value'])
        if not in_tx_infos.get('sender_public_key') is None:
            print('sender_public_key:', in_tx_infos['sender_public_key'])
        if not in_tx_infos.get('signature') is None:
            print('signature:', in_tx_infos['signature'])
        print('=============================================')
        return transaction
    def verify_transaction(self, in_tx_infos, in_transaction_core, in_chain):
        if self.verify_transaction_signature(in_tx_infos['sender_public_key'], in_tx_infos['signature'], in_transaction_core):
            if self.calculate_total_amount(in_tx_infos['sender_blockchain_address'], in_chain) < float(in_tx_infos['value']):
                print('<!> calculate_total_amount, error: no_value')
                return False
            return True
        else:
            print('<!> verify_transaction_signature, error')
            return False
    def calculate_total_amount(self, blockchain_address, in_chain):
        total_amount = 0.0
        for block in in_chain:
            for transaction in block['transactions']:
                if 'type' in transaction:
                    if transaction['type'] == const.BLOCKCHAIN_TYPE_POINT:
                        value = float(transaction['value'])
                        if blockchain_address == transaction['recipient_blockchain_address']:
                            total_amount += value
                        if blockchain_address == transaction['sender_blockchain_address']:
                            total_amount -= value
        return total_amount
    def exec_contract(self, in_tx_infos):
        return None
