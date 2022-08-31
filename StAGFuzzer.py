import sys
import os
import shutil
import random

import pandas as pd
import openpyxl as xl
import numpy as np
import copy
from itertools import accumulate
import itertools
import operator
import subprocess
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

if sys.version_info < (3, 6, 0):
    raise Exception("Must be using Python 3.6 or above")

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
except:
    print("You need to have Web3 module to use this replayer.")
    print("Go to command prompt and type in python -m pip install Web3")
    print("If error occurs during install, please see the error message and install the relevant component also")
    exit()

import json
import json_helper
import gen_input as gi
import mutate_input as mi


import src.tac_cfg as cfg

try:
    import eth_abi
except:
    exit()

w3 = None
NormalAccount = ""
OwnerAccount = ""
ConstructorAddressAccount = ""
AttackerContract = ""
contractmap = []
functionmap = []
failcount = 0
graph = None

path_bin = r'./Dataset/Smart_Contract_Binaries'
path_abi = r'./Dataset/Smart_Contract_ABIs'



class Transaction:
    def __init__(self, Index, From, Function, Value, Input, Gas, Priority, Hash):
        self.Index = Index
        self.From = From
        self.Function = Function
        self.Value = Value
        self.Input = Input
        self.Gas = Gas
        self.Priority = Priority
        self.Hash = Hash
        self.RWevents = []
        self.distanceImportantBlocks = {}

        # TODO
        self.blocks = []

    def printTx(self):
        print([self.Index, self.From, self.Function, self.Value, self.Input, self.Gas, self.Priority, self.Hash])

    def reducePriority(self):
        self.Priority = int(self.Priority*0.5)


class Function:
    def __init__(self, Name, Input, Payable, Count):
        self.Name = Name
        self.Input = Input
        self.Payable = Payable
        self.Count = Count
        self.Seeds = []


class Dependency:
    def __init__(self, MemoryLoc, Op1, Block1, TxHash1, Op2, Block2, TxHash2, Covered):
        self.MemoryLoc = MemoryLoc
        self.Op1 = Op1
        self.Block1 = Block1
        self.TxHash1 = TxHash1
        self.Op2 = Op2
        self.Block2 = Block2
        self.TxHash2 = TxHash2
        self.Covered = Covered

    def printDep(self):
        print([self.MemoryLoc[0:6] + "..." + self.MemoryLoc[-6:], self.Op1, self.Block1[0:6] + "..." + self.Block1[-6:],
               self.TxHash1[0:6] + "..." + self.TxHash1[-6:], self.Op2, self.Block2[0:6] + "..." + self.Block2[-6:],
               self.TxHash2[0:6] + "..." + self.TxHash2[-6:], self.Covered])


def getAttackerAgent():
    # notdeployed = True
    # while notdeployed:
    bytecode = "606060405260006000600050556001600360006101000a81548160ff021916908302179055506000600360016101000a81548160ff02191690830217905550600060046000505560006005600050555b5b610a508061005e6000396000f3606060405236156100b6576000357c01000000000000000000000000000000000000000000000000000000009004806306661abd146101de57806315140bd1146102065780633f948cac1461023057806348cccce9146102585780635aa945a4146102705780636b66ae0e146102d45780636ed65dae14610312578063789d1c5c1461033a57806383a64c1e146103995780639e455939146104195780639eeb30e614610457578063d3e204d714610481576100b6565b6101dc5b600360009054906101000a900460ff16156101bf5760006000818150548092919060010191905055506000600360006101000a81548160ff02191690830217905550600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166002600050604051808280546001816001161561010002031660029004801561019f5780601f106101745761010080835404028352916020019161019f565b820191906000526020600020905b81548152906001019060200180831161018257829003601f168201915b50509150506000604051808303816000866161da5a03f1915050506101d9565b6001600360006101000a81548160ff021916908302179055505b5b565b005b34610002576101f06004805050610501565b6040518082815260200191505060405180910390f35b3461000257610218600480505061050a565b60405180821515815260200191505060405180910390f35b3461000257610242600480505061051d565b6040518082815260200191505060405180910390f35b61026e6004808035906020019091905050610526565b005b34610002576102d26004808035906020019091908035906020019082018035906020019191908080601f016020809104026020016040519081016040528093929190818152602001838380828437820191505050505050909091905050610591565b005b34610002576102e66004805050610706565b604051808273ffffffffffffffffffffffffffffffffffffffff16815260200191505060405180910390f35b3461000257610324600480505061072c565b6040518082815260200191505060405180910390f35b6103976004808035906020019091908035906020019082018035906020019191908080601f016020809104026020016040519081016040528093929190818152602001838380828437820191505050505050909091905050610735565b005b34610002576103ab60048050506108b1565b60405180806020018281038252838181518152602001915080519060200190808383829060006004602084601f0104600302600f01f150905090810190601f16801561040b5780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b346100025761042b6004805050610952565b604051808273ffffffffffffffffffffffffffffffffffffffff16815260200191505060405180910390f35b34610002576104696004805050610981565b60405180821515815260200191505060405180910390f35b34610002576104936004805050610994565b60405180806020018281038252838181518152602001915080519060200190808383829060006004602084601f0104600302600f01f150905090810190601f1680156104f35780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b60006000505481565b600360019054906101000a900460ff1681565b60056000505481565b60046000818150548092919060010191905055508073ffffffffffffffffffffffffffffffffffffffff166108fc349081150290604051809050600060405180830381858888f19350505050151561058d5760056000818150548092919060010191905055505b5b50565b6000600360016101000a81548160ff0219169083021790555081600160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908302179055508060026000509080519060200190828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f1061062457805160ff1916838001178555610655565b82800160010185558215610655579182015b82811115610654578251826000505591602001919060010190610636565b5b5090506106809190610662565b8082111561067c5760008181506000905550600101610662565b5090565b50508173ffffffffffffffffffffffffffffffffffffffff1681604051808280519060200190808383829060006004602084601f0104600302600f01f150905090810190601f1680156106e75780820380516001836020036101000a031916815260200191505b509150506000604051808303816000866161da5a03f1915050505b5050565b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b60046000505481565b60006001600360016101000a81548160ff0219169083021790555034905082600160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908302179055508160026000509080519060200190828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f106107cd57805160ff19168380011785556107fe565b828001600101855582156107fe579182015b828111156107fd5782518260005055916020019190600101906107df565b5b509050610829919061080b565b80821115610825576000818150600090555060010161080b565b5090565b50508273ffffffffffffffffffffffffffffffffffffffff168183604051808280519060200190808383829060006004602084601f0104600302600f01f150905090810190601f1680156108915780820380516001836020036101000a031916815260200191505b5091505060006040518083038185876185025a03f192505050505b505050565b60026000508054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561094a5780601f1061091f5761010080835404028352916020019161094a565b820191906000526020600020905b81548152906001019060200180831161092d57829003601f168201915b505050505081565b6000600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905061097e565b90565b600360009054906101000a900460ff1681565b602060405190810160405280600081526020015060026000508054600181600116156101000203166002900480601f016020809104026020016040519081016040528092919081815260200182805460018160011615610100020316600290048015610a415780601f10610a1657610100808354040283529160200191610a41565b820191906000526020600020905b815481529060010190602001808311610a2457829003601f168201915b50505050509050610a4d565b9056"
    abi = json.loads(
        '[{"constant":true,"inputs":[],"name":"count","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"hasValue","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"sendFailedCount","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"contract_addr","type":"address"}],"name":"MySend","outputs":[],"payable":true,"type":"function"},{"constant":false,"inputs":[{"name":"contract_addr","type":"address"},{"name":"msg_data","type":"bytes"}],"name":"MyCallWithoutValue","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"call_contract_addr","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"sendCount","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"contract_addr","type":"address"},{"name":"msg_data","type":"bytes"}],"name":"MyCallWithValue","outputs":[],"payable":true,"type":"function"},{"constant":true,"inputs":[],"name":"call_msg_data","outputs":[{"name":"","type":"bytes"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"getContractAddr","outputs":[{"name":"addr","type":"address"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"turnoff","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"getCallMsgData","outputs":[{"name":"msg_data","type":"bytes"}],"payable":false,"type":"function"},{"inputs":[],"type":"constructor"},{"payable":true,"type":"fallback"}]')
    Attackercontract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = Attackercontract.constructor().transact()
    try:
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        notdeployed = False
    except Exception as e:
        print(e)
        notdeployed = True
    return w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)


def reentrancyCall(input, contract):
    try:
        attacker = AttackerContract
        tx_hash = attacker.functions.MyCallWithValue(contract.address, input).transact({'value': 1, 'gas': 800000})
        return tx_hash

    except Exception as e:
        print(e)


def initializeaccount(devmode):
    global failcount
    global w3
    global NormalAccount
    global OwnerAccount
    global AttackerContract
    global contractmap
    global functionmap
    w3 = Web3()
    try:
        print(w3.eth.blockNumber)
    except:
        failcount = failcount + 1
        if failcount < 10:
            initializeaccount(devmode)
        return
    if devmode:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    NORMALACCOUNT = w3.toChecksumAddress("0xf97ddc7b1836c7bb14cd907ef9845a6c028428f4")
    OWNERACCOUNT = w3.toChecksumAddress("0x96780224cb07a07c1449563c5dfc8500ffa0ea2a")
    w3.eth.defaultAccount = OWNERACCOUNT
    w3.geth.personal.unlockAccount(OWNERACCOUNT, "", 20 * 60 * 60)
    w3.geth.personal.unlockAccount(NORMALACCOUNT, "123456", 20 * 60 * 60)


    ATTACKERCONTRACT = getAttackerAgent()



def getBytecode(path):
    with open(path, 'r') as f:
        return f.read().replace('\n', '')


def getABI(path):
    with open(path, 'r') as f:
        abi = f.read().replace('\n', '').replace(' ', '')
        if abi[0] == "{":
            abi = abi[7:-1]
        return abi


def genConstructorInputs(abi):
    inputs = json_helper.get_function_from_abi(abi, 'type', 'constructor', 'inputs')
    new_input = []
    if inputs != None:
        for dict in inputs:
            new_input.append(dict['type'])
        return gi.gen_input(new_input, True, ConstructorAddressAccount)
    else:
        return None


def deployContract(bytecode, abi):
    inp_seq = genConstructorInputs(abi)
    pay = json_helper.get_function_from_abi(abi, 'type', 'constructor', 'payable')
    if pay is True:
        value = Web3.toWei(1, 'ether')
    else:
        value = 0

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    if inp_seq is None:
        tx_hash = contract.constructor().transact({'value': value})
    else:
        tx_hash = contract.constructor(*inp_seq).transact({'value': value})
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    return tx_receipt


def extractFunctions(funcs, abi):
    funcs_without_param = []
    funcs_with_param = []
    remove = []
    payable = []
    non_payable = []

    for f in funcs:

        f_name = (str(f).split(' ')[1]).split('(')[0]
        f_param = (str(f).split(' ')[1]).split('(')[1]

        pay = json_helper.get_function_from_abi(abi, 'name', f_name, 'payable')
        mutability = json_helper.get_function_from_abi(abi, 'name', f_name, 'constant')
        if (mutability is True) or ('tuple' in f_param):
            remove.append(f)
        else:
            if (str(f).split(' ')[1]).split('(')[1] == ')>':
                funcs_without_param.append(f_name)
            else:
                funcs_with_param.append(f_name)

            if pay is True:
                payable.append(f_name)
            else:
                non_payable.append(f_name)
    for r in remove:
        funcs.remove(r)

    return [funcs, funcs_without_param, funcs_with_param, payable, non_payable]


def readGethLog(log_seek, txmap, tx_hash):
    with open('geth_run.log', 'r') as f:
        f.seek(log_seek)
        lines = f.readlines()
        log_seek = f.tell()

    for idx, line in enumerate(lines):
        if "txHash=" in line:
            tx_hash = line.split("txHash=")[1].split(" ")[0]
            if tx_hash in txmap:
                txmap[tx_hash].append(line.replace('\n', ''))
            else:
                txmap[tx_hash] = [line.replace('\n', '')]
        if '#$#' in line:
            ErrTime = lines[idx - 1]
            ErrTime = datetime.strptime(
                '2021-' + ErrTime.split("[")[1].split("]")[0].replace('|', ' '),
                '%Y-%m-%d %H:%M:%S.%f')
            errors = line.split('#$#')
            errors = errors[1:]
            for e in errors:
                if e[-1] == ':':
                    e = e[:-1]
                tx_hash = e.split(":")[1].replace('\n', '')
                if tx_hash in txmap:
                    # + '&' + ErrTime
                    txmap[tx_hash].append('#$#' + e.replace('\n', '') + '&' + str(ErrTime))
                else:
                    txmap[tx_hash] = ['#$#' + e.replace('\n', '') + '&' + str(ErrTime)]
    return log_seek, txmap


def updateStorageAccessMap(t, txMemMap, txmap, Blocks, RunGas, VulnerabilitiesList, TxCount, ReEntrancy):
    global BranchCount
    newCoverage = False
    BlockList = []
    coveredBLocks = []
    OpList = []
    blkcnt = 0
    cnt = 0
    RWmap = {}
    gasConsumed = 0

    tx_hash = t.Hash
    if tx_hash in txmap:
        vulTx = []
        for line in txmap[tx_hash]:
            if '#$#' in line:
                vulnerability = line.split('&')[0]
                vulTime = line.split('&')[1]
                vulnerability = vulnerability.replace('#$#', '')
                if ReEntrancy == False:
                    vul = vulnerability.split(":")[0] + ' - ' + t.Function.Name
                    VulExists = False
                    for v in VulnerabilitiesList:
                        if v.split('#')[0] == vul:
                            VulExists = True
                    if VulExists == False:
                        vulTx.append(vul + '#' + vulTime+ '#' + str(TxCount))
                else:
                    if 'Reentrancy' in vulnerability:
                        vul = vulnerability.split(":")[0] + ' - ' + t.Function.Name
                        VulExists = False
                        for v in VulnerabilitiesList:
                            if v.split('#')[0] == vul:
                                VulExists = True
                        if VulExists == False:
                            vulTx.append(vul + '#' + vulTime+ '#' + str(TxCount))
            if 'CallStack' in line:
                gasConsumed = RunGas - int(line.split('gas=')[1].split(' ')[0])
                err = 'nil'
                if 'err=' in line:
                    err = line.split('err=')[1].split(' ')[0]
                if err != 'nil':
                    vulTx = []
                if 'invalid opcode' in line:
                    gasConsumed = -999
            if 'OpStep-SLOAD' in line:
                OpList.append('R,' + line.split('memorykey=')[1])
            if 'OpStep-SSTORE' in line:
                OpList.append('W,' + line.split('memorykey=')[1])
            if 'BlockHash' in line:
                if line.split('BlockHash=')[1].split(' ')[0] in Blocks.keys():
                    BlockList.append([line.split('BlockHash=')[1].split(' ')[0], OpList])
                    # print(line.split('BlockHash=')[1].split(' ')[0])
                    if Blocks[line.split('BlockHash=')[1].split(' ')[0]] == False:
                        newCoverage = True
                        Blocks[line.split('BlockHash=')[1].split(' ')[0]] = True
                OpList = []
            if 'tracestringhashlist' in line:
                l = line.split('tracestringhashlist=[')[1]
                l = l.replace(']', '').replace('\'', '').split(',')
                l = [x.split(':')[0] for x in l]
                coveredBLocks = l
                for idx, b in enumerate(l):
                    if idx == 0:
                        continue
                    else:
                        if l[idx - 1] in Blocks.keys():
                            isValid, PrevOpcodes = isValidJumpi(l[idx - 1])
                            if isValid:
                                if l[idx] in Blocks.keys():
                                    branch = str(l[idx - 1])+'-'+str(l[idx])
                                    if branch not in BranchCount:
                                        BranchCount.append(branch)
        blkcnt = 0
        cnt = 0
        RWmap = []
        for item in BlockList:
            blkcnt += 1
            if len(item[1]):
                cnt += 1
                for i in item[1]:
                    loc = i.split(',')[1]
                    event = i.split(',')[0]
                    block_id = str(item[0])
                    RWmap.append([loc, block_id, event])
        for v in vulTx:
            if v not in VulnerabilitiesList:
                VulnerabilitiesList.append(v)
    txMemMap[tx_hash] = RWmap

    return txMemMap, Blocks, gasConsumed, coveredBLocks, BlockList, newCoverage


def SBCFuzzer(Blocks, fRecord, Q, contract, addressArray, VulnerabilitiesList, log_seek, timeout, ImpBlockPredecessors):

    iterationCounter = 0
    Rungas = 800000

    ImpBlocksCovered = {}
    ImpBlockDistance = {}
    ImpBlocksVulnerable = {}
    for b in ImpBlockPredecessors.keys():
        ImpBlocksCovered[b] = False
        ImpBlockDistance[b] = 99
        ImpBlocksVulnerable[b] = False

    if range(len(fRecord)) is 0:
        return [Q, VulnerabilitiesList, log_seek]

    Set_of_Locs = []
    Func_Identifier = []
    RWs = []

    for f in fRecord:
        Func_Identifier.append(f.Name)

    startTime = time.time()
    numSeeds = 1

    for i in range(numSeeds*len(fRecord)):
        accountsToRun = [OwnerAccount, NormalAccount]
        bestTx = None

        for account in accountsToRun:
            f = fRecord[i]
            if len(f.Input) is not 0:
                inp_seq = gi.gen_input(f.Input, False, addressArray)
            else:
                inp_seq = []

            value = 0
            if f.Payable is True:
                RandomValue = random.randrange(0, Web3.toWei(0.005, 'ether'), Web3.toWei(0.0001, 'ether'))
                value = random.choice([100, 200, 500, 1000, RandomValue])
            priority = 100
            tx = Transaction(len(Q) + 1, account, f, value, inp_seq, 0, priority, None)

            # Step: Execute tx
            try:
                reEntrantCall = random.choice([True, False, False])
                if tx.From is OwnerAccount:
                    reEntrantCall = random.choice([True, False, False])

                if reEntrantCall is True:
                    if len(tx.Input) is 0:
                        input = contract.encodeABI(fn_name=tx.Function.Name.split("(")[0])
                    else:
                        input = contract.encodeABI(fn_name=tx.Function.Name.split("(")[0], args=tx.Input)
                    tx_hash = reentrancyCall(input, contract)
                    tx.Hash= tx_hash.hex()
                    tx_receipt = w3.eth.waitForTransactionReceipt(tx.Hash)
                    tx.Gas = tx_receipt['cumulativeGasUsed']
                else:
                    contract_f = contract.get_function_by_signature(tx.Function.Name)
                    if len(tx.Input) is 0:
                        tx_hash = contract_f().transact({'from': tx.From, 'value': tx.Value, 'gas': Rungas})
                    else:
                        tx_hash = contract_f(*tx.Input).transact({'from': tx.From, 'value': tx.Value, 'gas': Rungas})
                    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                    tx.Hash = tx_hash.hex()
                    tx.Gas = tx_receipt['cumulativeGasUsed']
                txmap = {}
                txMemMap = {}

                BLockCoverage = []
                BlockList = []
                newCoverage = False

                log_seek, txmap = readGethLog(log_seek, txmap, tx.Hash)
                txMemMap, Blocks, gasConsumed, BLockCoverage, BlockList, newCoverage = updateStorageAccessMap(tx, txMemMap, txmap, Blocks, Rungas, VulnerabilitiesList, i, reEntrantCall)

                tx.RWevents = []
                for block in BlockList:
                    if len(block[1]) > 0:
                        for b in block[1]:
                            tx.RWevents.append(b)

                # Step: Update Important BLocks Covered
                for block in ImpBlocksCovered.keys():
                    if block in BLockCoverage:
                        ImpBlocksCovered[block] = True

                tx.distanceImportantBlocks = {}
                # Step: Update Distance from Closest block for seends
                distance = 0
                for block in ImpBlocksCovered.keys():
                    if ImpBlocksCovered[block] == False:
                        preds = ImpBlockPredecessors[block]
                        flag = False
                        for p in preds:
                            if p[0] in BLockCoverage:
                                tx.distanceImportantBlocks[block] =  p[1]
                                distance = p[1]
                                flag = True
                                break
                        if flag == False:
                            tx.distanceImportantBlocks[block] =  99
                            distance = 99
                    else:
                        # print(block, 0)
                        tx.distanceImportantBlocks[block] =  0
                        distance = 0
                    if distance<ImpBlockDistance[block]:
                        ImpBlockDistance[block] = distance
                listDist = []
                for b in tx.distanceImportantBlocks:
                    listDist.append(str(b[1]).zfill(2))


            except Exception as e:
                print(e)

            # Step: Obtain BC, SBC, PC

            if bestTx is None:
                bestTx = tx
            else:
                if bestTx.Gas<tx.Gas:
                    bestTx = tx

        memLocs = []
        Reads = []
        Writes = []
        for e in bestTx.RWevents:
            if e.split(',')[0] is 'R':
                Reads.append(e.split(',')[1])
            else:
                Writes.append(e.split(',')[1])
            memLocs.append(e.split(',')[1])
        for m in set(memLocs):
            if m not in Set_of_Locs:
                Set_of_Locs.append(m)
        RR = []
        WW = []
        for R in Reads:
            RR.append(Set_of_Locs.index(R))
        for W in Writes:
            WW.append(Set_of_Locs.index(W))
        RWs.append([list(set(RR)), list(set(WW))])

        Q.append(bestTx)

    listFun = {}
    for f in fRecord:
        listFun[f.Name] = numSeeds

    t_mut = None
    TxBudget = 600

    TxCount = len(fRecord)*numSeeds


    listBlocks = list(ImpBlockDistance.keys())
    listRelevance = []
    while time.time() < startTime + timeout and TxCount<TxBudget:
        try:
            for t in Q:
                if TxCount >= TxBudget:
                    break
                TotalScore = 0
                t_mut = copy.deepcopy(t)
                t_mut.Index = len(Q) + 1
                t_mut.Priority = 100

                listFun[t_mut.Function.Name] += 1

                accountsToRun = [OwnerAccount, OwnerAccount, OwnerAccount, NormalAccount]
                account = random.choice(accountsToRun)
                t_mut.From = account

                if t_mut.Function.Payable is True:
                    RandomValue = random.randrange(0, Web3.toWei(0.005, 'ether'), Web3.toWei(0.0001, 'ether'))
                    t_mut.Value = random.choice([100, 200, 500, 1000, RandomValue])


                if len(t_mut.Input) > 0:
                    t_mut.Input = mi.mut_input(t.Function.Input, t.Input)
                    # print(t_mut.Input)

                # Step: execute Mutant t1'
                contract_f = contract.get_function_by_signature(t_mut.Function.Name)
                if len(t_mut.Input) is 0:
                    tx_hash = contract_f().transact({'from': t_mut.From, 'value': t_mut.Value, 'gas': Rungas})
                else:
                    tx_hash = contract_f(*t_mut.Input).transact({'from': t_mut.From, 'value': t_mut.Value, 'gas': Rungas})
                tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                t_mut.Hash = tx_hash.hex()
                t_mut.Gas = tx_receipt['cumulativeGasUsed']


                txmap = {}
                txMemMap = {}

                BLockCoverage = []
                BlockList = []
                newCoverage = False

                log_seek, txmap = readGethLog(log_seek, txmap, t_mut.Hash)
                txMemMap, Blocks, gasConsumed, BLockCoverage, BlockList, newCoverage = updateStorageAccessMap(t_mut, txMemMap,txmap, Blocks,Rungas,VulnerabilitiesList,TxCount,False)

                # Step: Update RWevents
                t_mut.RWevents = []
                for block in BlockList:
                    if len(block[1]) > 0:
                        for b in block[1]:
                            t_mut.RWevents.append(b)

                # Step: Update Important BLocks Covered
                for block in ImpBlocksCovered.keys():
                    if block in BLockCoverage:
                        ImpBlocksCovered[block] = True

                if newCoverage is True:
                    Q.insert(Q.index(t) + 1, t_mut)

                TxCount+=1

                # Step: FollowupTx
                # Step: chooseTx t2 by RWevent
                highScoreIndex = 0
                highScore = 0

                if t_mut is not None:
                    if len(fRecord)>1:
                        memLocs = []
                        Reads = []
                        Writes = []
                        for e in t_mut.RWevents:
                            if e.split(',')[0] is 'R':
                                Reads.append(e.split(',')[1])
                            else:
                                Writes.append(e.split(',')[1])
                            memLocs.append(e.split(',')[1])

                        for m in set(memLocs):
                            if m not in Set_of_Locs:
                                Set_of_Locs.append(m)

                        RR = []
                        WW = []
                        for R in Reads:
                            RR.append(Set_of_Locs.index(R))
                        for W in Writes:
                            WW.append(Set_of_Locs.index(W))
                        RWs.append([list(set(RR)), list(set(WW))])

                        Reads = set(Reads)
                        Writes = set(Writes)
                        memLocs = set(memLocs)
                        score = {}
                        Q_pattern = []
                        for t in Q:
                            s = 0
                            if t.Function.Name != t_mut.Function.Name:

                                t_memLocs = []
                                t_Reads = []
                                t_Writes = []
                                for e in t.RWevents:
                                    t_memLocs.append(e.split(',')[1])
                                    if e.split(',')[0] is 'R':
                                        t_Reads.append(e.split(',')[1])
                                    else:
                                        t_Writes.append(e.split(',')[1])


                                t_memLocs = set(t_memLocs)
                                t_Reads = set(t_Reads)
                                t_Writes = set(t_Writes)

                                for r in Reads:
                                    if r in t_Writes:
                                        s = s + 1
                                        if len(t_Writes) > 1:
                                            # s = s + 1
                                            s = s + (len(t_Writes)-1)

                                for w in Writes:
                                    if w in t_Writes:
                                        s = s + 1
                                        if len(t_Writes) > 1:
                                            # s = s + 1
                                            s = s + (len(t_Writes) - 1)

                                    if w in t_Reads:
                                        s = s + 1
                                        t_Writes_copy = copy.deepcopy(t_Writes)
                                        if w in t_Writes_copy:
                                            t_Writes_copy.remove(w)
                                            if len(t_Writes_copy) > 0:
                                                # s = s + 1
                                                s = s + len(t_Writes_copy)
                                score[t.Index] = s


                        TotalScore = sum(score.values())
                        chosenT = random.randint(0,TotalScore)
                        sumScore = 0
                        for key in score.keys():
                            sumScore += score[key]
                            if sumScore>=chosenT:
                                highScoreIndex = key
                                listRelevance.append(score[key])
                                break
                    else:
                        memLocs = []
                        Reads = []
                        Writes = []
                        for e in t_mut.RWevents:
                            if e.split(',')[0] is 'R':
                                Reads.append(e.split(',')[1])
                            else:
                                Writes.append(e.split(',')[1])
                            memLocs.append(e.split(',')[1])

                        for m in set(memLocs):
                            if m not in Set_of_Locs:
                                Set_of_Locs.append(m)

                        RR = []
                        WW = []
                        for R in Reads:
                            RR.append(Set_of_Locs.index(R))
                        for W in Writes:
                            WW.append(Set_of_Locs.index(W))
                        RWs.append([list(set(RR)), list(set(WW))])

                        Reads = set(Reads)
                        Writes = set(Writes)
                        memLocs = set(memLocs)

                        score = {}
                        for t in Q:
                            s = 0
                            t_memLocs = []
                            t_Reads = []
                            t_Writes = []
                            for e in t.RWevents:
                                if e.split(',')[0] is 'R':
                                    t_Reads.append(e.split(',')[1])
                                else:
                                    t_Writes.append(e.split(',')[1])
                                t_memLocs.append(e.split(',')[1])
                            t_memLocs = set(t_memLocs)
                            t_Reads = set(t_Reads)
                            t_Writes = set(t_Writes)

                            for r in Reads:
                                if r in t_Writes:
                                    s = s + 1
                                    if len(t_Writes) > 1:
                                        # s = s + 1
                                        s = s + (len(t_Writes) - 1)


                            for w in Writes:
                                if w in t_Writes:
                                    s = s + 1
                                    if len(t_Writes) > 1:
                                        # s = s + 1
                                        s = s + (len(t_Writes) - 1)

                                if w in t_Reads:
                                    s = s + 1
                                    t_Writes_copy = copy.deepcopy(t_Writes)
                                    if w in t_Writes_copy:
                                        t_Writes_copy.remove(w)
                                        if len(t_Writes_copy) > 0:
                                            # s = s + 1
                                            s = s + (len(t_Writes_copy) - 1)
                            score[t.Index] = s

                        # Power Law
                        TotalScore = sum(score.values())
                        chosenT = random.randint(0, TotalScore)
                        sumScore = 0
                        for key in score.keys():
                            sumScore += score[key]
                            if sumScore >= chosenT:
                                highScoreIndex = key
                                listRelevance.append(score[key])
                                break

                if TxCount >= TxBudget:
                    break
                if TotalScore == 0:
                    continue
                t = Q[highScoreIndex-1]

                # Step: MutateTx t2'
                T_Index = t.Index
                t_mut = copy.deepcopy(t)
                t_mut.Index = len(Q) + 1
                t_mut.Priority = 100

                listFun[t_mut.Function.Name] += 1

                accountsToRun = [OwnerAccount, OwnerAccount, OwnerAccount, NormalAccount]
                account = random.choice(accountsToRun)
                t_mut.From = account

                if t_mut.Function.Payable is True:
                    RandomValue = random.randrange(0, Web3.toWei(0.005, 'ether'), Web3.toWei(0.0001, 'ether'))
                    t_mut.Value = random.choice([100, 200, 500, 1000, RandomValue])

                if len(t_mut.Input) > 0:
                    t_mut.Input = mi.mut_input(t.Function.Input, t.Input)

                # Step: execute Mutant t2'
                contract_f = contract.get_function_by_signature(t_mut.Function.Name)
                if len(t_mut.Input) is 0:
                    tx_hash = contract_f().transact({'from': t_mut.From, 'value': t_mut.Value, 'gas': Rungas})
                else:
                    tx_hash = contract_f(*t_mut.Input).transact({'from': t_mut.From, 'value': t_mut.Value, 'gas': Rungas})
                tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                t_mut.Hash = tx_hash.hex()
                t_mut.Gas = tx_receipt['cumulativeGasUsed']

                txmap = {}
                txMemMap = {}

                BLockCoverage = []
                BlockList = []
                newCoverage = False

                log_seek, txmap = readGethLog(log_seek, txmap, t_mut.Hash)
                txMemMap, Blocks, gasConsumed, BLockCoverage, BlockList, newCoverage = updateStorageAccessMap(t_mut, txMemMap, txmap, Blocks, Rungas, VulnerabilitiesList, TxCount, False)

                # Step: Update RWevents
                t_mut.RWevents = []
                for block in BlockList:
                    if len(block[1]) > 0:
                        for b in block[1]:
                            t_mut.RWevents.append(b)

                # Step: Update Important BLocks Covered
                for block in ImpBlocksCovered.keys():
                    if block in BLockCoverage:
                        ImpBlocksCovered[block] = True

                memLocs = []
                Reads = []
                Writes = []
                for e in t_mut.RWevents:
                    if e.split(',')[0] is 'R':
                        Reads.append(e.split(',')[1])
                    else:
                        Writes.append(e.split(',')[1])
                    memLocs.append(e.split(',')[1])
                for m in set(memLocs):
                    if m not in Set_of_Locs:
                        Set_of_Locs.append(m)
                RR = []
                WW = []
                for R in Reads:
                    RR.append(Set_of_Locs.index(R))
                for W in Writes:
                    WW.append(Set_of_Locs.index(W))
                RWs.append([list(set(RR)), list(set(WW))])

                if newCoverage is True:
                    Q.insert(Q.index(t)+1,t_mut)
                TxCount += 1
        except Exception as e:
            # p = e
            print(e)


    return [Q, VulnerabilitiesList, log_seek, TxCount, listRelevance, RWs]


def getPredecessor(graph, pp, PredList, i):
    if len(pp.preds) > 0:
        for p in pp.preds:
            if p.block_hash not in [item[0] for item in PredList]:
                PredList.append([p.block_hash,i+1])
                PredList = getPredecessor(graph, p, PredList, i+1)
    return PredList


def getBlocks(graph):
    ImportantBlocks = []
    ImpBlockPredecessors = {}
    BlockHashes = {}

    for block in graph:
        if block.HasMissingOps == False:
            BlockHashes[block.block_hash] = False
            if block.interesting == True:
                ImportantBlocks.append(block.block_hash)

    for block in graph:
        if block.block_hash in ImportantBlocks:
            PredList = []
            i=0
            if len(block.preds) > 0:
                for p in block.preds:
                    PredList.append([p.block_hash,i+1])
                    PredList = getPredecessor(graph, p, PredList,i+1)
            ImpBlockPredecessors[block.block_hash] = PredList


    return ImportantBlocks, ImpBlockPredecessors, BlockHashes


def isValidJumpi(blockhash):
    global graph
    isValid = False
    PreviousOpcodes = []

    for block in graph.blocks:
        if block.block_hash == blockhash:
            lines = str(block).split('---')[2].split('\n')
            opcodes = [l.split(' ')[1] for l in list(filter(lambda a: a != '', lines))]

            if opcodes[-1] == "JUMPI":
                isValid = True
                if len(opcodes) >= 5:
                    PreviousOpcodes = opcodes[-5:]
                else:
                    PreviousOpcodes = opcodes

    return isValid, PreviousOpcodes


def findTx(txHashlist, txMemMap, Op, B, memLoc):
    T = {}
    for hash in txMemMap:
        for memLoc in txMemMap[hash]:
            if Op in memLoc:
                if B in memLoc:
                    T[txHashlist[hash].Gas] = hash

    maxGas = max(T.keys())

    return T[maxGas]


def FromTransactionFindABIFunction(tx, fRecord):
    for func in fRecord:
        if tx.Function == func.Name:
            return func


def MainLoop(start, end):
    try:
        shutil.rmtree('Ethereum')
        shutil.copytree('Ethereum-backup', 'Ethereum')

        os.system('pkill -INT geth')
        if os.path.isfile('geth_run.log'):
            os.system('rm geth_run.log')
    except Exception as e:
        print('No Process to Kill')

    os.system('nohup ./geth_run.sh>>geth_run.log 2>&1 &')
    waittime = 3
    timenow = time.time()
    while True:
        if time.time() - timenow > waittime:
            break

    global w3
    global contractmap
    global BranchCount
    global NormalAccount
    global OwnerAccount
    global ConstructorAddressAccount
    global AttackerContract
    global graph

    w3 = Web3()

    intermediatevariables = []
    answerreceived = False  # scriptchange
    connected = False  # scriptchange
    while not answerreceived:
        ans = 'y'  # input("Y/N?")
        if ans.lower() == "y":
            # print("Please specify the provider you are using?")
            answerreceived = True
            intermediatevariables.append(ans)
        elif ans.lower() == "n":
            print("Trying to auto connect to the ethereum chain")
            answerreceived = True
            try:
                print(
                    "Connected to chain " + w3.eth.chainId + " with latest block number:" + str(w3.eth.blockNumber))
                connected = True
                intermediatevariables.append(ans)
            except:
                print("Cannot connect to the ethereum chain")
                print("Please specify the provider you are using?")
        else:
            print("Please only answer 'Y' or 'N'")
            answerreceived = False
    answerreceived = False
    while not connected:
        # ans = input("1.HTTPProvider, 2. IPCProvider. 3. WebsocketProvider")
        ans = "1"
        if ans == "1":
            # uri = input("Please provide the endpoint uri such as 'https://localhost:8545'.")
            uri = 'http://127.0.0.1:8545'
            try:
                w3 = Web3(Web3.HTTPProvider(uri))
                print("Connected to chain with latest block number::" + str(w3.eth.blockNumber))
                connected = True
                intermediatevariables.append([ans, uri])
            except:
                print("Cannot connect to the chain. Please make sure the input provided are correct")
        elif ans == "2":
            # filesystempath = input("Please provide the file system path to the chain")
            filesystempath = '/home/imran/.ethereum/geth.ipc'
            try:
                w3 = Web3(Web3.IPCProvider(filesystempath))
                print("Connected to chain with latest block number::" + str(w3.eth.blockNumber))
                connected = True
                intermediatevariables.append([ans, filesystempath])
            except Exception as e:
                print(e)
                print("Cannot connect to the chain. Please make sure the input provided are correct")
                exit()
        elif ans == "3":
            endpointuri = input("Please provide the full URI to the RPC endpoint such as 'ws://localhost:8546'.")
            try:
                w3 = Web3(Web3.WebsocketProvider(endpointuri))
                print("Connected to chain with latest block number::" + str(w3.eth.blockNumber))
                connected = True
                intermediatevariables.append([ans, endpointuri])
            except:
                print("Cannot connect to the chain. Please make sure the input provided are correct")
        else:
            print("Please only answer 1,2,3")


    coinbase = w3.eth.coinbase
    OwnerAccount = w3.eth.accounts[0]
    NormalAccount = w3.eth.accounts[1]
    ConstructorAddressAccount = w3.eth.accounts[2]

    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    w3.geth.personal.unlockAccount(OwnerAccount, "", 20 * 60 * 60)
    w3.geth.personal.unlockAccount(NormalAccount, "123456", 20 * 60 * 60)
    w3.geth.personal.unlockAccount(ConstructorAddressAccount, "123456", 20 * 60 * 60)

    # TODO: Link Google Big-query to get Related Smart Contracts
    addressArray = []

    w3.eth.defaultAccount = OwnerAccount


    count = 0
    AttackerContract = getAttackerAgent()

    write_to_excel_coverage = {}
    write_to_excel_stats = {}

    for r, d, f in os.walk(path_bin):
        if end is 9999:
            filelist = sorted(f)[start:]
        else:
            filelist = sorted(f)[start:end]
        for file in filelist:
            if '.bin' in file:

                global BranchCount
                BranchCount = []
                count = count + 1

                try:
                    print('\nContract # ' + str(count) + ' - ' + str(time.ctime())[11:19] + ' - ' + file[:-4])
                    Time_start = time.time()
                    bytecode = getBytecode(path_bin + '/' + file)
                    abi = getABI(path_abi + '/' + file[:-4] + '.abi')

                    tx_receipt = deployContract(bytecode, abi)

                    contract = w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
                    contractAddress = tx_receipt.contractAddress

                    tx_hash = w3.eth.sendTransaction({'to': contract.address, 'from':OwnerAccount, 'value': Web3.toWei(10, 'ether'), 'gas':800000})
                    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

                    byte_code = w3.eth.getCode(contractAddress)

                    graph = cfg.getCFG(str(byte_code.hex()))

                    ImportantBlocks = []
                    ImpBlockPredecessors = {}
                    BlockHashes = {}

                    ImportantBlocks, ImpBlockPredecessors, BlockHashes = getBlocks(graph.blocks)

                    funcs = contract.all_functions()
                    [funcs, funcs_without_param, funcs_with_param, payable, non_payable] = extractFunctions(funcs, abi)

                    fRecord = []

                    for f in funcs:
                        f_name = str(f).split(' ')[1].split('>')[0]
                        inp = str(f).split(' ')[1].split('(')[1]
                        if inp != ')>':
                            inputs = inp[:-2].split(',')
                        else:
                            inputs = []
                        if f_name.split('(')[0] in payable:
                            pay = True
                        else:
                            pay = False
                        fun = Function(f_name, inputs, pay, 0)
                        fRecord.append(fun)

                    if len(fRecord) == 0:
                        print('No Functions to fuzz')
                        continue

                    Q = []
                    Q_size = 0
                    priority = 100
                    txHashlist = {}
                    VulnerabilitiesList = []
                    log_seek = 0
                    Totaltx = 0
                    timeout = 120

                    # Step: Fuzzer
                    [Q, VulnerabilitiesList, log_seek, Totaltx, listRelevance, RWs] = SBCFuzzer(BlockHashes, fRecord, Q, contract, addressArray, VulnerabilitiesList, log_seek, timeout, ImpBlockPredecessors)

                    blockCoverage_list = []
                    lines = []

                    # Step: Graph (Commented)
                    BLKcount = {}
                    starttime = None
                    with open('geth_run.log', 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            if 'Submitted contract creation' in line:
                                starttime = datetime.strptime(
                                    '2021-' + line.split("[")[1].split("]")[0].replace('|', ' '),
                                    '%Y-%m-%d %H:%M:%S.%f')
                            if 'Trace' in line:
                                ln = line.split('tracestringhashlist=[')[1].split(',')
                                for l in ln:
                                    l = l.split('\'')[1]
                                    if l in BlockHashes.keys():
                                        if l in BLKcount.keys():
                                            BLKcount[l] += 1
                                        else:
                                            BLKcount[l] = 1
                                            t = datetime.strptime(
                                                '2021-' + line.split("[")[1].split("]")[0].replace('|', ' '),
                                                '%Y-%m-%d %H:%M:%S.%f')
                                            diff = t - starttime
                                            blockCoverage_list.append(
                                                [l, diff.seconds + diff.microseconds / 1000000])
                    vulTimeList = []
                    for vul in VulnerabilitiesList:
                        vulTime = vul.split('#')[1]
                        vulTime = datetime.strptime(vulTime, '%Y-%m-%d %H:%M:%S.%f')
                        vulTime = vulTime - starttime
                        vulTimeList.append(vulTime.seconds + vulTime.microseconds / 1000000)

                    sortedBlockCoverage = sorted(blockCoverage_list, key=lambda x: x[1])
                    lenBLock = len(sortedBlockCoverage)


                    shutil.copy('geth_run.log', str(count) + '-' + file[:-4] + '.log')
                    shutil.move(str(count) + '-' + file[:-4] + '.log', 'logs')
                    open('geth_run.log', 'w').close()

                    write_to_excel_coverage[file[:-4]] = [VulnerabilitiesList, len(BranchCount)]

                    DataWriter = pd.ExcelWriter('Results - CoverageFuzzer.xlsx')
                    DataToWrite1 = pd.DataFrame.from_dict(write_to_excel_coverage, orient='index')
                    DataToWrite1.columns = ['Vul','Branches']
                    DataToWrite1.to_excel(DataWriter, sheet_name='Sheet1')

                    DataWriter.save()

                except Exception as e:
                    shutil.copy('geth_run.log', str(count) + '-' + file[:-4] + '.log')
                    shutil.move(str(count) + '-' + file[:-4] + '.log', 'logs')
                    open('geth_run.log', 'w').close()

    print(count)
    shutil.copy('Results - CoverageFuzzer.xlsx', 'Results - StAGFuzzer' + str(time.ctime())[3:19]  +  '.xlsx')

    shutil.rmtree('Ethereum')
    shutil.copytree('Ethereum-backup', 'Ethereum')

    os.system('pkill -INT geth')
    os.system('rm geth_run.log')


if __name__ == '__main__':
    MainLoop(0, 9999)
