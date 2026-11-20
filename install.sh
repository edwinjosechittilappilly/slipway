#!/usr/bin/env bash
# Slipway bootstrap: prerequisites, the `slipway` CLI, then `slipway install`.
#
#   Public repo:
#     curl -fsSL https://raw.githubusercontent.com/edwinjosechittilappilly/slipway/main/install.sh | bash
#   Private repo (uses your gh login):
#     gh api repos/edwinjosechittilappilly/slipway/contents/install.sh -H "Accept: application/vnd.github.raw" | bash
#   Pass flags after `bash -s --`, e.g. preview first:
#     ... | bash -s -- --dry-run
#   From a clone:
#     ./install.sh [--profile <name>] [--packs a,b] [--dry-run]
#
# --dry-run changes nothing: it says what the bootstrap would install, then previews `slipway install` from a
# temporary clone. Environment: SLIPWAY_REPO (owner/repo), SLIPWAY_HOME (checkout, default ~/.slipway).
set -euo pipefail

REPO="${SLIPWAY_REPO:-edwinjosechittilappilly/slipway}"
DRY=0
for arg in "$@"; do
  [ "$arg" = "--dry-run" ] && DRY=1
done

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }
would() { printf '  would: %s\n' "$*"; }
die() {
  printf '\033[31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

case "$(uname -s)" in
  Darwin | Linux) ;;
  *) die "Slipway supports macOS and Linux." ;;
esac

# 1. Find or choose the checkout. Running ./install.sh from a clone uses that clone.
script_dir=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$script_dir" ] && [ -f "$script_dir/slipway.toml" ]; then
  SLIPWAY_HOME="$script_dir"
else
  SLIPWAY_HOME="${SLIPWAY_HOME:-$HOME/.slipway}"
fi
export SLIPWAY_HOME

# 2. Homebrew is the one package manager Slipway relies on (macOS and Linux).
brew_bin() {
  local candidate
  for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew /home/linuxbrew/.linuxbrew/bin/brew; do
    [ -x "$candidate" ] && { echo "$candidate"; return 0; }
  done
  command -v brew 2>/dev/null
}

# New terminals must find brew-installed tools (gh, node, bd, openspec). The Homebrew installer only prints this
# step, so do it here, once, in the login file of the user's shell.
persist_brew_path() {
  local brew="$1" rc line
  case "${SHELL:-}" in
    */zsh) rc="$HOME/.zprofile" ;;
    */bash) rc="$HOME/.bash_profile" ;;
    *) rc="$HOME/.profile" ;;
  esac
  line="eval \"\$($brew shellenv)\""
  if ! grep -qsF "$line" "$rc"; then
    printf '\n# Homebrew (added by Slipway)\n%s\n' "$line" >>"$rc"
    say "Added Homebrew to $rc; open a new terminal (or run: $line)"
  fi
}

brew="$(brew_bin || true)"
if [ -z "$brew" ]; then
  if [ "$DRY" = 1 ]; then
    would "install Homebrew (asks for your password once) and add it to your shell profile"
  else
    say "Installing Homebrew (it asks for your password once)"
    installer="$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || die "cannot download Homebrew"
    if [ -r /dev/tty ]; then
      /bin/bash -c "$installer" </dev/tty || die "Homebrew install failed"
    else
      NONINTERACTIVE=1 /bin/bash -c "$installer" || die "Homebrew install failed"
    fi
    brew="$(brew_bin)" || die "Homebrew installed but not found"
  fi
fi
if [ -n "$brew" ]; then
  eval "$("$brew" shellenv)"
  [ "$DRY" = 1 ] || persist_brew_path "$brew"
fi

# 3. Prerequisites the CLI needs before it can manage anything else.
missing=()
for tool in git gh node uv; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [ "${#missing[@]}" -gt 0 ]; then
  if [ "$DRY" = 1 ]; then
    would "brew install ${missing[*]}"
  else
    say "Installing ${missing[*]}"
    HOMEBREW_NO_ENV_HINTS=1 brew install "${missing[@]}"
  fi
fi

clone() {
  local dest="$1"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo clone "$REPO" "$dest" -- --quiet --depth 1
  else
    git clone --quiet --depth 1 "https://github.com/$REPO.git" "$dest" ||
      die "clone failed. For a private repo run 'gh auth login' first."
  fi
}

# 4. Dry run: preview `slipway install` from the checkout (or a temporary clone) and stop.
if [ "$DRY" = 1 ]; then
  preview_home="$SLIPWAY_HOME"
  if [ ! -f "$preview_home/slipway.toml" ]; then
    would "clone $REPO into $SLIPWAY_HOME"
    command -v git >/dev/null 2>&1 || die "git is needed for the preview; install it, or run without --dry-run"
    preview_home="$(mktemp -d)/slipway"
    trap 'rm -rf "$(dirname "$preview_home")"' EXIT
    clone "$preview_home"
  fi
  would "uv tool install --editable $SLIPWAY_HOME   (puts \`slipway\` on your PATH)"
  say "Preview of: slipway install $*"
  export SLIPWAY_HOME="$preview_home" PYTHONPATH="$preview_home/src"
  if command -v uv >/dev/null 2>&1; then
    exec uv run --no-project --quiet --python ">=3.11" python -m slipway install "$@"
  elif python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    exec python3 -m slipway install "$@"
  else
    say "Install uv (brew install uv) or Python 3.11+ to preview the component list."
    exit 0
  fi
fi

# 5. Clone if needed.
if [ ! -f "$SLIPWAY_HOME/slipway.toml" ]; then
  say "Cloning $REPO into $SLIPWAY_HOME"
  clone "$SLIPWAY_HOME"
  git -C "$SLIPWAY_HOME" fetch --quiet --unshallow 2>/dev/null || true
fi

# 6. The CLI: an editable uv tool, so `git pull` in the checkout updates it.
say "Installing the slipway CLI from $SLIPWAY_HOME"
uv tool install --quiet --force --editable "$SLIPWAY_HOME"
bin_dir="$(uv tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *)
    export PATH="$bin_dir:$PATH"
    uv tool update-shell >/dev/null 2>&1 || true
    say "Added $bin_dir to your shell PATH; new terminals pick it up"
    ;;
esac

# 7. Everything else is declared in slipway.toml.
say "slipway install $*"
status=0
"$bin_dir/slipway" install "$@" || status=$?
say "Done. Open a new terminal (or run: exec \$SHELL -l), then: slipway doctor"
exit "$status"
