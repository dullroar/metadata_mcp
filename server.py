"""metadata_mcp — Broad File Metadata Reader/Writer MCP Server

Author: Jim Lehmer
License: MIT

Reads and writes metadata across a wide range of file formats by dispatching to
the best available backend for each format:

  ExifTool  — images (JPEG, TIFF, HEIC, PNG, WebP, RAW…), video (MP4, MOV, MKV…),
               PDF, and most document formats. Used for read_metadata on all formats.
  mutagen   — audio formats ExifTool cannot write: MP3 (ID3v2 frames), OGG/Vorbis
               and Opus (Vorbis comment tags). Installed in the server venv.
  in-process — text-based formats with no binary metadata section:
               HTML  → <meta name="..."> tag injection/update in <head>
               Markdown → YAML frontmatter block (--- ... ---)

The correct backend is chosen automatically inside write_metadata based on file
extension. You do not need to specify it; just pass the file path and tag dict.

For coding agents, inspect_file is the compact, read-only first call for any
exact path. It combines filesystem attributes, libmagic content detection, and
Git context. Use read_metadata afterwards only when embedded, format-specific
tags (EXIF, ID3, PDF properties, and similar) are actually needed.

BACKEND COVERAGE QUICK REFERENCE:

  Format       | read_metadata | write_metadata backend
  -------------|---------------|------------------------
  JPEG/TIFF/PNG| ExifTool      | ExifTool
  PDF          | ExifTool      | ExifTool
  MP4/MOV/MKV  | ExifTool      | ExifTool
  MP3          | ExifTool      | mutagen (ID3v2)
  OGG/Opus     | ExifTool      | mutagen (Vorbis comments)
  HTML/HTM     | —             | <meta> injection
  MD/Markdown  | —             | YAML frontmatter

BULK OPERATIONS (pass a glob, skip the loop)
=============================================

ExifTool-backed tools accept glob patterns and directory paths natively —
ExifTool expands them internally. This covers read_metadata, set_copyright,
strip_metadata, set_author, set_description, set_gps, copy_metadata, and
write_metadata for images/video/PDF.

For write_metadata on audio (MP3/OGG/Opus) and text (HTML/Markdown) formats,
the server expands globs in Python before dispatching to the format-specific
backend. All bulk operations happen in one tool call — no loop needed.

    read_metadata(path="photos/*.jpg")
    set_copyright(path="photos/2026/*.jpg", copyright="© 2026 Jim Lehmer")
    strip_metadata(path="exports/*.jpg")
    write_metadata(path="music/*.mp3", tags={"Artist": "Jim Lehmer", "Album": "Demo"})
    write_metadata(path="photos/*.jpg", tags={"Copyright": "© 2026"})
    exiftool_passthrough(arguments=["-r", "-Comment=Processed", "photos/"])

WORKED EXAMPLES:

- Read all metadata from any file:
    read_metadata(path: "photo.jpg")
    read_metadata(path: "song.mp3")
    read_metadata(path: "document.pdf")

- Write tags (backend chosen automatically):
    write_metadata(path: "photo.jpg",    tags: {"Comment": "holiday trip"})
    write_metadata(path: "song.mp3",     tags: {"Comment": "Added by metadata_mcp."})
    write_metadata(path: "track.ogg",    tags: {"Comment": "Added by metadata_mcp."})
    write_metadata(path: "index.html",   tags: {"Description": "Home page"})
    write_metadata(path: "README.md",    tags: {"Author": "Jim Lehmer", "Copyright": "2026"})

- Set Copyright on images/PDFs (ExifTool — accepts globs):
    set_copyright(path: "photo.jpg", copyright: "© My Company 2026")
    set_copyright(path: "photos/*.jpg", copyright: "© My Company 2026")

- Strip metadata before upload (ExifTool — accepts globs):
    strip_metadata(path: "photo.jpg")
    strip_metadata(path: "exports/*.jpg")

- Copy metadata between files (ExifTool):
    copy_metadata(source: "original.jpg", dest: "backup.jpg")

- Set GPS coordinates (ExifTool):
    set_gps(path: "photo.jpg", latitude: 40.7128, longitude: -74.0060,
            latitudeRef: "N", longitudeRef: "W")

- Arbitrary ExifTool flags via passthrough (full glob/recursive support):
    exiftool_passthrough(arguments: ["-a", "-G", "-v", "photo.jpg"])
    exiftool_passthrough(arguments: ["-r", "-Copyright=© 2026", "photos/"])

PASSTHROUGH GUIDANCE:

Use exiftool_passthrough for any ExifTool operation not covered by the pre-built
tools. Real-world use cases: custom date formatting ("-d@Y:md:hs"), conditional
filtering ("-if"), recursive operations ("-r"), group output ("-G").
"""


import glob as _glob
import mimetypes
import os
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# Check for ExifTool before anything else
EXIFTOOL_PATH = os.environ.get("EXIFTOOL") or ("exiftool.exe" if os.name == "nt" else "exiftool")


def _check_exiftool() -> bool:
    import subprocess
    try:
        result = subprocess.run(
            [EXIFTOOL_PATH, "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _expand(pattern: str) -> list[str]:
    """Expand a glob pattern; return [pattern] if no wildcards."""
    if any(c in pattern for c in ("*", "?", "[")):
        return sorted(_glob.glob(pattern, recursive=True))
    return [pattern]


mcp = FastMCP(
    "metadata",
    instructions=(
        "For an exact path, call inspect_file first for compact filesystem, "
        "content-type, and Git context. Call read_metadata only when embedded "
        "format-specific tags are needed. Request Git blame only with a small, "
        "explicit line range."
    ),
)


def _run_readonly_command(arguments: list[str], timeout: int = 5) -> tuple[int | None, str, str, str | None]:
    """Run a fixed-argument local command and return a non-throwing result."""
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr, None
    except FileNotFoundError:
        return None, "", "", f"Command not found: {arguments[0]}"
    except subprocess.TimeoutExpired:
        return None, "", "", f"Command timed out after {timeout} seconds: {arguments[0]}"
    except OSError as exc:
        return None, "", "", f"Could not run {arguments[0]}: {exc}"


def _utc_timestamp(timestamp: float) -> str:
    """Format a POSIX timestamp as an unambiguous UTC ISO-8601 value."""
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _file_kind(mode: int) -> str:
    """Return a portable name for a stat mode's file kind."""
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISCHR(mode):
        return "character_device"
    if stat.S_ISBLK(mode):
        return "block_device"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    return "other"


def _filesystem_info(file_path: Path) -> dict:
    """Collect lstat-based attributes without following symlinks."""
    try:
        attributes = file_path.lstat()
    except FileNotFoundError:
        return {"status": "missing", "error": "Path does not exist"}
    except OSError as exc:
        return {"status": "error", "error": f"Cannot stat path: {exc}"}

    is_symlink = stat.S_ISLNK(attributes.st_mode)
    result: dict[str, Any] = {
        "status": "ok",
        "kind": _file_kind(attributes.st_mode),
        "is_symlink": is_symlink,
        "size_bytes": attributes.st_size,
        "allocated_bytes": getattr(attributes, "st_blocks", 0) * 512 if hasattr(attributes, "st_blocks") else None,
        "mode": f"0o{stat.S_IMODE(attributes.st_mode):03o}",
        "permissions": stat.filemode(attributes.st_mode),
        "timestamps": {
            "accessed_at": _utc_timestamp(attributes.st_atime),
            "modified_at": _utc_timestamp(attributes.st_mtime),
            # On Unix this is inode/status-change time; on Windows it is creation time.
            "changed_at": _utc_timestamp(attributes.st_ctime),
        },
    }
    if os.name == "posix":
        result["owner"] = {"uid": attributes.st_uid, "gid": attributes.st_gid}
    if is_symlink:
        try:
            result["symlink_target"] = os.readlink(file_path)
            result["symlink_target_exists"] = file_path.exists()
        except OSError as exc:
            result["symlink_error"] = str(exc)
    return result


def _content_type_info(file_path: Path, filesystem: dict) -> dict:
    """Use libmagic's file(1) when available; label extension fallback clearly."""
    if filesystem.get("status") != "ok":
        return {"status": "not_applicable", "reason": "Path is not accessible"}
    if filesystem.get("kind") not in {"file", "symlink"}:
        return {"status": "not_applicable", "reason": "Content detection applies to files only"}
    if filesystem.get("is_symlink") and not filesystem.get("symlink_target_exists"):
        return {"status": "not_applicable", "reason": "Symlink target does not exist"}

    file_command = shutil.which("file")
    if not file_command:
        mime_type, encoding = mimetypes.guess_type(str(file_path))
        return {
            "status": "fallback",
            "detection": "extension_fallback",
            "mime_type": mime_type,
            "encoding": encoding,
            "description": None,
            "note": "libmagic file command is unavailable; values were inferred from the extension.",
        }

    mime_rc, mime_stdout, mime_stderr, mime_error = _run_readonly_command(
        [file_command, "--brief", "--dereference", "--mime", "--", str(file_path)]
    )
    description_rc, description_stdout, description_stderr, description_error = _run_readonly_command(
        [file_command, "--brief", "--dereference", "--", str(file_path)]
    )
    if mime_error or description_error or mime_rc != 0 or description_rc != 0:
        detail = mime_error or description_error or mime_stderr.strip() or description_stderr.strip()
        return {
            "status": "error",
            "detection": "libmagic",
            "error": detail or "file command could not identify the path",
        }

    mime_value = mime_stdout.strip()
    mime_type, _, charset = mime_value.partition("; charset=")
    return {
        "status": "ok",
        "detection": "libmagic",
        "mime_type": mime_type or None,
        "encoding": charset or None,
        "description": description_stdout.strip() or None,
    }


def _git_last_commit(repo_root: str, relative_path: str) -> dict | None:
    """Return the latest commit affecting one path, following a single rename chain."""
    rc, stdout, stderr, error = _run_readonly_command(
        [
            "git", "-C", repo_root, "log", "-1", "--follow",
            "--format=%H%x00%an%x00%ae%x00%aI%x00%s", "--", relative_path,
        ]
    )
    if error or rc != 0:
        return {"error": error or stderr.strip() or "Could not read file history"}
    values = stdout.rstrip("\n").split("\x00") if stdout else []
    if len(values) != 5:
        return None
    return {
        "hash": values[0],
        "author": {"name": values[1], "email": values[2]},
        "authored_at": values[3],
        "subject": values[4],
    }


def _parse_git_blame(output: str) -> list[dict]:
    """Parse porcelain blame output into one compact attribution object per line."""
    lines: list[dict] = []
    current: dict[str, Any] = {}
    for raw_line in output.splitlines():
        if raw_line.startswith("\t"):
            if "final_line" in current:
                lines.append({
                    "line": current["final_line"],
                    "commit": current.get("commit"),
                    "author": {
                        "name": current.get("author"),
                        "email": current.get("author_email"),
                        "authored_at": current.get("authored_at"),
                    },
                    "summary": current.get("summary"),
                })
            current = {}
            continue
        if raw_line.startswith(("author ", "author-mail ", "author-time ", "summary ")):
            key, value = raw_line.split(" ", 1)
            mapped_key = {"author": "author", "author-mail": "author_email", "author-time": "authored_at", "summary": "summary"}[key]
            if mapped_key == "authored_at":
                current[mapped_key] = _utc_timestamp(float(value))
            else:
                current[mapped_key] = value.strip("<>")
            continue
        fields = raw_line.split()
        if len(fields) >= 3 and len(fields[0]) in {40, 64} and all(c in "0123456789abcdef" for c in fields[0].lower()):
            current = {"commit": fields[0], "final_line": int(fields[2])}
    return lines


def _git_info(file_path: Path, blame_start_line: int | None, blame_end_line: int | None) -> dict:
    """Gather read-only Git context for a file, optionally including bounded blame."""
    start_directory = file_path if file_path.is_dir() else file_path.parent
    rc, stdout, stderr, error = _run_readonly_command(
        ["git", "-C", str(start_directory), "rev-parse", "--show-toplevel"]
    )
    if error:
        return {"status": "unavailable", "error": error}
    if rc != 0:
        return {"status": "not_repository", "reason": "Path is not inside a Git work tree"}

    repo_root = stdout.strip()
    relative_path = os.path.relpath(file_path, repo_root)
    branch_rc, branch_stdout, _, _ = _run_readonly_command(
        ["git", "-C", repo_root, "symbolic-ref", "--quiet", "--short", "HEAD"]
    )
    head_rc, head_stdout, head_stderr, head_error = _run_readonly_command(
        ["git", "-C", repo_root, "rev-parse", "HEAD"]
    )
    tracked_rc, _, _, _ = _run_readonly_command(
        ["git", "-C", repo_root, "ls-files", "--error-unmatch", "--", relative_path]
    )
    status_rc, status_stdout, status_stderr, status_error = _run_readonly_command(
        ["git", "-C", repo_root, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "--", relative_path]
    )
    if status_error or status_rc != 0:
        return {"status": "error", "repository_root": repo_root, "error": status_error or status_stderr.strip()}

    porcelain = status_stdout.splitlines()[0] if status_stdout.splitlines() else ""
    xy = porcelain[:2] if porcelain else "  "
    if xy == "??":
        worktree_state = "untracked"
    elif xy == "!!":
        worktree_state = "ignored"
    elif "D" in xy:
        worktree_state = "deleted"
    elif "A" in xy:
        worktree_state = "added"
    elif "R" in xy:
        worktree_state = "renamed"
    elif porcelain:
        worktree_state = "modified"
    else:
        worktree_state = "clean"

    result: dict[str, Any] = {
        "status": "ok",
        "repository_root": repo_root,
        "relative_path": relative_path,
        "branch": branch_stdout.strip() if branch_rc == 0 else None,
        "head": head_stdout.strip() if head_rc == 0 else None,
        "head_error": (head_error or head_stderr.strip()) if head_rc != 0 else None,
        "tracked": tracked_rc == 0,
        "worktree_state": worktree_state,
        "index_status": xy[0] if porcelain else " ",
        "working_tree_status": xy[1] if porcelain else " ",
    }
    result["last_commit"] = _git_last_commit(repo_root, relative_path) if tracked_rc == 0 else None

    if blame_start_line is not None and blame_end_line is not None:
        if tracked_rc != 0:
            result["blame"] = {"status": "not_applicable", "reason": "Git does not track this path"}
        else:
            blame_rc, blame_stdout, blame_stderr, blame_error = _run_readonly_command(
                ["git", "-C", repo_root, "blame", "--line-porcelain", "-L", f"{blame_start_line},{blame_end_line}", "--", relative_path],
                timeout=15,
            )
            if blame_error or blame_rc != 0:
                result["blame"] = {"status": "error", "error": blame_error or blame_stderr.strip()}
            else:
                result["blame"] = {
                    "status": "ok",
                    "start_line": blame_start_line,
                    "end_line": blame_end_line,
                    "lines": _parse_git_blame(blame_stdout),
                }
    return result


@mcp.tool()
def inspect_file(
    path: str,
    blame_start_line: Optional[int] = None,
    blame_end_line: Optional[int] = None,
) -> dict:
    """Inspect one exact path for compact filesystem, content-type, and Git context.

    Use this as the first call for coding-agent file context. It does not read
    embedded EXIF/ID3/PDF tags; call read_metadata only when those format-specific
    tags are needed. Git blame is intentionally opt-in and requires both inclusive
    line bounds, so a request cannot accidentally return attribution for a large file.

    Args:
        path: One exact file or directory path. Glob patterns are not expanded.
        blame_start_line: First line for optional Git blame (requires blame_end_line).
        blame_end_line: Last inclusive line for optional Git blame (requires blame_start_line).

    Returns:
        A result with independent filesystem, content_type, and git sections.
        A failed optional subsystem is reported in its own section.
    """
    original_path = Path(path).expanduser()
    absolute_path = original_path.absolute()
    resolved_path = original_path.resolve(strict=False)
    result: dict[str, Any] = {
        "path": {
            "input": path,
            "absolute": str(absolute_path),
            "resolved": str(resolved_path),
        }
    }
    filesystem = _filesystem_info(absolute_path)
    result["filesystem"] = filesystem

    try:
        result["content_type"] = _content_type_info(absolute_path, filesystem)
    except Exception as exc:
        result["content_type"] = {"status": "error", "error": f"Content detection failed: {exc}"}

    invalid_blame = (
        (blame_start_line is None) != (blame_end_line is None)
        or (blame_start_line is not None and blame_start_line < 1)
        or (blame_end_line is not None and blame_end_line < blame_start_line)
    )
    if invalid_blame:
        result["git"] = {
            "status": "not_requested",
            "blame": {
                "status": "invalid_request",
                "error": "Provide both blame_start_line and blame_end_line as an inclusive range starting at 1.",
            },
        }
        return result

    try:
        result["git"] = _git_info(absolute_path, blame_start_line, blame_end_line)
    except Exception as exc:
        result["git"] = {"status": "error", "error": f"Git inspection failed: {exc}"}
    return result


@mcp.tool()
def read_metadata(path: str) -> dict:
    """Read all metadata tags from a file or glob pattern.

    ExifTool handles glob patterns and directory paths natively, so you can
    read metadata from multiple files in one call.

    Args:
        path: Path to the file, a glob pattern (e.g. "photos/*.jpg"),
              or a directory path to read all files in that directory.

    Returns:
        Dictionary containing all metadata tags found (single file), or a
        dict mapping filename → tags for glob/directory inputs.

    Examples:
        read_metadata(path="photo.jpg")
        read_metadata(path="photos/*.jpg")    # one call, no loop
        read_metadata(path="photos/")         # all files in directory
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
            capture_output=True, text=True, timeout=30, check=True
        )
        metadata = {}
        for line in result.stdout.strip().split("\n"):
            if "=" in line and not line.startswith("-"):
                key, value = line.split("=", 1)
                metadata[key] = value
            elif line.strip() and not line.startswith("-"):
                metadata[line.strip()] = ""
        return metadata
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


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

        meta_name_map = {
            'comment': 'description', 'description': 'description',
            'author': 'author', 'keywords': 'keywords', 'generator': 'generator',
        }

        for tag, value in tags.items():
            meta_name = meta_name_map.get(tag.lower(), tag.lower())
            escaped_value = str(value).replace('"', '&quot;')

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
    """Write arbitrary tag=value pairs to a file or glob pattern.

    The correct backend is chosen automatically by file extension. For images,
    video, and PDF the path is passed directly to ExifTool, which handles glob
    patterns and directory paths natively. For audio (MP3/OGG/Opus) and text
    (HTML/Markdown) formats, globs are expanded in Python and each file is
    processed individually.

    Args:
        path: Path to the file, a glob pattern (e.g. "photos/*.jpg"),
              or a directory path (ExifTool formats only).
        tags: Dictionary of tag names and values to write.

    Returns:
        Dict with success/error info. For bulk operations, includes per-file results.

    Examples:
        write_metadata(path="photo.jpg",    tags={"Comment": "holiday trip"})
        write_metadata(path="photos/*.jpg", tags={"Copyright": "© 2026"})  # one call, no loop
        write_metadata(path="music/*.mp3",  tags={"Artist": "Jim Lehmer"}) # one call, no loop
        write_metadata(path="track.ogg",    tags={"Comment": "Added by metadata_mcp."})
        write_metadata(path="README.md",    tags={"Author": "Jim Lehmer", "Copyright": "2026"})
    """
    if not tags:
        return {"error": "No tags provided to write", "message": "Please provide at least one tag=value pair."}

    ext = os.path.splitext(path)[1].lower()

    # For mutagen and text backends, expand globs in Python since those backends
    # operate on individual files (only ExifTool handles globs natively)
    is_glob = any(c in path for c in ("*", "?", "["))
    if is_glob and (ext in _MUTAGEN_FORMATS or ext in _TEXT_FORMATS):
        files = _expand(path)
        if not files:
            return {"error": f"No files matched: {path}"}
        results = []
        for f in files:
            results.append({"file": f, "result": write_metadata(f, tags)})
        return {"success": True, "bulk_results": results}

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
        cmd = [EXIFTOOL_PATH, "-overwrite_original"]
        for tag, value in tags.items():
            cmd.append(f"-{tag}={value}")
        cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return {"success": True, "message": "Tags written successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def set_copyright(path: str, copyright: str, recursive: bool = False) -> dict:
    """Set Copyright tag on a file, glob pattern, or directory (ExifTool).

    ExifTool handles glob patterns and directory paths natively, so you can
    set copyright on many files in one call.

    Args:
        path: File path, glob pattern (e.g. "photos/*.jpg"), or directory.
        copyright: Copyright text to set.
        recursive: If True and path is a directory, apply to all files recursively.

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        set_copyright(path="photo.jpg", copyright="© My Company 2026")
        set_copyright(path="photos/*.jpg", copyright="© My Company 2026")  # one call, no loop
        set_copyright(path="photos/", copyright="© My Company 2026", recursive=True)
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return {"success": True, "message": "Copyright set successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def set_author(path: str, author: str) -> dict:
    """Set Author tag on a file or glob pattern (ExifTool).

    ExifTool handles glob patterns natively, so you can tag many files at once.

    Args:
        path: Path to the file, or a glob pattern (e.g. "docs/*.pdf").
        author: Author name to set.

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        set_author(path="photo.jpg", author="Jim Lehmer")
        set_author(path="docs/*.pdf", author="Jim Lehmer")  # one call, no loop
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
            capture_output=True, text=True, timeout=30, check=True
        )
        return {"success": True, "message": "Author set successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def set_description(path: str, description: str) -> dict:
    """Set Description tag on a file or glob pattern (ExifTool).

    ExifTool handles glob patterns natively, so you can tag many files at once.

    Args:
        path: Path to the file, or a glob pattern (e.g. "photos/*.jpg").
        description: Description text to set.

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        set_description(path="photo.jpg", description="Family holiday 2026")
        set_description(path="photos/*.jpg", description="Family holiday 2026")  # one call, no loop
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
            capture_output=True, text=True, timeout=30, check=True
        )
        return {"success": True, "message": "Description set successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def set_gps(path: str, latitude: float, longitude: float, latitudeRef: str = "N",
            longitudeRef: str = "E", altitude: Optional[float] = None,
            altitudeRef: str = "above") -> dict:
    """Set GPS coordinates on a file or glob pattern (ExifTool).

    ExifTool handles glob patterns natively. Useful for geotagging batches of
    photos taken at the same location.

    Args:
        path: Path to the file, or a glob pattern (e.g. "trip/*.jpg").
        latitude: GPS latitude (-90 to 90).
        longitude: GPS longitude (-180 to 180).
        latitudeRef: "N" or "S".
        longitudeRef: "E" or "W".
        altitude: GPS altitude in meters (optional).
        altitudeRef: "above" or "below" (optional).

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        set_gps(path="photo.jpg", latitude=40.7128, longitude=-74.0060, latitudeRef="N", longitudeRef="W")
        set_gps(path="trip/*.jpg", latitude=48.8566, longitude=2.3522, latitudeRef="N", longitudeRef="E")
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    if latitude < -90 or latitude > 90:
        return {"error": "Invalid latitude", "message": f"Latitude must be between -90 and 90, got {latitude}"}
    if longitude < -180 or longitude > 180:
        return {"error": "Invalid longitude", "message": f"Longitude must be between -180 and 180, got {longitude}"}

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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        return {"success": True, "message": "GPS coordinates set successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def copy_metadata(source: str, dest: str, only: Optional[list[str]] = None) -> dict:
    """Copy metadata from source file to destination file (ExifTool).

    Args:
        source: Source file path.
        dest: Destination file path.
        only: List of tag names to copy (if set, only these tags are copied).

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        copy_metadata(source="original.jpg", dest="backup.jpg")
        copy_metadata(source="master.jpg", dest="copy.jpg", only=["Copyright", "Author"])
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        return {"success": True, "message": "Metadata copied successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def strip_metadata(path: str, recursive: bool = False) -> dict:
    """Strip all metadata from a file, glob pattern, or directory (ExifTool).

    ExifTool handles glob patterns and directory paths natively, so you can
    strip metadata from many files in one call.

    Args:
        path: File path, glob pattern (e.g. "export/*.jpg"), or directory.
        recursive: If True and path is a directory, apply to all files recursively.

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        strip_metadata(path="photo.jpg")
        strip_metadata(path="export/*.jpg")          # one call, no loop
        strip_metadata(path="export/", recursive=True)
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return {"success": True, "message": "Metadata stripped successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def exiftool_passthrough(arguments: list[str]) -> dict:
    """Run arbitrary ExifTool CLI arguments (full glob and recursive support).

    ExifTool natively handles glob patterns, directory paths, and recursive
    traversal (-r). Use this for any operation not covered by the pre-built tools.

    Args:
        arguments: List of ExifTool CLI arguments (omit 'exiftool' itself).

    Returns:
        Dictionary containing the result of the operation.

    Examples:
        exiftool_passthrough(arguments=["-a", "-G", "photo.jpg"])
        exiftool_passthrough(arguments=["-Copyright=© 2026", "photos/*.jpg"])  # bulk
        exiftool_passthrough(arguments=["-r", "-Comment=Processed", "photos/"])  # recursive
        exiftool_passthrough(arguments=["-d", "%Y-%m-%d", "photo.jpg"])
        exiftool_passthrough(arguments=["-if", "$GPSLatitude", "-r", "photos/"])
    """
    if not _check_exiftool():
        return {
            "error": "ExifTool is not installed or not accessible",
            "message": "Please install ExifTool from https://exiftool.org/ and ensure it's in your PATH."
        }
    try:
        import subprocess
        cmd = [EXIFTOOL_PATH] + arguments
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return {"success": True, "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool command failed: {e}", "stderr": e.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool command timed out", "message": "Try breaking it into smaller parts."}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


@mcp.tool()
def help() -> str:
    """Get information about available metadata_mcp tools and bulk operation support.

    Tools and backends:
    - inspect_file:         Compact first-call context for one path: filesystem
                              attributes, libmagic type detection, and Git state.
                              Optional Git blame requires explicit line bounds.
    - read_metadata:        Read all metadata tags from any file (ExifTool — accepts globs)
    - write_metadata:       Write tag=value pairs — backend chosen by file extension:
                              ExifTool for images/video/PDF (accepts globs/dirs natively)
                              mutagen for MP3 (ID3v2), OGG/Opus (glob expanded in Python)
                              in-process for HTML (<meta> injection) and Markdown (YAML frontmatter)
    - set_copyright:        Set Copyright tag on a file, glob, or directory (ExifTool)
    - set_author:           Set Author tag on a file or glob (ExifTool)
    - set_description:      Set Description tag on a file or glob (ExifTool)
    - set_gps:              Set GPS coordinates on a file or glob (ExifTool)
    - copy_metadata:        Copy metadata from source to destination (ExifTool)
    - strip_metadata:       Strip all metadata from a file, glob, or directory (ExifTool)
    - exiftool_passthrough: Run arbitrary ExifTool CLI commands (full glob/recursive support)

    Bulk examples (one call, no loop needed):
        read_metadata(path="photos/*.jpg")
        set_copyright(path="photos/*.jpg", copyright="© 2026 Jim Lehmer")
        strip_metadata(path="exports/*.jpg")
        write_metadata(path="music/*.mp3", tags={"Artist": "Jim Lehmer"})
        exiftool_passthrough(arguments=["-r", "-all=", "exports/"])
    """
    return "metadata_mcp — use inspect_file first for compact filesystem, type, and Git context; use read_metadata for embedded format-specific tags. See tool docstrings for details."


@mcp.tool()
def version() -> str:
    """Return version information for the metadata_mcp server."""
    return "2.1.0"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="metadata_mcp — broad file metadata reader/writer MCP server")
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
