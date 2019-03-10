{ pkgs ? import <nixpkgs> {}
, interpreter ? "python3"
, files ? []
}:

let
    mkSetup = file: pkgs."${interpreter}".pkgs.callPackage
      ({ stdenv, fetchurl, unzip, python, pip, wheel, pyyaml, cffi, pbr, setuptools_scm, six }:
      let query = builtins.fromJSON (builtins.readFile file); in
      stdenv.mkDerivation {
        name = "setup.json";
        src = fetchurl query.fetchurl;
        buildInputs = [ unzip python pip wheel pyyaml cffi pbr setuptools_scm six ];
        phases = [ "unpackPhase" "installPhase" ];
        installPhase = ''
          cp ${./eval_setup.py} eval_setup.py
          python eval_setup.py > $out
        '';
      }) { };
in

map mkSetup files
