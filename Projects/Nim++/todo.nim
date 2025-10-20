import std/strutils;
import sequtils;

var notes: seq[string] = @[];

proc runCmd(cmd: string) {
    if cmd == "add" {
        print("What to add? ");
        let thingToAdd = input();
        notes.add(thingToAdd);
    
    } elif cmd == "list" {
        for i, note in notes {
            print($(i + 1) + ". " + note);
        }

    } elif cmd == "remove" {
        print("Enter number to remove: ");
        let input = input().strip();
    
        try {
            let index = parseInt(input) - 1;
            if index >= 0 and index < notes.len {
                notes.delete(index);
                print("Removed");
            } else {
                print("Invalid number");
            }

        } except ValueError {
            print("Please enter a valid number");
        }

    } elif cmd == "help" {
        print(""" 
        
        Available Commands:

            add (Adds an item to the To Do list)
            list (List all items in the To Do List)
            remove (Removes a select item from the To Do list)
            help (Displays information about each command)
            quit (Quits the program)
        """)
    
    } elif cmd == "quit" {
        quit(0);
    
    } else {
        print("Unknown command: " + cmd);
    }
}

while true {
    stdout.write(">>> ");
    stdout.flushFile();  # ensure prompt shows immediately
    let cmd = input().strip();
    runCmd(cmd);
}