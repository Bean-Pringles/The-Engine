import os, strutils, osproc, times

# Preprocess Nim source: convert { } blocks to proper Nim indentation
proc preprocessFile(inputFile, outputFile: string) =
  let lines = readFile(inputFile).splitLines()
  var outLines: seq[string] = @[]
  var indentLevel = 0
  var braceStack: seq[string] = @[]
  
  for line in lines:
    var trimmed = line.strip()
    
    if trimmed.endsWith(";"):
      trimmed = trimmed[0..^2]
    
    if trimmed.len == 0:
      outLines.add("")
      continue
    
    if trimmed == "}":
      indentLevel = max(0, indentLevel - 1)
      if braceStack.len > 0:
        discard braceStack.pop()
      continue
    
    if trimmed.startsWith("}"):
      indentLevel = max(0, indentLevel - 1)
      if braceStack.len > 0:
        discard braceStack.pop()
      trimmed = trimmed[1..^1].strip()
      if trimmed.len == 0:
        continue
    
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