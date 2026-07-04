on run argv
    if (count of argv) is not 1 then
        error "Usage: osascript scripts/import_vba_sources_to_seed.applescript <seed.xlsm>"
    end if

    set seedPath to item 1 of argv
    set seedAlias to POSIX file seedPath

    tell application "Microsoft Excel"
        set targetWorkbook to (open workbook workbook file name seedAlias)
        activate object targetWorkbook
        run VB macro "ImportVbaSourcesToSeedFromRepo"
        save targetWorkbook
        close targetWorkbook saving yes
    end tell
end run
