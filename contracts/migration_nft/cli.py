from decimal import Decimal
import json
import sys
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from client import AppClient
from settings import APP_CREATOR_ADDRESS, APP_CREATOR_SK, APP_ID, NFT_ASSET_ID, ALGOD_URL, ALGOD_TOKEN, INDEXER_URL, INDEXER_TOKEN

algod = AlgodClient(ALGOD_TOKEN, ALGOD_URL)
indexer = IndexerClient(INDEXER_TOKEN, INDEXER_URL)
app_client = AppClient(algod, indexer, APP_CREATOR_ADDRESS, app_id=APP_ID, nft_asset_id=NFT_ASSET_ID)


def create():
    result = app_client.create_app().sign(APP_CREATOR_SK).submit(algod, wait=True)
    if "application-id" in result:
        print(result["application-id"])
    else:
        raise Exception(result)

def update():
    result = app_client.update_app().sign(APP_CREATOR_SK).submit(algod, wait=True)
    if result.get('confirmed-round'):
        print(result['confirmed-round'], result['txid'])
    else:
        raise Exception(result)


def setup():
    result = app_client.setup().sign(APP_CREATOR_SK).submit(algod, wait=True)
    if result.get('confirmed-round'):
        print(result['confirmed-round'], result['txid'])
    else:
        raise Exception(result)

def fund(amount_string):
    amount = int(Decimal(amount_string) * 10**6)
    result = app_client.pay_to_application(amount).sign(APP_CREATOR_SK).submit(algod, wait=True)
    if result.get('confirmed-round'):
        print(result['confirmed-round'], result['txid'])
    else:
        raise Exception(result)

def add_recipients(addresses):
    recipients = addresses.split(",")
    print(recipients)
    result = app_client.add_recipients(recipients).sign(APP_CREATOR_SK).submit(algod, wait=True)
    if result.get('confirmed-round'):
        print(result['confirmed-round'], result['txid'])
    else:
        raise Exception(result)


def calculate_cost(filename):
    per_box = 0.0025
    per_byte = 0.0004
    addresses = json.load(open(filename))
    num_boxes = len(addresses)
    min_balance_cost = num_boxes * (per_box + (per_byte * 32))
    print('min_balance_cost', min_balance_cost)
    num_txns = int(num_boxes / 8) + 1
    print('num_txns', num_txns)
    print('fees', num_txns * 0.001)


def update_recipients(filename):
    addresses = json.load(open(sys.argv[2]))
    currrent_recipients = set(app_client.list_recipients())
    claims = set(app_client.list_claims())
    new_addresses = [a for a in addresses if a not in currrent_recipients and a not in claims]
    addresses_to_be_removed = [a for a in currrent_recipients if a not in addresses]
    print('Claims:', len(claims))
    print('Current recipients:', len(currrent_recipients))
    print('New recipients:', len(new_addresses))
    print('Recipients to be removed:', len(addresses_to_be_removed))
    input("Continue?")
    n = 0
    for i in range(0, len(new_addresses), 8):
        recipients = new_addresses[i: i + 8]
        n += 1
        result = app_client.add_recipients(recipients).sign(APP_CREATOR_SK).submit(algod, wait=False)
        print(n, result['txid'])



def list_recipients():
    recipients = app_client.list_recipients()
    print(len(recipients))
    for a in recipients:
        print(a)


def list_claims():
    claims = app_client.list_claims()
    print(len(claims))
    for a in claims:
        print(a)


if sys.argv[1] == "create":
    create()
elif sys.argv[1] == "update":
    update()
elif sys.argv[1] == "fund":
    fund(sys.argv[2])
elif sys.argv[1] == "setup":
    setup()
elif sys.argv[1] == "add_recipients":
    add_recipients(sys.argv[2])
elif sys.argv[1] == "cost":
    calculate_cost(sys.argv[2])
elif sys.argv[1] == "update_recipients":
    update_recipients(sys.argv[2])
elif sys.argv[1] == "list_recipients":
    list_recipients()
elif sys.argv[1] == "list_claims":
    list_claims()
