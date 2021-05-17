###############################################################################
# sender.py
# Name:
# JHED ID:
###############################################################################

from typing import TextIO
from assignment2.sender_receiver.util import PacketHeader, compute_checksum
import sys
import socket
from threading import Timer
import logging

logging.basicConfig(level=logging.DEBUG)

START = 0
END = 1
DATA = 2
ACK = 3
TIMEOUT_INTERVAL = 0.5
MAX_BUFFER = 2048
MAX_DATA_SIZE = 1456 # 1500 - 8 (UDP) - 20 (IP) - 16 (RTP header)

# global timer, attached to the first datagram in the sending window
timer = None

def send_window(sock: socket.socket, seq, receiver_ip, receiver_port, n):
    """send datagrams in `seq`

    Args:
        sock (socket.socket): 
        seq (list): sending window
        n (int): if -1 send all datagrams in `seq`, otherwise send last n datagrams in `seq`
    """
    if not seq:
        return
    # if timeout, re-send all datagrams in `seq`
    global timer
    timer = Timer(TIMEOUT_INTERVAL, send_window, [sock, seq[:], receiver_ip, receiver_port, -1])
    if n == -1:
        for pkt in seq:
            sock.sendto(str(pkt), (receiver_ip, receiver_port))
    else:
        for pkt in seq[-n:]:
            sock.sendto(str(pkt), (receiver_ip, receiver_port))
    timer.start()


def connect(setup, sock: socket.socket, seq_num, receiver_ip, receiver_port):
    """connect or disconnect to the receiver

    Args:
        setup (bool): if True set up connection, otherwise terminate connection
    Returns:
        True if success else False
    """
    # send header to set up or terminate a connection
    header = PacketHeader(type= START if setup else END, seq_num=seq_num, length=0)
    header.checksum = compute_checksum(header)
    send_window(sock, [header], receiver_ip, receiver_port, -1)

    # wait for an ACK
    recv_pkt, address = sock.recvfrom(MAX_BUFFER)
    global timer
    timer.cancel()
    recv_pkt_header = PacketHeader(recv_pkt[:16])
    if recv_pkt_header.type == ACK and recv_pkt_header.seq_num == header.seq_num:
        return True
    else:
        return False

def forward_window(seq: list, n, first = False):
    """slide forward the sending window, read new data, pack it into datagram and push it into `seq`
    `len(seq)` is garanteed to be less or equal to window_size

    Args:
        seq (list): sending window
        n (int): steps to forward
        first (bool, optional): if first time to forward the window (i.e. fill the initial window). Defaults to False.
    """
    if first:
        prev_seq_num = 0 # START
    else :
        prev_seq_num = PacketHeader(seq[-1][:16]).seq_num
    for _ in range(n):
        if not first:
            seq.pop(0)
        data = sys.stdin.read(MAX_DATA_SIZE)
        if not data: # all data read
            return
        pkt_header = PacketHeader(type=DATA, seq_num=prev_seq_num + 1, length=len(data))
        pkt_header.checksum = compute_checksum(pkt_header / data)
        pkt = pkt_header / data
        seq.append(pkt)
        prev_seq_num += 1

def check_cur_ack_num(last_ack_num, ack_seq: set):
    """check and return current acumulative ACK number
    """
    cur_num = last_ack_num
    while True:
        if cur_num + 1 in ack_seq:
            cur_num += 1
        else:
            return cur_num


def sender(receiver_ip, receiver_port, window_size):
    """send data using RTP to receiver
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Set up connection

    while not connect(True, s, 0, receiver_ip, receiver_port):
        continue # Try to connect to the receiver 

    logging.info('Successfully connect to the receiver')

    seq = [] # sequence to be sent
    ack_seq = {0} # received ACK numbers
    forward_window(seq, window_size, True) # fill the sequence with window size
    logging.info('initial sending window filled')

    # Send all data

    last_ack_num = 0 # START
    send_window(s, seq[:], receiver_ip, receiver_port, -1) # use a copy of `seq` since it could change after sending
    s.settimeout(TIMEOUT_INTERVAL * 10)
    # trying to receive all ACKs since for each `seq_num` its coresponding ACK could be received at most (and shoud be) once
    # socket timout indicates that all ACKs have been received, which means all data have been sent successfully
    try: 
        while True:
            recv_pkt, addr = s.recvfrom(MAX_BUFFER)
            header = PacketHeader(recv_pkt[:16])
            if header.type == ACK:
                ack_num = header.seq_num
            else:
                logging.warning('sender received datagram other than ACK')
                continue
            ack_seq.add(ack_num - 1) 
            cur_num = check_cur_ack_num(last_ack_num, ack_seq)
            # if cumulative ack number increase, then forward window and send newly added datagrams, reset timer
            if cur_num > last_ack_num:
                global timer
                timer.cancel()
                forward_window(seq, cur_num - last_ack_num)
                send_window(s, seq[:], receiver_ip, receiver_port, cur_num - last_ack_num)
                last_ack_num = cur_num
    except socket.timeout:
        pass

    # Terminate connection
    while not connect(False, s, last_ack_num + 1, receiver_ip, receiver_port):
        continue

    s.close()

def main():
    """Parse command-line arguments and call sender function """
    if len(sys.argv) != 4:
        sys.exit("Usage: python sender.py [Receiver IP] [Receiver Port] [Window Size] < [message]")
    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    sender(receiver_ip, receiver_port, window_size)

if __name__ == "__main__":
    main()
