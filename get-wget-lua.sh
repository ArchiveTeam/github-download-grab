#!/bin/bash
#
# This script downloads and compiles wget-lua.
#

# first, try to detect gnutls or openssl
CONFIGURE_SSL_OPT=""
if builtin type -p pkg-config &>/dev/null
then
  if pkg-config gnutls
  then
    echo "Compiling wget with GnuTLS."
    CONFIGURE_SSL_OPT="--with-ssl=gnutls"
  elif pkg-config openssl
  then
    echo "Compiling wget with OpenSSL."
    CONFIGURE_SSL_OPT="--with-ssl=openssl"
  fi
fi

TARFILE=wget-lua-1.14.8-e8a24.tar.bz2
TARDIR=wget-1.14.8-e8a24

rm -rf $TARFILE $TARDIR/

wget --no-check-certificate https://github.com/downloads/ArchiveTeam/cinch-grab/$TARFILE
tar xjf $TARFILE
cd $TARDIR/
if ./configure $CONFIGURE_SSL_OPT --disable-nls && make && src/wget -V | grep -q lua
then
  cp src/wget ../wget-lua
  cd ../
  echo
  echo
  echo "###################################################################"
  echo
  echo "wget-lua successfully built."
  echo
  ./wget-lua --help | grep -iE "gnu|warc|lua"
  rm -rf $TARFILE $TARDIR/
else
  echo
  echo "wget-lua not successfully built."
  echo
fi

