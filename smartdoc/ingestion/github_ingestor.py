"""
GitHub repository ingestor with code-aware chunking.
"""

from pathlib import Path
from typing import Dict, Any, List
import logging
import shutil
import tempfile
from datetime import datetime
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError

from .base_ingestor import BaseIngestor
from ..config import (
    GITHUB_EXTENSIONS,
    GITHUB_EXCLUDE_DIRS,
    CODE_CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_FILE_SIZE_WARNING,
    MAX_FILE_SIZE_HARD,
    GITHUB_TOKEN
)

logger = logging.getLogger(__name__)


class GitHubIngestor(BaseIngestor):
    """Ingest GitHub repositories with code-aware chunking."""
    
    def validate_source(self, source: str) -> bool:
        """Validate GitHub repository URL."""
        try:
            parsed = urlparse(source)
            return 'github.com' in parsed.netloc
        except:
            return False
    
    def ingest(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Ingest a GitHub repository.
        
        Args:
            source: GitHub repository URL
            **kwargs:
                - branch: str (default: main/master)
                - extensions: List[str] (override default extensions)
                - max_depth: int (limit directory depth)
        
        Returns:
            Dict with ingestion results
        """
        if not self.validate_source(source):
            raise ValueError(f"Invalid GitHub URL: {source}")
        
        self.log_ingestion_start(source, 'github')
        
        # Parse repo info
        repo_info = self._parse_repo_url(source)
        
        # Add to registry
        source_id = self.registry.add_source(
            source_type='github',
            source_path=source,
            metadata=repo_info
        )
        
        temp_dir = None
        
        try:
            # Clone repository
            logger.info(f"Cloning {repo_info['owner']}/{repo_info['repo']}...")
            temp_dir = tempfile.mkdtemp()
            repo = self._clone_repo(source, temp_dir, kwargs.get('branch'))
            
            # Get commit info
            commit_sha = repo.head.commit.hexsha
            commit_date = datetime.fromtimestamp(repo.head.commit.committed_date).isoformat()
            
            # Scan and process files
            logger.info("Scanning repository files...")
            files = self._scan_repository(
                Path(temp_dir),
                extensions=kwargs.get('extensions', GITHUB_EXTENSIONS),
                max_depth=kwargs.get('max_depth')
            )
            
            logger.info(f"Found {len(files)} files to process")
            
            # Process files
            chunks = self._process_files(files, temp_dir, source)
            
            # Store in ChromaDB
            self._store_chunks(chunks, source, commit_sha)
            
            # Update registry
            metadata = {
                'owner': repo_info['owner'],
                'repo': repo_info['repo'],
                'commit_sha': commit_sha,
                'commit_date': commit_date,
                'files_processed': len(files),
                'total_chunks': len(chunks),
                'branch': kwargs.get('branch', 'main')
            }
            self.registry.update_status(source, 'success', metadata)
            
            self.log_ingestion_complete(source, len(chunks))
            
            return {
                'status': 'success',
                'source': source,
                'chunks_added': len(chunks),
                'files_processed': len(files),
                'commit_sha': commit_sha,
                'metadata': metadata
            }
            
        except Exception as e:
            self.log_ingestion_error(source, e)
            self.registry.update_status(source, 'failed', {'error': str(e)})
            raise
        
        finally:
            # Cleanup temp directory
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
                logger.info("Cleaned up temporary clone")
    
    def _parse_repo_url(self, url: str) -> Dict[str, str]:
        """Parse GitHub URL to extract owner and repo."""
        # Handle various URL formats
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        
        parsed = urlparse(url)
        
        if parsed.netloc == 'github.com':
            # HTTPS URL
            parts = parsed.path.strip('/').split('/')
            owner = parts[0]
            repo = parts[1].replace('.git', '')
        else:
            # SSH URL: git@github.com:owner/repo.git
            if '@github.com:' in url:
                path = url.split(':')[1]
                parts = path.strip('/').split('/')
                owner = parts[0]
                repo = parts[1].replace('.git', '')
            else:
                raise ValueError(f"Unsupported GitHub URL format: {url}")
        
        return {
            'owner': owner,
            'repo': repo,
            'url': url
        }
    
    def _clone_repo(self, url: str, target_dir: str, branch: str = None) -> Repo:
        """Clone GitHub repository."""
        # Modify URL to include token if available
        if GITHUB_TOKEN and url.startswith('https://github.com'):
            url = url.replace('https://github.com', f'https://{GITHUB_TOKEN}@github.com')
        
        try:
            if branch:
                repo = Repo.clone_from(url, target_dir, branch=branch, depth=1)
            else:
                # Try main first, fallback to master
                try:
                    repo = Repo.clone_from(url, target_dir, branch='main', depth=1)
                except GitCommandError:
                    repo = Repo.clone_from(url, target_dir, branch='master', depth=1)
            
            return repo
        
        except GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            raise
    
    def _scan_repository(
        self,
        repo_path: Path,
        extensions: List[str],
        max_depth: int = None
    ) -> List[Path]:
        """Scan repository for processable files."""
        files = []
        
        for file_path in repo_path.rglob('*'):
            # Skip if not a file
            if not file_path.is_file():
                continue
            
            # Check depth
            if max_depth:
                relative = file_path.relative_to(repo_path)
                if len(relative.parts) > max_depth:
                    continue
            
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in GITHUB_EXCLUDE_DIRS):
                continue
            
            # Check extension
            if file_path.suffix.lower() in extensions:
                files.append(file_path)
        
        return files
    
    def _process_files(
        self,
        files: List[Path],
        repo_root: str,
        source_url: str
    ) -> List[Dict[str, Any]]:
        """Process files and create chunks."""
        chunks = []
        repo_root_path = Path(repo_root)
        
        for file_path in files:
            try:
                # Check file size
                if not self.check_file_size(file_path, MAX_FILE_SIZE_WARNING, MAX_FILE_SIZE_HARD):
                    logger.info(f"Skipping large file: {file_path.name}")
                    continue
                
                # Read file content
                try:
                    content = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    logger.warning(f"Skipping binary file: {file_path.name}")
                    continue
                
                # Detect language
                language = self._detect_language(file_path)
                
                # Chunk content
                file_chunks = self._chunk_code(content, language)
                
                # Get relative path
                relative_path = file_path.relative_to(repo_root_path)
                
                # Create chunks with metadata
                for chunk_idx, chunk_text in enumerate(file_chunks):
                    chunks.append({
                        'content': chunk_text,
                        'file_path': str(relative_path),
                        'language': language,
                        'chunk_index': chunk_idx,
                        'source_url': source_url
                    })
                
            except Exception as e:
                logger.warning(f"Failed to process {file_path.name}: {e}")
        
        return chunks
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()
        
        language_map = {
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'cpp',
            '.hpp': 'cpp',
            '.ino': 'arduino',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.rs': 'rust',
            '.go': 'go',
            '.md': 'markdown',
            '.txt': 'text',
            '.rst': 'restructuredtext'
        }
        
        return language_map.get(ext, 'unknown')
    
    def _chunk_code(self, code: str, language: str) -> List[str]:
        """Chunk code with language-aware splitting."""
        if language == 'markdown' or language == 'text':
            # For documentation, use regular text chunking
            return self.chunk_text(code, CODE_CHUNK_SIZE * 2, CHUNK_OVERLAP)
        
        # For code, try to preserve function/class boundaries
        return self._chunk_code_smart(code)
    
    def _chunk_code_smart(self, code: str) -> List[str]:
        """
        Smart code chunking that tries to preserve function/class boundaries.
        Falls back to simple chunking if parsing fails.
        """
        # Simple heuristic: split on function definitions
        lines = code.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # Check if this line starts a new function/class
            is_boundary = any(keyword in line for keyword in [
                'def ', 'class ', 'function ', 'void ', 'int ', 'bool '
            ]) and '{' in line or '(' in line
            
            # If we're at a boundary and chunk is getting large, start new chunk
            if is_boundary and current_size > CODE_CHUNK_SIZE * 0.5:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
                
                # If chunk is too large, force split
                if current_size > CODE_CHUNK_SIZE * 1.5:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks if chunks else [code]
    
    def _store_chunks(self, chunks: List[Dict[str, Any]], source_url: str, commit_sha: str):
        """Store chunks in ChromaDB."""
        if not chunks:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, chunk in enumerate(chunks):
            # Generate unique ID
            content_hash = self.hash_content(chunk['content'])
            chunk_id = self.generate_chunk_id(source_url, idx, content_hash)
            
            # Prepare metadata
            metadata = {
                'source': source_url,
                'source_type': 'github',
                'content_type': 'code',
                'file_path': chunk['file_path'],
                'language': chunk['language'],
                'chunk_index': chunk['chunk_index'],
                'commit_sha': commit_sha,
                'indexed_at': datetime.now().isoformat()
            }
            
            documents.append(chunk['content'])
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        # Add to ChromaDB
        self.chroma.add_documents(documents, metadatas, ids)

