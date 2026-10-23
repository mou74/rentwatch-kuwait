#!/bin/zsh
LABEL="com.rentwatch.kuwait"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "تم إيقاف وإزالة مهمة $LABEL"
