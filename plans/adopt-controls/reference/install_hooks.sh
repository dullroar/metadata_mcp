#!/usr/bin/env bash
# Install the secret-guard pre-commit and pre-push hooks in this repository.
#
# Run me when: I cloned a repository, or the hooks are missing (check with --check).
#
# Usage: install_hooks.sh [--check | --self-test]
#   (no option)   install the hooks in the common Git directory, so that all worktrees use them
#   --check       exit 1 if a hook is missing or is not ours
#   --self-test   install in a disposable repository and prove that both hooks and the chain work
#
# An existing hook that is not ours moves to <hook>.local. Our hook calls it after the guard,
# with the same arguments and stdin. Running the installer twice changes nothing.
# The hooks use scripts/secret_guard.py of the repository. If it is absent, they use $SECRET_GUARD.
set -euo pipefail

MARKER="# secret-guard hook v1 (installed by scripts/install_hooks.sh)"
HOOKS=(pre-commit pre-push)

hook_body() {
  cat <<'COMMON'
#!/bin/sh
COMMON
  printf '%s\n' "$MARKER"
  cat <<'COMMON'
# Do not edit. Put a local hook in <this hook>.local. This hook calls it after the guard.
top=$(git rev-parse --show-toplevel) || exit 2
guard="$top/scripts/secret_guard.py"
[ -f "$guard" ] || guard="${SECRET_GUARD:-}"
if [ -z "$guard" ] || [ ! -f "$guard" ]; then
  echo "secret-guard: scripts/secret_guard.py not found. Set SECRET_GUARD to the runner copy." >&2
  exit 1
fi
local_hook="$(dirname "$0")/$(basename "$0").local"
COMMON
  case "$1" in
    pre-commit)
      cat <<'HOOK'
python3 "$guard" --staged || exit 1
if [ -x "$local_hook" ]; then exec "$local_hook" "$@"; fi
exit 0
HOOK
      ;;
    pre-push)
      cat <<'HOOK'
input=$(mktemp) || exit 2
trap 'rm -f "$input"' EXIT
cat >"$input"
while read -r local_ref local_sha remote_ref remote_sha; do
  [ -n "$local_sha" ] || continue
  case "$local_sha" in *[!0]*) ;; *) continue ;; esac
  case "$remote_sha" in
    *[!0]*)
      if git cat-file -e "$remote_sha^{commit}" 2>/dev/null; then
        python3 "$guard" --range "$remote_sha..$local_sha" </dev/null || exit 1
      else
        python3 "$guard" --new-ref "$local_sha" </dev/null || exit 1
      fi
      ;;
    *) python3 "$guard" --new-ref "$local_sha" </dev/null || exit 1 ;;
  esac
done <"$input"
if [ -x "$local_hook" ]; then "$local_hook" "$@" <"$input"; exit $?; fi
exit 0
HOOK
      ;;
  esac
}

hooks_dir() {
  local dir
  dir=$(git rev-parse --git-path hooks) || { echo "install_hooks: not a Git repository" >&2; exit 2; }
  # --git-path gives the common hooks directory for a worktree, and respects core.hooksPath.
  case "$dir" in /*) ;; *) dir="$(pwd)/$dir" ;; esac
  printf '%s\n' "$dir"
}

is_ours() { [ -f "$1" ] && grep -qxF "$MARKER" "$1"; }

install() {
  local dir hook path
  dir=$(hooks_dir)
  mkdir -p "$dir"
  for hook in "${HOOKS[@]}"; do
    path="$dir/$hook"
    if [ -e "$path" ] && ! is_ours "$path"; then
      if [ -e "$path.local" ]; then
        echo "install_hooks: $path and $path.local both exist. Merge them by hand." >&2
        exit 2
      fi
      mv "$path" "$path.local"
      echo "install_hooks: kept the old $hook as $hook.local"
    fi
    if ! { [ -f "$path" ] && cmp -s "$path" <(hook_body "$hook"); }; then
      hook_body "$hook" >"$path.tmp"
      mv "$path.tmp" "$path"
      echo "install_hooks: installed $hook"
    fi
    [ -x "$path" ] || chmod +x "$path"
  done
}

check() {
  local dir hook path rc=0
  dir=$(hooks_dir)
  for hook in "${HOOKS[@]}"; do
    path="$dir/$hook"
    if ! [ -x "$path" ] || ! cmp -s "$path" <(hook_body "$hook"); then
      echo "install_hooks: $hook is missing, not executable or not ours: $path" >&2
      rc=1
    fi
  done
  return "$rc"
}

self_test() {
  local here guard tmp rc=0
  here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  guard="$here/secret_guard.py"
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' RETURN
  export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
  export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
  export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
  export SECRET_GUARD="$guard"
  fail() { echo "self-test FAIL: $*" >&2; rc=1; }

  git init -q --bare "$tmp/remote.git"
  git init -q -b main "$tmp/repo"
  cd "$tmp/repo"
  git remote add origin "$tmp/remote.git"
  printf '#!/bin/sh\necho "args=$*" >"%s/chain.log"\ncat >>"%s/chain.log"\n' "$tmp" "$tmp" >.git/hooks/pre-push
  chmod +x .git/hooks/pre-push

  bash "$here/install_hooks.sh" >/dev/null || fail "first install"
  local before after
  before=$(cat .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/pre-push.local | cksum)
  bash "$here/install_hooks.sh" >/dev/null || fail "second install"
  after=$(cat .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/pre-push.local | cksum)
  [ "$before" = "$after" ] || fail "second install changed the hooks"
  grep -q 'chain.log' .git/hooks/pre-push.local || fail "old pre-push not kept as pre-push.local"
  bash "$here/install_hooks.sh" --check || fail "--check after install"

  # A fake key, built from parts so that this file holds no secret.
  local fake="sk-""ant-""$(printf 'Q%.0s' $(seq 1 40))"

  echo "clean" >clean.txt
  git add clean.txt
  git commit -q -m clean || fail "clean commit was refused"
  echo "key = $fake" >leak.txt
  git add leak.txt
  if git commit -q -m leak 2>/dev/null; then fail "pre-commit let a secret in"; fi
  git rm -q --cached leak.txt && rm leak.txt

  git worktree add -q -b wt "$tmp/wt"
  echo "key = $fake" >"$tmp/wt/leak.txt"
  git -C "$tmp/wt" add leak.txt
  if git -C "$tmp/wt" commit -q -m leak 2>/dev/null; then fail "pre-commit did not run in a worktree"; fi

  git push -q origin main 2>/dev/null || fail "clean push was refused"
  grep -q "args=origin $tmp/remote.git" "$tmp/chain.log" 2>/dev/null || fail "pre-push.local did not get the arguments"
  grep -q "refs/heads/main" "$tmp/chain.log" 2>/dev/null || fail "pre-push.local did not get stdin"

  echo "key = $fake" >leak.txt
  git add leak.txt
  git commit -q --no-verify -m "add leak"
  git rm -q leak.txt
  git commit -q -m "remove leak"
  rm -f "$tmp/chain.log"
  if git push -q origin main 2>/dev/null; then fail "pre-push let a secret in an earlier commit of the range"; fi
  [ ! -e "$tmp/chain.log" ] || fail "pre-push.local ran after the guard failed"

  git checkout -q -b topic
  if git push -q origin topic 2>/dev/null; then fail "pre-push let a secret in on a new branch"; fi

  rm .git/hooks/pre-commit
  if bash "$here/install_hooks.sh" --check 2>/dev/null; then fail "--check passed with a missing hook"; fi

  cd /
  if [ "$rc" -eq 0 ]; then echo "install_hooks self-test: ok"; fi
  return "$rc"
}

case "${1:-}" in
  "") install ;;
  --check) check ;;
  --self-test) self_test ;;
  *) echo "usage: install_hooks.sh [--check | --self-test]" >&2; exit 2 ;;
esac
