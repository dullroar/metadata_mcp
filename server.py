"""ExifTool MCP Server

Author: Jim Lehmer
License: MIT

A Model Context Protocol (MCP) server that exposes ExifTool as an MCP tool.
Connect it to any MCP-compatible LLM client (Claude Desktop, Claude Code, etc.)
and let the LLM read/write metadata on image, video, and document files — no
ExifTool CLI knowledge required.

When this MCP server is available, agents can ask to:
- Read all EXIF metadata from a file
- Write arbitrary tags to media files
- Set Copyright recursively across a directory
- Set GPS coordinates on a file
- Copy metadata between files
- Strip all metadata
- And more via the passthrough tool

---

## Reasons to Use

1. Token/cost savings — the model coordinates metadata work without needing to
   remember ExifTool flags.

2. Safety — metadata manipulation via MCP is auditable and explicit.

3. Local privacy — metadata stays on the local machine; no upload needed.

4. Better workflow — "Read all tags from this image and tell me the camera model"
   is much friendlier than remembering exiftool -a -G.

5. Agentic pipeline building — extract → validate → embed → archive becomes
   modular steps.

---

## Tools

### `read_metadata`

Read all metadata tags from a file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File path to read metadata from |

### `write_metadata`

Write arbitrary tag=value pairs to a file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File path |
| `tags` | `dict` | required | tag=value pairs, e.g. {"Title": "My Photo", "Artist": "Me"} |

### `set_copyright`

Set Copyright tag across a file or directory (recursive flag available).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File or directory path |
| `copyright` | `str` | required | Copyright text to set |
| `recursive` | `bool` | False | Apply to all files in directory recursively |

### `set_author`

Set Author tag on a file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File path |
| `author` | `str` | required | Author name to set |

### `set_description`

Set Description tag on a file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File path |
| `description` | `str` | required | Description text to set |

### `set_gps`

Set GPS coordinates (lat/lon) on a file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File path |
| `latitude` | `float` | required | GPS latitude |
| `longitude` | `float` | required | GPS longitude |
| `latitudeRef` | `str` | "N" | "N" or "S" |
| `longitudeRef` | `str` | "E" | "E" or "W" |
| `altitude` | `float` | optional | GPS altitude (optional) |
| `altitudeRef` | `str` | "above" | "above" or "below" (optional) |

### `copy_metadata`

Copy all metadata from source file to destination file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `source` | `str` | required | Source file path |
| `dest` | `str` | required | Destination file path |
| `only` | `list[str]` | optional | Copy only these tag names (if set) |

### `strip_metadata`

Strip all metadata from a file or directory (recursive).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File or directory path |
| `recursive` | `bool` | False | Apply to all files in directory recursively |

### `exiftool_passthrough`

Passthrough tool for arbitrary ExifTool arguments. Run any ExifTool command.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `arguments` | `list[str]` | required | Raw ExifTool CLI arguments |

---

## Requirements

- Python 3.10+
- [ExifTool](https://exiftool.org/) installed and on your PATH
- Python packages: `mcp[cli]`

---

## Installation

```bash
git clone https://github.com/dullroar/exiftool_mcp.git
cd exiftool_mcp

# Recommended: use a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

---

## MCP client configuration

### Claude Desktop

Add to your `claude_desktop_config.json` (usually at `%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "exiftool": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

Using a virtual environment (recommended — avoids dependency conflicts):

```json
{
  "mcpServers": {
    "exiftool": {
      "command": "C:\\path\\to\\exiftool_mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\exiftool_mcp\\server.py"]
    }
  }
}
```

Restart Claude Desktop after editing the config. You should see a hammer icon in the chat input area indicating MCP tools are available.

### Claude Code

Register the server with the Claude Code CLI:

```bash
claude mcp add exiftool -- python C:\path\to\exiftool_mcp\server.py
```

Or with a virtual environment:

```bash
claude mcp add exiftool -- C:\path\to\exiftool_mcp\.venv\Scripts\python.exe C:\path\to\exiftool_mcp\server.py
```

Verify it registered:

```bash
claude mcp list
```

To remove it later:

```bash
claude mcp remove exiftool
```

### HTTP/SSE mode (for other MCP clients)

By default the server uses stdio. Pass `--transport sse` to start an HTTP/SSE server instead:

```bash
python server.py --transport sse
# Listening on http://127.0.0.1:8000/sse
```

Optional flags:

| Flag | Default | Description |
| --- | --- | --- |
| `--transport` | `stdio` | `stdio` or `sse` |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |

You can also set `FASTMCP_HOST` and `FASTMCP_PORT` environment variables instead of flags.

Any MCP client that speaks HTTP/SSE (VS Code extensions, the MCP Inspector, or custom agents) can connect to `http://127.0.0.1:8000/sse`.

**Tunneling for a one-off remote demo** (e.g., ChatGPT connector):

```bash
python server.py --transport sse &
ngrok http 8000
# Paste the ngrok HTTPS URL into the ChatGPT custom connector dialog
```

> Note: for production exposure add an auth token. For local experiments, localhost is fine.

---

## Example prompts

Once connected to a Claude client, you can ask naturally:

- *"Read all the metadata from this photo and tell me what camera was used."*
- *"Set the Copyright tag on this image to '© My Company 2026'."*
- *"Copy all metadata from original.jpg to backup.jpg."*
- *"Strip all metadata from this file before uploading."*
- *"Set my GPS coordinates on this photo so I can geotag my travels."*
- *"Set the Author tag on all files in my Pictures folder."*
- *"What tags does this file have?"*

The LLM translates your plain-English request into the appropriate `read_metadata`,
`write_metadata`, and other ExifTool tools — you don't need to know ExifTool flags.

---

## Testing with the MCP Inspector

```bash
mcp dev server.py
```

This opens a browser-based inspector where you can call tools manually and inspect inputs/outputs before wiring up a full client.

---

## Error Handling

- If ExifTool is not installed, you'll see a helpful error message suggesting
  where to download it from https://exiftool.org/
- Invalid file paths, missing files, or unsupported file types will be reported
  clearly with suggestions for fixes.

---

## License

MIT — see [LICENSE](LICENSE).
"""

import sys
import os
from pathlib import Path
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# Check for ExifTool before anything else
EXIFTOOL_PATH = os.environ.get("EXIFTOOL") or "exiftool.exe" if os.name == "nt" else "exiftool"

# Verify ExifTool is installed
def _check_exiftool() -> bool:
    """Check if ExifTool is installed and accessible."""
    import subprocess
    try:
        result = subprocess.run(
            [EXIFTOOL_PATH, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        return False

# Create MCP server
mcp = FastMCP("exiftool")

@mcp.tool()
def read_metadata(path: str) -> dict:
    """
    Read all metadata tags from a file.
    
    Examples:
    - Read EXIF data from a JPEG photo
    - Read metadata from a PDF document
    - Read ID3 tags from an MP3 file
    
    Args:
        path: Path to the file to read metadata from
    
    Returns:
        Dictionary containing all metadata tags found in the file
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        result = subprocess.run(
            [EXIFTOOL_PATH, "-a", "-G", path],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        # Parse output - ExifTool outputs one tag per line as "TAGNAME=value"
        metadata = {}
        for line in result.stdout.strip().split("\n"):
            if "=" in line and not line.startswith("-"):
                key, value = line.split("=", 1)
                # Handle values that might contain spaces or quotes
                metadata[key] = value
            elif line.strip() and not line.startswith("-"):
                # Tag with no value
                metadata[line.strip()] = ""
        
        return metadata
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def write_metadata(path: str, tags: dict[str, Any]) -> dict:
    """
    Write arbitrary tag=value pairs to a file.
    
    Examples:
    - Set Title and Artist on a JPEG photo
    - Set custom tags on a PDF
    - Write tags to an MP3 file
    
    Args:
        path: Path to the file to write tags to
        tags: Dictionary of tag names and values to write
        
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    if not tags:
        return {
            "error": "No tags provided to write",
            "message": "Please provide at least one tag=value pair."
        }
    
    try:
        import subprocess
        # Build ExifTool command
        cmd = [EXIFTOOL_PATH, "-overwrite", path]
        for tag, value in tags.items():
            cmd.extend(["-T", f"{tag}", "-t", str(value)])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        
        return {
            "success": True,
            "message": "Tags written successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def set_copyright(path: str, copyright: str, recursive: bool = False) -> dict:
    """
    Set Copyright tag across a file or directory.
    
    Examples:
    - Set copyright on a single image
    - Set copyright recursively across a directory of photos
    
    Args:
        path: File or directory path
        copyright: Copyright text to set
        recursive: If True and path is a directory, apply to all files recursively
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        cmd = [EXIFTOOL_PATH, "-T", "Copyright", "-c", copyright]
        if recursive:
            cmd.append("-r")
        cmd.append(path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        
        return {
            "success": True,
            "message": "Copyright set successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def set_author(path: str, author: str) -> dict:
    """
    Set Author tag on a file.
    
    Examples:
    - Set author name on a photo
    - Set creator on a document
    
    Args:
        path: Path to the file
        author: Author name to set
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        result = subprocess.run(
            [EXIFTOOL_PATH, "-overwrite", "-T", "Author", "-t", author, path],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        return {
            "success": True,
            "message": "Author set successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def set_description(path: str, description: str) -> dict:
    """
    Set Description tag on a file.
    
    Examples:
    - Set description on a photo
    - Set keywords on a document
    
    Args:
        path: Path to the file
        description: Description text to set
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        result = subprocess.run(
            [EXIFTOOL_PATH, "-overwrite", "-T", "Description", "-t", description, path],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        return {
            "success": True,
            "message": "Description set successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def set_gps(path: str, latitude: float, longitude: float, latitudeRef: str = "N",
            longitudeRef: str = "E", altitude: Optional[float] = None,
            altitudeRef: str = "above") -> dict:
    """
    Set GPS coordinates on a file.
    
    Examples:
    - Set GPS location on a photo for geotagging
    - Add GPS data to a map image
    
    Args:
        path: Path to the file
        latitude: GPS latitude (-90 to 90)
        longitude: GPS longitude (-180 to 180)
        latitudeRef: "N" or "S"
        longitudeRef: "E" or "W"
        altitude: GPS altitude in meters (optional)
        altitudeRef: "above" or "below" (optional)
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    # Validate latitude
    if latitude < -90 or latitude > 90:
        return {
            "error": "Invalid latitude",
            "message": f"Latitude must be between -90 and 90, got {latitude}"
        }
    
    # Validate longitude
    if longitude < -180 or longitude > 180:
        return {
            "error": "Invalid longitude",
            "message": f"Longitude must be between -180 and 180, got {longitude}"
        }
    
    try:
        import subprocess
        cmd = [EXIFTOOL_PATH, "-overwrite", path]
        cmd.extend(["-T", "GPSLatitude", "-t", str(abs(latitude))])
        cmd.extend(["-T", "GPSLongitude", "-t", str(abs(longitude))])
        cmd.extend(["-T", "GPSLatitudeRef", "-t", latitudeRef])
        cmd.extend(["-T", "GPSLongitudeRef", "-t", longitudeRef])
        
        if altitude is not None:
            cmd.extend(["-T", "GPSAltitude", "-t", str(altitude)])
            cmd.extend(["-T", "GPSAltitudeRef", "-t", altitudeRef])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        return {
            "success": True,
            "message": "GPS coordinates set successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def copy_metadata(source: str, dest: str, only: Optional[list[str]] = None) -> dict:
    """
    Copy metadata from source file to destination file.
    
    Examples:
    - Copy all metadata from original.jpg to backup.jpg
    - Copy only specific tags from source to destination
    
    Args:
        source: Source file path
        dest: Destination file path
        only: List of tag names to copy (if set, only these tags are copied)
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        cmd = [EXIFTOOL_PATH, "-c", source, dest]
        
        if only:
            # Copy only specific tags
            cmd.extend(["-O"] + only)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        return {
            "success": True,
            "message": "Metadata copied successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def strip_metadata(path: str, recursive: bool = False) -> dict:
    """
    Strip all metadata from a file or directory.
    
    Examples:
    - Remove all EXIF data from a photo before uploading
    - Strip metadata recursively from a directory of images
    
    Args:
        path: File or directory path
        recursive: If True and path is a directory, apply to all files recursively
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        cmd = [EXIFTOOL_PATH, "-all="]
        if recursive:
            cmd.append("-r")
        cmd.append(path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        
        return {
            "success": True,
            "message": "Metadata stripped successfully",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The file may be locked or the command took too long."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

@mcp.tool()
def exiftool_passthrough(arguments: list[str]) -> dict:
    """
    Passthrough tool for arbitrary ExifTool arguments.
    
    Run any ExifTool command by passing the arguments directly.
    
    Examples:
    - exiftool -a -G image.jpg  (read all metadata)
    - exiftool -d "%Y-%m-%d" image.jpg (set date with custom format)
    - exiftool -v image.jpg (verbose output)
    - exiftool -r -c -d "2024" folder/ (recursive, clean output, filter date)
    
    Args:
        arguments: List of ExifTool CLI arguments
    
    Returns:
        Dictionary containing the result of the operation
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    
    try:
        import subprocess
        # Build command from arguments
        cmd = [EXIFTOOL_PATH] + arguments
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        
        return {
            "success": True,
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"ExifTool command failed: {e}",
            "stderr": e.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "ExifTool command timed out",
            "message": "The command took too long. Try breaking it into smaller parts."
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "message": str(e)
        }

# Help command (built-in)
@mcp.help()
def help() -> str:
    """
    Get information about available ExifTool MCP tools.
    
    Available tools:
    - read_metadata: Read all metadata tags from a file
    - write_metadata: Write arbitrary tag=value pairs to a file
    - set_copyright: Set Copyright tag on a file or directory
    - set_author: Set Author tag on a file
    - set_description: Set Description tag on a file
    - set_gps: Set GPS coordinates on a file
    - copy_metadata: Copy metadata from source to destination
    - strip_metadata: Strip all metadata from a file or directory
    - exiftool_passthrough: Run arbitrary ExifTool commands
    
    For detailed help on each tool, check the tool documentation above.
    
    Example:
    Read all metadata from an image:
    read_metadata(path="C:/Pictures/photo.jpg")
    
    Set copyright on a file:
    set_copyright(path="C:/Pictures/photo.jpg", copyright="© My Company 2026")
    """
    return "ExifTool MCP Server help information"

# Version command (built-in)
@mcp.version()
def version() -> str:
    """
    Return version information for the ExifTool MCP server.
    
    Returns:
        Version string "1.0.0"
    """
    return "1.0.0"
