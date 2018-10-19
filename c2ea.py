import sys, csv, os, re
import nightmare, csv, glob

TABLE_INLINED = False

def showExceptionAndExit(exc_type, exc_value, tb):
    import traceback

    traceback.print_exception(exc_type, exc_value, tb)
    sys.exit(-1)

def generateInstaller(installerName, csvList, includeTableDefinitions):
    """
    Takes a list of csv files and adds them to the EA installer
    """

    with open(installerName, "w") as file:
        file.write("// EA Table Master Installer file generated by c2ea\n\n")

        if includeTableDefinitions:
            file.write('#include "Table Definitions.txt"\n\n')

        for csv in csvList:
            # get event file name from csv name (TODO: pass the event file list directly?)
            filename = csv.replace(".csv", ".event")

            # get relative path to event from the installer directory
            filename = os.path.relpath(filename, os.path.dirname(installerName))

            # write include directive
            file.write('#include "{}"\n\n'.format(filename))

class BadCellError(Exception):
    def __init__(self, csv, row, col, desc):
        self.csv  = csv
        self.row  = row
        self.col  = col
        self.desc = desc

    def csvName(self):
        return self.csv

    def errDesc(self):
        return self.desc

    def rowIndex(self):
        return self.row

    def colIndex(self):
        return self.col

    def __str__(self):
        return "`{}` row {:d}: {}".format(self.csv, self.row, self.desc)

    def __repr__(self):
        return self.__str__()

def identifierFromAnyString(filename):
    """
    Takes a string and returns a suitable EA identifier.
    All this really does is replace problematic characters with '_'.
    """

    # regular expression object is cached, so performance of this should be okay
    return re.sub(r'[^0-9A-Za-z_]', '_', filename)

def getCodeLengthFromNmmEntry(nmmEntry):
    """
    Takes the nmm entry object and returns the length of the appropriate EA code.
    This isn't necessarily equal to nmmEntry.length, as alignment also has to be taken into account.
    """

    if (nmmEntry.length == 4) & (nmmEntry.offset % 4 == 0):
        return 4
    elif (nmmEntry.length == 2) & (nmmEntry.offset % 2 == 0):
        return 2
    else:
        return 1

def getEACodeFromLength(length):
    """
    Takes a code length and returns the appropriate EA code.
    """

    if length == 4:
        return "WORD"
    elif length == 2:
        return "SHORT"
    else:
        return "BYTE"

def getMacroDefinition(macroName, nmm):
    """
    retuns a macro definition of the given name corresponding to the entries of the given nmm object
    """

    currentCodeLength = 0 # because we start with nothing

    macroArgs  = [] # list of argument names for the definition
    macroCodes = [] # list of codes for the definition

    for i, entry in enumerate(nmm.columns):
        argString = "__arg{:03d}".format(i)
        macroArgs.append(argString)

        length = getCodeLengthFromNmmEntry(entry)

        # only append a new code if the previous code wasn't the same.
        if length != currentCodeLength:
            currentCodeLength = length
            macroCodes.append(getEACodeFromLength(length))

        # add argument to the last (current) code in the list
        macroCodes[-1] += ' {}'.format(argString)

    return '#define {0}({1}) "{2}"'.format(macroName, ','.join(macroArgs), ';'.join(macroCodes))

def intToEALiteral(intValue):
    """
    converts integer to an EA literal string representing it
    """

    return '{:d}'.format(intValue) if (intValue < 100) else '${:X}'.format(intValue)

def process(inputCSV, inputNMM, filename, rom):
    """
    Takes a csv and nmm and spits out an EA event file.
    Returns the rom (in case it has been prompted for and updated)
    """

    global TABLE_INLINED

    macroName = "_C2EA_{}".format(identifierFromAnyString(os.path.splitext(os.path.basename(inputCSV))[0]))
    nmm = nightmare.NightmareTable(inputNMM)

    macroDefinition = getMacroDefinition(macroName, nmm)

    outputLines = [] # list of event lines (full macro invocation)
    tableConfig = '' # this gets changed to whatever is in the first cell of the csv

    doFillEmptyWithZero = None

    with open(inputCSV, 'r') as csvFile:
        table = csv.reader(csvFile)

        tableConfig = next(table)[0]

        for rowIndex, row in enumerate(table):
            lineEntries = [] # each macro argument in order

            for entryIndex, (entry, cell) in enumerate(zip(nmm.columns, row[1:])):
                cellEntry = ''

                # If cell is empty, prompt for what to do
                if cell == '':
                    if doFillEmptyWithZero == None:
                        doFillEmptyWithZero = input(
                            "Warning: `{}` has a blank cell!\n"
                            "Continue anyway? Fills cells with '0' (y/n)".format(inputCSV)
                        ).strip().lower()=='y'

                    if doFillEmptyWithZero:
                        cell = '0'

                    else:
                        raise BadCellError(inputCSV, rowIndex+2, entryIndex+2, "Cell is empty!")

                # If it is a "standard" entry type, we can allow complex expressions and what not
                if entry.length == getCodeLengthFromNmmEntry(entry):
                    try:
                        intValue = int(cell, base = 0) & ((1 << 8*entry.length)-1)
                        cellEntry = intToEALiteral(intValue)

                    except ValueError:
                        cellEntry = '({})'.format(cell)

                # This entry has mutiple parts (bytes) to it, we can only unpack a literal integer here
                # (if entry.length != getCodeLengthFromNmmEntry(entry); then getCodeLengthFromNmmEntry(entry) == 1)
                else:
                    try:
                        bytelist = int(cell, base = 0).to_bytes(entry.length, 'little', signed = entry.signed)

                    except ValueError:
                        raise BadCellError(inputCSV, rowIndex+2, entryIndex+2, "Cell contains non-literal expression for non-trivial NMM entry!")

                    cellEntry = ' '.join(map(lambda x: intToEALiteral(x), bytelist))

                lineEntries.append(cellEntry)

            outputLines.append("{}({})".format(macroName, ','.join(lineEntries)))

    with open(filename, 'w') as outFile:
        inline = False
        outFile.write('{}\n\n'.format(macroDefinition))

        if tableConfig.strip()[0:6] == 'INLINE':
            from c2eaPfinder import pointerOffsets

            inline        = True
            TABLE_INLINED = True

            if rom == None:
                import tkinter as tk

                root = tk.Tk()
                root.withdraw()

                from tkinter import filedialog

                rom = filedialog.askopenfilename(
                    filetypes=[("GBA files", ".gba"), ("All files", ".*")],
                    initialdir = os.getcwd(),
                    title = "Select ROM to use for repointing"
                )

            label = identifierFromAnyString(tableConfig.replace("INLINE",'').strip())

            # Here we do *not* want to use PFinder

            outFile.write("PUSH\n")

            for offset in pointerOffsets(rom, nmm.offset | 0x8000000):
                outFile.write("ORG ${:X}\n".format(offset))
                outFile.write("POIN {}\n".format(label))

            outFile.write("POP\n")

            # There, much better :)

            outFile.write("ALIGN 4\n{}:\n".format(label))

        else:
            outFile.write("PUSH\nORG " + tableConfig + "\n")

        outFile.write('\n'.join(outputLines))

        if not inline:
            outFile.write("\nPOP")

        outFile.write('\n')

    return rom

def main():
    sys.excepthook = showExceptionAndExit

    rom = None

    doSingleFile = False

    folder = os.getcwd()
    installer = "Table Installer.event"

    noTableDefinitions = False

    csvFile   = None
    nmmFile   = None
    outFile   = None

    quiet = False

    if len(sys.argv) > 1:
        import argparse

        parser = argparse.ArgumentParser(description = 'Convert CSV file(s) to EA events using NMM file(s) as reference. Defaults to looking for CSVs in the current directory. You can specify a directory to look in using -folder, or you can switch to processing singles CSVs using -csv.')

        # Common arguments
        parser.add_argument('rom', nargs='?', help = 'reference ROM (for pointer searching)')
        # parser.add_argument('--nocache') # sounds like no$ xd
        # parser.add_argument('--clearcache')
        parser.add_argument('-q', '--quiet', action = "store_true", help = 'disables console output')

        # Arguments for single CSV processing
        parser.add_argument('-csv', help = 'CSV for single csv processing')
        parser.add_argument('-nmm', help = '(use with -csv) reference NMM (default: [CSVFile]:.csv=.nmm)')
        parser.add_argument('-out', help = '(use with -csv) output event (default: [CSVFile]:.csv=.event)')

        # Arguments for folder processing
        parser.add_argument('-folder', help = 'folder to look for csvs in')
        parser.add_argument('-installer', help = 'output installer event (default: [Folder]/Table Installer.event)')

        parser.add_argument('--no-definitions', action = "store_true", help = 'disables installer including "Table Definitions.txt"')

        args = parser.parse_args()

        rom = args.rom

        if args.quiet:
            quiet = True

        if args.csv != None:
            if (args.folder != None) or (args.installer != None):
                sys.exit("ERROR: -folder or -installer argument specified with -csv, aborting.")

            doSingleFile = True

            csvFile = args.csv
            nmmFile = args.nmm if args.nmm != None else csvFile.replace(".csv", ".nmm")
            outFile = args.out if args.out != None else csvFile.replace(".csv", ".event")

        else:
            if (args.nmm != None) or (args.out != None):
                sys.exit("ERROR: -nmm or -out argument specified without -csv, aborting.")

            if args.folder != None:
                folder = args.folder

            if args.no_definitions:
                noTableDefinitions = True

            installer = args.installer if args.installer != None else (folder + '/Table Installer.event')

    try:
        if doSingleFile:
            if not os.path.exists(csvFile):
                sys.exit("ERROR: CSV File `{}` doesn't exist!".format(csvFile))

            if not os.path.exists(nmmFile):
                sys.exit("ERROR: NMM File `{}` doesn't exist!".format(nmmFile))

            process(csvFile, nmmFile, outFile, rom)

            if not quiet:
                print("Wrote to {}".format(outFile))

        else: # not doSingleFile
            csvList = glob.glob(folder + '/**/*.csv', recursive = True)

            for filename in csvList:
                rom = process(
                    filename,
                    filename.replace(".csv", ".nmm"),
                    filename.replace(".csv", ".event"),
                    rom
                )

                if not quiet:
                    print("Wrote to {}".format(filename.replace(".csv", ".event")))

            generateInstaller(installer, csvList, not noTableDefinitions)

    except BadCellError as e:
        sys.exit("ERROR: in csv `{}`, row {}, column {}:\n  {}".format(
            e.csvName(), e.rowIndex(), e.colIndex(), e.errDesc()
        ))

    if TABLE_INLINED:
        # If we ran successfully and used pfinder, save the pfinder cache.
        from c2eaPfinder import writeCache
        writeCache()

    if not quiet:
        input("Press Enter to continue\n")

if __name__ == '__main__':
    main()
