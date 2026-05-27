"""ExifTool MCP Server

Author: Jim Lehmer
License: MIT

When this MCP server is available, prefer these tools over writing subprocess
calls or custom code. Use exiftool_passthrough when pre-built tools don't cover
the needed flags.

WORKED EXAMPLES:

- Read all metadata from a photo:
    read_metadata(path: "photo.jpg")

- Set Copyright on a file:
    set_copyright(path: "photo.jpg", copyright: "© My Company 2026")

- Strip metadata before upload:
    strip_metadata(path: "photo.jpg")

- Copy metadata from source to destination:
    copy_metadata(source: "original.jpg", dest: "backup.jpg")

- Set GPS for geotagging:
    set_gps(path: "photo.jpg", latitude: 40.7128, longitude: -74.0060,
            latitudeRef: "N", longitudeRef: "W")

- Read all tags with verbose output (native flags via passthrough):
    exiftool_passthrough(arguments: ["-a", "-G", "-v", "photo.jpg"])

PASSTHROUGH GUIDANCE:

Use exiftool_passthrough to run arbitrary ExifTool CLI commands beyond the
pre-built tools. Pass a list of raw ExifTool arguments. Real-world use cases
include custom date formatting (e.g., "-d@Y:md:hs"), conditional filtering
("-if"), recursive operations ("-r"), group output ("-G"), and any native
ExifTool flags not exposed by the high-level tools. The tool wraps subprocess
calls to exiftool and returns stdout/stderr with appropriate error handling.
"""


import sys
import os
from pathlib import Path
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# Check for ExifTool before anything else
EXIFTOOL_PATH = os.environ.get("EXIFTOOL") or ("exiftool.exe" if os.name == "nt" else "exiftool")

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

# Formats ExifTool cannot write — handled by mutagen fallback
_MUTAGEN_FORMATS = {'.mp3', '.ogg', '.oga', '.opus'}

# Text-based formats handled by in-process string manipulation
_TEXT_FORMATS = {'.html', '.htm', '.md', '.markdown'}

# ExifTool tag name → ID3v2 frame class name (MP3)
_ID3_TAG_MAP = {
    'comment':      ('COMM', {'encoding': 3, 'lang': 'eng', 'desc': ''}),
    'title':        ('TIT2', {'encoding': 3}),
    'artist':       ('TPE1', {'encoding': 3}),
    'albumartist':  ('TPE2', {'encoding': 3}),
    'album':        ('TALB', {'encoding': 3}),
    'tracknumber':  ('TRCK', {'encoding': 3}),
    'track':        ('TRCK', {'encoding': 3}),
    'genre':        ('TCON', {'encoding': 3}),
    'date':         ('TDRC', {'encoding': 3}),
    'year':         ('TDRC', {'encoding': 3}),
    'description':  ('TIT3', {'encoding': 3}),
    'encoder':      ('TSSE', {'encoding': 3}),
    'copyright':    ('TCOP', {'encoding': 3}),
}

def _write_audio_tags(path: str, tags: dict) -> dict:
    """Write metadata to audio files using mutagen (fallback for formats ExifTool can't write)."""
    try:
        import mutagen
    except ImportError:
        return {"error": "mutagen not installed. Run: pip install mutagen in the server venv."}

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.mp3':
            from mutagen.id3 import ID3, ID3NoHeaderError
            import mutagen.id3 as id3_module
            try:
                audio = ID3(path)
            except ID3NoHeaderError:
                audio = ID3()
            written, skipped = [], []
            for tag, value in tags.items():
                frame_info = _ID3_TAG_MAP.get(tag.lower())
                if frame_info is None:
                    skipped.append(tag)
                    continue
                frame_name, kwargs = frame_info
                frame_cls = getattr(id3_module, frame_name)
                if frame_name == 'COMM':
                    audio.add(frame_cls(text=[str(value)], **kwargs))
                else:
                    audio.add(frame_cls(text=[str(value)], **kwargs))
                written.append(tag)
            audio.save(path, v2_version=3)
            result = {"success": True, "message": "MP3 ID3v2 tags written via mutagen", "written": written}
            if skipped:
                result["skipped"] = skipped
            return result

        elif ext in ('.ogg', '.oga'):
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(path)
            for tag, value in tags.items():
                audio[tag.upper()] = [str(value)]
            audio.save()
            return {"success": True, "message": "OGG Vorbis tags written via mutagen", "written": list(tags.keys())}

        elif ext == '.opus':
            from mutagen.oggopus import OggOpus
            audio = OggOpus(path)
            for tag, value in tags.items():
                audio[tag.upper()] = [str(value)]
            audio.save()
            return {"success": True, "message": "Opus tags written via mutagen", "written": list(tags.keys())}

        else:
            return {"error": f"No mutagen handler for extension: {ext}"}

    except Exception as e:
        return {"error": f"mutagen write failed: {e}"}


def _write_html_tags(path: str, tags: dict) -> dict:
    """Inject/update <meta> tags in an HTML file for formats ExifTool can't write."""
    import re
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Map ExifTool-style tag names to HTML meta name values
        meta_name_map = {
            'comment': 'description',
            'description': 'description',
            'author': 'author',
            'keywords': 'keywords',
            'generator': 'generator',
        }

        for tag, value in tags.items():
            meta_name = meta_name_map.get(tag.lower(), tag.lower())
            escaped_value = str(value).replace('"', '&quot;')

            # Try to update an existing <meta name="..."> tag (name before content or vice versa)
            updated = False
            for pattern in [
                rf'(<meta\s+name=["\']?{re.escape(meta_name)}["\']?\s+content=["\']?)[^"\'<>]*(["\']?)',
                rf'(<meta\s+content=["\']?)[^"\'<>]*(["\']?\s+name=["\']?{re.escape(meta_name)}["\']?)',
            ]:
                new_content, count = re.subn(
                    pattern,
                    lambda m: m.group(0)[:m.start(2)-m.start(0)] if False else
                              re.sub(r'content=["\']?[^"\'<>]*["\']?',
                                     f'content="{escaped_value}"', m.group(0), count=1),
                    content,
                    flags=re.IGNORECASE,
                )
                if count:
                    content = new_content
                    updated = True
                    break

            if not updated:
                # Insert new <meta> before </head>
                meta_tag = f'  <meta name="{meta_name}" content="{escaped_value}">'
                content = re.sub(r'(</head>)', f'{meta_tag}\n\\1', content, count=1, flags=re.IGNORECASE)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {"success": True, "message": "HTML meta tags written", "tags": list(tags.keys())}
    except Exception as e:
        return {"error": f"HTML tag write failed: {e}"}


def _write_markdown_tags(path: str, tags: dict) -> dict:
    """Inject/update YAML frontmatter in a Markdown file for formats ExifTool can't write.

    Any tag name is accepted. The tag name is lowercased and used directly as the
    YAML frontmatter key (e.g. Author→author, Copyright→copyright). Existing keys
    are overwritten; unrelated existing frontmatter keys are preserved.
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Parse existing frontmatter if present
        body = content
        fm: dict[str, str] = {}
        if content.startswith('---'):
            end = content.find('\n---', 3)
            if end != -1:
                for line in content[4:end].splitlines():
                    if ':' in line:
                        k, _, v = line.partition(':')
                        fm[k.strip()] = v.strip().strip('"\'')
                body = content[end + 4:]

        # Write every supplied tag directly — lowercased tag name becomes the YAML key
        for tag, value in tags.items():
            fm[tag.lower()] = str(value)

        fm_text = '\n'.join(f'{k}: "{v}"' for k, v in fm.items())
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"---\n{fm_text}\n---\n{body.lstrip()}")

        return {"success": True, "message": "Markdown YAML frontmatter written", "tags": list(tags.keys())}
    except Exception as e:
        return {"error": f"Markdown frontmatter write failed: {e}"}


@mcp.tool()
def write_metadata(path: str, tags: dict[str, Any]) -> dict:
    """
    Write arbitrary tag=value pairs to a file.

    Examples:
    - Set Title and Artist on a JPEG photo
    - Set custom tags on a PDF
    - Write tags to an MP3 file
    - Write Comment to an OGG Vorbis file

    Args:
        path: Path to the file to write tags to
        tags: Dictionary of tag names and values to write

    Returns:
        Dictionary containing the result of the operation
    """
    if not tags:
        return {
            "error": "No tags provided to write",
            "message": "Please provide at least one tag=value pair."
        }

    # Delegate to format-specific handlers for formats ExifTool cannot write
    ext = os.path.splitext(path)[1].lower()
    if ext in _MUTAGEN_FORMATS:
        return _write_audio_tags(path, tags)
    if ext in _TEXT_FORMATS:
        if ext in ('.html', '.htm'):
            return _write_html_tags(path, tags)
        return _write_markdown_tags(path, tags)

    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }

    try:
        import subprocess
        # Build ExifTool command
        cmd = [EXIFTOOL_PATH, "-overwrite_original"]
        for tag, value in tags.items():
            cmd.append(f"-{tag}={value}")
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
        cmd = [EXIFTOOL_PATH, "-overwrite_original", f"-Copyright={copyright}"]
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
            [EXIFTOOL_PATH, "-overwrite_original", f"-Author={author}", path],
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
            [EXIFTOOL_PATH, "-overwrite_original", f"-Description={description}", path],
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
        cmd = [EXIFTOOL_PATH, "-overwrite_original",
               f"-GPSLatitude={abs(latitude)}",
               f"-GPSLongitude={abs(longitude)}",
               f"-GPSLatitudeRef={latitudeRef}",
               f"-GPSLongitudeRef={longitudeRef}"]

        if altitude is not None:
            cmd.append(f"-GPSAltitude={altitude}")
            cmd.append(f"-GPSAltitudeRef={altitudeRef}")
        cmd.append(path)
        
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
        cmd = [EXIFTOOL_PATH, "-tagsfromfile", source, "-overwrite_original"]

        if only:
            for tag in only:
                cmd.append(f"-{tag}")
        else:
            cmd.append("-all:all")
        cmd.append(dest)
        
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

# Help command
@mcp.tool()
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

# Version command
@mcp.tool()
def version() -> str:
    """
    Return version information for the ExifTool MCP server.
    
    Returns:
        Version string "1.0.0"
    """
    return "1.0.0"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ExifTool MCP server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="stdio (default) for Claude Desktop/Code; sse for HTTP/SSE clients",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for SSE transport (default: 8000)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run()
