class Packet:
    def __init__(self, data, number, checksum, eof=False):
        self.data = data
        self.number = number
        self.checksum = checksum
        self.end_of_file = eof
