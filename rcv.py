import socket
import sys
import time
import hashlib
import pickle
import os
from src.Packet import Packet
from src.Acknowledgement import Acknowledgement

class Server:
    def __init__(self, port):
        self.host = "0.0.0.0"
        self.port = port
        self.buffer_size = 1024
        self.should_block = True
        self.start_time = time.time()
        self.end_time = time.time()
        self.local_file_name = ""
        self.current_file_packet = dict()

    @staticmethod
    def calculate_checksum(data):
        return hashlib.md5(data).hexdigest()

    def set_packet(self, packet_count, data):
        self.current_file_packet[packet_count] = data

    def write_file(self, local_file_name):
        # open the file to write into it
        with open(local_file_name, "wb") as file_handler:
            for i in range(len(self.current_file_packet)):
                file_handler.write(self.current_file_packet[i])

        # reset the file_packet variable to an empty dictionary to receive the next file
        self.current_file_packet = dict()

    def print_stats(self):
        # getsize returns bytes, divide by 1MM to get MBs
        size = os.path.getsize(self.local_file_name) / 1000000.00
        # calculate the elapsed time
        elapsed_time = self.end_time - self.start_time
        # file size / time yields the speed
        connection_speed = size / elapsed_time
        print "Received file " + self.local_file_name + " (" + str(round(size,4 )) + " Mbs)..." \
            "from " + self.host + " in " + str(round(elapsed_time, 4)) + " at " + str(round(connection_speed, 4)) + " Mbs/second"

    # start the timer for the transfer stats
    def start_timer(self):
        self.start_time = time.time()

    # end the timer for the transfer stats
    def end_timer(self):
        self.end_time = time.time()

    def start_listener(self):
        # initialize and bind the given sockets
        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        connection.bind((self.host, self.port))
        # set blocking to true
        connection.setblocking(True)
        print "RCV listening on port " + str(self.port)

        while True:
            try:
                # wait until the initializing packet is sent with the file name
                file_name, sender_address = connection.recvfrom(self.buffer_size)
                self.local_file_name = file_name
                # start receiving
                is_receiving = True

                # start timing the file transfer
                self.start_timer()

                # receive all the packets until the EOF packet is sent
                while is_receiving:
                    transmission, sender_address = connection.recvfrom(self.buffer_size)
                    packet = pickle.loads(transmission)
                    # Make sure the checksums match
                    if self.calculate_checksum(packet.data) != packet.checksum:
                        # if the checksums don't match, request a retransmission
                        ack = Acknowledgement(self.calculate_checksum(packet.data), True)
                    else:
                        # otherwise add the packet to the local store
                        ack = Acknowledgement(self.calculate_checksum(packet.data), False)
                        self.set_packet(packet.number, packet.data)

                    # marshal and send the acknolwedgement
                    connection.sendto(pickle.dumps(ack), sender_address)

                    # if the server detects the EOF flag stop receiving so another sender
                    # can send and write the file
                    if packet.end_of_file:
                        is_receiving = False
                        self.end_timer()
                        self.write_file(self.local_file_name)
                        self.print_stats()


            except socket.error:
                is_receiving = False
                connection.close()
                sys.exit(1)
            except KeyboardInterrupt:
                connection.close()
                sys.exit(0)

def main():
    if len(sys.argv) < 2:
        print("Usage python ./rcv.py <port_number>")
        sys.exit(1)
    port = int(sys.argv[1])
    server = Server(port)
    server.start_listener()

if __name__ == "__main__":
    main()