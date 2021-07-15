import binascii
import config.defines as const
import json
import requests
import signal
import sys
import urllib.parse

from functools import partial

from flask import Flask
from flask import jsonify
from flask import request
from flask import render_template

from lib.accountclient import AccountClient
from lib.blockchain import BlockChain
from lib.utils import SystemConfigApi
from lib.serverapi import ServerApi

def signal_handler(signal_args, signal, frame):
    #print(signal_args)
    sys.exit()

app = Flask(__name__, template_folder='./templates')

@app.route('/')
def index():
    return render_template('./index.html')

@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    serverapi = ServerApi()
    token = serverapi.parseToken(request.headers.get(const.ENV_TOKEN_KEY_FLASK))
    print(token)
    driver, server, dbname, uid, pwd = serverapi.getDBInfo()
    if request.method == 'GET':
        user_oid = token['user_oid']
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        accounts = accountclient.getAccounts(user_oid)
        accountclient.close()
        if len(accounts) > 0:
            response = {
                'result': 0,
                'accounts': accounts,
            }
        else:
            response = {
                'result': 1,
            }
        return jsonify(response), 200
    if request.method == 'POST':
        request_json = request.json
        required = ('user_id', 'password')
        if not all(k in request_json for k in required):
            return jsonify({'result': 1}), 400
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        token = accountclient.createAccount(request_json['user_id'],request_json['password'])
        accountclient.close()
        if token is None:
            response = {
                'result': 1,
            }
        else:
            response = {
                'result': 0,
                'token': token,
            }
        return jsonify(response), 200

@app.route('/accounts/token', methods=['GET'])
def token():
    serverapi = ServerApi()
    token = serverapi.parseToken(request.headers.get(const.ENV_TOKEN_KEY_FLASK))
    driver, server, dbname, uid, pwd = serverapi.getDBInfo()
    if request.method == 'GET':
        required = ['user_id', 'password']
        if not all(k in request.args for k in required):
            return jsonify({'result': 1}), 400
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        token = accountclient.getToken(request.args.get('user_id'), request.args.get('password'))
        accountclient.close()
        if token is None:
            response = {
                'result': 1,
            }
        else:
            response = {
                'result': 0,
                'token': token,
            }
        return jsonify(response), 200

@app.route('/transactions', methods=['POST'])
def transactions():
    serverapi = ServerApi()
    token = serverapi.parseToken(request.headers.get(const.ENV_TOKEN_KEY_FLASK))
    driver, server, dbname, uid, pwd = serverapi.getDBInfo()
    if request.method == 'POST':
        user_oid = token['user_oid']
        request_json = request.json
        if request_json.get('type') is None:
            return 'missing values', 400
        type = request_json['type']
        request_json_template = {}
        if type == const.BLOCKCHAIN_TYPE_POINT:
            required = (
                'recipient_blockchain_address',
                'value')
            if not all(k in request_json for k in required):
                return 'missing values', 400
            request_json_template['recipient_blockchain_address'] = request_json['recipient_blockchain_address']
            request_json_template['value'] = request_json['value']
        elif type == const.BLOCKCHAIN_TYPE_NFT:
            required = (
                'recipient_blockchain_address',
                'id',
                'value')
            if not all(k in request_json for k in required):
                return 'missing values', 400
            request_json_template['recipient_blockchain_address'] = request_json['recipient_blockchain_address']
            request_json_template['id'] = request_json['id']
            request_json_template['value'] = request_json['value']
        else:
            print('<!> not support type:', type)
            return 'not support type', 400

        # 所定の情報取得
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        hosts = accountclient.getHosts()
        accounts = accountclient.getAccounts(user_oid)
        accountclient.close()
        if len(accounts) == 0:
            response = {
                'result': 1,
            }
            return jsonify(response), 200
        request_json_template['key'] = accounts[0]['key']
        request_json_template['secret_key'] = accounts[0]['secret_key']
        request_json_template['sender_blockchain_address'] = accounts[0]['blockchain_address']

        if type == const.BLOCKCHAIN_TYPE_NFT:
            # URL/コントラクト取得
            url = serverapi.getNftRequestUrl(hosts)
            url = url + '?id=' + urllib.parse.quote(request_json['id'])
            response = requests.get(
                url,
                {'blockchain_address': accounts[0]['blockchain_address']},
                timeout=3)
            if response.status_code == 200:
                nfts = response.json()['nfts']
                if len(nfts) == 0:
                    print('<!> not found nft')
                    return jsonify({'result': 1}), 200
                request_json_template['url'] = nfts[0]['url']
                request_json_template['contract'] = nfts[0]['contract']
            else:
                print(response)
                return jsonify({'result': 1}), 200

        # 署名作成
        request_json = serverapi.createTransactionRequestJson(type, request_json_template)
        if request_json is None:
            print('<!> createTransactionRequestJson failed')
            return jsonify({'result': 1}), 200

        # トランザクション登録
        url = serverapi.getTransactionRequestUrl(hosts)
        if url is None:
            print('<!> getTransactionRequestUrl failed')
            return jsonify({'result': 1}), 200
        print(url)

        # リクエスト
        try:
            response = requests.post(
                url,
                json=request_json,
                timeout=3)
        except Exception as exception:
            print(exception)
            return jsonify({'result': 1}), 200
        if response.status_code == 200:
            return jsonify({'result': 0}), 200
        else:
            print(response)
            return jsonify({'result': 1}), 200

@app.route('/amounts', methods=['GET'])
def amounts():
    serverapi = ServerApi()
    token = serverapi.parseToken(request.headers.get(const.ENV_TOKEN_KEY_FLASK))
    driver, server, dbname, uid, pwd = serverapi.getDBInfo()
    if request.method == 'GET':
        user_oid = token['user_oid']
        
        # 所定の情報取得
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        hosts = accountclient.getHosts()
        accounts = accountclient.getAccounts(user_oid)
        accountclient.close()
        if len(accounts) == 0:
            print('<!> not found user_oid')
            return jsonify({'result': 1}), 200
        blockchain_address = accounts[0]['blockchain_address']

        # URL取得
        url = serverapi.getAmountRequestUrl(hosts)
        if url is None:
            print('<!> getAmountRequestUrl failed')
            return jsonify({'result': 1}), 200
        print(url)

        # リクエスト
        response = requests.get(
            url,
            {'blockchain_address': blockchain_address},
            timeout=3)
        if response.status_code == 200:
            total = response.json()['amount']
            return jsonify({'result': 0, 'amount': total}), 200
        else:
            print(response)
            return jsonify({'result': 1}), 200

@app.route('/api/transactions', methods=['POST'])
def api_transactions():
    serverapi = ServerApi()
    driver, server, dbname, uid, pwd = serverapi.getDBInfo()
    if request.method == 'POST':
        request_json = request.json
        if request_json.get('type') is None:
            return 'missing values', 400
        type = request_json['type']
        request_json_template = {}
        if type == const.BLOCKCHAIN_TYPE_POINT:
            required = (
                'key',
                'secret_key',
                'sender_blockchain_address',
                'recipient_blockchain_address',
                'value')
            if not all(k in request_json for k in required):
                return 'missing values', 400
            request_json_template['key'] = request_json['key']
            request_json_template['secret_key'] = request_json['secret_key']
            request_json_template['sender_blockchain_address'] = request_json['sender_blockchain_address']
            request_json_template['recipient_blockchain_address'] = request_json['recipient_blockchain_address']
            request_json_template['value'] = request_json['value']
        else:
            print('<!> not support type:', type)
            return 'not support type', 400

        # 所定の情報取得
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        hosts = accountclient.getHosts()
        accountclient.close()

        # 署名作成
        request_json = serverapi.createTransactionRequestJson(type, request_json_template)
        if request_json is None:
            print('<!> createTransactionRequestJson failed')
            return jsonify({'result': 1}), 200

        # トランザクション登録
        url = serverapi.getTransactionRequestUrl(hosts)
        if url is None:
            print('<!> getTransactionRequestUrl failed')
            return jsonify({'result': 1}), 200
        print(url)

        # リクエスト
        try:
            response = requests.post(
                url,
                json=request_json,
                timeout=3)
        except Exception as exception:
            print(exception)
            return jsonify({'result': 1}), 200
        if response.status_code == 200:
            return jsonify({'result': 0}), 200
        else:
            print(response)
            return jsonify({'result': 1}), 200

@app.route('/nfts', methods=['GET', 'POST'])
def nfts():
    serverapi = ServerApi()
    token = serverapi.parseToken(request.headers.get(const.ENV_TOKEN_KEY_FLASK))
    driver, server, dbname, uid, pwd = serverapi.getDBInfo()
    user_oid = token['user_oid']
    if request.method == 'GET':
        # 所定の情報取得
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        hosts = accountclient.getHosts()
        accounts = accountclient.getAccounts(user_oid)
        accountclient.close()
        if len(accounts) == 0:
            print('<!> not found user_oid')
            return jsonify({'result': 1}), 200
        blockchain_address = accounts[0]['blockchain_address']

        # URL取得
        url = serverapi.getNftRequestUrl(hosts)
        if url is None:
            print('<!> getNftRequestUrl failed')
            return jsonify({'result': 1}), 200
        if not request.args.get('id') is None:
            id = None
            url = url + '?id=' + urllib.parse.quote(request.args.get('id'))
        print(url)

        # リクエスト
        response = requests.get(
            url,
            {'blockchain_address': blockchain_address},
            timeout=3)
        if response.status_code == 200:
            nfts = response.json()['nfts']
            return jsonify({'result': 0, 'nfts': nfts}), 200
        else:
            print(response)
            return jsonify({'result': 1}), 200
    if request.method == 'POST':
        if 'id' not in request.form:
            print('<!> not found id')
            return jsonify({'result': 1}), 400
        if 'url' not in request.form:
            print('<!> not found url')
            return jsonify({'result': 1}), 400
        id = request.form.get('id')
        url = request.form.get('url')
        contract = None
        if 'contract' in request.files:
            fs = request.files['contract']
            contract = fs.read()  # この時点でバイナリデータ
            #contract = binascii.hexlify(contract)  # エンコード(...するとJSON送信できない)
            contract = contract.decode('utf-8')
            print(contract)
        else:
            print('not register contract')
        request_json_template = {}
        request_json_template['id'] = id
        request_json_template['value'] = 0
        request_json_template['url'] = url
        request_json_template['contract'] = contract

        # 所定の情報取得
        accountclient = AccountClient()
        accountclient.connect(driver, server, dbname, uid, pwd)
        hosts = accountclient.getHosts()
        accounts = accountclient.getAccounts(user_oid)
        accountclient.close()
        if len(accounts) == 0:
            print('<!> not found user_oid')
            return jsonify({'result': 1}), 200
        request_json_template['key'] = accounts[0]['key']
        request_json_template['secret_key'] = accounts[0]['secret_key']
        request_json_template['sender_blockchain_address'] = accounts[0]['blockchain_address']
        request_json_template['recipient_blockchain_address'] = accounts[0]['blockchain_address']  # 同一人物

        # 署名作成
        request_json = serverapi.createNftRequestJson(const.BLOCKCHAIN_TYPE_NFT, request_json_template)
        if request_json is None:
            print('<!> createNftRequestJson failed')
            return jsonify({'result': 1}), 200

        # URL取得
        url = serverapi.getNftRequestUrl(hosts)
        if url is None:
            print('<!> getNftRequestUrl failed')
            return jsonify({'result': 1}), 200
        print(url)

        # リクエスト
        try:
            response = requests.post(
                url,
                json=request_json,
                timeout=3)
        except Exception as exception:
            print(exception)
            return jsonify({'result': 1}), 200
        if response.status_code == 200:
            return jsonify({'result': 0}), 200
        else:
            print(response)
            return jsonify({'result': 1}), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8080, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.config['port'] = port

    # シグナル設定
    signal_args = "exchange"
    signal.signal(signal.SIGINT, partial(signal_handler, signal_args))

    # 起動
    app.run(host='0.0.0.0', port=port, threaded=True, debug=True)
