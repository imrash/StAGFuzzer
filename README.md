# StAGFuzzer
Pattern-Aware Phase Alternation for Fuzzing Smart Contracts
 
# Idea
STAGFUZZER is a probabilistic phase-alternating technique supported by a suite of cross-transaction single-variable (ctsv) and intra-transaction cross-variable (itcv) state access patterns.

# Setup
We implement our test framework in Python with one miner and Geth v1.9.0.
We perform the experiments on a virtual machine with 64GB RAM, an 8-core Intel Xeon 2.2 GHz processor, and Ubuntu 18.04.

Before starting the experiment on a linux equipped machine, move the 'geth' file to directory usr/bin/ and install golang to avoid any problems.
Also, the file 'geth_run.sh' needs to be granted the permission to execute as a program.

# Execution
Place the smart contract ABIs and Binary files in the respective folders under the Dataset Folder.

Run StAGFuzzer.py to test the smart contracts.
