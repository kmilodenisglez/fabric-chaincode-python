#!/usr/bin/env python3
# Copyright the fabric-chaincode-python contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Token Chaincode Example (CCAAS)

This is a simple token transfer chaincode that demonstrates:
- Token initialization (minting)
- Balance queries
- Token transfers between accounts
- State management with the Fabric ledger

Deploy this as a Chaincode-as-a-Service (CCAAS) in Fabric.
"""

import sys
import logging

from src.fabric_shim.interfaces import Chaincode, ChaincodeStubInterface
from src.fabric_shim.server import start
from src.fabric_shim.response import ResponseCode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class TokenChaincode(Chaincode):
    """Simple token management chaincode"""

    async def init(self, stub: ChaincodeStubInterface):
        """
        Chaincode initialization - issues initial tokens to accounts
        
        Args:
            stub: ChaincodeStubInterface for ledger access
            
        Returns:
            Success or error response
        """
        logger.info("=== TokenChaincode Init ===")
        try:
            # Initialize token balances for test accounts
            await stub.put_state('tommy', b'1000')  # Issue 1000 tokens to tommy
            await stub.put_state('jerry', b'1000')  # Issue 1000 tokens to jerry
            
            logger.info("Token initialization successful")
            return ResponseCode.SUCCESS, b'init ok'
        except Exception as e:
            logger.error(f"Error during init: {str(e)}")
            return ResponseCode.ERROR, str(e).encode()

    async def invoke(self, stub: ChaincodeStubInterface):
        """
        Chaincode invocation handler - routes to appropriate function
        
        Args:
            stub: ChaincodeStubInterface for ledger access
            
        Returns:
            Response from the invoked function
        """
        logger.info("=== TokenChaincode Invoke ===")
        try:
            fcn, args = stub.get_function_and_parameters()
            logger.info(f"Invoking function: {fcn} with args: {args}")

            if fcn == 'reset':
                return await self.init(stub)
            elif fcn == 'balance':
                if len(args) < 1:
                    return ResponseCode.ERROR, b'balance requires 1 argument: account'
                return await self.balance(stub, args[0])
            elif fcn == 'transfer':
                if len(args) < 3:
                    return ResponseCode.ERROR, b'transfer requires 3 arguments: from, to, amount'
                return await self.transfer(stub, args[0], args[1], args[2])
            else:
                return ResponseCode.ERROR, f'method {fcn} not supported'.encode()

        except Exception as e:
            logger.error(f"Error during invoke: {str(e)}")
            return ResponseCode.ERROR, str(e).encode()

    async def balance(self, stub: ChaincodeStubInterface, account: str):
        """
        Query the balance of an account
        
        Args:
            stub: ChaincodeStubInterface for ledger access
            account: Account name to query
            
        Returns:
            Balance information
        """
        logger.info(f"Querying balance for account: {account}")
        try:
            value = await stub.get_state(account)
            if not value:
                return ResponseCode.ERROR, f'account {account} not found'.encode()
            
            logger.info(f"Balance for {account}: {value.decode()}")
            return ResponseCode.SUCCESS, b'balance => ' + value
        except Exception as e:
            logger.error(f"Error querying balance: {str(e)}")
            return ResponseCode.ERROR, str(e).encode()

    async def transfer(self, stub: ChaincodeStubInterface, owner: str, to: str, value: str):
        """
        Transfer tokens from one account to another
        
        Args:
            stub: ChaincodeStubInterface for ledger access
            owner: Source account
            to: Destination account
            value: Amount to transfer
            
        Returns:
            Success or error response
        """
        logger.info(f"Transferring {value} tokens from {owner} to {to}")
        try:
            value = int(value)
            
            # Get owner balance
            owner_balance_bytes = await stub.get_state(owner)
            if not owner_balance_bytes:
                return ResponseCode.ERROR, f'account {owner} not found'.encode()
            
            owner_balance = int(owner_balance_bytes.decode())
            
            # Check sufficient balance
            if owner_balance < value:
                return ResponseCode.ERROR, f'insufficient balance: {owner_balance} < {value}'.encode()
            
            # Get recipient balance
            to_balance_bytes = await stub.get_state(to)
            if not to_balance_bytes:
                return ResponseCode.ERROR, f'account {to} not found'.encode()
            
            to_balance = int(to_balance_bytes.decode())
            
            # Update balances
            owner_balance -= value
            to_balance += value
            
            # Write updated balances to ledger
            await stub.put_state(owner, str(owner_balance).encode())
            await stub.put_state(to, str(to_balance).encode())
            
            logger.info(f"Transfer successful: {owner} ({owner_balance}), {to} ({to_balance})")
            return ResponseCode.SUCCESS, b'transfer ok'
        except ValueError:
            return ResponseCode.ERROR, f'invalid amount: {value}'.encode()
        except Exception as e:
            logger.error(f"Error during transfer: {str(e)}")
            return ResponseCode.ERROR, str(e).encode()


if __name__ == '__main__':
    # Start the chaincode server
    logger.info("Starting TokenChaincode server...")
    start(TokenChaincode())
