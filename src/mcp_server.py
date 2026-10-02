#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Cloud Search Lite.
Zero-dependency, high-performance stdio JSON-RPC 2.0 server.
Provides instant (<2ms) SQLite FTS5 search and directory browsing
across Google Drive, OneDrive, and cloud remotes without FUSE crawling overhead.
"""

import json
from pathlib import Path
import sys
import traceback
from typing import Any, Dict, List, Optional

# Set up backend imports
SRC_DIR = Path(__file__).resolve().parent
APP_DIR = SRC_DIR.parent
BACKEND_DIR = APP_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from config import DB_PATH, REMOTES, PORT, HOST
from db import search_files, get_folder_contents, get_stats

class CloudSearchMCPServer:
    """Zero-dependency Model Context Protocol server exposing Cloud Search Lite."""

    def __init__(self):
        self.server_info = {
            "name": "cloud-search-lite",
            "version": "3.0.0",
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns the list of tool definitions adhering to the MCP schema."""
        available_remotes = list(REMOTES.keys())
        return [
            {
                "name": "cloud_search",
                "description": (
                    "Instant sub-millisecond SQLite FTS5 search across all indexed cloud files "
                    "(OneDrive, Google Drive, etc., 339k+ files). Returns full local filesystem paths "
                    "(e.g. /home/redking/OneDrive/..., /home/redking/GoogleDrive/...), sizes, and timestamps "
                    "without triggering slow, freezing FUSE directory crawls."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Search term or pattern (e.g. 'Monster Manual', 'taxes 2023', 'folder:rpg'). "
                                "Supports prefix matching and 'folder:<name>' or 'dir:<name>' syntax."
                            ),
                        },
                        "remote": {
                            "type": "string",
                            "description": f"Optional remote filter. Available remotes: {available_remotes}",
                            "enum": available_remotes if available_remotes else ["onedrive", "gdrive"],
                        },
                        "file_type": {
                            "type": "string",
                            "description": "Optional category filter.",
                            "enum": ["docs", "images", "audio", "videos", "archives", "code", "folders"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 20, max: 100).",
                            "default": 20,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "cloud_browse",
                "description": (
                    "Instantly browse indexed cloud directory contents in ~0.2ms from SQLite cache "
                    "without FUSE network lag. Returns child folders, files, sizes, and breadcrumbs."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "remote": {
                            "type": "string",
                            "description": f"Remote to browse. Available remotes: {available_remotes}",
                            "enum": available_remotes if available_remotes else ["onedrive", "gdrive"],
                        },
                        "path": {
                            "type": "string",
                            "description": "Relative folder path within the cloud drive (empty string for root).",
                            "default": "",
                        },
                    },
                    "required": ["remote"],
                },
            },
            {
                "name": "cloud_status",
                "description": "Check total indexed file counts and last sync timestamps across all cloud remotes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Executes the requested tool and returns the JSON string result."""
        if name == "cloud_search":
            query = arguments.get("query", "")
            remote = arguments.get("remote")
            file_type = arguments.get("file_type")
            limit = min(int(arguments.get("limit", 20)), 100)

            raw_res = search_files(
                query=query,
                remote_id=remote,
                file_type=file_type,
                limit=limit,
                offset=0,
            )

            # Format results cleanly for AI agent consumption
            results = []
            for item in raw_res.get("results", []):
                results.append({
                    "filename": item.get("filename"),
                    "local_path": item.get("local_path"),
                    "remote": item.get("remote_name"),
                    "size": item.get("size_formatted"),
                    "is_dir": item.get("is_dir", False),
                    "modified": item.get("mtime", ""),
                })

            output = {
                "query": query,
                "total_matched": raw_res.get("total", 0),
                "returned_count": len(results),
                "elapsed_ms": raw_res.get("elapsed_ms", 0),
                "results": results,
            }
            return json.dumps(output, indent=2)

        elif name == "cloud_browse":
            remote = arguments.get("remote", "")
            path = arguments.get("path", "")

            raw_res = get_folder_contents(remote_id=remote, folder_path=path)

            items = []
            for item in raw_res.get("items", []):
                items.append({
                    "name": item.get("filename"),
                    "local_path": item.get("local_path"),
                    "is_dir": item.get("is_dir", False),
                    "size": item.get("size_formatted"),
                    "modified": item.get("mtime", ""),
                })

            output = {
                "remote": raw_res.get("remote_name", remote),
                "current_path": raw_res.get("current_path", path),
                "breadcrumbs": [b.get("name") for b in raw_res.get("breadcrumbs", [])],
                "folder_count": raw_res.get("folder_count", 0),
                "file_count": raw_res.get("file_count", 0),
                "elapsed_ms": raw_res.get("elapsed_ms", 0),
                "items": items,
            }
            return json.dumps(output, indent=2)

        elif name == "cloud_status":
            raw_res = get_stats()
            return json.dumps(raw_res, indent=2)

        else:
            raise ValueError(f"Unknown tool: '{name}'")

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handles a single JSON-RPC 2.0 MCP request dict and returns response dict."""
        method = request.get("method")
        msg_id = request.get("id")

        # Ignore notifications (no id)
        if msg_id is None and method and method.startswith("notifications/"):
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": self.server_info,
                },
            }

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {},
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.get_tool_definitions(),
                },
            }

        elif method == "tools/call":
            params = request.get("params", {})
            t_name = params.get("name")
            t_args = params.get("arguments", {})

            try:
                text_result = self.call_tool(t_name, t_args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": text_result,
                            }
                        ],
                        "isError": False,
                    },
                }
            except Exception as e:
                err_trace = traceback.format_exc()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error executing tool '{t_name}': {str(e)}\n{err_trace}",
                            }
                        ],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found.",
                },
            }


def run_stdio_server():
    """Runs standard input/output loop for the MCP server."""
    server = CloudSearchMCPServer()

    for line in sys.stdin:
        line_clean = line.strip()
        if not line_clean:
            continue
        try:
            req = json.loads(line_clean)
            resp = server.handle_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
        except Exception as ex:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal error: {str(ex)}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
