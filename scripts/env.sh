# Node.js PATH for local dev scripts (run.sh, build.sh, start-dashboard-local.sh).
# Edit for your machine. Do not commit personal paths unless updating the project default.
#
# Default: user-local Node 20 tarball under ~/.local.
# nvm/apt/fnm: comment out the block below if node/npm are already on PATH.

NODE_BIN="${HOME}/.local/node-v20.18.0-linux-x64/bin"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="${NODE_BIN}:${PATH}"
fi

# Alternatives (pick one, comment out the block above):
# export PATH="/path/to/node/bin:${PATH}"
