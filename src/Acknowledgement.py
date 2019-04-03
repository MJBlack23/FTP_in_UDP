class Acknowledgement:
    def __init__(self, checksum, retransmit=False):
        self.checksum = checksum
        self.retransmit = retransmit
