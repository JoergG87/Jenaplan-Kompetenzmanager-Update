#!/bin/bash
set -euo pipefail

APP_NAME="Jenaplan-Kompetenzmanager"
DATA_ROOT="${JENAPLAN_APP_DATA_DIR:-$HOME/Library/Application Support/$APP_NAME}"
DATABASE="$DATA_ROOT/kompetenzmanager.sqlite"
BACKUPS="$DATA_ROOT/backups"

if pgrep -f '/Jenaplan-Kompetenzmanager.app/Contents/MacOS/Jenaplan-Kompetenzmanager' >/dev/null 2>&1; then
    echo "Bitte den Jenaplan-Kompetenzmanager vollständig schließen und das Backup erneut starten." >&2
    exit 1
fi
if [ ! -f "$DATABASE" ]; then
    echo "Keine Benutzerdatenbank gefunden: $DATABASE" >&2
    exit 1
fi
if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "Das macOS-Werkzeug sqlite3 fehlt; es wurde keine Sicherung erstellt." >&2
    exit 1
fi

mkdir -p "$BACKUPS"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
DESTINATION="$BACKUPS/$TIMESTAMP"
STAGING="$BACKUPS/.incomplete-$TIMESTAMP-$$"
if [ -e "$DESTINATION" ]; then
    echo "Die Sicherung existiert bereits und wird nicht überschrieben: $DESTINATION" >&2
    exit 1
fi
mkdir "$STAGING"
cleanup() {
    if [ -d "$STAGING" ]; then
        rm -rf "$STAGING"
    fi
}
trap cleanup EXIT

sqlite3 "$DATABASE" ".backup '$STAGING/kompetenzmanager.sqlite'"
if [ -d "$DATA_ROOT/documents" ]; then
    ditto "$DATA_ROOT/documents" "$STAGING/documents"
else
    mkdir "$STAGING/documents"
fi
{
    echo "Jenaplan-Kompetenzmanager Pilot-Backup"
    echo "Erstellt: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "Quelle: $DATA_ROOT"
    echo "Inhalt: kompetenzmanager.sqlite, documents/"
} > "$STAGING/BACKUP_INFO.txt"

mv "$STAGING" "$DESTINATION"
trap - EXIT
echo "Backup vollständig erstellt:"
echo "$DESTINATION"
