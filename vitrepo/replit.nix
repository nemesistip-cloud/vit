{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.lcms2
    pkgs.freetype
    pkgs.openjpeg
    pkgs.libwebp
    pkgs.libtiff
    pkgs.libjpeg
    pkgs.zlib
    pkgs.postgresql
    pkgs.pkg-config
    pkgs.openssl
  ];
}
