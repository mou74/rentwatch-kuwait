#!/bin/zsh
# ينشئ مستودع GitHub عاماً، يرفع المشروع، يفعّل GitHub Pages من مجلد docs ويشغّل أول فحص سحابي.
set -e
cd "$(dirname "$0")"
REPO="${1:-rentwatch-kuwait}"
USER=$(gh api user -q .login)
echo "→ GitHub user: $USER"
if ! gh repo view "$USER/$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" --public --description "RentWatch Kuwait - rental listing monitor"
fi
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$USER/$REPO.git"
git pull --rebase -q origin main 2>/dev/null || true
git push -u origin main
echo "→ enabling GitHub Pages (main → /docs)"
gh api -X POST "repos/$USER/$REPO/pages" -f build_type=legacy -f 'source[branch]=main' -f 'source[path]=/docs' >/dev/null 2>&1 || \
gh api -X PUT  "repos/$USER/$REPO/pages" -f build_type=legacy -f 'source[branch]=main' -f 'source[path]=/docs' >/dev/null 2>&1 || true
sleep 2
gh workflow run watch.yml >/dev/null 2>&1 && echo "→ first cloud run started" || echo "→ (workflow not registered yet, will run on schedule)"
echo
echo "✅ الرابط الذي تفتحه من الموبايل (قد يحتاج دقيقة أو اثنتين لأول مرة):"
gh api "repos/$USER/$REPO/pages" -q .html_url
echo "✅ المستودع: https://github.com/$USER/$REPO"
