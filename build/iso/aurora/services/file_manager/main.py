"""
Aurora OS - AI File Manager Service

This service provides intelligent file management capabilities with AI-powered
organization, search, and predictive file access.

Key Features:
- AI-powered file organization and categorization
- Predictive file access based on usage patterns
- Natural language file search and commands
- Intelligent file recommendations
- Context-aware file operations
- Automated file cleanup and optimization
"""

import asyncio
import time
import logging
import json
import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime, timedelta
import sqlite3
import pickle

# AI and ML
try:
    import sklearn.feature_extraction.text as text_features
    import sklearn.metrics.pairwise as metrics
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Aurora components
from mcp.provider_manager import MCPProviderManager
from desktop.aurora_shell.ai.prediction_engine import UIPredictionEngine


class FileCategory(Enum):
    """File categorization types"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    ARCHIVE = "archive"
    CONFIG = "config"
    EXECUTABLE = "executable"
    TEMPORARY = "temporary"
    SYSTEM = "system"
    OTHER = "other"


class FileAccessPattern:
    """File access pattern analysis"""
    
    def __init__(self):
        self.access_history: Dict[str, List[float]] = {}  # file_path -> timestamps
        self.usage_frequency: Dict[str, float] = {}  # file_path -> accesses per day
        self.access_contexts: Dict[str, List[str]] = {}  # file_path -> contexts
        self.related_files: Dict[str, List[str]] = {}  # file_path -> related file paths


@dataclass
class FileMetadata:
    """Enhanced file metadata"""
    path: str
    name: str
    size: int
    created_time: float
    modified_time: float
    accessed_time: float
    category: FileCategory
    mime_type: str
    file_hash: str
    tags: List[str] = field(default_factory=list)
    content_preview: str = ""
    importance_score: float = 0.0
    access_frequency: float = 0.0
    last_access_context: str = ""
    
    # AI-generated properties
    predicted_next_access: Optional[float] = None
    suggested_location: Optional[str] = None
    related_documents: List[str] = field(default_factory=list)
    auto_tags: List[str] = field(default_factory=list)


@dataclass
class SearchQuery:
    """File search query"""
    query_text: str
    file_types: List[str] = field(default_factory=list)
    date_range: Optional[Tuple[float, float]] = None
    size_range: Optional[Tuple[int, int]] = None
    tags: List[str] = field(default_factory=list)
    content_search: bool = False
    fuzzy_match: bool = True
    limit: int = 100


@dataclass
class SearchResult:
    """File search result"""
    file_path: str
    relevance_score: float
    match_type: str  # name, content, tag, metadata
    match_details: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[FileMetadata] = None


class AIFileManager:
    """AI-powered file manager for Aurora OS"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # File system paths
        self.watch_directories = self.config.get("watch_directories", [
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads"),
            str(Path.home() / "Pictures"),
            str(Path.home() / "Videos"),
            str(Path.home() / "Music"),
            str(Path.home() / "Desktop")
        ])
        self.index_path = self.config.get("index_path", "/var/lib/aurora/file_manager.db")
        
        # Database and indexing
        self.db_connection: Optional[sqlite3.Connection] = None
        self.file_index: Dict[str, FileMetadata] = {}
        self.content_index: Dict[str, str] = {}  # file_path -> content_hash
        
        # AI components
        self.prediction_engine: Optional[UIPredictionEngine] = None
        self.access_pattern = FileAccessPattern()
        
        # File organization
        self.organization_rules: Dict[str, Any] = {}
        self.auto_organize = self.config.get("auto_organize", True)
        self.cleanup_rules: Dict[str, Any] = {}
        
        # Monitoring and updates
        self.is_monitoring = False
        self.monitor_interval = self.config.get("monitor_interval", 30)  # seconds
        self.last_scan_time = 0.0
        
        # Performance tracking
        self.stats = {
            "total_files": 0,
            "indexed_files": 0,
            "search_queries": 0,
            "auto_organized": 0,
            "cleanup_runs": 0
        }
        
        # Caching
        self.search_cache: Dict[str, List[SearchResult]] = {}
        self.cache_ttl = self.config.get("cache_ttl", 300)  # 5 minutes
        
        # Integration
        self.mcp_manager: Optional[MCPProviderManager] = None
        
        # Logging
        self.logger = logging.getLogger("ai_file_manager")
        
        # Initialize organization rules
        self._initialize_organization_rules()
    
    def _initialize_organization_rules(self) -> None:
        """Initialize file organization rules"""
        self.organization_rules = {
            "document_types": {
                ".pdf": "Documents/PDFs",
                ".docx": "Documents/Word",
                ".doc": "Documents/Word", 
                ".txt": "Documents/Text",
                ".md": "Documents/Markdown",
                ".rtf": "Documents/Text"
            },
            "image_types": {
                ".jpg": "Pictures/Photos",
                ".jpeg": "Pictures/Photos",
                ".png": "Pictures/Graphics",
                ".gif": "Pictures/Animated",
                ".svg": "Pictures/Vector",
                ".bmp": "Pictures/Bitmap"
            },
            "code_types": {
                ".py": "Development/Python",
                ".js": "Development/JavaScript",
                ".html": "Development/Web",
                ".css": "Development/Web",
                ".cpp": "Development/C++",
                ".java": "Development/Java"
            },
            "archive_types": {
                ".zip": "Archives/ZIP",
                ".tar": "Archives/TAR",
                ".gz": "Archives/Compressed",
                ".rar": "Archives/RAR"
            }
        }
        
        # Auto-cleanup rules
        self.cleanup_rules = {
            "temporary_files": {
                "patterns": ["*.tmp", "*.temp", "~*"],
                "max_age_days": 7,
                "action": "delete"
            },
            "duplicate_files": {
                "enabled": True,
                "action": "notify",
                "keep_newest": True
            },
            "old_downloads": {
                "directory": "Downloads",
                "max_age_days": 30,
                "file_types": ["*.exe", "*.dmg", "*.pkg"],
                "action": "archive"
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize the AI file manager"""
        try:
            # Initialize database
            await self._initialize_database()
            
            # Initialize AI components
            await self._initialize_ai_components()
            
            # Scan and index files
            await self._scan_directories()
            
            # Start file monitoring
            await self._start_monitoring()
            
            self.logger.info("AI File Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI file manager: {e}")
            return False
    
    async def _initialize_database(self) -> None:
        """Initialize SQLite database for file indexing"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            self.db_connection = sqlite3.connect(self.index_path)
            cursor = self.db_connection.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_time REAL NOT NULL,
                    modified_time REAL NOT NULL,
                    accessed_time REAL NOT NULL,
                    category TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    content_preview TEXT,
                    importance_score REAL DEFAULT 0.0,
                    access_frequency REAL DEFAULT 0.0,
                    last_access_context TEXT,
                    predicted_next_access REAL,
                    suggested_location TEXT,
                    related_documents TEXT,  -- JSON array
                    auto_tags TEXT,  -- JSON array
                    indexed_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    access_time REAL NOT NULL,
                    context TEXT,
                    operation TEXT,  -- read, write, execute
                    FOREIGN KEY (file_path) REFERENCES files (path)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
                CREATE INDEX IF NOT EXISTS idx_files_modified_time ON files(modified_time);
                CREATE INDEX IF NOT EXISTS idx_files_importance_score ON files(importance_score);
                CREATE INDEX IF NOT EXISTS idx_access_log_file_path ON file_access_log(file_path);
                CREATE INDEX IF NOT EXISTS idx_access_log_access_time ON file_access_log(access_time);
            """)
            
            self.db_connection.commit()
            self.logger.info("Database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _initialize_ai_components(self) -> None:
        """Initialize AI components"""
        try:
            # Initialize prediction engine
            self.prediction_engine = UIPredictionEngine()
            await self.prediction_engine.initialize()
            
            # Connect to MCP manager
            self.mcp_manager = MCPProviderManager()
            await self.mcp_manager.initialize()
            
            self.logger.info("AI components initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI components: {e}")
    
    async def _scan_directories(self) -> None:
        """Scan and index all watched directories"""
        try:
            self.logger.info(f"Scanning {len(self.watch_directories)} directories...")
            
            total_files = 0
            indexed_files = 0
            
            for directory in self.watch_directories:
                if os.path.exists(directory):
                    files_count = await self._scan_directory(directory)
                    total_files += files_count[0]
                    indexed_files += files_count[1]
            
            self.stats["total_files"] = total_files
            self.stats["indexed_files"] = indexed_files
            self.last_scan_time = time.time()
            
            self.logger.info(f"Scan completed: {total_files} files, {indexed_files} indexed")
            
        except Exception as e:
            self.logger.error(f"Directory scan failed: {e}")
    
    async def _scan_directory(self, directory: str) -> Tuple[int, int]:
        """Scan a single directory and index files"""
        total_files = 0
        indexed_files = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    try:
                        # Skip hidden files and system files
                        if file_name.startswith('.'):
                            continue
                        
                        # Extract file metadata
                        metadata = await self._extract_file_metadata(file_path)
                        
                        if metadata:
                            # Index the file
                            await self._index_file(metadata)
                            indexed_files += 1
                        
                        total_files += 1
                        
                    except Exception as e:
                        self.logger.debug(f"Failed to process file {file_path}: {e}")
                        continue
            
        except Exception as e:
            self.logger.error(f"Failed to scan directory {directory}: {e}")
        
        return total_files, indexed_files
    
    async def _extract_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """Extract comprehensive metadata from a file"""
        try:
            path_obj = Path(file_path)
            stat = path_obj.stat()
            
            # Basic file info
            name = path_obj.name
            size = stat.st_size
            created_time = stat.st_ctime
            modified_time = stat.st_mtime
            accessed_time = stat.st_atime
            
            # File categorization
            category = self._categorize_file(name, file_path)
            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            # File hash
            file_hash = await self._calculate_file_hash(file_path)
            
            # Content preview for text files
            content_preview = ""
            if category == FileCategory.DOCUMENT or mime_type.startswith('text/'):
                content_preview = await self._get_content_preview(file_path)
            
            # Create metadata object
            metadata = FileMetadata(
                path=file_path,
                name=name,
                size=size,
                created_time=created_time,
                modified_time=modified_time,
                accessed_time=accessed_time,
                category=category,
                mime_type=mime_type,
                file_hash=file_hash,
                content_preview=content_preview
            )
            
            # AI-enhanced analysis
            await self._analyze_file_with_ai(metadata)
            
            return metadata
            
        except Exception as e:
            self.logger.debug(f"Failed to extract metadata for {file_path}: {e}")
            return None
    
    def _categorize_file(self, name: str, path: str) -> FileCategory:
        """Categorize a file based on name and path"""
        name_lower = name.lower()
        
        # Check extension-based categories
        for rule_type, extensions in self.organization_rules.items():
            for ext, folder in extensions.items():
                if name_lower.endswith(ext):
                    if "document" in rule_type:
                        return FileCategory.DOCUMENT
                    elif "image" in rule_type:
                        return FileCategory.IMAGE
                    elif "code" in rule_type:
                        return FileCategory.CODE
                    elif "archive" in rule_type:
                        return FileCategory.ARCHIVE
        
        # MIME type based categorization
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            if mime_type.startswith('image/'):
                return FileCategory.IMAGE
            elif mime_type.startswith('video/'):
                return FileCategory.VIDEO
            elif mime_type.startswith('audio/'):
                return FileCategory.AUDIO
            elif mime_type.startswith('text/'):
                return FileCategory.DOCUMENT
            elif 'executable' in mime_type:
                return FileCategory.EXECUTABLE
        
        # Path-based categorization
        if '/tmp/' in path or name.startswith('.'):
            return FileCategory.TEMPORARY
        elif '/etc/' in path or '/sys/' in path:
            return FileCategory.SYSTEM
        elif name.endswith(('.conf', '.config', '.ini')):
            return FileCategory.CONFIG
        
        return FileCategory.OTHER
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest()
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    async def _get_content_preview(self, file_path: str, max_chars: int = 200) -> str:
        """Get content preview for text files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read(max_chars)
                        # Ensure valid UTF-8
                        return content.encode('utf-8', errors='ignore').decode('utf-8')
                        
                except UnicodeDecodeError:
                    continue
            
            return ""
            
        except Exception as e:
            self.logger.debug(f"Failed to get content preview for {file_path}: {e}")
            return ""
    
    async def _analyze_file_with_ai(self, metadata: FileMetadata) -> None:
        """Analyze file using AI components"""
        try:
            if not self.prediction_engine:
                return
            
            # Analyze importance based on usage patterns
            if metadata.path in self.access_pattern.usage_frequency:
                metadata.importance_score = min(1.0, self.access_pattern.usage_frequency[metadata.path] / 10.0)
                metadata.access_frequency = self.access_pattern.usage_frequency[metadata.path]
            
            # Generate auto tags
            metadata.auto_tags = await self._generate_auto_tags(metadata)
            
            # Suggest organization location
            if self.auto_organize:
                metadata.suggested_location = await self._suggest_organization_location(metadata)
            
            # Find related documents
            metadata.related_documents = await self._find_related_documents(metadata)
            
        except Exception as e:
            self.logger.debug(f"AI analysis failed for {metadata.path}: {e}")
    
    async def _generate_auto_tags(self, metadata: FileMetadata) -> List[str]:
        """Generate automatic tags for a file"""
        tags = []
        
        try:
            # Category-based tags
            tags.append(metadata.category.value)
            
            # Size-based tags
            if metadata.size > 100 * 1024 * 1024:  # > 100MB
                tags.append("large")
            elif metadata.size < 1024:  # < 1KB
                tags.append("small")
            
            # Date-based tags
            file_date = datetime.fromtimestamp(metadata.modified_time)
            if (datetime.now() - file_date).days < 7:
                tags.append("recent")
            elif (datetime.now() - file_date).days > 365:
                tags.append("old")
            
            # Path-based tags
            path_parts = metadata.path.lower().split('/')
            for part in path_parts:
                if part in ['documents', 'pictures', 'downloads', 'desktop']:
                    tags.append(part)
            
            # Content-based tags for text files
            if metadata.content_preview:
                content_lower = metadata.content_preview.lower()
                if any(keyword in content_lower for keyword in ['import', 'def', 'class', 'function']):
                    tags.append("code")
                if any(keyword in content_lower for keyword in ['todo', 'task', 'reminder']):
                    tags.append("todo")
                if any(keyword in content_lower for keyword in ['meeting', 'agenda', 'notes']):
                    tags.append("meeting")
            
        except Exception as e:
            self.logger.debug(f"Auto-tag generation failed: {e}")
        
        return list(set(tags))  # Remove duplicates
    
    async def _suggest_organization_location(self, metadata: FileMetadata) -> Optional[str]:
        """Suggest organization location for a file"""
        try:
            # Check against organization rules
            name_lower = metadata.name.lower()
            
            for rule_type, extensions in self.organization_rules.items():
                for ext, location in extensions.items():
                    if name_lower.endswith(ext):
                        return str(Path.home() / location)
            
            # Suggest based on content
            if metadata.content_preview:
                if any(keyword in metadata.content_preview.lower() 
                      for keyword in ['invoice', 'receipt', 'bill']):
                    return str(Path.home() / "Documents" / "Financial")
                
                if any(keyword in metadata.content_preview.lower() 
                      for keyword in ['contract', 'agreement', 'legal']):
                    return str(Path.home() / "Documents" / "Legal")
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Location suggestion failed: {e}")
            return None
    
    async def _find_related_documents(self, metadata: FileMetadata) -> List[str]:
        """Find related documents based on content and usage patterns"""
        related = []
        
        try:
            if not ML_AVAILABLE:
                return related
            
            # Find files with similar names
            name_without_ext = os.path.splitext(metadata.name)[0]
            for file_path, file_metadata in self.file_index.items():
                if file_path != metadata.path:
                    other_name = os.path.splitext(file_metadata.name)[0]
                    if name_without_ext.lower() in other_name.lower() or other_name.lower() in name_without_ext.lower():
                        related.append(file_path)
            
            # Could add more sophisticated content-based similarity here
            
        except Exception as e:
            self.logger.debug(f"Related documents search failed: {e}")
        
        return related[:5]  # Limit to 5 related documents
    
    async def _index_file(self, metadata: FileMetadata) -> None:
        """Index a file in the database and memory"""
        try:
            # Store in memory index
            self.file_index[metadata.path] = metadata
            
            # Store in database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO files (
                        path, name, size, created_time, modified_time, accessed_time,
                        category, mime_type, file_hash, tags, content_preview,
                        importance_score, access_frequency, last_access_context,
                        predicted_next_access, suggested_location, related_documents, auto_tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.path,
                    metadata.name,
                    metadata.size,
                    metadata.created_time,
                    metadata.modified_time,
                    metadata.accessed_time,
                    metadata.category.value,
                    metadata.mime_type,
                    metadata.file_hash,
                    json.dumps(metadata.tags),
                    metadata.content_preview,
                    metadata.importance_score,
                    metadata.access_frequency,
                    metadata.last_access_context,
                    metadata.predicted_next_access,
                    metadata.suggested_location,
                    json.dumps(metadata.related_documents),
                    json.dumps(metadata.auto_tags)
                ))
                
                self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to index file {metadata.path}: {e}")
    
    async def _start_monitoring(self) -> None:
        """Start file system monitoring"""
        try:
            self.is_monitoring = True
            
            # Start background monitoring task
            asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("File monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Periodic directory scan
                if time.time() - self.last_scan_time > self.monitor_interval:
                    await self._scan_directories()
                
                # Check for file changes and update accordingly
                await self._check_file_changes()
                
                # Perform auto-organization
                if self.auto_organize:
                    await self._perform_auto_organization()
                
                # Perform cleanup
                await self._perform_cleanup()
                
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _check_file_changes(self) -> None:
        """Check for file changes and update index"""
        try:
            # This would use inotify or similar for efficient change detection
            # For now, just do periodic rescan of recently accessed files
            
            recent_files = [
                path for path, metadata in self.file_index.items()
                if time.time() - metadata.accessed_time < 3600  # Last hour
            ]
            
            for file_path in recent_files:
                if os.path.exists(file_path):
                    # Check if file was modified
                    current_stat = os.stat(file_path)
                    stored_metadata = self.file_index[file_path]
                    
                    if current_stat.st_mtime > stored_metadata.modified_time:
                        # File was modified, re-index
                        new_metadata = await self._extract_file_metadata(file_path)
                        if new_metadata:
                            await self._index_file(new_metadata)
                
        except Exception as e:
            self.logger.debug(f"File change check failed: {e}")
    
    async def _perform_auto_organization(self) -> None:
        """Perform automatic file organization"""
        try:
            organized_count = 0
            
            for file_path, metadata in self.file_index.items():
                if metadata.suggested_location and metadata.importance_score < 0.5:
                    # Move low-importance files to suggested locations
                    if await self._move_file_to_location(file_path, metadata.suggested_location):
                        organized_count += 1
            
            if organized_count > 0:
                self.stats["auto_organized"] += organized_count
                self.logger.info(f"Auto-organized {organized_count} files")
                
        except Exception as e:
            self.logger.error(f"Auto-organization failed: {e}")
    
    async def _move_file_to_location(self, file_path: str, target_location: str) -> bool:
        """Move a file to its suggested location"""
        try:
            # Create target directory if it doesn't exist
            os.makedirs(target_location, exist_ok=True)
            
            # Generate new file path
            file_name = os.path.basename(file_path)
            new_file_path = os.path.join(target_location, file_name)
            
            # Handle name conflicts
            counter = 1
            while os.path.exists(new_file_path):
                name, ext = os.path.splitext(file_name)
                new_file_path = os.path.join(target_location, f"{name}_{counter}{ext}")
                counter += 1
            
            # Move the file
            os.rename(file_path, new_file_path)
            
            # Update index
            if file_path in self.file_index:
                metadata = self.file_index.pop(file_path)
                metadata.path = new_file_path
                self.file_index[new_file_path] = metadata
                await self._index_file(metadata)
            
            self.logger.debug(f"Moved {file_path} to {new_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move file {file_path}: {e}")
            return False
    
    async def _perform_cleanup(self) -> None:
        """Perform automatic file cleanup"""
        try:
            cleanup_count = 0
            
            # Clean up temporary files
            for rule_name, rule in self.cleanup_rules.items():
                if rule_name == "temporary_files":
                    cleanup_count += await self._cleanup_temporary_files(rule)
                elif rule_name == "old_downloads":
                    cleanup_count += await self._cleanup_old_downloads(rule)
                elif rule_name == "duplicate_files":
                    cleanup_count += await self._cleanup_duplicate_files(rule)
            
            if cleanup_count > 0:
                self.stats["cleanup_runs"] += 1
                self.logger.info(f"Cleaned up {cleanup_count} files")
                
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    async def _cleanup_temporary_files(self, rule: Dict[str, Any]) -> int:
        """Clean up temporary files"""
        cleaned = 0
        current_time = time.time()
        max_age_seconds = rule["max_age_days"] * 24 * 3600
        
        for file_path, metadata in self.file_index.items():
            if metadata.category == FileCategory.TEMPORARY:
                if current_time - metadata.created_time > max_age_seconds:
                    try:
                        os.remove(file_path)
                        del self.file_index[file_path]
                        cleaned += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to delete temporary file {file_path}: {e}")
        
        return cleaned
    
    async def _cleanup_old_downloads(self, rule: Dict[str, Any]) -> int:
        """Clean up old download files"""
        cleaned = 0
        current_time = time.time()
        max_age_seconds = rule["max_age_days"] * 24 * 3600
        
        for file_path, metadata in self.file_index.items():
            if rule["directory"] in file_path:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in rule["file_types"]:
                    if current_time - metadata.created_time > max_age_seconds:
                        try:
                            if rule["action"] == "delete":
                                os.remove(file_path)
                                del self.file_index[file_path]
                                cleaned += 1
                            elif rule["action"] == "archive":
                                # Archive instead of delete
                                archive_path = str(Path.home() / "Archive" / "Old Downloads")
                                await self._move_file_to_location(file_path, archive_path)
                                cleaned += 1
                        except Exception as e:
                            self.logger.debug(f"Failed to clean up old download {file_path}: {e}")
        
        return cleaned
    
    async def _cleanup_duplicate_files(self, rule: Dict[str, Any]) -> int:
        """Clean up duplicate files"""
        if not rule["enabled"]:
            return 0
        
        cleaned = 0
        hash_groups: Dict[str, List[str]] = {}
        
        # Group files by hash
        for file_path, metadata in self.file_index.items():
            if metadata.file_hash:
                if metadata.file_hash not in hash_groups:
                    hash_groups[metadata.file_hash] = []
                hash_groups[metadata.file_hash].append(file_path)
        
        # Process duplicates
        for file_hash, file_list in hash_groups.items():
            if len(file_list) > 1:
                # Sort by modified time (newest first)
                file_list.sort(key=lambda path: self.file_index[path].modified_time, reverse=True)
                
                # Keep newest, delete others
                for file_path in file_list[1:]:
                    try:
                        if rule["keep_newest"]:
                            os.remove(file_path)
                            del self.file_index[file_path]
                            cleaned += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to delete duplicate {file_path}: {e}")
        
        return cleaned
    
    # Public API methods
    
    async def search_files(self, query: SearchQuery) -> List[SearchResult]:
        """Search for files based on query"""
        try:
            self.stats["search_queries"] += 1
            
            # Check cache first
            cache_key = self._generate_cache_key(query)
            if cache_key in self.search_cache:
                cached_time = time.time()
                if cached_time - self.search_cache[cache_key][0].metadata.last_accessed_time < self.cache_ttl:
                    return self.search_cache[cache_key]
            
            results = []
            
            # Name-based search
            name_results = await self._search_by_name(query)
            results.extend(name_results)
            
            # Content-based search
            if query.content_search:
                content_results = await self._search_by_content(query)
                results.extend(content_results)
            
            # Tag-based search
            if query.tags:
                tag_results = await self._search_by_tags(query)
                results.extend(tag_results)
            
            # Sort by relevance score
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Apply limit
            results = results[:query.limit]
            
            # Cache results
            self.search_cache[cache_key] = results
            
            return results
            
        except Exception as e:
            self.logger.error(f"File search failed: {e}")
            return []
    
    async def _search_by_name(self, query: SearchQuery) -> List[SearchResult]:
        """Search files by name"""
        results = []
        query_terms = query.query_text.lower().split()
        
        for file_path, metadata in self.file_index.items():
            # Simple name matching
            name_match = True
            for term in query_terms:
                if term not in metadata.name.lower():
                    name_match = False
                    break
            
            if name_match:
                relevance_score = self._calculate_name_relevance(metadata.name, query.query_text)
                result = SearchResult(
                    file_path=file_path,
                    relevance_score=relevance_score,
                    match_type="name",
                    match_details={"matched_terms": query_terms},
                    metadata=metadata
                )
                results.append(result)
        
        return results
    
    async def _search_by_content(self, query: SearchQuery) -> List[SearchResult]:
        """Search files by content"""
        results = []
        
        for file_path, metadata in self.file_index.items():
            if metadata.content_preview:
                if query.query_text.lower() in metadata.content_preview.lower():
                    relevance_score = self._calculate_content_relevance(
                        metadata.content_preview, query.query_text
                    )
                    result = SearchResult(
                        file_path=file_path,
                        relevance_score=relevance_score,
                        match_type="content",
                        match_details={"preview": metadata.content_preview[:100]},
                        metadata=metadata
                    )
                    results.append(result)
        
        return results
    
    async def _search_by_tags(self, query: SearchQuery) -> List[SearchResult]:
        """Search files by tags"""
        results = []
        
        for file_path, metadata in self.file_index.items():
            all_tags = metadata.tags + metadata.auto_tags
            
            for tag in query.tags:
                if tag.lower() in [t.lower() for t in all_tags]:
                    relevance_score = 0.8
                    result = SearchResult(
                        file_path=file_path,
                        relevance_score=relevance_score,
                        match_type="tag",
                        match_details={"matched_tag": tag},
                        metadata=metadata
                    )
                    results.append(result)
                    break
        
        return results
    
    def _calculate_name_relevance(self, filename: str, query: str) -> float:
        """Calculate relevance score for name match"""
        filename_lower = filename.lower()
        query_lower = query.lower()
        
        # Exact match gets highest score
        if filename_lower == query_lower:
            return 1.0
        
        # Contains query gets high score
        if query_lower in filename_lower:
            return 0.9
        
        # Partial matches based on terms
        query_terms = query_lower.split()
        matched_terms = sum(1 for term in query_terms if term in filename_lower)
        
        if matched_terms > 0:
            return matched_terms / len(query_terms) * 0.7
        
        return 0.0
    
    def _calculate_content_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score for content match"""
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Count occurrences
        occurrences = content_lower.count(query_lower)
        
        if occurrences == 0:
            return 0.0
        
        # Score based on frequency and position
        first_pos = content_lower.find(query_lower)
        position_score = 1.0 - (first_pos / len(content))
        frequency_score = min(1.0, occurrences / 5.0)  # Normalize to max 5 occurrences
        
        return (position_score * 0.6 + frequency_score * 0.4)
    
    def _generate_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for search query"""
        import hashlib
        query_str = f"{query.query_text}_{','.join(query.file_types)}_{query.content_search}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    async def get_file_info(self, file_path: str) -> Optional[FileMetadata]:
        """Get detailed information about a file"""
        return self.file_index.get(file_path)
    
    async def update_file_access(self, file_path: str, context: str = "", operation: str = "read") -> None:
        """Update file access information"""
        try:
            if file_path in self.file_index:
                metadata = self.file_index[file_path]
                metadata.accessed_time = time.time()
                metadata.last_access_context = context
                
                # Update access pattern
                current_time = time.time()
                if file_path not in self.access_pattern.access_history:
                    self.access_pattern.access_history[file_path] = []
                
                self.access_pattern.access_history[file_path].append(current_time)
                
                # Keep only last 30 days of access history
                cutoff_time = current_time - (30 * 24 * 3600)
                self.access_pattern.access_history[file_path] = [
                    t for t in self.access_pattern.access_history[file_path] if t > cutoff_time
                ]
                
                # Calculate frequency (accesses per day)
                if len(self.access_pattern.access_history[file_path]) > 1:
                    time_span = current_time - self.access_pattern.access_history[file_path][0]
                    metadata.access_frequency = (len(self.access_pattern.access_history[file_path]) / time_span) * 86400
                
                # Record in database
                if self.db_connection:
                    cursor = self.db_connection.cursor()
                    cursor.execute("""
                        INSERT INTO file_access_log (file_path, access_time, context, operation)
                        VALUES (?, ?, ?, ?)
                    """, (file_path, current_time, context, operation))
                    self.db_connection.commit()
                
                # Update index
                await self._index_file(metadata)
                
        except Exception as e:
            self.logger.error(f"Failed to update file access: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get file manager statistics"""
        return {
            **self.stats,
            "indexed_files": len(self.file_index),
            "categories": {
                category.value: len([m for m in self.file_index.values() if m.category == category])
                for category in FileCategory
            },
            "total_size": sum(m.size for m in self.file_index.values()),
            "average_importance": sum(m.importance_score for m in self.file_index.values()) / max(1, len(self.file_index)),
            "most_accessed_files": sorted(
                [(path, m.access_frequency) for path, m in self.file_index.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            # Stop monitoring
            self.is_monitoring = False
            
            # Close database connection
            if self.db_connection:
                self.db_connection.close()
            
            # Cleanup AI components
            if self.prediction_engine:
                await self.prediction_engine.cleanup()
            
            self.logger.info("AI File Manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")


# Global file manager instance
ai_file_manager = AIFileManager()