#!/bin/zsh
# يشغّل فحصاً واحداً. يُستدعى من launchd كل 30 دقيقة.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
exec .venv/bin/python -m rentwatch run "$@"
