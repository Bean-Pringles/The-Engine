import os, strutils, osproc, times

# Preprocess Nim source: convert { } blocks and Python-style syntax to proper Nim
proc preprocessFile(inputFile, outputFile: string) =
  let content = readFile(inputFile)
  let lines = content.splitLines()
  var outLines: seq[string] = @[]
  var indentLevel = 0
  var braceStack: seq[string] = @[]
  
  var i = 0
  while i < lines.len:
    var line = lines[i]
    var trimmed = line.strip()
    
    # Handle triple-quoted strings specially
    if trimmed.contains("print(\"\"\"") or trimmed.contains("print(\'\'\'"):
      let baseIndent = repeat("  ", indentLevel)
      var quoteType = "\"\"\""
      if trimmed.contains("print(\'\'\'"):
        quoteType = "\'\'\'"
      
      # Count how many triple quotes are in this line
      var quoteCount = 0
      var pos = 0
      var temp = trimmed
      while pos < temp.len:
        let idx = temp.find(quoteType, pos)
        if idx >= 0:
          quoteCount += 1
          pos = idx + 3
        else:
          break
      
      # If there are 2 triple quotes, it's a single-line multi-line string
      if quoteCount >= 2:
        # Single line: print("""...""")
        var echoLine = trimmed.replace("print(", "echo ")
        # Remove the closing parenthesis
        if echoLine.endsWith(")"):
          echoLine = echoLine[0..^2]
        outLines.add(baseIndent & echoLine)
        i += 1
        continue
      else:
        # Multi-line triple quote
        var echoLine = trimmed.replace("print(", "echo ")
        # Remove any closing parenthesis on this line
        if echoLine.endsWith(")"):
          echoLine = echoLine[0..^2]
        outLines.add(baseIndent & echoLine)
        i += 1
        
        # Continue reading lines until we find the closing triple quote
        while i < lines.len:
          line = lines[i]
          
          # Check if this line contains the closing triple quote
          if line.contains(quoteType):
            # This line has the closing quotes - apply base indentation and remove )
            let trimmedClosing = line.strip()
            if trimmedClosing == quoteType & ")":
              # Just the closing quotes with )
              outLines.add(baseIndent & quoteType)
            elif trimmedClosing.startsWith(quoteType):
              # Closing quotes at start, possibly with ) after
              outLines.add(baseIndent & quoteType)
            else:
              # Content on same line as closing quotes
              let quotePos = line.find(quoteType)
              if quotePos >= 0:
                outLines.add(line[0..quotePos+2])
              else:
                outLines.add(line)
            i += 1
            break
          else:
            # Middle line - keep as is with original spacing
            outLines.add(line)
            i += 1
        continue
    
    if trimmed.endsWith(";"):
      trimmed = trimmed[0..^2]
    
    if trimmed.len == 0:
      outLines.add("")
      i += 1
      continue
    
    # Convert print() to echo - handle simple cases (non-triple-quote)
    if trimmed.startsWith("print(") and not trimmed.contains("\"\"\"") and not trimmed.contains("\'\'\'"):
      let startIdx = 0
      var parenCount = 0
      var contentStart = 6  # after "print("
      var contentEnd = contentStart
      var j = contentStart
      
      while j < trimmed.len:
        if trimmed[j] == '(':
          parenCount += 1
        elif trimmed[j] == ')':
          if parenCount == 0:
            contentEnd = j
            break
          else:
            parenCount -= 1
        j += 1
      
      if contentEnd > contentStart:
        var content = trimmed[contentStart..<contentEnd]
        
        # Convert + to , (outside of strings)
        var inString = false
        var stringChar = ' '
        var newContent = ""
        
        for k, c in content:
          if (c == '"' or c == '\'') and (k == 0 or content[k-1] != '\\'):
            if not inString:
              inString = true
              stringChar = c
            elif c == stringChar:
              inString = false
          
          if c == '+' and not inString:
            newContent = newContent.strip()
            newContent.add(", ")
          else:
            newContent.add(c)
        
        let indent = repeat("  ", indentLevel)
        let after = if contentEnd + 1 < trimmed.len: trimmed[contentEnd + 1..^1] else: ""
        outLines.add(indent & "echo " & newContent.strip() & after)
        i += 1
        continue
    
    # Convert input() to readLine(stdin)
    if trimmed.contains("input("):
      trimmed = trimmed.replace("input()", "readLine(stdin)")
    
    if trimmed == "}":
      indentLevel = max(0, indentLevel - 1)
      if braceStack.len > 0:
        discard braceStack.pop()
      i += 1
      continue
    
    # Handle } elif, } else, } except as special cases
    if trimmed.startsWith("} elif ") or trimmed.startsWith("} else") or trimmed.startsWith("} except "):
      # Close the previous block
      indentLevel = max(0, indentLevel - 1)
      if braceStack.len > 0:
        discard braceStack.pop()
      
      # Now process the elif/else/except part
      trimmed = trimmed[1..^1].strip()  # Remove the leading }
      
      let indent = repeat("  ", indentLevel)
      if trimmed.endsWith("{"):
        trimmed = trimmed[0..^2].strip() & ":"
        outLines.add(indent & trimmed)
        indentLevel += 1
        braceStack.add("control")
      elif trimmed.endsWith(":"):
        outLines.add(indent & trimmed)
        indentLevel += 1
        braceStack.add("control")
      else:
        outLines.add(indent & trimmed & ":")
        indentLevel += 1
        braceStack.add("control")
      i += 1
      continue
    
    if trimmed.startsWith("}"):
      indentLevel = max(0, indentLevel - 1)
      if braceStack.len > 0:
        discard braceStack.pop()
      trimmed = trimmed[1..^1].strip()
      if trimmed.len == 0:
        i += 1
        continue
    
    # Handle elif, else, except (without leading })
    if trimmed.startsWith("elif ") or trimmed.startsWith("else") or trimmed.startsWith("except "):
      let indent = repeat("  ", indentLevel)
      if trimmed.endsWith("{"):
        trimmed = trimmed[0..^2].strip() & ":"
        outLines.add(indent & trimmed)
        indentLevel += 1
        braceStack.add("control")
      elif trimmed.endsWith(":"):
        outLines.add(indent & trimmed)
        indentLevel += 1
        braceStack.add("control")
      else:
        outLines.add(indent & trimmed & ":")
        indentLevel += 1
        braceStack.add("control")
      i += 1
      continue
    
    if trimmed.endsWith("{"):
      trimmed = trimmed[0..^2].strip()
      let indent = repeat("  ", indentLevel)
      if trimmed.endsWith(")"):
        outLines.add(indent & trimmed & " =")
      else:
        outLines.add(indent & trimmed & ":")
      indentLevel += 1
      braceStack.add("brace")
    else:
      let indent = repeat("  ", indentLevel)
      if trimmed.endsWith("="):
        outLines.add(indent & trimmed)
        indentLevel += 1
        braceStack.add("proc")
      else:
        outLines.add(indent & trimmed)
    
    i += 1
  
  writeFile(outputFile, outLines.join("\n"))

proc compileWindowsExe(sourceFile, exeName: string) =
  let cmd = "nim c -d:release -o:" & exeName & " " & sourceFile
  echo "Running: ", cmd
  echo "----------------------------------------"
  try:
    let (output, exitCode) = execCmdEx(cmd)
    echo output
    echo "----------------------------------------"
    if exitCode == 0:
      echo "Compilation successful!"
    else:
      echo "Compilation failed with exit code: ", exitCode
  except OSError as e:
    echo "Error running Nim compiler: ", e.msg

if paramCount() >= 1:
  let inputFile = paramStr(1)
  var outputFile: string
  var tempFileCreated = false
  
  if paramCount() >= 2 and not paramStr(2).endsWith(".exe"):
    outputFile = paramStr(2)
  else:
    outputFile = getTempDir() / "nim_temp_" & $getTime().toUnix() & ".nim"
    tempFileCreated = true
  
  preprocessFile(inputFile, outputFile)
  echo "Preprocessed ", inputFile, " -> ", outputFile
  
  var exeName: string
  if paramCount() >= 2 and paramStr(2).endsWith(".exe"):
    exeName = paramStr(2)
  elif paramCount() >= 3:
    exeName = paramStr(3)
  else:
    exeName = inputFile.changeFileExt("exe")
  
  compileWindowsExe(outputFile, exeName)
  
  if tempFileCreated:
    try:
      removeFile(outputFile)
      echo "Cleaned up temp file: ", outputFile
    except OSError:
      echo "Warning: Could not delete temp file: ", outputFile
else:
  echo "Usage: preprocessor.exe <input.nim> [output.nim] [output.exe]"
  echo "  If output.nim is omitted, uses a temp file"
  echo "  If output.exe is omitted, creates <input>.exe"