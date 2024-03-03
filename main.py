from tinkoff.invest import Client
from tinkoff.invest import Quotation, MoneyValue
from tinkoff.invest import OrderDirection # ...
from tinkoff.invest.sandbox.client import SandboxClient

import numpy as np
import pandas as pd

import os
import json

class Client(object):
    def __init__(self, token):
        self.token = token
        self.services = SandboxClient(self.token).__enter__()

    def _account(self):
        accounts = self.services.users.get_accounts().accounts
        
if __name__ == "__main__": 
    # get token
    with open('./config.json', 'r') as f:
        data  = json.load(f)

    os.environ['token'] = data['token']

