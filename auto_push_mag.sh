#!/bin/bash
# Auto-push mag-otc index.html to GitHub Pages
# Runs every 60s via launchd. Only pushes when there are uncommitted changes.

cd ~/mag-otc || exit 1

# Remove stale lock (older than 5 minutes), skip if fresh
if [ -f .git/index.lock ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f %m .git/index.lock) ))
    if [ "$LOCK_AGE" -gt 300 ]; then
        echo "$(date): Removing stale lock (${LOCK_AGE}s old)"
        rm -f .git/index.lock
    else
        echo "$(date): Skipping - git lock active (${LOCK_AGE}s old)"
        exit 0
    fi
fi

# Only push if index.html has uncommitted changes
if git status --porcelain | grep -q 'index.html'; then
    git add index.html
    git commit -m "Auto update: $(date +%Y-%m-%d)"
    git push
    echo "$(date): ✅ Pushed to GitHub Pages"
else
    echo "$(date): No changes"
fi
