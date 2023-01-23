from base64 import b64decode, b64encode
import os.path
from random import randbytes

from algosdk.future import transaction
from algosdk.encoding import decode_address, encode_address
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient
from algojig import TealishProgram
from utils import TransactionGroup


dirname = os.path.dirname(__file__)
approval_program = TealishProgram(os.path.join(dirname, "app.tl"))
clear_program = TealishProgram(tealish="#pragma version 8\nexit(1)")

state_schema = {
    'local': transaction.StateSchema(num_uints=0, num_byte_slices=0),
    'global': transaction.StateSchema(num_uints=2, num_byte_slices=2),
}


class AppClient:
    
    def __init__(self, algod, indexer, user_address, app_id, nft_asset_id) -> None:
        self.algod = algod
        self.indexer = indexer
        self.user_address = user_address
        self.app_id = app_id
        self.nft_asset_id = nft_asset_id

    def submit(self, stxns):
        stxns = [stxns] if not isinstance(stxns, list) else stxns
        txid = self.algod.send_transactions(stxns)
        print(txid)
        result = transaction.wait_for_confirmation(self.algod, txid)
        print(result)
        return result

    def create_app(self):
        txn = transaction.ApplicationCreateTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval_program.bytecode,
            clear_program=clear_program.bytecode,
            global_schema=state_schema['global'],
            local_schema=state_schema['local'],
            extra_pages=0,
        )
        return TransactionGroup([txn])

    def update_app(self):
        txn = transaction.ApplicationUpdateTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            approval_program=approval_program.bytecode,
            clear_program=clear_program.bytecode,
            index=self.app_id,
        )
        return TransactionGroup([txn])

    def delete_app(self):
        txn = transaction.ApplicationDeleteTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            index=self.app_id,
            accounts=[self.user_address],
            foreign_assets=[self.nft_asset_id]
        )
        txn.fee = 2000
        return TransactionGroup([txn])

    def setup(self):
        txn = transaction.ApplicationNoOpTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            index=self.app_id,
            app_args=['setup'],
            accounts=[self.user_address],
            foreign_assets=[self.nft_asset_id],
        )
        txn.fee = 2000
        return TransactionGroup([txn])

    def pay_to_application(self, amount):
        txn = transaction.PaymentTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            receiver=get_application_address(self.app_id),
            amt=amount,
        )
        return TransactionGroup([txn])

    def add_recipients(self, recipients):
        addresses = [decode_address(a) for a in recipients]
        txn = transaction.ApplicationNoOpTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            index=self.app_id,
            app_args=['add_recipients'] + addresses,
            boxes=[(0, a) for a in addresses],
        )
        return TransactionGroup([txn])

    def claim_nft(self):
        # txn0 = transaction.AssetOptInTxn(
        #     sender=self.user_address,
        #     sp=self.algod.suggested_params(),
        #     index=self.nft_asset_id,
        # )
        txn = transaction.ApplicationNoOpTxn(
            sender=self.user_address,
            sp=self.algod.suggested_params(),
            index=self.app_id,
            app_args=['claim_nft'],
            boxes=[(0, decode_address(self.user_address))],
            foreign_assets=[self.nft_asset_id],
            note=randbytes(10)
        )
        txn.fee = 2000
        # txns = transaction.assign_group_id([txn0, txn])
        return TransactionGroup([txn])

    def list_recipients(self):
        boxes = self.algod.application_boxes(self.app_id)["boxes"]
        recipients = [encode_address(b64decode(box["name"])) for box in boxes]
        return recipients

    def list_claims(self):
        token = None
        accounts = set()
        while True:
            result = self.indexer.search_asset_transactions(address=get_application_address(self.app_id), asset_id=self.nft_asset_id, next_page=token)
            for txn in result.get('transactions', []):
                if txn.get("application-transaction", {}).get("application-args", [None])[0] == b64encode(b"claim_nft").decode():
                    accounts.add(txn['sender'])
            token = result.get('next-token')
            if not token:
                break
        return accounts
