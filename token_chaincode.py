# this code is just a guide
# To test the library use the chaincode inside the main.py

# import Shim  # Introduce fabric_shim


class TokenChaincode:  # Define chaincode
    async def init(self, stub):  # Chaincode initialization processing
        await stub.put_state('tommy', b'1000')  # Issue 1000 tokens to tommy
        await stub.put_state('jerry', b'1000')  # Issue 1000 tokens to jerry
        return Shim.success(b'init ok')  # return success information

    async def invoke(self, stub):  # Chaincode transaction processing
        fcn, args = stub.get_function_and_parameters()  # Get the chaincode calling method name and parameter list

        if fcn == 'reset':  # Route according to method name
            return await self.init(stub)
        if fcn == 'balance':
            return await self.balance(stub, args[0])
        if fcn == 'transfer':
            return await self.transfer(stub, args[0], args[1], args[2])

        return Shim.error(b'method not supported')  # Unknown method name returns an error message

    async def balance(self, stub, account):  # Account balance query method
        value = await stub.get_state(account)  # Read the balance from the ledger
        return Shim.success(b'balance => ' + value)  # Return balance information

    async def transfer(self, stub, owner, to, value):  # Token transfer method
        value = int(value)
        owner_balance = await stub.get_state(owner)
        owner_balance = int(owner_balance) - value  # Deduct the balance of the sender
        to_balance = await stub.get_state(to)
        to_balance = int(to_balance) + value  # Increase the balance
        await stub.put_state(owner,  # Update the state of the sender
                             bytes(str(owner_balance), 'utf-8'))
        await stub.put_state(to, bytes(str(to_balance), 'utf-8'))  # Update the state of the transfer party
        return Shim.success(b'transfer ok')  # return success information


Shim.start(TokenChaincode())  # Start chaincode
