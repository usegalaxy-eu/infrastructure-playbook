/*
 * setuid binary for calling cvmfs_config wipecache
 */

#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    // must set the real uid (cvmfs_config checks it)
    setreuid(0, 0);
    if (execle("/usr/bin/cvmfs_config", "cvmfs_config", "wipecache", NULL) < 0)
        perror("cvmfs_wipecache: ");
}
