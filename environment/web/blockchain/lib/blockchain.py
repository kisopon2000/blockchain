#====================
# blockchain.py
#====================

import config.defines as const
import contextlib
import datetime
import hashlib
import json
import os
import pickle
import plyvel
import requests
import threading
import time
import sys

from lib.block import Block
from lib.bl_point import BlPoint
from lib.bl_nft import BlNft
from lib.serverapi import ServerApi
from lib.utils import SystemConfigApi
from lib.utils import Utils

from ecdsa import NIST256p
from ecdsa import VerifyingKey

class BlockChain(object):
    def __init__(self, id, key, secret_key, blockchain_address=None, port=None):
        self.id = id
        self.key = key
        self.secret_key = secret_key
        self.transaction_pool = []
        self.chain = []
        self.neighbours = []
        self.blockchain_address = blockchain_address
        self.db = None
        self.create_block(0, Utils.hash({}))
        self.mining_semaphore = threading.Semaphore(1)
        self.bl_point = BlPoint(id, blockchain_address, port, self.transaction_pool, self.chain)  # 参照渡しになる？
        self.bl_nft = BlNft(id, blockchain_address, port, self.transaction_pool, self.chain)  # 参照渡しになる？
                
        self.neighbours = []
        self.port = port
        self.sync_neighbours_semaphore = threading.Semaphore(const.BLOCKCHAIN_SEMAPHORE_NEIGHBOURS)
        self.sdk_semaphore = threading.Semaphore(const.BLOCKCHAIN_SEMAPHORE_SDK)
    def __setup_db(self):
        systemconfigapi = SystemConfigApi()
        dir = systemconfigapi.getLevelDBDir()
        filename = 'tx_point_%s.ldb' % (self.id)
        filepath = os.path.join(dir, filename)
        if os.path.exists(dir) is False:
            os.makedirs(dir)
        print('db filepath:', filepath)
        self.db = plyvel.DB(filepath, create_if_missing=True)
        
        chain = self.db.get(u'chain'.encode('utf-8'))
        transaction_pool = self.db.get(u'transaction_pool'.encode('utf-8'))
        if not chain is None:
            self.chain = pickle.loads(chain)
        if not transaction_pool is None:
            self.transaction_pool = pickle.loads(transaction_pool)
    def __get_block_obj(self, in_type):
        if in_type == const.BLOCKCHAIN_TYPE_POINT:
            return self.bl_point
        elif in_type == const.BLOCKCHAIN_TYPE_NFT:
            return self.bl_nft
        else:
            print('<!> not support type:', in_type)
            return None
    def __is_contract_exec(self, in_type):
        if in_type == const.BLOCKCHAIN_TYPE_POINT:
            return False
        elif in_type == const.BLOCKCHAIN_TYPE_NFT:
            return True
        else:
            print('<!> not support type:', in_type)
            return False
    def run(self):
        self.__setup_db()
        self.sync_neighbours()
        self.resolve_conflicts()
    def finalize(self):
        print('blockchain finalize start')
        chain = pickle.dumps(self.chain)
        transaction_pool = pickle.dumps(self.transaction_pool)
        self.db.put(u'chain'.encode('utf-8'), chain)
        self.db.put(u'transaction_pool'.encode('utf-8'), transaction_pool)
        self.db.close()
        print('blockchain finalize end')
    def get_chain(self):
        return self.chain
    def get_transaction_pool(self):
        return self.transaction_pool
    def delete_transaction_pool(self):
        self.transaction_pool = []
    def set_neighbours(self):
        self.neighbours = Utils.find_neighbours(
            Utils.get_host(), self.port,
            const.BLOCKCHAIN_NEIGHBOURS_IP_RANGE_NUM[0], const.BLOCKCHAIN_NEIGHBOURS_IP_RANGE_NUM[1],
            const.BLOCKCHAIN_PORT_RANGE[0], const.BLOCKCHAIN_PORT_RANGE[1]
        )
        print(self.neighbours)
    def sub_sync_neighbours(self):
        is_acquire = self.sync_neighbours_semaphore.acquire(blocking=False)
        if is_acquire:
            print('===== sub_sync_neighbours =====')
            self.set_neighbours()
            self.sync_neighbours_semaphore.release()
        time.sleep(const.BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC)
        t = threading.Thread(target=self.sub_sync_neighbours)
        t.setDaemon(True)
        t.start()
    def sync_neighbours(self):
        # これだと終了してくれない
        #is_acquire = self.sync_neighbours_semaphore.acquire(blocking=False)
        #if is_acquire:
        #    print('===== sync_neighbours =====')
        #    with contextlib.ExitStack() as stack:
        #        stack.callback(self.sync_neighbours_semaphore.release)
        #        self.set_neighbours()
        #        loop = threading.Timer(const.BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC, self.sync_neighbours)
        #        loop.start()
        t = threading.Thread(target=self.sub_sync_neighbours)
        t.setDaemon(True)
        t.start()
    def mining(self):
        blockobj = self.__get_block_obj(const.BLOCKCHAIN_TYPE_POINT)
        if blockobj is None:
            print('<!> cannot create object')
            return False
        #if not self.transaction_pool:
        #    return False
        is_updated, transaction_id = self.add_transaction(const.BLOCKCHAIN_TYPE_POINT, {
            'sender_blockchain_address': const.BLOCKCHAIN_MINING_SENDER,
            'recipient_blockchain_address': self.blockchain_address,
            'value': const.BLOCKCHAIN_MINING_REWARD
        })
        nonce = blockobj.proof_of_work(self.chain, self.transaction_pool)
        previous_hash = Utils.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)
        print('action: mining, status: success')
        for node in self.neighbours:
            print('##### put consensus (%s)' % (node) )
            requests.put(f'http://{node}/consensus')
        return True
    def sub_start_mining(self):
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            print('===== sub_start_mining =====')
            self.mining()
            self.mining_semaphore.release()
        time.sleep(const.BLOCKCHAIN_MINING_TIMER_SEC)
        t = threading.Thread(target=self.sub_start_mining)
        t.setDaemon(True)
        t.start()
    def start_mining(self):
        # これだと終了してくれない
        #is_acquire = self.mining_semaphore.acquire(blocking=False)
        #if is_acquire:
        #    with contextlib.ExitStack() as stack:
        #        stack.callback(self.mining_semaphore.release)
        #        self.mining()
        #        loop = threading.Timer(const.BLOCKCHAIN_MINING_TIMER_SEC, self.start_mining)
        #        loop.start()
        t = threading.Thread(target=self.sub_start_mining)
        t.setDaemon(True)
        t.start()
    def resolve_conflicts(self):
        blockobj = self.__get_block_obj(const.BLOCKCHAIN_TYPE_POINT)
        if blockobj is None:
            print('<!> cannot create object')
            return False, None
        longest_chain = None
        longest_transactions = None
        max_length = len(self.chain)
        print('########### kiteru? 1')
        for node in self.neighbours:
            print('########### kiteru? 2')
            response = requests.get(f'http://{node}/chain')
            response_transactions = requests.get(f'http://{node}/transactions')
            if response.status_code == 200:
                response_json = response.json()
                response_transactions_json = response_transactions.json()
                chain = response_json['chain']
                chain_length = len(chain)
                transactions = response_transactions_json['transactions']
                print('### chain_length:', chain_length)
                print('### max_length:', max_length)
                if chain_length > max_length and blockobj.valid_chain(chain):
                    max_length = chain_length
                    longest_chain = chain
                    longest_transactions = transactions
                    print('########### kiteru? 3')
        if longest_chain:
            print('########### kiteru? 4')
            self.chain = longest_chain
            print('action: resolve_conflicts(chain), status: replaced')
            if len(longest_transactions) > 0:
                self.transaction_pool = longest_transactions
                print('action: resolve_conflicts(transaction), status: replaced')
            return True
        print('action: resolve_conflicts, status: not replaced')
        return False
    def create_block(self, nonce, previous_hash):
        block = Utils.sorted_dict_by_key({
            'timestamp': time.time(),
            'transactions': self.transaction_pool,
            'nonce': nonce,
            'previous_hash': previous_hash
        })
        self.chain.append(block)
        self.transaction_pool = []
        for node in self.neighbours:
            requests.delete(f'http://{node}/transactions')
        return block
    def add_transaction(self, in_type, in_tx_infos, in_contract_exec=True):
        blockobj = self.__get_block_obj(in_type)
        if blockobj is None:
            print('<!> cannot create object')
            return False, None
        if in_tx_infos.get('transaction_id') is None:
            transaction_id = None
        else:
            transaction_id = in_tx_infos['transaction_id']
        if transaction_id is None:
            transaction_id = blockobj.create_transaction_id(in_tx_infos)
        else:
            transaction_id = transaction_id
        if in_tx_infos.get('transaction_datetime') is None:
            in_tx_infos['transaction_datetime'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        transaction_core = blockobj.get_transaction_core(in_tx_infos)
        transaction = blockobj.get_transaction(transaction_id, in_type, in_tx_infos)
        if in_tx_infos['sender_blockchain_address'] == const.BLOCKCHAIN_MINING_SENDER:
            self.transaction_pool.append(transaction)
            print('##### [mining] transaction_pool:', self.transaction_pool)
            return True, transaction_id
        is_verified = blockobj.verify_transaction(in_tx_infos, transaction_core, self.chain)
        if is_verified:
            self.transaction_pool.append(transaction)
            print('##### transaction_pool:', self.transaction_pool)
            if self.__is_contract_exec(in_type) and in_contract_exec:
                print('##### type:', in_type)
                is_acquire = self.sdk_semaphore.acquire(blocking=True)
                if is_acquire:
                    # コントラクト実行
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_SENDER_ADDRESS'] = in_tx_infos['recipient_blockchain_address']
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_RECIPIENT_ADDRESS'] = in_tx_infos['sender_blockchain_address']
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_VALUE'] = str(in_tx_infos['value'])
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_KEY'] = self.key
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_SECRET_KEY'] = self.secret_key
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_PORT'] = str(self.port)
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_RATE'] = '0'
                    response = blockobj.exec_contract(in_tx_infos)
                    point_rate = float(os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_RATE'])
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_SENDER_ADDRESS'] = ''
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_RECIPIENT_ADDRESS'] = ''
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_VALUE'] = '0'
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_KEY'] = ''
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_SECRET_KEY'] = ''
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_PORT'] = '0'
                    os.environ['BLOCKCHAIN_ENV_CONTRACT_POINT_RATE'] = '0'
                    self.sdk_semaphore.release()
                    print('##### point_rate:', str(point_rate))
                    if float(in_tx_infos['value']) > 0:
                        if point_rate > 0:
                            value = float(in_tx_infos['value']) - float(in_tx_infos['value']) * point_rate
                        else:
                            value = float(in_tx_infos['value'])
                        serverapi = ServerApi()
                        request_json_template = {}
                        request_json_template['sender_blockchain_address'] = in_tx_infos['recipient_blockchain_address']
                        request_json_template['recipient_blockchain_address'] = in_tx_infos['sender_blockchain_address']
                        request_json_template['value'] = float(in_tx_infos['value']) - float(in_tx_infos['value']) * point_rate
                        request_json_template['key'] = self.key
                        request_json_template['secret_key'] = self.secret_key
                        request_json = serverapi.createTransactionRequestJson(const.BLOCKCHAIN_TYPE_POINT, request_json_template)
                        if request_json is None:
                            print('<!> createTransactionRequestJson failed')
                        print('##### send point:', request_json_template['value'])
                        for node in self.neighbours:
                            try:
                                response = requests.post(
                                    f'http://{node}/transactions',
                                    json=request_json,
                                    timeout=3)
                            except Exception as exception:
                                print(exception)
                else:
                    print('<!> cannot aquire semaphore')
            return True, transaction_id
        return False, None
    def create_transaction(self, in_type, in_tx_infos):
        blockobj = self.__get_block_obj(in_type)
        if blockobj is None:
            print('<!> cannot create object')
            return False
        is_transacted, transaction_id = self.add_transaction(in_type, in_tx_infos)
        if is_transacted:
            tx_infos = in_tx_infos
            tx_infos['type'] = in_type
            tx_infos['transaction_id'] = transaction_id
            tx_json = blockobj.get_transaction_json(tx_infos)
            for node in self.neighbours:
                print('##### put transactions (%s)' % (node))
                requests.put(
                    f'http://{node}/transactions',
                    json=tx_json
                )
        return is_transacted
    def calculate_total_amount(self, blockchain_address):
        blockobj = self.__get_block_obj(const.BLOCKCHAIN_TYPE_POINT)
        if blockobj is None:
            print('<!> cannot create object')
            return 0
        return blockobj.calculate_total_amount(blockchain_address, self.chain)
    def get_nfts(self, blockchain_address, in_id=None):
        blockobj = self.__get_block_obj(const.BLOCKCHAIN_TYPE_NFT)
        if blockobj is None:
            print('<!> cannot create object')
            return 0
        return blockobj.get_nfts(blockchain_address, self.chain, in_id)
    def create_nft(self, in_nft_infos):
        return self.create_transaction(const.BLOCKCHAIN_TYPE_NFT, in_nft_infos)
