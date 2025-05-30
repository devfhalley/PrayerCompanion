{pkgs}: {
  deps = [
    pkgs.ffmpeg-full
    pkgs.openjdk
    pkgs.gradle
    pkgs.sqlite
    pkgs.postgresql
    pkgs.portmidi
    pkgs.pkg-config
    pkgs.libpng
    pkgs.libjpeg
    pkgs.freetype
    pkgs.fontconfig
    pkgs.SDL2_ttf
    pkgs.SDL2_mixer
    pkgs.SDL2_image
    pkgs.SDL2
  ];
}
