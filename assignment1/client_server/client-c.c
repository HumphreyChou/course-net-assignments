/*****************************************************************************
 * client-c.c
 * Name:
 * JHED ID:
 *****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netdb.h>
#include <netinet/in.h>
#include <errno.h>

#define SEND_BUFFER_SIZE 2048


/* TODO: client()
 * Open socket and send message from stdin.
 * Return 0 on success, non-zero on failure
*/
int client(char *server_ip, char *server_port) {
  // create socket
  int sock = 0;
  if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
  {
    perror("socket failed");
    exit(EXIT_FAILURE);
  }

  // create server address
  struct sockaddr_in serv_addr;
  memset(&serv_addr, '0', sizeof(serv_addr));
  serv_addr.sin_family = AF_INET;
  serv_addr.sin_port = htons(atoi(server_port));

  // convert IPv4 and IPv6 addresses from text to binary form
  if(inet_pton(AF_INET, server_ip, &serv_addr.sin_addr)<=0)
  {
    perror("address failed");
    exit(EXIT_FAILURE);
  }

  // connect to server
  if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
  {
    perror("connect failed");
    exit(EXIT_FAILURE);
  }

  // send data
  char buffer[SEND_BUFFER_SIZE];
  int n;
  while((n = read(STDIN_FILENO, buffer, SEND_BUFFER_SIZE)) > 0) {
    int n_sent = 0;
    while(n_sent < n) {
      int res = send(sock, buffer + n_sent, n - n_sent, 0);
      if(res < 0) {
        // send failed, probably blocked by other clients
        // just re-send and DO NOT exit
        res = 0; 
      } 
      n_sent += res;
    }
  }


  // close socket
  close(sock);

  return 0;
}

/*
 * main()
 * Parse command-line arguments and call client function
*/
int main(int argc, char **argv) {
  char *server_ip;
  char *server_port;

  if (argc != 3) {
    fprintf(stderr, "Usage: ./client-c [server IP] [server port] < [message]\n");
    exit(EXIT_FAILURE);
  }

  server_ip = argv[1];
  server_port = argv[2];
  return client(server_ip, server_port);
}
