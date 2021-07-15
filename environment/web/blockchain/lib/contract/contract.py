#====================
# contract.py
#====================

from abc import ABCMeta, abstractmethod, ABC

class Contract(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self):
        print('<!> do nothing')

    @abstractmethod
    def __str__(self):
        raise NotImplemented()

    @abstractmethod
    def main(self, in_event):
        raise NotImplemented()
