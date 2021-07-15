#====================
# block.py
#====================

import config.defines as const
import hashlib
import json
import sys

from lib.utils import Utils

from ecdsa import NIST256p
from ecdsa import VerifyingKey

class Block(object):
    def __init__(self, id, blockchain_address, port, transaction_pool, chain):
        self.id = id
        self.blockchain_address = blockchain_address
        self.neighbours = []
    def set_neighbours(self, neighbours):
        self.neighbours = neighbours
    def verify_transaction_signature(self, sender_public_key, signature, transaction):
        sha256 = hashlib.sha256()
        sha256.update(str(transaction).encode('utf-8'))
        message = sha256.digest()
        signature_bytes = bytes().fromhex(signature)
        verifying_key = VerifyingKey.from_string(bytes().fromhex(sender_public_key), curve=NIST256p)
        verified_key = verifying_key.verify(signature_bytes, message)
        return verified_key
    def valid_proof(self, transactions, previous_hash, nonce, difficulty=const.BLOCKCHAIN_MINING_DIFFICULTY):
        guess_block = Utils.sorted_dict_by_key({
            'transactions': transactions,
            'nonce': nonce,
            'previous_hash': previous_hash
        })
        guess_hash = Utils.hash(guess_block)
        print('##### guess:', guess_hash[:difficulty])
        return guess_hash[:difficulty] == '0'*difficulty
    def proof_of_work(self, in_chain, in_transaction_pool):
        transactions = in_transaction_pool.copy()
        previous_hash = Utils.hash(in_chain[-1])
        nonce = 0
        while self.valid_proof(transactions, previous_hash, nonce) is False:
            nonce += 1
        return nonce
    def valid_chain(self, chain):
        pre_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != Utils.hash(pre_block):
                print('########### dame 1')
                return False
            if not self.valid_proof(
                block['transactions'], block['previous_hash'],
                block['nonce'], const.BLOCKCHAIN_MINING_DIFFICULTY):
                print('########### dame 2')
                return False
            pre_block = block
            current_index += 1
        return True
