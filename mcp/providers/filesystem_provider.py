"""
Aurora OS - MCP Filesystem Context Provider

This module provides filesystem-related context through the Model Context Protocol,
enabling the AI control plane to understand and interact with the filesystem.

Key Features:
- Real-time filesystem monitoring
- File access pattern analysis
- Storage space monitoring
- File type classification
- Security-aware file access
- Predictive file caching suggestions
"""

import os
import asyncio
import json
import time
import hashlib
import mimetypes
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiofiles
import watchdog.observers
import watchdog.events

from ..system.mcp_host import MCPProvider, MCPContext


@dataclass
class FileMetadata:
    """Metadata for a file or directory"""
    path: str
    name: str
    size: int
    modified_time: float
    created_time: float
    accessed_time: float
    is_directory: bool
    is_file: bool
    is_symlink: bool
    permissions: str
    owner: str
    group: str
    mime_type: Optional[str] = None
    file_hash: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class FileSystemStats:
    """Overall filesystem statistics"""
    total_space: int
    free_space: int
    used_space: int
    total_files: int
    total_directories: int
    largest_files: List[Dict[str, Any]]
    most_recent_files: List[Dict[str, Any]]
    file_type_distribution: Dict[str, int]
    access_patterns: Dict[str, int]


@dataclass
class AccessPattern:
    """File access pattern data"""
    path: str
    access_count: int
    last_access: float
    access_frequency: float  # accesses per hour
    predicted_next_access: Optional[float] = None
    access_type: str = "read"  # read, write, execute


class FileSystemEventHandler(watchdog.events.FileSystemEventHandler):
    """File system event handler for monitoring changes"""
    
    def __init__(self, provider):
        self.provider = provider
        self.event_queue = asyncio.Queue()
        super().__init__()
    
    def on_created(self, event):
        if not event.is_directory:
            asyncio.create_task(self.provider._handle_file_created(event.src_path))
    
    def on_modified(self, event):
        if not event.is_directory:
            asyncio.create_task(self.provider._handle_file_modified(event.src_path))
    
    def on_deleted(self, event):
        asyncio.create_task(self.provider._handle_file_deleted(event.src_path))
    
    def on_moved(self, event):
        asyncio.create_task(self.provider._handle_file_moved(event.src_path, event.dest_path))


class FileSystemContextProvider(MCPProvider):
    """MCP Provider for filesystem context"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("filesystem", "Aurora OS Filesystem Provider", "1.0.0")
        self.logger = logging.getLogger(f"mcp_filesystem_provider")
        
        self.monitored_paths = config.get("monitored_paths", ["~/"])
        self.max_files_cached = config.get("max_files_cached", 10000)
        self.update_interval = config.get("update_interval", 30)  # seconds
        self.enable_hashing = config.get("enable_hashing", False)
        self.track_access_patterns = config.get("track_access_patterns", True)
        
        # Internal state
        self.file_cache: Dict[str, FileMetadata] = {}
        self.access_patterns: Dict[str, AccessPattern] = {}
        self.filesystem_stats: Optional[FileSystemStats] = None
        self.last_scan_time = 0
        self.observer = None
        
        # Performance metrics
        self.scan_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def initialize(self) -> bool:
        """Initialize the filesystem provider"""
        try:
            # Start file system monitoring
            self.observer = watchdog.observers.Observer()
            
            for path_str in self.monitored_paths:
                path = Path(path_str).expanduser()
                if path.exists():
                    self.observer.schedule(
                        FileSystemEventHandler(self),
                        str(path),
                        recursive=True
                    )
            
            self.observer.start()
            
            # Perform initial scan
            await self._scan_filesystem()
            
            # Start periodic update task
            asyncio.create_task(self._periodic_update())
            
            self.logger.info(f"Filesystem provider initialized for paths: {self.monitored_paths}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize filesystem provider: {e}")
            return False
    
    async def get_context_data(self, request: Dict[str, Any]) -> MCPContext:
        """Get filesystem context data"""
        start_time = time.time()
        
        try:
            context_type = request.get("type", "overview")
            path_filter = request.get("path", None)
            include_patterns = request.get("include_patterns", [])
            exclude_patterns = request.get("exclude_patterns", [])
            
            if context_type == "overview":
                data = await self._get_overview_context()
            elif context_type == "file_info":
                file_path = request.get("file_path")
                data = await self._get_file_context(file_path)
            elif context_type == "directory":
                dir_path = request.get("directory_path", "~")
                data = await self._get_directory_context(dir_path)
            elif context_type == "access_patterns":
                data = await self._get_access_patterns_context()
            elif context_type == "storage_analysis":
                data = await self._get_storage_analysis_context()
            else:
                data = {"error": f"Unknown context type: {context_type}"}
            
            processing_time = time.time() - start_time
            
            return MCPContext(context_id=f"ctx_{int(time.time()*1000)}_{os.urandom(4).hex()}", 
                provider_id=self.provider_id,
                context_type=context_type,
                data=data,
                timestamp=time.time(),
                metadata={
                    "processing_time": processing_time,
                    "cache_stats": {
                        "hits": self.cache_hits,
                        "misses": self.cache_misses,
                        "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
                    },
                    "monitored_paths": self.monitored_paths,
                    "total_files_cached": len(self.file_cache)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting filesystem context: {e}")
            return MCPContext(context_id=f"ctx_{int(time.time()*1000)}_{os.urandom(4).hex()}", 
                provider_id=self.provider_id,
                context_type="error",
                data={"error": str(e)},
                timestamp=time.time(),
                metadata={"error": True}
            )
    
    async def _scan_filesystem(self) -> None:
        """Scan and cache filesystem metadata"""
        try:
            scan_start = time.time()
            total_files = 0
            total_directories = 0
            file_type_dist = {}
            
            for path_str in self.monitored_paths:
                path = Path(path_str).expanduser()
                if not path.exists():
                    continue
                
                for root, dirs, files in os.walk(path):
                    # Process directories
                    for dir_name in dirs:
                        dir_path = Path(root) / dir_name
                        metadata = await self._get_file_metadata(dir_path)
                        if metadata:
                            self.file_cache[str(dir_path)] = metadata
                            total_directories += 1
                    
                    # Process files
                    for file_name in files:
                        file_path = Path(root) / file_name
                        try:
                            metadata = await self._get_file_metadata(file_path)
                            if metadata:
                                self.file_cache[str(file_path)] = metadata
                                total_files += 1
                                
                                # Update file type distribution
                                if metadata.mime_type:
                                    file_type_dist[metadata.mime_type] = file_type_dist.get(metadata.mime_type, 0) + 1
                            
                            # Limit cache size
                            if len(self.file_cache) > self.max_files_cached:
                                self._cleanup_cache()
                                
                        except (OSError, PermissionError) as e:
                            self.logger.debug(f"Skipping file {file_path}: {e}")
                            continue
            
            # Update filesystem statistics
            self.filesystem_stats = await self._calculate_filesystem_stats()
            
            scan_time = time.time() - scan_start
            self.last_scan_time = time.time()
            self.scan_count += 1
            
            self.logger.info(f"Filesystem scan completed: {total_files} files, {total_directories} dirs in {scan_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error during filesystem scan: {e}")
    
    async def _get_file_metadata(self, path: Path) -> Optional[FileMetadata]:
        """Get metadata for a specific file or directory"""
        try:
            if not path.exists():
                return None
            
            stat = path.stat()
            
            # Basic metadata
            metadata = FileMetadata(
                path=str(path),
                name=path.name,
                size=stat.st_size,
                modified_time=stat.st_mtime,
                created_time=stat.st_ctime,
                accessed_time=stat.st_atime,
                is_directory=path.is_dir(),
                is_file=path.is_file(),
                is_symlink=path.is_symlink(),
                permissions=oct(stat.st_mode)[-3:],
                owner=str(stat.st_uid),
                group=str(stat.st_gid)
            )
            
            # MIME type for files
            if metadata.is_file:
                mime_type, _ = mimetypes.guess_type(str(path))
                metadata.mime_type = mime_type
            
            # File hash (if enabled and for small files)
            if self.enable_hashing and metadata.is_file and metadata.size < 10 * 1024 * 1024:  # 10MB limit
                metadata.file_hash = await self._calculate_file_hash(path)
            
            # Smart tags based on file properties
            metadata.tags = self._generate_file_tags(metadata)
            
            return metadata
            
        except Exception as e:
            self.logger.debug(f"Error getting metadata for {path}: {e}")
            return None
    
    async def _calculate_file_hash(self, path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        try:
            hash_obj = hashlib.sha256()
            async with aiofiles.open(path, 'rb') as f:
                while chunk := await f.read(8192):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.debug(f"Error calculating hash for {path}: {e}")
            return ""
    
    def _generate_file_tags(self, metadata: FileMetadata) -> List[str]:
        """Generate smart tags for a file"""
        tags = []
        
        # File type tags
        if metadata.is_directory:
            tags.append("directory")
        elif metadata.is_file:
            tags.append("file")
        
        if metadata.is_symlink:
            tags.append("symlink")
        
        # Size-based tags
        if metadata.size == 0:
            tags.append("empty")
        elif metadata.size < 1024:
            tags.append("small")
        elif metadata.size > 100 * 1024 * 1024:  # 100MB
            tags.append("large")
        
        # Time-based tags
        now = time.time()
        age_days = (now - metadata.modified_time) / (24 * 3600)
        
        if age_days < 1:
            tags.append("recent")
        elif age_days > 365:
            tags.append("old")
        
        # MIME type based tags
        if metadata.mime_type:
            if "image/" in metadata.mime_type:
                tags.append("image")
            elif "video/" in metadata.mime_type:
                tags.append("video")
            elif "audio/" in metadata.mime_type:
                tags.append("audio")
            elif "text/" in metadata.mime_type:
                tags.append("text")
            elif "application/pdf" in metadata.mime_type:
                tags.append("document")
            elif "application/zip" in metadata.mime_type or "application/x-tar" in metadata.mime_type:
                tags.append("archive")
        
        return tags
    
    async def _get_overview_context(self) -> Dict[str, Any]:
        """Get filesystem overview context"""
        if not self.filesystem_stats:
            await self._scan_filesystem()
        
        return {
            "statistics": asdict(self.filesystem_stats) if self.filesystem_stats else {},
            "monitored_paths": self.monitored_paths,
            "cache_status": {
                "total_files": len(self.file_cache),
                "cache_size": self.max_files_cached,
                "last_scan": self.last_scan_time
            },
            "recent_activity": await self._get_recent_activity()
        }
    
    async def _get_file_context(self, file_path: str) -> Dict[str, Any]:
        """Get detailed context for a specific file"""
        if not file_path:
            return {"error": "File path not provided"}
        
        # Check cache first
        if file_path in self.file_cache:
            self.cache_hits += 1
            metadata = self.file_cache[file_path]
        else:
            self.cache_misses += 1
            path = Path(file_path)
            metadata = await self._get_file_metadata(path)
            if metadata:
                self.file_cache[file_path] = metadata
        
        if not metadata:
            return {"error": f"File not found: {file_path}"}
        
        result = asdict(metadata)
        
        # Add access pattern if available
        if file_path in self.access_patterns:
            result["access_pattern"] = asdict(self.access_patterns[file_path])
        
        # Add related files (same directory, similar names)
        result["related_files"] = await self._find_related_files(file_path)
        
        return result
    
    async def _get_directory_context(self, dir_path: str) -> Dict[str, Any]:
        """Get context for a directory"""
        path = Path(dir_path).expanduser()
        
        if not path.exists() or not path.is_dir():
            return {"error": f"Directory not found: {dir_path}"}
        
        # Get directory metadata
        dir_metadata = await self._get_file_metadata(path)
        
        # List contents
        contents = []
        try:
            for item in path.iterdir():
                item_metadata = await self._get_file_metadata(item)
                if item_metadata:
                    contents.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item_metadata.size,
                        "modified": item_metadata.modified_time,
                        "mime_type": item_metadata.mime_type,
                        "tags": item_metadata.tags
                    })
        except PermissionError:
            pass
        
        # Sort by type and name
        contents.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        
        return {
            "metadata": asdict(dir_metadata) if dir_metadata else {},
            "contents": contents,
            "total_items": len(contents),
            "subdirectory_count": sum(1 for item in contents if item["type"] == "directory"),
            "file_count": sum(1 for item in contents if item["type"] == "file"),
            "total_size": sum(item["size"] for item in contents if item["type"] == "file")
        }
    
    async def _get_access_patterns_context(self) -> Dict[str, Any]:
        """Get file access patterns context"""
        if not self.track_access_patterns:
            return {"error": "Access pattern tracking is disabled"}
        
        patterns = []
        for path, pattern in self.access_patterns.items():
            patterns.append({
                "path": path,
                "access_count": pattern.access_count,
                "last_access": pattern.last_access,
                "frequency": pattern.access_frequency,
                "predicted_next": pattern.predicted_next_access,
                "access_type": pattern.access_type
            })
        
        # Sort by access frequency
        patterns.sort(key=lambda x: x["frequency"], reverse=True)
        
        return {
            "patterns": patterns[:100],  # Top 100 files
            "total_tracked": len(self.access_patterns),
            "insights": await self._analyze_access_patterns()
        }
    
    async def _get_storage_analysis_context(self) -> Dict[str, Any]:
        """Get storage analysis context"""
        if not self.filesystem_stats:
            await self._scan_filesystem()
        
        # Analyze storage usage by file type
        type_usage = {}
        for metadata in self.file_cache.values():
            if metadata.mime_type and metadata.is_file:
                type_usage[metadata.mime_type] = type_usage.get(metadata.mime_type, 0) + metadata.size
        
        # Find large files
        large_files = []
        for path, metadata in self.file_cache.items():
            if metadata.is_file and metadata.size > 10 * 1024 * 1024:  # > 10MB
                large_files.append({
                    "path": path,
                    "size": metadata.size,
                    "modified": metadata.modified_time,
                    "mime_type": metadata.mime_type
                })
        
        large_files.sort(key=lambda x: x["size"], reverse=True)
        
        return {
            "overall_stats": asdict(self.filesystem_stats) if self.filesystem_stats else {},
            "usage_by_type": dict(sorted(type_usage.items(), key=lambda x: x[1], reverse=True)),
            "large_files": large_files[:50],  # Top 50 largest files
            "storage_optimization_suggestions": await self._generate_storage_suggestions()
        }
    
    async def _calculate_filesystem_stats(self) -> FileSystemStats:
        """Calculate overall filesystem statistics"""
        total_files = 0
        total_directories = 0
        total_size = 0
        file_type_dist = {}
        largest_files = []
        most_recent_files = []
        
        for metadata in self.file_cache.values():
            if metadata.is_file:
                total_files += 1
                total_size += metadata.size
                
                if metadata.mime_type:
                    file_type_dist[metadata.mime_type] = file_type_dist.get(metadata.mime_type, 0) + 1
                
                # Track large files
                if len(largest_files) < 10:
                    largest_files.append({
                        "path": metadata.path,
                        "size": metadata.size,
                        "name": metadata.name
                    })
                    largest_files.sort(key=lambda x: x["size"], reverse=True)
                elif metadata.size > largest_files[-1]["size"]:
                    largest_files[-1] = {
                        "path": metadata.path,
                        "size": metadata.size,
                        "name": metadata.name
                    }
                    largest_files.sort(key=lambda x: x["size"], reverse=True)
                
                # Track recent files
                if len(most_recent_files) < 10:
                    most_recent_files.append({
                        "path": metadata.path,
                        "modified": metadata.modified_time,
                        "name": metadata.name
                    })
                    most_recent_files.sort(key=lambda x: x["modified"], reverse=True)
                elif metadata.modified_time > most_recent_files[-1]["modified"]:
                    most_recent_files[-1] = {
                        "path": metadata.path,
                        "modified": metadata.modified_time,
                        "name": metadata.name
                    }
                    most_recent_files.sort(key=lambda x: x["modified"], reverse=True)
                
            elif metadata.is_directory:
                total_directories += 1
        
        # Get disk usage
        disk_usage = await self._get_disk_usage()
        
        return FileSystemStats(
            total_space=disk_usage["total"],
            free_space=disk_usage["free"],
            used_space=disk_usage["used"],
            total_files=total_files,
            total_directories=total_directories,
            largest_files=largest_files,
            most_recent_files=most_recent_files,
            file_type_distribution=file_type_dist,
            access_patterns=dict(self.access_patterns)
        )
    
    async def _get_disk_usage(self) -> Dict[str, int]:
        """Get disk usage statistics"""
        try:
            # Use the first monitored path's disk
            first_path = Path(self.monitored_paths[0]).expanduser()
            if first_path.exists():
                stat = os.statvfs(str(first_path))
                return {
                    "total": stat.f_blocks * stat.f_frsize,
                    "free": stat.f_bavail * stat.f_frsize,
                    "used": (stat.f_blocks - stat.f_bavail) * stat.f_frsize
                }
        except Exception as e:
            self.logger.error(f"Error getting disk usage: {e}")
        
        return {"total": 0, "free": 0, "used": 0}
    
    async def _find_related_files(self, file_path: str) -> List[Dict[str, Any]]:
        """Find files related to the given file"""
        related = []
        path = Path(file_path)
        
        if not path.exists():
            return related
        
        # Files in the same directory
        try:
            for sibling in path.parent.iterdir():
                if sibling != path and sibling.is_file():
                    sibling_meta = self.file_cache.get(str(sibling))
                    if sibling_meta:
                        related.append({
                            "path": str(sibling),
                            "name": sibling.name,
                            "relationship": "same_directory",
                            "similarity": self._calculate_file_similarity(path, sibling)
                        })
        except PermissionError:
            pass
        
        # Sort by similarity and return top 5
        related.sort(key=lambda x: x["similarity"], reverse=True)
        return related[:5]
    
    def _calculate_file_similarity(self, file1: Path, file2: Path) -> float:
        """Calculate similarity between two files"""
        similarity = 0.0
        
        # Same extension
        if file1.suffix == file2.suffix:
            similarity += 0.3
        
        # Similar names (common prefix/suffix)
        name1_parts = file1.stem.lower().split()
        name2_parts = file2.stem.lower().split()
        common_parts = set(name1_parts) & set(name2_parts)
        if common_parts:
            similarity += 0.4 * len(common_parts) / max(len(name1_parts), len(name2_parts))
        
        # Size similarity
        meta1 = self.file_cache.get(str(file1))
        meta2 = self.file_cache.get(str(file2))
        if meta1 and meta2 and meta1.size > 0 and meta2.size > 0:
            size_ratio = min(meta1.size, meta2.size) / max(meta1.size, meta2.size)
            similarity += 0.3 * size_ratio
        
        return similarity
    
    async def _analyze_access_patterns(self) -> Dict[str, Any]:
        """Analyze access patterns and provide insights"""
        insights = []
        
        if not self.access_patterns:
            return {"insights": insights}
        
        # Find most frequently accessed files
        frequent_files = sorted(
            self.access_patterns.items(),
            key=lambda x: x[1].access_frequency,
            reverse=True
        )[:10]
        
        insights.append({
            "type": "frequent_access",
            "description": "Most frequently accessed files",
            "files": [{"path": path, "frequency": pattern.access_frequency} 
                     for path, pattern in frequent_files]
        })
        
        # Find files that haven't been accessed recently
        now = time.time()
        stale_files = [
            path for path, pattern in self.access_patterns.items()
            if now - pattern.last_access > 7 * 24 * 3600  # 7 days
        ]
        
        if stale_files:
            insights.append({
                "type": "stale_files",
                "description": "Files not accessed in the last 7 days",
                "count": len(stale_files),
                "files": stale_files[:10]  # Show first 10
            })
        
        return {"insights": insights}
    
    async def _generate_storage_suggestions(self) -> List[Dict[str, Any]]:
        """Generate storage optimization suggestions"""
        suggestions = []
        
        if not self.filesystem_stats:
            return suggestions
        
        # Low space warning
        space_usage_percent = (self.filesystem_stats.used_space / self.filesystem_stats.total_space) * 100
        if space_usage_percent > 80:
            suggestions.append({
                "type": "low_space",
                "priority": "high",
                "description": f"Disk usage is {space_usage_percent:.1f}%. Consider cleaning up files.",
                "action": "cleanup"
            })
        
        # Duplicate file suggestions (simplified)
        extensions = {}
        for metadata in self.file_cache.values():
            if metadata.is_file and metadata.mime_type:
                if "image/" in metadata.mime_type:
                    extensions["images"] = extensions.get("images", 0) + 1
                elif "video/" in metadata.mime_type:
                    extensions["videos"] = extensions.get("videos", 0) + 1
        
        for ext_type, count in extensions.items():
            if count > 100:
                suggestions.append({
                    "type": "media_cleanup",
                    "priority": "medium",
                    "description": f"You have {count} {ext_type}. Consider organizing or removing old ones.",
                    "action": "organize_media"
                })
        
        return suggestions
    
    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent filesystem activity"""
        activity = []
        
        # Get recently modified files
        recent_files = []
        now = time.time()
        for metadata in self.file_cache.values():
            if now - metadata.modified_time < 24 * 3600:  # Last 24 hours
                recent_files.append(metadata)
        
        recent_files.sort(key=lambda x: x.modified_time, reverse=True)
        
        for metadata in recent_files[:20]:
            activity.append({
                "type": "file_modified",
                "path": metadata.path,
                "timestamp": metadata.modified_time,
                "size": metadata.size
            })
        
        return activity
    
    def _cleanup_cache(self) -> None:
        """Clean up old entries from cache"""
        if len(self.file_cache) <= self.max_files_cached:
            return
        
        # Sort by last access time and remove oldest
        sorted_items = sorted(
            self.file_cache.items(),
            key=lambda x: x[1].accessed_time
        )
        
        # Remove oldest 10% of entries
        remove_count = int(self.max_files_cached * 0.1)
        for path, _ in sorted_items[:remove_count]:
            del self.file_cache[path]
    
    async def _periodic_update(self) -> None:
        """Periodic update task"""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                await self._scan_filesystem()
            except Exception as e:
                self.logger.error(f"Error in periodic update: {e}")
    
    # Event handlers for file system monitoring
    async def _handle_file_created(self, file_path: str) -> None:
        """Handle file creation event"""
        path = Path(file_path)
        metadata = await self._get_file_metadata(path)
        if metadata:
            self.file_cache[file_path] = metadata
            self.logger.debug(f"File created: {file_path}")
    
    async def _handle_file_modified(self, file_path: str) -> None:
        """Handle file modification event"""
        path = Path(file_path)
        metadata = await self._get_file_metadata(path)
        if metadata:
            self.file_cache[file_path] = metadata
            self.logger.debug(f"File modified: {file_path}")
    
    async def _handle_file_deleted(self, file_path: str) -> None:
        """Handle file deletion event"""
        if file_path in self.file_cache:
            del self.file_cache[file_path]
        if file_path in self.access_patterns:
            del self.access_patterns[file_path]
        self.logger.debug(f"File deleted: {file_path}")
    
    async def _handle_file_moved(self, old_path: str, new_path: str) -> None:
        """Handle file move event"""
        if old_path in self.file_cache:
            metadata = self.file_cache.pop(old_path)
            metadata.path = new_path
            metadata.name = Path(new_path).name
            self.file_cache[new_path] = metadata
        
        if old_path in self.access_patterns:
            pattern = self.access_patterns.pop(old_path)
            pattern.path = new_path
            self.access_patterns[new_path] = pattern
        
        self.logger.debug(f"File moved: {old_path} -> {new_path}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.file_cache.clear()
        self.access_patterns.clear()
        self.logger.info("Filesystem provider cleaned up")
    
    def get_capabilities(self) -> List[str]:
        """Get provider capabilities"""
        return [
            "file_monitoring",
            "metadata_extraction",
            "access_pattern_tracking",
            "storage_analysis",
            "file_classification",
            "real_time_updates"
        ]
    async def start(self) -> bool:
        """Start the filesystem provider"""
        try:
            if not self.is_started:
                # Start file monitoring
                if self.observer:
                    self.observer.start()
                
                # Start background tasks
                asyncio.create_task(self._periodic_scan())
                asyncio.create_task(self._update_access_patterns())
                
                self.is_started = True
                self.logger.info("Filesystem provider started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start filesystem provider: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the filesystem provider"""
        try:
            if self.is_started:
                # Stop file monitoring
                if self.observer:
                    self.observer.stop()
                    self.observer.join()
                
                self.is_started = False
                self.logger.info("Filesystem provider stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop filesystem provider: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Check basic health indicators
            if not self.is_started:
                return False
            
            # Check if scan is overdue
            if self.last_scan_time > 0:
                time_since_scan = time.time() - self.last_scan_time
                if time_since_scan > self.update_interval * 3:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def get_context(self, request: Dict[str, Any]) -> MCPContext:
        """Get filesystem context"""
        return await self.get_context_data(request)
