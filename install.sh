#!/bin/zsh
# يثبّت/يحدّث مهمة launchd التي تشغّل الفحص كل 30 دقيقة وعند تسجيل الدخول.
set -e
cd "$(dirname "$0")"
PROJECT="$(pwd)"
LABEL="com.rentwatch.kuwait"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
INTERVAL="${1:-1800}"
mkdir -p "$HOME/Library/LaunchAgents" logs
[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/zsh</string><string>$PROJECT/run.sh</string></array>
  <key>WorkingDirectory</key><string>$PROJECT</string>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$PROJECT/logs/rentwatch.log</string>
  <key>StandardErrorPath</key><string>$PROJECT/logs/rentwatch.err.log</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string></dict>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"
echo "✅ تم التثبيت: $LABEL يعمل كل $((INTERVAL/60)) دقيقة. السجل: $PROJECT/logs/rentwatch.log"
echo "لإلغاء التثبيت: launchctl bootout gui/$(id -u)/$LABEL && rm '$PLIST'"
