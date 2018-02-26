/*
 * setuid binary for calling cvmfs_talk remount sync
 */

#include <stdarg.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/un.h>
#include <dirent.h>
#include <stdbool.h>

#define CVMFS_SOCK_PREFIX "/var/lib/cvmfs/shared/cvmfs_io."
#define CVMFS_REPO_DIR "/etc/cvmfs/keys"
#define CVMFS_TALK_COMMAND "remount sync"

void pdie(char *msg) {
  perror(msg);
  exit(1);
}

void die(char *msg, ...) {
  va_list args;
  va_start(args, msg);
  vprintf(msg, args);
  va_end(args);
  exit(1);
}

bool checkrepo(char *repo) {
  DIR *dir;
  struct dirent *ent;
  bool r = false;
  char crt[UNIX_PATH_MAX + 4];

  if ((dir = opendir(CVMFS_REPO_DIR)) == NULL)
    pdie("opendir() failed");

  snprintf(crt, UNIX_PATH_MAX + 4, "%s.crt", repo);

  while ((ent = readdir(dir)))
    if (!strcmp(ent->d_name, crt))
      r = true;

  closedir(dir);

  return r;
}

int main(int argc, char *argv[]) {
  int fd;
  struct sockaddr_un addr;
  char response[512];
  ssize_t bytes;

  if (argc < 2)
    die("usage: %s <repo>\n", argv[0]);

  if ((strlen(CVMFS_SOCK_PREFIX) + strlen(argv[1])) > UNIX_PATH_MAX)
    die("error: repo name exceeds max length of %i\n", UNIX_PATH_MAX);

  if (!checkrepo(argv[1]))
    die("error: invalid repo: %s\n", argv[1]);

  if ((fd = socket(AF_UNIX, SOCK_STREAM, 0)) < 0)
    pdie("error: socket() failed");

  addr.sun_family = AF_UNIX;
  snprintf(addr.sun_path, UNIX_PATH_MAX, "%s%s", CVMFS_SOCK_PREFIX, argv[1]);

  //printf("connecting to socket: %s\n", addr.sun_path);

  if (connect(fd, (struct sockaddr *)&addr, sizeof(struct sockaddr_un)) < 0)
    pdie("error: connect() failed");

  write(fd, CVMFS_TALK_COMMAND, strlen(CVMFS_TALK_COMMAND));
  bytes = read(fd, response, 512);
  close(fd);

  response[bytes] = '\0';
  printf(response);

  return 0;
}
