#====================
# bl_nft.py
#====================

import binascii
import config.defines as const
import datetime
import json
import os
import pickle
import plyvel
import requests
import threading
import time

from importlib import import_module

from lib.block import Block
from lib.utils import SystemConfigApi
from lib.utils import Utils

class BlNft(Block):
    def __init__(self, id, blockchain_address, port, transaction_pool, chain):
        super().__init__(id, blockchain_address, port, transaction_pool, chain)
    def get_transaction_json(self, in_tx_infos):
        json={
            'type': in_tx_infos['type'],
            'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
            'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address'],
            'value': in_tx_infos['value'],
            'id': in_tx_infos['id'],
            'url': in_tx_infos['url'],
            'contract': in_tx_infos['contract'],
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
            'value': in_tx_infos['value'],
        })
    def get_transaction(self, in_transaction_id, in_type, in_tx_infos):
        if in_tx_infos['contract']:
            contract = in_tx_infos['contract'].encode('utf-8')
            contract = binascii.hexlify(contract)
            contract = contract.decode('utf-8')  # JSON送信のエラー回避
        else:
            contract = in_tx_infos['contract']
        transaction = Utils.sorted_dict_by_key({
            'transaction_id': in_transaction_id,
            'type': in_type,
            'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
            'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address'],
            'value': float(in_tx_infos['value']),
            'id': in_tx_infos['id'],
            'url': in_tx_infos['url'],
            'contract': contract,
            'transaction_datetime': in_tx_infos['transaction_datetime'],
        })
        print('=============================================')
        print('transaction_id:', in_transaction_id)
        print('type:', in_type)
        print('sender_blockchain_address:', in_tx_infos['sender_blockchain_address'])
        print('recipient_blockchain_address:', in_tx_infos['recipient_blockchain_address'])
        print('value:', in_tx_infos['value'])
        if not in_tx_infos.get('id') is None:
            print('id:', in_tx_infos['id'])
        if not in_tx_infos.get('url') is None:
            print('url:', in_tx_infos['url'])
        if not contract is None:
            print('contract:', contract)
        if not in_tx_infos.get('sender_public_key') is None:
            print('sender_public_key:', in_tx_infos['sender_public_key'])
        if not in_tx_infos.get('signature') is None:
            print('signature:', in_tx_infos['signature'])
        if not in_tx_infos.get('transaction_datetime') is None:
            print('transaction_datetime:', in_tx_infos['transaction_datetime'])
        print('=============================================')
        return transaction
    def verify_transaction(self, in_tx_infos, in_transaction_core, in_chain):
        if self.verify_transaction_signature(in_tx_infos['sender_public_key'], in_tx_infos['signature'], in_transaction_core):
            # ★NFT固有のチェック (自身が保有しているか等)
            return True
        else:
            print('<!> verify_transaction_signature, error')
            return False
    def get_nfts(self, blockchain_address, in_chain, in_id=None):
        nfts = []
        nfts_myself = []
        for block in in_chain:
            for transaction in block['transactions']:
                if 'type' in transaction:
                    if transaction['type'] == const.BLOCKCHAIN_TYPE_NFT:
                        #if transaction['recipient_blockchain_address'] == blockchain_address:
                        if not in_id is None and in_id:
                            if not in_id == transaction['id']:
                                continue
                        nfts.append({
                            'id': transaction['id'],
                            'datetime': transaction['transaction_datetime'],
                            'url': transaction['url'],
                            'contract': transaction['contract'],
                            'recipient_blockchain_address': transaction['recipient_blockchain_address']
                        })
        index_i = 0
        for nft_i in nfts:
            index_j = 0
            myself = True
            url = nft_i['url']
            datetime = nft_i['datetime']
            for nft_j in nfts:
                if not index_i == index_j:
                    if url == nft_j['url'] and datetime < nft_j['datetime']:
                        myself = False
                        break
                index_j += 1
            if myself and blockchain_address == nft_i['recipient_blockchain_address']:
                nfts_myself.append({
                    'id': nft_i['id'],
                    'datetime': nft_i['datetime'],
                    'url': nft_i['url'],
                    'contract': nft_i['contract'],
                })
            index_i += 1
        return nfts_myself
    def exec_contract(self, in_tx_infos):
        response = None
        if in_tx_infos['sender_blockchain_address'] == in_tx_infos['recipient_blockchain_address']:
            print('contract do nothing')
            return response
        if in_tx_infos['contract']:
            contract = in_tx_infos['contract'].encode('utf-8')
            contract = binascii.unhexlify(contract)
            contract = contract.decode()

            # コントラクト実行用一時ファイル出力
            filename = Utils.randomname(30)
            filename = 'rtc_contract_' + filename
            filename_w_ext = filename + '.py'
            filepath = f'contract/{filename_w_ext}'
            filepath = os.path.join(os.path.dirname(__file__), filepath)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(contract)
            try:
                # コントラクト実行
                module = import_module(filename)
                module = module.create()
                response = module.main({
                    'sender_blockchain_address': in_tx_infos['sender_blockchain_address'],
                    'recipient_blockchain_address': in_tx_infos['recipient_blockchain_address']
                })
            except Exception as exception:
                # 個々のコントラクトのエラーは無視
                print(exception)
            # コントラクト実行用一時ファイル削除
            os.remove(filepath)
        return response
