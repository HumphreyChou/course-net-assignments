###############################################################################
# receiver.py
# Name:
# JHED ID:
###############################################################################

import sys
import socket
import logging

logging.basicConfig(level=logging.DEBUG)

from assignment2.sender_receiver.util import PacketHeader, compute_checksum

START = 0
END = 1
DATA = 2
ACK = 3
TIMEOUT_INTERVAL = 0.5
MAX_BUFFER = 2048

def check_cur_ack_num(last_ack_num, ack_seq: set):
    """check and return current acumulative ACK number
    """
    cur_num = last_ack_num
    while True:
        if cur_num + 1 in ack_seq:
            cur_num += 1
        else:
            return cur_num

def forward_window(seq: list, n):
    """forward receiving window by n steps, which means print the first n messages to stdout
    after forwarding, `seq` (i.e. window) should be empty (filled with None)
    """
    for msg in seq[:n]:
        sys.stdout.write(msg)
    sys.stdout.flush()

    for i in range(len(seq)):
        seq[i] = None

def receiver(receiver_port, window_size):
    """Listen on socket and print received message to sys.stdout"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('127.0.0.1', receiver_port))

    connected = False # indicate whether the receiver has connected to a certain sender
    s.settimeout(TIMEOUT_INTERVAL * 10)

    while True:
        try:
            # Caution: this RTP does not provide a 3-way handshake machenism, which could cause problem when setting up connection
            # if `connected` is set to be True but its ACK to the sender is lost, the receiver would not be able to receive any data
            # or set up any connections at all
            # to solve this, I set sock timeout interval to be large and close connection if timeout (see implementation below)
            pkt, address = s.recvfrom(2048)

            # extract header and payload
            pkt_header = PacketHeader(pkt[:16])
            msg = pkt[16:16+pkt_header.length]

            # verify checksum
            pkt_checksum = pkt_header.checksum
            pkt_header.checksum = 0
            computed_checksum = compute_checksum(pkt_header / msg)
            if pkt_checksum != computed_checksum:
                logging.info('RECV: checksum does not match, drop')
                continue

            # Set up connection
            if pkt_header.type == START:
                if not connected:
                    connected = True
                    last_ack_num = 0
                    seq = [None] * window_size
                    ack_seq = {0}
                    ack_pkt = PacketHeader(type=ACK, seq_num=pkt_header.seq_num, length=0)
                    ack_pkt.checksum = compute_checksum(ack_pkt)
                    s.sendto(str(ack_pkt), address)

                else:
                    logging.info('RECV: ignore another connection')
                continue
            
            # Terminate connection
            if pkt_header.type == END:
                if not connected:
                    logging.warning('RECV: not connected but received END')
                else:
                    connected = False
                    ack_pkt = PacketHeader(type=ACK, seq_num=pkt_header.seq_num, length=0)
                    ack_pkt.checksum = compute_checksum(ack_pkt)
                    s.sendto(str(ack_pkt), address)
                continue
            
            # Receive data
            seq_num = pkt_header.seq_num
            if seq_num in ack_seq :
                logging.info('RECV: duplicated data')
                continue
            if seq_num - last_ack_num > window_size: 
                logging.info('RECV: datagram overflows receiving window, drop')
                continue
            # buffer new data
            ack_seq.add(seq_num)
            seq[seq_num - last_ack_num - 1] = msg
            # forward window if possible and update last ack number
            cur_ack_num = check_cur_ack_num(last_ack_num, ack_seq)
            if cur_ack_num > last_ack_num:
                forward_window(seq, cur_ack_num - last_ack_num)
                last_ack_num = cur_ack_num
            # send back ACK
            ack_pkt = PacketHeader(type=ACK, seq_num=last_ack_num + 1, length=0)
            ack_pkt.checksum = compute_checksum(ack_pkt)
            s.sendto(str(ack_pkt), address) 
            
        except socket.timeout:
            connected = False

def main():
    """Parse command-line argument and call receiver function """
    if len(sys.argv) != 3:
        sys.exit("Usage: python receiver.py [Receiver Port] [Window Size]")
    receiver_port = int(sys.argv[1])
    window_size = int(sys.argv[2])
    receiver(receiver_port, window_size)

if __name__ == "__main__":
    main()
