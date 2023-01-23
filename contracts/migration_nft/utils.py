from base64 import b64encode
from algosdk.account import address_from_private_key
from algosdk.error import AlgodHTTPError
from algosdk.future.transaction import (
    LogicSigTransaction,
    assign_group_id,
    wait_for_confirmation,
)


class TransactionGroup:
    def __init__(self, transactions):
        # Clear previously assigned group ids
        for txn in transactions:
            txn.group = None

        transactions = assign_group_id(transactions)
        self.transactions = transactions
        self.signed_transactions = [None for _ in self.transactions]

    @property
    def id(self):
        try:
            byte_group_id = self.transactions[0].group
        except IndexError:
            return

        group_id = b64encode(byte_group_id).decode("utf-8")
        return group_id

    def sign_with_logicsig(self, logicsig):
        address = logicsig.address()
        for i, txn in enumerate(self.transactions):
            if txn.sender == address:
                self.signed_transactions[i] = LogicSigTransaction(txn, logicsig)
        return self

    def sign_with_private_key(self, address, private_key):
        for i, txn in enumerate(self.transactions):
            if txn.sender == address:
                self.signed_transactions[i] = txn.sign(private_key)
        return self

    def sign(self, private_key, sender=None):
        if sender is None:
            sender = address_from_private_key(private_key)
        for i, txn in enumerate(self.transactions):
            if txn.sender == sender:
                self.signed_transactions[i] = txn.sign(private_key)
        return self

    def submit(self, algod, wait=False):
        try:
            txid = algod.send_transactions(self.signed_transactions)
        except AlgodHTTPError as e:
            raise Exception(e) from None
        if wait:
            txn_info = wait_for_confirmation(algod, txid)
            txn_info["txid"] = txid
            return txn_info
        return {"txid": txid}

    def __add__(self, other):
        transactions = self.transactions + other.transactions
        return TransactionGroup(transactions)