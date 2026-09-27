#!/usr/bin/env bash
set -euo pipefail
: "${DEPLOY_SSH_KEY:?}"
: "${DEPLOY_KNOWN_HOSTS:?}"
: "${DEPLOY_NAME:?}"
: "${DEPLOY_TARGET:?}"
: "${DEPLOY_USER:?}"
[[ "$DEPLOY_NAME" =~ ^(theread|mashrute|company|ihaa)$ ]]
[[ "$DEPLOY_TARGET" =~ ^[a-zA-Z0-9.-]+$ ]]
[[ "$DEPLOY_USER" =~ ^[a-zA-Z0-9-]+$ ]]
credentials=$(mktemp -d)
trap 'rm -rf "$credentials"' EXIT
chmod 700 "$credentials"
printf '%s\n' "$DEPLOY_SSH_KEY" > "$credentials/key"
printf '%s\n' "$DEPLOY_KNOWN_HOSTS" > "$credentials/known_hosts"
chmod 600 "$credentials/key" "$credentials/known_hosts"
cat > "$credentials/config" <<EOF
Host relay
    HostName 100.109.94.54
    User relay-$DEPLOY_NAME
Host destination
    HostName $DEPLOY_TARGET
    User $DEPLOY_USER
    ProxyJump relay
Host *
    IdentityFile $credentials/key
    IdentitiesOnly yes
    IdentityAgent none
    BatchMode yes
    StrictHostKeyChecking yes
    UserKnownHostsFile $credentials/known_hosts
    ConnectTimeout 30
    ServerAliveInterval 15
    ServerAliveCountMax 8
EOF
ssh -F "$credentials/config" destination deploy | tee "$credentials/result"
grep -Eq '^DEPLOYED_REVISION=[0-9a-f]{40}$' "$credentials/result"
