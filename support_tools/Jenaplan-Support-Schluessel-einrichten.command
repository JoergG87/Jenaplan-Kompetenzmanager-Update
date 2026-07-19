#!/bin/zsh

set -u

SCRIPT_DIR="${0:A:h}"
EXECUTABLE="$SCRIPT_DIR/bin/Jenaplan-Support-Schluessel-einrichten"
SOURCE_ENTRY="$SCRIPT_DIR/keypair_cli.py"

if [[ -x "$EXECUTABLE" ]]; then
    "$EXECUTABLE"
    EXIT_STATUS=$?
elif [[ -f "$SOURCE_ENTRY" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import cryptography' >/dev/null 2>&1; then
        python3 "$SOURCE_ENTRY"
        EXIT_STATUS=$?
    else
        print -u2 "Die Python-Abhängigkeit cryptography fehlt. Bitte das vollständige Supportpaket verwenden."
        EXIT_STATUS=126
    fi
else
    print -u2 "Das sichere Einrichtungswerkzeug oder seine Laufzeit fehlt. Bitte das Supportpaket erneut bereitstellen."
    EXIT_STATUS=127
fi

print
if [[ "$EXIT_STATUS" -eq 0 ]]; then
    print "Die Schlüsseleinrichtung wurde erfolgreich beendet."
else
    print "Die Schlüsseleinrichtung wurde mit Exitcode $EXIT_STATUS beendet."
fi
if [[ -t 0 ]]; then
    read -r "?Zum Schließen des Fensters die Eingabetaste drücken … "
fi
exit "$EXIT_STATUS"
