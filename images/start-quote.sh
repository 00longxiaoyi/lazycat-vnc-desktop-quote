#!/bin/bash
# One isolated profile per Lazycat instance; never put business data in $HOME.
set -euo pipefail
umask 077
# Do not fill the persistent export directory with crash dumps.
ulimit -c 0
uid=${LAZYCAT_APP_DEPLOY_UID:?LAZYCAT_APP_DEPLOY_UID must identify this user instance}
if [[ ! "$uid" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo 'Invalid Lazycat deployment UID' >&2
    exit 1
fi
root="/lzcapp/var/users/$uid"
export QUOTE_DATA_DIR="$root/quote-desktop"
export QUOTE_EXPORT_DIR="$root/exports"
mkdir -p "$QUOTE_DATA_DIR" "$QUOTE_EXPORT_DIR" "$HOME/Desktop"
# All launch paths use this lock: desktop double-click cannot create two writers.
exec 9>"$root/quote.lock"
flock -n 9 || exit 0
ln -sfn "$QUOTE_EXPORT_DIR" "$HOME/Desktop/报价导出（持久保存）"
ln -sfn "$QUOTE_DATA_DIR" "$HOME/Desktop/报价数据（请勿手动修改）"
# GTK file dialogs and file manager shortcuts also lead to persistent storage.
for directory in Documents Downloads; do
    # Kasm creates an empty Downloads directory before XFCE starts.
    if [[ -d "$HOME/$directory" && ! -L "$HOME/$directory" ]]; then
        rmdir "$HOME/$directory" 2>/dev/null || true
    fi
    if [[ ! -e "$HOME/$directory" || -L "$HOME/$directory" ]]; then
        ln -sfn "$QUOTE_EXPORT_DIR" "$HOME/$directory"
    fi
done
cd "$QUOTE_EXPORT_DIR"
exec /opt/quote-desktop/quote-desktop --no-sandbox --disable-dev-shm-usage "$@" >"$root/startup.log" 2>&1
