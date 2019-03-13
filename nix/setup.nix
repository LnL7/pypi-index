{ pkgs ? import <nixpkgs> {}
, interpreter ? "python3"
, inputs ? builtins.readFile /dev/stdin
}:

let
    mkSetup = args: pkgs."${interpreter}".pkgs.callPackage
      ({ stdenv, fetchurl, unzip, python, pip, wheel, pyyaml, cffi, pbr, setuptools_scm, six }:
      stdenv.mkDerivation {
        name = "setup.json";
        src = fetchurl args.fetchurl;
        buildInputs = [ unzip python pip wheel pyyaml cffi pbr setuptools_scm six ];
        phases = [ "unpackPhase" "installPhase" ];
        installPhase = ''
          cp ${./eval_setup.py} eval_setup.py
          python eval_setup.py --data '${builtins.toJSON args}' > $out
        '';
      }) { };
in

map mkSetup (builtins.fromJSON inputs)
