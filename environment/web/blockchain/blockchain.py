import config.defines as const
import os
import signal
import sys

from functools import partial

from flask import Flask
from flask import jsonify
from flask import request

from lib.accountclient import AccountClient
from lib.blockchain import BlockChain
from lib.serverapi import ServerApi
from lib.wallet import Wallet

def signal_handler(signal_args, signal, frame):
    print('finishing', signal_args)
    get_blockchain().finalize()
    print('finished', signal_args)
    sys.exit()

app = Flask(__name__)

cache = {}
def get_blockchain():
    cached_blockchain = cache.get('blockchain')
    if not cached_blockchain:
        id = app.config['id']
        serverapi = ServerApi()
        driver, server, dbname, uid, pwd = serverapi.getDBInfo()
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        hosts = accountclient.getHosts(id)
        if len(hosts) == 0:
            print('<!> not found host')
            sys.exit(1)
        user_oid = hosts[0]['user_oid']
        accounts = accountclient.getAccounts(user_oid)
        if len(accounts) == 0:
            print('<!> not found account')
            sys.exit(1)
        key = accounts[0]['key']
        secret_key = accounts[0]['secret_key']
        blockchain_address = accounts[0]['blockchain_address']
        accountclient.close()

        cache['blockchain'] = BlockChain(
            id = id,
            key = key,
            secret_key = secret_key,
            blockchain_address = blockchain_address,
            port = app.config['port'])
        app.logger.warning({
            'private_key': secret_key,
            'public_key': key,
            'blockchain_address': blockchain_address})
    return cache['blockchain']

@app.route('/chain', methods=['GET'])
def get_chain():
    block_chain = get_blockchain()
    response = {
        'chain': block_chain.get_chain()
    }
    return jsonify(response), 200

@app.route('/transactions', methods=['GET', 'POST', 'PUT', 'DELETE'])
def transaction():
    block_chain = get_blockchain()
    if request.method == 'GET':
        transactions = block_chain.get_transaction_pool()
        response = {
            'transactions': transactions,
            'length': len(transactions)
        }
        return jsonify(response), 200
    if request.method == 'POST':
        request_json = request.json
        if request_json.get('type') is None:
            return 'missing values', 400
        type = request_json['type']
        if type == const.BLOCKCHAIN_TYPE_POINT:
            required = (
                'sender_blockchain_address',
                'recipient_blockchain_address',
                'value',
                'sender_public_key',
                'signature')
            if not all(k in request_json for k in required):
                return jsonify({'result': 1}), 400
        elif type == const.BLOCKCHAIN_TYPE_NFT:
            required = (
                'sender_blockchain_address',
                'recipient_blockchain_address',
                'value',
                'id',
                'url',
                'contract',
                'sender_public_key',
                'signature')
            if not all(k in request_json for k in required):
                return jsonify({'result': 1}), 400
        is_created = block_chain.create_transaction(type, request_json)
        if not is_created:
            return jsonify({'result': 1}), 400
        return jsonify({'result': 0}), 200
    if request.method == 'PUT':
        request_json = request.json
        if request_json.get('type') is None:
            return 'missing values', 400
        is_contract_exec = True
        type = request_json['type']
        if type == const.BLOCKCHAIN_TYPE_POINT:
            required = (
                'sender_blockchain_address',
                'recipient_blockchain_address',
                'value',
                'sender_public_key',
                'signature',
                'transaction_id')
            if not all(k in request_json for k in required):
                return jsonify({'result': 1}), 400
            is_contract_exec = True
        elif type == const.BLOCKCHAIN_TYPE_NFT:
            required = (
                'sender_blockchain_address',
                'recipient_blockchain_address',
                'value',
                'id',
                'url',
                'sender_public_key',
                'signature',
                'transaction_id')
            if not all(k in request_json for k in required):
                return jsonify({'result': 1}), 400
            is_contract_exec = False
        else:
            print('<!> not support type:', type)
            return jsonify({'result': 1}), 400
        is_updated, transaction_id = block_chain.add_transaction(type, request_json, is_contract_exec)
        if not is_updated:
            return jsonify({'result': 1}), 400
        return jsonify({'result': 0}), 200
    if request.method == 'DELETE':
        block_chain.delete_transaction_pool()
        return jsonify({'result': 0}), 200

@app.route('/mine', methods=['GET'])
def mine():
    block_chain = get_blockchain()
    is_mined = block_chain.mining()
    if is_mined:
        return jsonify({'result': 0}), 200
    return jsonify({'result': 1}), 400

@app.route('/mine/start', methods=['GET'])
def start_mine():
    get_blockchain().start_mining()
    return jsonify({'result': 0}), 200

@app.route('/consensus', methods=['PUT'])
def consensus():
    block_chain = get_blockchain()
    replaced = block_chain.resolve_conflicts()
    return jsonify({'replaced': replaced}), 200

@app.route('/amounts', methods=['GET'])
def get_total_amount():
    blockchain_address = request.args['blockchain_address']
    return jsonify({
        'amount': get_blockchain().calculate_total_amount(blockchain_address)
    }), 200

@app.route('/nfts', methods=['GET', 'POST'])
def nfts():
    block_chain = get_blockchain()
    if request.method == 'GET':
        blockchain_address = request.args['blockchain_address']
        if request.args.get('id') is None:
            id = None
        else:
            id = request.args.get('id')
        return jsonify({
            'nfts': block_chain.get_nfts(blockchain_address, id)
        }), 200
    if request.method == 'POST':
        request_json = request.json
        required = (
            'sender_blockchain_address',
            'recipient_blockchain_address',
            'id',
            'value',
            'url',
            'contract',
            'sender_public_key',
            'signature')
        if not all(k in request_json for k in required):
            return jsonify({'result': 1}), 400
        print('##########', request_json)
        is_created = block_chain.create_nft(request_json)
        if not is_created:
            return jsonify({'result': 1}), 400
        return jsonify({'result': 0}), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-id', '--id', default='1', type=str, help='pod id')
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    id = args.id
    app.config['id'] = id
    port = args.port
    app.config['port'] = port

    # パス登録
    sys.path.append(os.path.join(os.path.dirname(__file__), 'lib/contract'))

    # シグナル設定
    signal_args = "blockchain"
    signal.signal(signal.SIGINT, partial(signal_handler, signal_args))

    # 起動
    get_blockchain().run()
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)    # debug=Trueにするとデバッグ用スレッドも起動する？
