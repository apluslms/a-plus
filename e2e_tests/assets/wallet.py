class Wallet:

    # Added line in wallet.py.
    def __init__(self, owner_name, balance=0):
        self.__owner_name = owner_name


    def get_owner_name(self):
        return self.__owner_name


    def get_balance(self):
        return self.__balance


    def deposit(self, amount):
        if amount > 0:
            self.__balance += amount
            return True
        return False


    def withdraw(self, amount):
        if amount > 0 and self.get_balance() >= amount:
            self.__balance -= amount
            return True
        return False


    def has_more_money(self, other):
        if self.get_balance() > other.get_balance():
            return True
        return False


    def __str__(self):
        return "{:s}: {:.2f} euros".format(self.get_owner_name(), self.get_balance())
