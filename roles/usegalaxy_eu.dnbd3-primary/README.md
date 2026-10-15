# DNBD Primary Miscellaneous Role
This role helps setting up a dnbd-primary server, it
- creates directories for tftp, dnbd and http server
- copies a ipxe.efi boot binary file
- templates boot.menu and slx-config

It also contains the embeddable script that can be used to compile a ipxe.efi (usually not needed), see https://github.com/ipxe/ipxe and https://ipxe.org/howto/chainloading
