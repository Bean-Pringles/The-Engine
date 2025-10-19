import std/strutils;
import sequtils

var notes: seq[string] = @[];

proc runCmd(cmd: string) {
    if cmd == "add" {
        echo "What to add? ";
        let thingToAdd = readLine(stdin);
        notes.add(thingToAdd);
    
    } elif cmd == "list" {
        for i, note in notes {
            echo $(i + 1), ". ", note;
        }

    } elif cmd == "remove" {
        echo "Enter number to remove: ";
        let input = readLine(stdin).strip();
    
        try {
            let index = parseInt(input) - 1;
            if index >= 0 and index < notes.len {
                notes.delete(index);
                echo "Removed";
            } else {
                echo "Invalid number";
            }

        } except ValueError {
            echo "Please enter a valid number";
        }

    } elif cmd == "help" {
        echo """ 
        
        Available Commands:

            add (Adds an item to the To Do list)
            list (List all items in the To Do List)
            remove (Removes a select item from the To Do list)
            help (Displays information about each command)
            quit (Quits the program)
        """
    
    } elif cmd == "quit" {
        quit(0);
    
    } else {
        echo "Unknown command: ", cmd;
    }
}

while true {
    stdout.write(">>> ");
    stdout.flushFile();  # ensure prompt shows immediately
    let cmd = readLine(stdin).strip();
    runCmd(cmd);
}