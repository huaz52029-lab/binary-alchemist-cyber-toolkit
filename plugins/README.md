# Plugins

Drop plugin folders here. Each plugin must contain at least:

```text
my_plugin/
├── plugin.json   # required manifest (name, version, entry, ...)
├── main.py       # entry module defining one or more BaseTool subclasses
└── README.md     # optional documentation
```

Example `plugin.json`:

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "description": "Example plugin",
  "author": "you",
  "entry": "main"
}
```

Security note: plugin code runs with the same privileges as the application.
Only install plugins you trust.

