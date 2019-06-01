{ pkgs ? import <nixpkgs> {}
, interpreter ? "python3"
, inputs
}:

let
  mkSetup = args: pkgs."${interpreter}".pkgs.callPackage
    ({ stdenv, fetchurl, unzip, python, pip, wheel, distlib, pyyaml, cffi, pbr, setuptools_scm, six }:
    let isWheel = stdenv.lib.hasSuffix ".whl" args.fetchurl.url; in
    stdenv.mkDerivation {
      name = "${args.name}-${args.version}.json";
      src = fetchurl args.fetchurl;
      buildInputs = [ unzip python pip wheel pyyaml cffi pbr setuptools_scm six ]
        ++ stdenv.lib.optional isWheel distlib;
      phases = [ "unpackPhase" "installPhase" ];
      unpackPhase = stdenv.lib.optionalString isWheel ''
        cp $src ''${src#*-}
      '';
      installPhase = ''
        printFailure() {
            echo >&2
            echo "error: running setup.py for ${args.name}==${args.version} failed" >&2
            echo >&2
            echo >&2
        }
        failureHooks+=" printFailure"

      '' + stdenv.lib.optionalString isWheel ''
        cp ${./eval_dist.py} eval_dist.py
        python eval_dist.py $out --data '${builtins.toJSON args}'
      '' + stdenv.lib.optionalString (!isWheel) ''
        cp ${./eval_setup.py} eval_setup.py
        python eval_setup.py $out --data '${builtins.toJSON args}'
      '';
    }) { };
in

map mkSetup (builtins.fromJSON inputs)
