#pragma version 8

if Txn.ApplicationID == 0:
    # Handle Create App
    exit(1)
end

switch Txn.OnCompletion:
    NoOp: main
    OptIn: opt_in
    CloseOut: close_out
    UpdateApplication: update_app
    DeleteApplication: delete_app
end

block opt_in:
    # Disallow Opt In
    exit(0)
end

block close_out:
    # Disallow Closing Out
    exit(0)
end

block update_app:
    # Handle Update App
    # Only allow the Creator to update the app
    assert(Txn.Sender == Global.CreatorAddress)
    exit(1)
end

block delete_app:
    # Handle Delete App
    # Only allow the Creator to delete the app
    assert(Txn.Sender == Global.CreatorAddress)
    int num_boxes
    _, num_boxes = acct_params_get(AcctTotalBoxes, Global.CurrentApplicationAddress)
    assert(num_boxes == 0)
    inner_txn:
        TypeEnum: Axfer
        Sender: Global.CurrentApplicationAddress
        AssetReceiver: Global.CurrentApplicationAddress
        AssetCloseTo: Global.CreatorAddress
        XferAsset: app_global_get("asset_id")
        AssetAmount: 0
        Fee: 0
    end
    # Close out the app account
    inner_txn:
        TypeEnum: Pay
        Sender: Global.CurrentApplicationAddress
        Receiver: Global.CurrentApplicationAddress
        CloseRemainderTo: Global.CreatorAddress
        Amount: 0
        Fee: 0
    end
    exit(1)
end

block main:

    switch Txn.ApplicationArgs[0]:
        "setup": setup
        "reclaim_algo": reclaim_algo
        "add_recipients": add_recipients
        "remove_recipients": remove_recipients
        "set_manager": set_manager
        "claim_nft": claim_nft
    end

    block setup:
        assert(Txn.Sender == Global.CreatorAddress)
        # Store the NFT asset id in global state
        app_global_put("asset_id", Txn.Assets[0])
        app_global_put("manager", Txn.Accounts[1])
        # Optin to the NFT asset
        inner_txn:
            TypeEnum: Axfer
            Sender: Global.CurrentApplicationAddress
            AssetReceiver: Global.CurrentApplicationAddress
            AssetAmount: 0
            XferAsset: Txn.Assets[0]
            Fee: 0
        end
        exit(1)
    end

    block add_recipients:
        assert(Txn.Sender == app_global_get("manager"))
        # Up to 8 recipients can be added per app call
        int n = Txn.NumAppArgs
        for i in 1:n:
            assert(len(Txn.ApplicationArgs[i]) == 32)
            box_put(Txn.ApplicationArgs[i], "")
        end
        exit(1)
    end

    block remove_recipients:
        assert(Txn.Sender == app_global_get("manager"))
        int n = Txn.NumAppArgs
        for i in 1:n:
            assert(len(Txn.ApplicationArgs[i]) == 32)
            _ = box_del(Txn.ApplicationArgs[i])
        end
        exit(1)
    end

    block claim_nft:
        int existed = box_del(Txn.Sender)
        if !existed:
            exit(0)
        end
        inner_txn:
            TypeEnum: Axfer
            Sender: Global.CurrentApplicationAddress
            AssetReceiver: Txn.Sender
            AssetAmount: 1
            XferAsset: app_global_get("asset_id")
            Fee: 0
        end
        exit(1)
    end

    block reclaim_algo:
        assert(Txn.Sender == Global.CreatorAddress)
        int extra = balance(Global.CurrentApplicationAddress) - min_balance(Global.CurrentApplicationAddress)
        inner_txn:
            TypeEnum: Pay
            Sender: Global.CurrentApplicationAddress
            AssetReceiver: Txn.Sender
            AssetAmount: extra
            Fee: 0
        end
        exit(1)
    end

    block set_manager:
        assert(Txn.Sender == Global.CreatorAddress)
        app_global_put("manager", Txn.Accounts[1])
        exit(1)
    end
end
