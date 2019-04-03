import socket
import sys
import os
import hashlib
import pickle
import time
from src.Packet import Packet
from src.Acknowledgement import Acknowledgement

# NCP is a process that sends a target file to a remote host using the
# Unreliable UDP transfer protocol
# The program should verify that the args variables are valid
# then it should send the destination file name
# it should attempt to open a file and provide a file-handler
# it should determine how large the file is, and split it into packets
# it need to keep track of how many packets have been sent and acknowledged
# it should calculate the checksum of each packet of data


# Usage: python ncp.py <local_file_path> <dest_file_name>@<dest_server_host:dest_server_port>
class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.buffer_size = 512
        self.start_time = time.time()
        self.end_time = time.time()
        self.local_file_path = ""

    # start the timer for the transfer stats
    def start_timer(self):
        self.start_time = time.time()

    # end the timer for the transfer stats
    def end_timer(self):
        self.end_time = time.time()

    def send_file(self, local_file_path, dest_file_name):
        # read the file, and get its contents as data
        packets = self.get_file_as_packets(local_file_path)

        # Connect to the remove server
        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        connection.connect((self.host, self.port))
        connection.setblocking(True)

        # Send the dest_file_name so the server knows to init a new file transfer
        connection.send(dest_file_name)

        # track the starting time
        self.start_timer()
        # send the packets and wait for each to be acknowledged
        for packet in packets:
            # marshal the packet in pickle format
            connection.send(pickle.dumps(packet))

            # init was_acked for each packet to false
            was_acked = False
            retries = 0 # init the retry counter
            while not was_acked:
                # wait to receive an acknowledgement from the server
                acknowledgement, server_address = connection.recvfrom(self.buffer_size)
                # marshal the response
                ack = pickle.loads(acknowledgement)
                # If the server requested a re-transmission
                if ack.retransmit:
                    # Abort the connection if too many retries
                    if retries >= 10:
                        self.fatal("Too many packets lost, aborting connection.  Please try again...")
                    # resend the packet
                    connection.send(pickle.dumps(packet))
                    retries += 1
                else:
                    # otherwise consider the packet acknowledged
                    was_acked = True

        # track the end time
        self.end_timer()

        # close the connection
        connection.close()

    def print_send_stats(self):
        # getsize returns bytes, divide by 1MM to get MBs
        size = os.path.getsize(self.local_file_path) / 1000000.00
        # calculate the elapsed time
        elapsed_time = self.end_time - self.start_time
        # file size / time yields the speed
        connection_speed = size / elapsed_time
        print "Transferred file " + self.local_file_path + "(" + str(round(size, 4)) + " Mbs)..." \
            "to " + self.host + " in " + str(round(elapsed_time, 4)) + " at " + str(round(connection_speed, 4)) + " Mbs/second"

    # Calculate an md5 checksum for the body
    @staticmethod
    def calculate_checksum(contents):
        return hashlib.md5(contents).hexdigest()

    # given a file path, read the file and break into packets
    def get_file_as_packets(self, local_file_path):
        self.local_file_path = local_file_path

        if not os.path.isfile(local_file_path):
            self.fatal("File path doesn't exist, please check it and try again.")
        # init an empty list for the packets
        packets = list()
        packet_count = 0
        # open the file path and read the data into packets
        with open(local_file_path, "rb") as file_handler:
            data = file_handler.read(self.buffer_size)
            while data:
                packets.append(Packet(data, packet_count, self.calculate_checksum(data)))
                packet_count += 1
                data = file_handler.read(self.buffer_size)

        # flag the last packet with and EOF marker
        packets[len(packets) - 1].end_of_file = True
        return packets

    @staticmethod
    def fatal(message):
        print(message)
        sys.exit(1)

def parseArgs():
    # if less than 3 args, not enough to start the transfer
    if len(sys.argv) < 3:
        print "Usage: python ncp.py <local_file_path> <dest_file_name>@<dest_server_host:dest_server_port>"
        sys.exit(1)
    local_file_path = sys.argv[1]
    dest = sys.argv[2].split("@")
    dest_file_name = dest[0]
    server = dest[1].split(":")
    host = server[0]
    port = int(server[1])
    return local_file_path, dest_file_name, host, port

def main():
    # Usage: python ncp.py <local_file_path> <dest_file_name>@<dest_server_host:dest_server_port>
    local_file_path, dest_file_name, host, port = parseArgs()

    # Init the client and send the file
    client = Client(host, port)
    client.send_file(local_file_path, dest_file_name)
    client.print_send_stats()


if __name__ == "__main__":
    main()