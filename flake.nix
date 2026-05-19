{
  description = "GeoTUI - Midnight Commander-style TUI for geospatial server management";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        pythonPkgs = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pythonPkgs.pip
            pythonPkgs.virtualenv
            pythonPkgs.textual
            pythonPkgs.rich
            pythonPkgs.httpx
            pythonPkgs.pydantic
            pythonPkgs.pydantic-settings
            pythonPkgs.keyring
            pythonPkgs.pytest
            pythonPkgs.pytest-asyncio
            pythonPkgs.pytest-cov
            pythonPkgs.pytest-bdd
            pythonPkgs.babel
            pythonPkgs.hatchling
            pythonPkgs.ruff
            pythonPkgs.mypy

            # Docs
            pythonPkgs.mkdocs
            pythonPkgs.mkdocs-material
            pythonPkgs.mkdocstrings

            # Tools
            pkgs.pre-commit
            pkgs.gh
            pkgs.gettext
          ];

          shellHook = ''
            echo "Welcome to GeoTUI development environment"
            echo "  Run: python -m geotui"
            echo "  Test: pytest"
            echo "  Docs: mkdocs serve"
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

        packages.default = pythonPkgs.buildPythonPackage {
          pname = "geotui";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = [ pythonPkgs.hatchling ];

          propagatedBuildInputs = [
            pythonPkgs.textual
            pythonPkgs.rich
            pythonPkgs.httpx
            pythonPkgs.pydantic
            pythonPkgs.pydantic-settings
            pythonPkgs.keyring
          ];
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/geotui";
        };

        apps.docs = {
          type = "app";
          program = let
            script = pkgs.writeShellScriptBin "geotui-docs" ''
              cd ${./.}/docs && ${pythonPkgs.mkdocs}/bin/mkdocs serve
            '';
          in "${script}/bin/geotui-docs";
        };

        apps.test = {
          type = "app";
          program = let
            script = pkgs.writeShellScriptBin "geotui-test" ''
              cd ${./.} && ${pythonPkgs.pytest}/bin/pytest
            '';
          in "${script}/bin/geotui-test";
        };

        apps.lint = {
          type = "app";
          program = let
            script = pkgs.writeShellScriptBin "geotui-lint" ''
              cd ${./.} && ${pythonPkgs.ruff}/bin/ruff check src/ tests/
            '';
          in "${script}/bin/geotui-lint";
        };
      });
}
