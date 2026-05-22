{
  description = "GeoTUI - Midnight Commander-style TUI for GeoServer management";

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
            pythonPkgs.cryptography
            pythonPkgs.keyring
            pythonPkgs.pytest
            pythonPkgs.pytest-asyncio
            pythonPkgs.pytest-cov
            pythonPkgs.pytest-bdd
            pythonPkgs.babel
            pythonPkgs.hatchling
            pythonPkgs.ruff
            pythonPkgs.mypy
            pythonPkgs.bandit
            pythonPkgs.pillow
            pythonPkgs.fpdf2
            pythonPkgs.click

            # Docs
            pythonPkgs.mkdocs
            pythonPkgs.mkdocs-material
            pythonPkgs.mkdocstrings

            # Tools
            pkgs.pre-commit
            pkgs.gh
            pkgs.gettext
            pkgs.codespell
            pkgs.docker
            pkgs.docker-compose
          ];

          shellHook = ''
            echo "GeoTUI development environment"
            echo "  Run:        python -m geotui"
            echo "  Test:       pytest"
            echo "  Lint:       ruff check src/ tests/"
            echo "  Format:     ruff format src/ tests/"
            echo "  Types:      mypy src/ --ignore-missing-imports"
            echo "  Security:   bandit -r src/ -c pyproject.toml"
            echo "  Docs:       cd docs && mkdocs serve"
            echo "  CI local:   ./scripts/ci-local.sh"
            echo ""
            echo "  GeoServer:  ./scripts/geoserver-up.sh    (start test instance)"
            echo "              ./scripts/geoserver-down.sh   (stop and destroy)"
            echo "              ./scripts/geoserver-status.sh (check status)"
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

        packages.default = pythonPkgs.buildPythonPackage {
          pname = "geotui";
          version = "1.0.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = [ pythonPkgs.hatchling ];

          propagatedBuildInputs = [
            pythonPkgs.textual
            pythonPkgs.rich
            pythonPkgs.httpx
            pythonPkgs.pydantic
            pythonPkgs.pydantic-settings
            pythonPkgs.cryptography
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
