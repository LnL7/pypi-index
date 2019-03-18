{ pkgs ? import <nixpkgs> {}
, interpreter ? "python3"
, inputs
}:

let
    mkSetup = args: pkgs."${interpreter}".pkgs.callPackage
      ({ stdenv, fetchurl, unzip, python, pip, wheel, pyyaml, cffi, pbr, setuptools_scm, six }:
      stdenv.mkDerivation {
        name = "${args.name}-${args.version}.json";
        src = fetchurl args.fetchurl;
        buildInputs = [ unzip python pip wheel pyyaml cffi pbr setuptools_scm six ];
        phases = [ "unpackPhase" "installPhase" ];
        installPhase = ''
          printFailure() {
              echo >&2
              echo "error: running setup.py for ${args.name}==${args.version} failed" >&2
              echo >&2
              echo >&2
          }
          failureHooks+=" printFailure"

          cp ${./eval_setup.py} eval_setup.py
          python eval_setup.py --data '${builtins.toJSON args}' > $out
        '';
      }) { };
in

map mkSetup (builtins.fromJSON inputs)
