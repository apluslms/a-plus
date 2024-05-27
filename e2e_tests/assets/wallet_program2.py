# Added line in wallet_program2.py
from wallet import Wallet


def main():
    name1 = input("Who is the owner of the first wallet?\n")
    balance1 = float(input("What is the balance of the first wallet?\n"))
    name2 = input("Who is the owner of the second wallet?\n")
    balance2 = float(input("What is the balance of the second wallet?\n")) # Modified line in wallet_program2.py.
    print("Creating wallets...")
    wallet1 = Wallet(name1, balance1)
    wallet2 = Wallet(name2, balance2)
    print()
    print("Wallets created:")
    print(wallet1)
    print(wallet2)
    print()
    amount_deposit1 = float(input("How much is deposited to the first wallet?\n"))
    if wallet1.deposit(amount_deposit1):
        print("Deposit successful!")
    else:
        print("Deposit failed!")
    print("Balance of first wallet: {:.2f}".format(wallet1.get_balance()))
    amount_deposit2 = float(input("How much is deposited to the second wallet?\n"))
    if wallet2.deposit(amount_deposit2):
        print("Deposit successful!")
    else:
        print("Deposit failed!")
    print("Balance of second wallet: {:.2f}".format(wallet2.get_balance()))
    amount_withdraw1 = float(input("How much is withdrawn from the first wallet?\n"))
    if wallet1.withdraw(amount_withdraw1):
        print("Withdraw successful!")
    else:
        print("Withdraw failed!")
    print("Balance of first wallet: {:.2f}".format(wallet1.get_balance()))
    amount_withdraw2 = float(input("How much is withdrawn from the second wallet?\n"))
    if wallet2.withdraw(amount_withdraw2):
        print("Withdraw successful!")
    else:
        print("Withdraw failed!")
    print("Balance of second wallet: {:.2f}".format(wallet2.get_balance()))
    if wallet1.has_more_money(wallet2):
        print("The wallet of {:s} has more money than the wallet of {:s}.".format(wallet1.get_owner_name(), wallet2.get_owner_name()))
    else:
        print("The wallet of {:s} does not have more money than the wallet of {:s}.".format(wallet1.get_owner_name(), wallet2.get_owner_name()))


main()
