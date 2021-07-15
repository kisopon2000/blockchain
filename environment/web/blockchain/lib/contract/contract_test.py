#====================
# contract_test.py
#====================

import sys

from contract import Contract
from contract_sdk import ContractPoint

class ContractTest(Contract):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return 'Hello'

    def main(self, in_event):
        contractpoint = ContractPoint()  # SDK
        return contractpoint.sendPoint('2FBCsrTRU3ZGkn4qodneHcXLYTv1S13v6N', 0.1)

def create():
    return ContractTest()
