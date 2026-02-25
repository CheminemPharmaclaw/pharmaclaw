#!/bin/bash
# PharmaClaw Deploy Script — seamless switch between GitHub Pages and Netlify
#
# Usage:
#   ./scripts/deploy.sh              # Deploy to current target (default: github)
#   ./scripts/deploy.sh github       # Deploy to GitHub Pages
#   ./scripts/deploy.sh netlify      # Deploy to Netlify
#   ./scripts/deploy.sh switch       # Toggle between the two
#   ./scripts/deploy.sh status       # Show current deploy target

set -e

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$WORKSPACE/.deploy-target"
SITE_SOURCE="$WORKSPACE/pharmaclaw/index.html"

# Default target
if [ -f "$CONFIG_FILE" ]; then
    CURRENT_TARGET=$(cat "$CONFIG_FILE")
else
    CURRENT_TARGET="github"
fi

deploy_github() {
    echo "🚀 Deploying to GitHub Pages (main branch, root /)..."
    cd "$WORKSPACE"
    
    # Copy site to root index.html (GitHub Pages serves from /)
    cp "$SITE_SOURCE" "$WORKSPACE/index.html"
    
    # Ensure we're on main or can push to it
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        git stash 2>/dev/null || true
        git checkout main
        git checkout "$CURRENT_BRANCH" -- pharmaclaw/index.html
        cp pharmaclaw/index.html index.html
    fi
    
    git add index.html
    if git diff --cached --quiet; then
        echo "✅ No changes to deploy."
    else
        git commit -m "Deploy site update to GitHub Pages"
        git push origin main
        echo "✅ Pushed to GitHub Pages. Live at https://pharmaclaw.com in ~60s."
    fi
    
    # Switch back if needed
    if [ "$CURRENT_BRANCH" != "main" ]; then
        git checkout "$CURRENT_BRANCH"
        git stash pop 2>/dev/null || true
    fi
}

deploy_netlify() {
    echo "🚀 Deploying to Netlify..."
    cd "$WORKSPACE"
    
    # Netlify config
    NETLIFY_TOML="$WORKSPACE/pharmaclaw/netlify.toml"
    if [ ! -f "$NETLIFY_TOML" ]; then
        cat > "$NETLIFY_TOML" << 'EOF'
[build]
  publish = "."
  command = ""

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
EOF
        echo "Created netlify.toml"
    fi
    
    # Check if netlify CLI is available
    if command -v netlify &>/dev/null; then
        cd "$WORKSPACE/pharmaclaw"
        netlify deploy --prod --dir=.
        echo "✅ Deployed to Netlify."
    else
        # Fallback: just push to git (if Netlify is connected to repo)
        git add pharmaclaw/
        if git diff --cached --quiet; then
            echo "✅ No changes to deploy."
        else
            git commit -m "Deploy site update (Netlify)"
            git push origin main
            echo "✅ Pushed to repo. Netlify will auto-deploy if connected."
        fi
    fi
}

case "${1:-deploy}" in
    github)
        echo "github" > "$CONFIG_FILE"
        deploy_github
        ;;
    netlify)
        echo "netlify" > "$CONFIG_FILE"
        deploy_netlify
        ;;
    switch)
        if [ "$CURRENT_TARGET" = "github" ]; then
            NEW_TARGET="netlify"
        else
            NEW_TARGET="github"
        fi
        echo "$NEW_TARGET" > "$CONFIG_FILE"
        echo "🔄 Switched deploy target: $CURRENT_TARGET → $NEW_TARGET"
        echo "Run './scripts/deploy.sh' to deploy to $NEW_TARGET"
        ;;
    status)
        echo "📍 Current deploy target: $CURRENT_TARGET"
        echo "   Config: $CONFIG_FILE"
        echo "   Source: $SITE_SOURCE"
        if [ "$CURRENT_TARGET" = "github" ]; then
            echo "   GitHub Pages: main branch, root /"
            echo "   URL: https://pharmaclaw.com"
        else
            echo "   Netlify: pharmaclaw/ directory"
            echo "   URL: https://pharmaclaw.com"
        fi
        ;;
    deploy|"")
        if [ "$CURRENT_TARGET" = "netlify" ]; then
            deploy_netlify
        else
            deploy_github
        fi
        ;;
    *)
        echo "Usage: deploy.sh [github|netlify|switch|status]"
        exit 1
        ;;
esac
