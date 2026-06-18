#!/bin/sh
# Pre-pull Ollama models into the running Ollama server.
#
# Invoked by the `ollama-init` compose service once the `ollama` service is healthy.
# `OLLAMA_HOST` (set in the compose service env) must point at the Ollama server,
# so this script is a *client* — it asks the server to pull into its own (persistent)
# storage rather than downloading anything itself.
#
# `OLLAMA_MODELS` is a space-separated list of model tags
# (default: "gemma4:31b-cloud", the cloud-hosted Gemma 4 31B).
#
# Idempotent: `ollama pull` no-ops for models already present, so re-running on every
# `up` is cheap. Failures are deliberately non-fatal — e.g. a cloud model whose
# `OLLAMA_API_KEY` is not yet configured — so a missing key never blocks the rest of
# the stack from starting. See docs/05-user-guide/docker-deployment-guide.md#ollama.
set -u

models="${OLLAMA_MODELS:-gemma4:31b-cloud}"

echo "[ollama-init] Ollama server: ${OLLAMA_HOST:-<unset>}"
echo "[ollama-init] Pulling models: ${models}"

for model in ${models}; do
    echo "[ollama-init] -> ${model}"
    if ollama pull "${model}"; then
        echo "[ollama-init] ok: ${model}"
    else
        echo "[ollama-init] WARNING: failed to pull '${model}' (continuing)."
        echo "[ollama-init]   Note: running *-cloud models later needs 'ollama signin';"
        echo "[ollama-init]   pulling a cloud model only stores its manifest."
    fi
done

echo "[ollama-init] Done."
