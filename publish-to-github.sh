#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo 'Usage: bash publish-to-github.sh https://github.com/YOUR_USER/AI-Novel-Studio.git'
  echo 'Create an EMPTY PRIVATE repository on GitHub first. Do not include README.'
  exit 2
fi
repo="$1"
if [[ ! "$repo" =~ ^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+\.git$ ]]; then
  echo 'ERROR: Expected https://github.com/OWNER/REPO.git'
  exit 2
fi
cd "$(dirname "$0")"
if [[ -d .git ]]; then
  echo 'ERROR: .git already exists. Do not overwrite an existing Git history.'
  exit 2
fi
git init
git add .
git commit -m 'Initialize AI Novel Studio story continuity system'
git branch -M main
git remote add origin "$repo"
echo "Publishing to: $repo"
git push -u origin main
