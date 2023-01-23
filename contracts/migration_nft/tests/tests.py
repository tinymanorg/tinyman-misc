import os
import unittest

import algojig
from algojig import TealishProgram
from algojig import get_suggested_params
from algojig.ledger import JigLedger
from algosdk.account import generate_account
from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk.encoding import decode_address
from algojig.exceptions import LogicEvalError, AppCallReject
from client import AppClient, approval_program, clear_program, state_schema


class DummyAlgod:
    def suggested_params(self):
        return get_suggested_params()


class TestCreateApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = get_suggested_params()
        cls.app_creator_sk, cls.app_creator_address = generate_account()
        cls.user_sk, cls.user_address = generate_account()

    def setUp(self):
        self.ledger = JigLedger()
        self.ledger.set_account_balance(self.app_creator_address, 1_000_000)
        self.ledger.set_account_balance(self.user_address, 1_000_000)

    def test_create_app(self):
        app_client = AppClient(DummyAlgod(), None, self.app_creator_address, 0, 0)
        transactions = app_client.create_app().sign(self.app_creator_sk)
        self.ledger.eval_transactions(transactions.signed_transactions)


class TestAppAsCreator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = get_suggested_params()
        cls.app_creator_sk, cls.app_creator_address = generate_account()
        cls.user_sk, cls.user_address = generate_account()
        cls.adresses = [generate_account()[1] for _ in range(16)]

    def setUp(self):
        self.app_id = 10
        self.nft_asset_id = 1001
        self.ledger = JigLedger()
        self.ledger.set_account_balance(self.app_creator_address, 1_000_000)
        self.ledger.set_account_balance(self.app_creator_address, 0, self.nft_asset_id)
        self.ledger.set_account_balance(self.user_address, 1_000_000)
        self.ledger.set_account_balance(get_application_address(self.app_id), 1_000_000)
        self.ledger.set_account_balance(get_application_address(self.app_id), 10_000, self.nft_asset_id)
        self.ledger.create_app(
            app_id=self.app_id,
            approval_program=approval_program,
            creator=self.app_creator_address,
            local_ints=state_schema['local'].num_uints,
            local_bytes=state_schema['local'].num_byte_slices,
            global_ints=state_schema['global'].num_uints,
            global_bytes=state_schema['global'].num_byte_slices,
        )
        self.ledger.set_global_state(self.app_id, {"asset_id": self.nft_asset_id, "manager": decode_address(self.app_creator_address)})

    def test_update_app(self):
        txn = transaction.ApplicationUpdateTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            index=self.app_id,
            approval_program=approval_program.bytecode,
            clear_program=clear_program.bytecode,
        )
        stxn = txn.sign(self.app_creator_sk)
        self.ledger.eval_transactions(transactions=[stxn])

    def test_update_app_fail(self):
        txn = transaction.ApplicationUpdateTxn(
            sender=self.user_address,
            sp=self.sp,
            index=self.app_id,
            approval_program=approval_program.bytecode,
            clear_program=clear_program.bytecode,
        )
        stxn = txn.sign(self.user_sk)
        with self.assertRaises(LogicEvalError):
            self.ledger.eval_transactions(transactions=[stxn])

    def test_delete_app(self):
        txn = transaction.ApplicationDeleteTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            index=self.app_id,
            foreign_assets=[self.nft_asset_id],
        )
        txn.fee = 3000
        stxn = txn.sign(self.app_creator_sk)
        self.ledger.eval_transactions(transactions=[stxn])

    def test_delete_app_with_boxes_fail(self):
        self.ledger.set_box(self.app_id, decode_address(self.user_address), None)
        txn = transaction.ApplicationDeleteTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            index=self.app_id,
            foreign_assets=[self.nft_asset_id],
        )
        txn.fee = 3000
        stxn = txn.sign(self.app_creator_sk)
        with self.assertRaises(LogicEvalError):
            self.ledger.eval_transactions(transactions=[stxn])

    def test_add_recipients(self):
        addresses = [decode_address(a) for a in self.adresses[:8]]
        txn = transaction.ApplicationNoOpTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            index=self.app_id,
            app_args=['add_recipients'] + addresses,
            boxes=[(0, a) for a in addresses],
        )
        stxn = txn.sign(self.app_creator_sk)

        block = self.ledger.eval_transactions(transactions=[stxn])
        block_txns = block[b"txns"]

        self.assertEqual(len(block_txns), 1)
        txn = block_txns[0]


class TestAppAsUser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = get_suggested_params()
        cls.app_creator_sk, cls.app_creator_address = generate_account()
        cls.user_sk, cls.user_address = generate_account()
        cls.adresses = [generate_account()[1] for _ in range(16)]

    def setUp(self):
        self.app_id = 10
        self.nft_asset_id = 1001
        self.ledger = JigLedger()
        self.ledger.set_account_balance(self.app_creator_address, 1_000_000)
        self.ledger.set_account_balance(self.user_address, 1_000_000)
        self.ledger.opt_in_asset(self.user_address, self.nft_asset_id)
        self.ledger.set_account_balance(get_application_address(self.app_id), 1_000_000)
        self.ledger.set_account_balance(get_application_address(self.app_id), 10_000, self.nft_asset_id)
        self.ledger.create_app(
            app_id=self.app_id,
            approval_program=approval_program,
            creator=self.app_creator_address,
            local_ints=state_schema['local'].num_uints,
            local_bytes=state_schema['local'].num_byte_slices,
            global_ints=state_schema['global'].num_uints,
            global_bytes=state_schema['global'].num_byte_slices,
        )
        self.ledger.set_global_state(self.app_id, {"asset_id": self.nft_asset_id, "manager": decode_address(self.app_creator_address)})
        self.app_client = AppClient(DummyAlgod(), None, self.user_address, self.app_id, self.nft_asset_id)


    def test_claim_nft(self):
        # addresses = [decode_address(a) for a in self.adresses[:8]]
        # addresses[0] = decode_address(self.user_address)
        # txn = transaction.ApplicationNoOpTxn(
        #     sender=self.app_creator_address,
        #     sp=self.sp,
        #     index=self.app_id,
        #     app_args=['add_recipients'] + addresses,
        #     boxes=[(0, a) for a in addresses],
        # )
        # stxn = txn.sign(self.app_creator_sk)

        self.ledger.set_box(self.app_id, decode_address(self.user_address), None)

        txn_group = self.app_client.claim_nft().sign(self.user_sk)
        self.ledger.eval_transactions(txn_group.signed_transactions)


    def test_claim_nft_again(self):
        # addresses = [decode_address(a) for a in self.adresses[:8]]
        # addresses[0] = decode_address(self.user_address)
        # txn = transaction.ApplicationNoOpTxn(
        #     sender=self.app_creator_address,
        #     sp=self.sp,
        #     index=self.app_id,
        #     app_args=['add_recipients'] + addresses,
        #     boxes=[(0, a) for a in addresses],
        # )
        # stxn = txn.sign(self.app_creator_sk)

        self.ledger.set_box(self.app_id, decode_address(self.user_address), None)

        txn_group_1 = self.app_client.claim_nft().sign(self.user_sk)
        self.ledger.eval_transactions(txn_group_1.signed_transactions)

        txn_group_2 = self.app_client.claim_nft().sign(self.user_sk)
        with self.assertRaises(AppCallReject) as e:
            self.ledger.eval_transactions(txn_group_2.signed_transactions)