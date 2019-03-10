{ pkgs ? import <nixpkgs> {}
, interpreter ? "python3"
}:

pkgs."${interpreter}".pkgs.callPackage
  ({ stdenv, python, distlib, ipython, requests }:
   stdenv.mkDerivation {
     name = "user-environment";
     strictDeps = true;
     nativeBuildInputs = [ ipython ];
     buildInputs = [ python distlib requests ];
     SOURCE_DATE_EPOCH = 315532800;
     shellHook = ''
       export prefix=${toString ./.}/inst
       mkdir -p $prefix/lib/python3.7/site-packages
       export PATH=$prefix/bin:$PATH
       export PYTHONPATH=$prefix/lib/python3.7/site-packages:$PYTHONPATH
       # python setup.py develop --prefix=$prefix
     '';
   }) { }
