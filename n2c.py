import nightmare, csv, sys, glob, os

def showExceptionAndExit(exc_type, exc_value, tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Press Enter key to exit.")
    sys.exit(-1)

def process(nmm, rom, outFile):
    # First cell is offset of table in ROM
    headers = [hex(nmm.offset)]
    
    # Generate header row (contains field descriptions)
    for col in nmm.columns:
        headers.append(col.description)
    
    table = [headers]

    for row in range(nmm.rowNum):
        # rowOffset is the offset in ROM of the row data
        rowOffset = nmm.offset + row*nmm.rowLength
        
        # First cell is row/entry name
        try:
            thisRow = [nmm.entryNames[row]]
        
        except IndexError:
            thisRow = [hex(row)]
        
        for entry in nmm.columns:
            # currentOffset is offset in ROM of current field data
            currentOffset = rowOffset + entry.offset
            
            # get int from data
            dt = int.from_bytes(rom[currentOffset:currentOffset+entry.length], 'little', signed = entry.signed)
            
            if (entry.base == 16):
                dt = hex(dt)
            
            thisRow.append(dt)
        
        table.append(thisRow)
    
    # Write table as csv
    with open(outFile, 'w') as myfile:
        wr = csv.writer(myfile, quoting = csv.QUOTE_ALL, lineterminator = '\n')
        wr.writerows(table)

    print("Wrote to " + outFile)

def main():
    sys.excepthook = showExceptionAndExit

    try:
        romFile = sys.argv[1]

    except IndexError:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        romFile = filedialog.askopenfilename(
            title = "Select ROM to rip data from",
            initialdir = os.getcwd(),
            filetypes = [
                ("GBA files", ".gba"),
                ("All files", ".*")
            ]
        )

    (dirname, filename) = os.path.split(romFile)
    
    # generating module list
    moduleList = glob.glob('**/*.nmm', recursive=True)

    # read ROM bytes
    with open(romFile, 'rb') as f:
        romBytes = bytes(f.read())
    
    for nmmFile in moduleList:
        csvFile = nmmFile.replace(".nmm", ".csv") #let's just keep the same file name for now

        try:
            nmm = nightmare.NightmareTable(nmmFile)
            process(nmm, romBytes, csvFile)
        
        except AssertionError as e:
            # NMM is malformed
            print("Error in " + nmmFile + ":\n" + str(e))

    input("Press Enter to continue.")

if __name__ == '__main__':
    main()
