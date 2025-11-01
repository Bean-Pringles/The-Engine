import std/[json, os, tables, strutils, times, osproc, strformat]

const
  CONFIG_DIR = "Termpile"
  CONFIG_FILE = CONFIG_DIR / "toolbox.json"
  BACKUP_DIR = "Backups"

type
  FileEntry = object
    path: string
    alias: string
    project: string
    created: string

  Config = object
    projects: Table[string, seq[FileEntry]]
    aliases: Table[string, string] # alias -> project mapping

proc loadConfig(): Config =
  result = Config()
  result.projects = initTable[string, seq[FileEntry]]()
  result.aliases = initTable[string, string]()
  
  if fileExists(CONFIG_FILE):
    let data = parseFile(CONFIG_FILE)
    if data.hasKey("projects"):
      for project, entries in data["projects"].pairs:
        var fileEntries: seq[FileEntry] = @[]
        for entry in entries.items:
          fileEntries.add(FileEntry(
            path: entry["path"].getStr,
            alias: entry["alias"].getStr,
            project: entry["project"].getStr,
            created: entry["created"].getStr
          ))
        result.projects[project] = fileEntries
    
    if data.hasKey("aliases"):
      for alias, project in data["aliases"].pairs:
        result.aliases[alias] = project.getStr

proc saveConfig(config: Config) =
  createDir(CONFIG_DIR)
  
  var data = newJObject()
  var projectsObj = newJObject()
  
  for project, entries in config.projects.pairs:
    var entriesArr = newJArray()
    for entry in entries:
      var entryObj = newJObject()
      entryObj["path"] = %entry.path
      entryObj["alias"] = %entry.alias
      entryObj["project"] = %entry.project
      entryObj["created"] = %entry.created
      entriesArr.add(entryObj)
    projectsObj[project] = entriesArr
  
  var aliasesObj = newJObject()
  for alias, project in config.aliases.pairs:
    aliasesObj[alias] = %project
  
  data["projects"] = projectsObj
  data["aliases"] = aliasesObj
  
  writeFile(CONFIG_FILE, data.pretty)

proc newProject(name: string) =
  var config = loadConfig()
  
  if config.projects.hasKey(name):
    echo "Project '", name, "' already exists"
    return
  
  config.projects[name] = @[]
  saveConfig(config)
  echo "Created project: ", name

proc addFile(project, filePath, alias: string) =
  var config = loadConfig()
  
  if not config.projects.hasKey(project):
    echo "Project '", project, "' does not exist. Create it first with 'toolbox new ", project, "'"
    return
  
  # Check if alias already exists globally
  if config.aliases.hasKey(alias):
    echo "Alias '", alias, "' already exists in project '", config.aliases[alias], "'"
    return
  
  let absolutePath = if filePath.isAbsolute: filePath else: getCurrentDir() / filePath
  
  if not fileExists(absolutePath):
    echo "File not found: ", absolutePath
    return
  
  let entry = FileEntry(
    path: absolutePath,
    alias: alias,
    project: project,
    created: $now()
  )
  
  config.projects[project].add(entry)
  config.aliases[alias] = project
  saveConfig(config)
  echo "Added '", alias, "' -> '", absolutePath, "' to project '", project, "'"

proc resolveProject(project: string) =
  var config = loadConfig()
  
  if not config.projects.hasKey(project):
    echo "Project '", project, "' does not exist"
    return
  
  let entries = config.projects[project]
  for entry in entries:
    if fileExists(entry.path):
      try:
        removeFile(entry.path)
        echo "Deleted: ", entry.path
      except:
        echo "Failed to delete: ", entry.path
    config.aliases.del(entry.alias)
  
  config.projects[project] = @[]
  saveConfig(config)
  echo "Resolved project: ", project

proc listProject(project: string) =
  let config = loadConfig()
  
  if not config.projects.hasKey(project):
    echo "Project '", project, "' does not exist"
    return
  
  let entries = config.projects[project]
  if entries.len == 0:
    echo "Project '", project, "' has no files"
    return
  
  echo "Files in project '", project, "':"
  for entry in entries:
    let exists = if fileExists(entry.path): "✓" else: "✗"
    echo "  [", exists, "] ", entry.alias, " -> ", entry.path

proc viewFile(alias: string) =
  let config = loadConfig()
  
  if not config.aliases.hasKey(alias):
    echo "Alias '", alias, "' not found"
    return
  
  let project = config.aliases[alias]
  var filePath = ""
  
  for entry in config.projects[project]:
    if entry.alias == alias:
      filePath = entry.path
      break
  
  if filePath == "" or not fileExists(filePath):
    echo "File not found for alias '", alias, "'"
    return
  
  # Try common text editors
  when defined(windows):
    discard execCmd("notepad \"" & filePath & "\"")
  elif defined(macosx):
    discard execCmd("open -e \"" & filePath & "\"")
  else:
    # Try common Linux editors
    if execCmd("which nano > /dev/null 2>&1") == 0:
      discard execCmd("nano \"" & filePath & "\"")
    elif execCmd("which vim > /dev/null 2>&1") == 0:
      discard execCmd("vim \"" & filePath & "\"")
    else:
      echo "No text editor found. File path: ", filePath

proc removeAlias(alias: string) =
  var config = loadConfig()
  
  if not config.aliases.hasKey(alias):
    echo "Alias '", alias, "' not found"
    return
  
  let project = config.aliases[alias]
  var newEntries: seq[FileEntry] = @[]
  var removedPath = ""
  
  for entry in config.projects[project]:
    if entry.alias != alias:
      newEntries.add(entry)
    else:
      removedPath = entry.path
      if fileExists(entry.path):
        try:
          removeFile(entry.path)
          echo "Deleted file: ", entry.path
        except:
          echo "Failed to delete file: ", entry.path
  
  config.projects[project] = newEntries
  config.aliases.del(alias)
  saveConfig(config)
  echo "Removed alias: ", alias

proc deleteProject(project: string) =
  var config = loadConfig()
  
  if not config.projects.hasKey(project):
    echo "Project '", project, "' does not exist"
    return
  
  # Remove all aliases for this project
  for entry in config.projects[project]:
    config.aliases.del(entry.alias)
  
  config.projects.del(project)
  saveConfig(config)
  echo "Deleted project: ", project

proc renameProject(oldName, newName: string) =
  var config = loadConfig()
  
  if not config.projects.hasKey(oldName):
    echo "Project '", oldName, "' does not exist"
    return
  
  if config.projects.hasKey(newName):
    echo "Project '", newName, "' already exists"
    return
  
  var entries = config.projects[oldName]
  for i in 0..<entries.len:
    entries[i].project = newName
    config.aliases[entries[i].alias] = newName
  
  config.projects[newName] = entries
  config.projects.del(oldName)
  saveConfig(config)
  echo "Renamed project '", oldName, "' to '", newName, "'"

proc backupProject(project: string) =
  let config = loadConfig()
  
  if not config.projects.hasKey(project):
    echo "Project '", project, "' does not exist"
    return
  
  let backupPath = BACKUP_DIR / project
  createDir(backupPath)
  
  for entry in config.projects[project]:
    if fileExists(entry.path):
      let (_, _, ext) = splitFile(entry.path)
      let destPath = backupPath / entry.alias & ext
      copyFile(entry.path, destPath)
      echo "Backed up: ", entry.alias, " -> ", destPath
  
  echo "Backed up project: ", project

proc backupAlias(alias: string) =
  let config = loadConfig()
  
  if not config.aliases.hasKey(alias):
    echo "Alias '", alias, "' not found"
    return
  
  let project = config.aliases[alias]
  createDir(BACKUP_DIR)
  
  for entry in config.projects[project]:
    if entry.alias == alias and fileExists(entry.path):
      let destPath = BACKUP_DIR / alias & splitFile(entry.path).ext
      copyFile(entry.path, destPath)
      echo "Backed up: ", alias, " -> ", destPath
      return

proc restoreProject(project: string) =
  let config = loadConfig()
  
  if not config.projects.hasKey(project):
    echo "Project '", project, "' does not exist"
    return
  
  let backupPath = BACKUP_DIR / project
  if not dirExists(backupPath):
    echo "No backup found for project: ", project
    return
  
  for entry in config.projects[project]:
    let backupFile = backupPath / entry.alias & splitFile(entry.path).ext
    if fileExists(backupFile):
      copyFile(backupFile, entry.path)
      echo "Restored: ", entry.alias, " -> ", entry.path

proc restoreAlias(alias: string) =
  let config = loadConfig()
  
  if not config.aliases.hasKey(alias):
    echo "Alias '", alias, "' not found"
    return
  
  let project = config.aliases[alias]
  
  for entry in config.projects[project]:
    if entry.alias == alias:
      let backupFile = BACKUP_DIR / alias & splitFile(entry.path).ext
      if fileExists(backupFile):
        copyFile(backupFile, entry.path)
        echo "Restored: ", alias, " -> ", entry.path
      else:
        echo "No backup found for alias: ", alias
      return

proc showHelp() =
  echo """
Toolbox - Temp File Manager

Commands:
  toolbox new <project>                  - Create a new project
  toolbox add <project> <file> <alias>   - Add a file to project with alias
  toolbox resolve <project>              - Delete all files and entries in project
  toolbox list <project>                 - List all files in project
  toolbox view <alias>                   - Open file in text editor
  toolbox remove <alias>                 - Remove alias and delete file
  toolbox delete <project>               - Delete project (keeps files)
  toolbox rename <old> <new>             - Rename project
  toolbox backup <project|alias>         - Backup project or alias
  toolbox restore <project|alias>        - Restore project or alias from backup
  toolbox help                           - Show this help
"""

proc main() =
  let args = commandLineParams()
  
  if args.len == 0:
    showHelp()
    return
  
  case args[0]
  of "new":
    if args.len < 2:
      echo "Usage: toolbox new <project>"
      return
    newProject(args[1])
  
  of "add":
    if args.len < 4:
      echo "Usage: toolbox add <project> <file> <alias>"
      return
    addFile(args[1], args[2], args[3])
  
  of "resolve":
    if args.len < 2:
      echo "Usage: toolbox resolve <project>"
      return
    resolveProject(args[1])
  
  of "list":
    if args.len < 2:
      echo "Usage: toolbox list <project>"
      return
    listProject(args[1])
  
  of "view":
    if args.len < 2:
      echo "Usage: toolbox view <alias>"
      return
    viewFile(args[1])
  
  of "remove":
    if args.len < 2:
      echo "Usage: toolbox remove <alias>"
      return
    removeAlias(args[1])
  
  of "delete":
    if args.len < 2:
      echo "Usage: toolbox delete <project>"
      return
    deleteProject(args[1])
  
  of "rename":
    if args.len < 3:
      echo "Usage: toolbox rename <old> <new>"
      return
    renameProject(args[1], args[2])
  
  of "backup":
    if args.len < 2:
      echo "Usage: toolbox backup <project|alias>"
      return
    let config = loadConfig()
    if config.projects.hasKey(args[1]):
      backupProject(args[1])
    elif config.aliases.hasKey(args[1]):
      backupAlias(args[1])
    else:
      echo "Project or alias '", args[1], "' not found"
  
  of "restore":
    if args.len < 2:
      echo "Usage: toolbox restore <project|alias>"
      return
    let config = loadConfig()
    if config.projects.hasKey(args[1]):
      restoreProject(args[1])
    elif config.aliases.hasKey(args[1]):
      restoreAlias(args[1])
    else:
      echo "Project or alias '", args[1], "' not found"
  
  of "help", "-h", "--help":
    showHelp()
  
  else:
    echo "Unknown command: ", args[0]
    showHelp()

when isMainModule:
  main()