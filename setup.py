"""
Setup script for MCP Browser.

This package is developed exclusively by AI assistants.
"""

from setuptools import setup, find_packages, Command
import os
import sys
import subprocess
from pathlib import Path
import asyncio


class GenerateAIDocs(Command):
    """Generate AI-friendly documentation."""
    description = 'Generate documentation for AI navigation'
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        """Run all AI documentation generators."""
        print("Generating AI-friendly documentation...")
        
        # 1. Generate API documentation
        try:
            subprocess.run([sys.executable, '-m', 'pydoc', '-w', '.'], 
                         cwd='mcp_browser', check=True)
            print("✓ Generated pydoc API documentation")
        except Exception as e:
            print(f"⚠ pydoc generation failed: {e}")
        
        # 2. Generate ctags for code navigation
        try:
            subprocess.run(['ctags', '-R', '--languages=Python', 
                          '--python-kinds=-i', '-f', '.tags'], check=True)
            print("✓ Generated ctags file")
        except FileNotFoundError:
            print("⚠ ctags not installed (install with: apt-get install universal-ctags)")
        except Exception as e:
            print(f"⚠ ctags generation failed: {e}")
        
        # 3. Generate structure documentation
        self.generate_structure_doc()
        
        # 4. Generate API summary
        self.generate_api_summary()
        
        print("\nAI documentation generation complete!")
        print("Files created:")
        print("  - docs/STRUCTURE.md - Project structure overview")
        print("  - docs/API_SUMMARY.md - API quick reference")
        print("  - .tags - ctags for code navigation")
        print("  - *.html - pydoc HTML documentation")
    
    def generate_structure_doc(self):
        """Generate project structure documentation."""
        structure = []
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            level = root.replace('.', '').count(os.sep)
            indent = '  ' * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            
            subindent = '  ' * (level + 1)
            for file in sorted(files):
                if file.endswith('.py'):
                    structure.append(f"{subindent}{file}")
        
        os.makedirs('docs', exist_ok=True)
        with open('docs/STRUCTURE.md', 'w') as f:
            f.write("# Project Structure\n\n")
            f.write("```\n")
            f.write('\n'.join(structure))
            f.write("\n```\n")
    
    def generate_api_summary(self):
        """Generate API summary for quick reference."""
        api_summary = []
        api_summary.append("# MCP Browser API Summary\n")
        api_summary.append("## Main Classes\n")
        
        # Extract main classes and methods
        main_files = [
            ('mcp_browser/proxy.py', 'MCPBrowser'),
            ('mcp_browser/registry.py', 'ToolRegistry'),
            ('mcp_browser/server.py', 'MCPServer'),
            ('mcp_browser/multi_server.py', 'MultiServerManager'),
        ]
        
        for file_path, class_name in main_files:
            if os.path.exists(file_path):
                api_summary.append(f"\n### {class_name} ({file_path})\n")
                # Simple method extraction (could be enhanced)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip().startswith('def ') and not line.strip().startswith('def _'):
                                method = line.strip()[4:].split('(')[0]
                                api_summary.append(f"- `{method}()`")
                except Exception:
                    pass
        
        os.makedirs('docs', exist_ok=True)
        with open('docs/API_SUMMARY.md', 'w') as f:
            f.write('\n'.join(api_summary))


class TestCommand(Command):
    """Run all tests including integration tests."""
    description = 'Run unit and integration tests'
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        """Run all tests."""
        print("Running MCP Browser Tests")
        print("=" * 50)
        
        # Run pytest for unit tests
        print("\nRunning unit tests with pytest...")
        try:
            subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v', 
                          '--ignore=tests/test_integration.py'], check=True)
            print("✓ Unit tests passed")
        except subprocess.CalledProcessError:
            print("✗ Unit tests failed")
            sys.exit(1)
        except FileNotFoundError:
            print("⚠ pytest not installed. Run: pip install -e .[dev]")
            sys.exit(1)
        
        # Run integration tests
        print("\nRunning integration tests...")
        try:
            # Run integration test directly
            subprocess.run([sys.executable, 'tests/test_integration.py'], check=True)
            print("✓ Integration tests passed")
        except subprocess.CalledProcessError:
            print("✗ Integration tests failed")
            sys.exit(1)
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")


# Read long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name="mcp-browser",
    version="0.1.0",
    description="A generic MCP browser with context optimization for AI systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Claude4Ξlope",
    author_email="xilope@esus.name",
    url="https://github.com/Xilope0/mcp-browser",
    packages=find_packages(include=['mcp_browser*', 'mcp_servers*']),
    package_data={
        'mcp_browser': ['py.typed'],
        'mcp_servers': ['**/*.py'],
        'mcp_servers.screen': ['*.py'],
        'mcp_servers.memory': ['*.py'], 
        'mcp_servers.pattern_manager': ['*.py'],
        'mcp_servers.onboarding': ['*.py'],
    },
    include_package_data=True,
    install_requires=[
        "aiofiles>=23.0.0",
        "jsonpath-ng>=1.6.0",
        "pyyaml>=6.0",
        "typing-extensions>=4.0.0;python_version<'3.11'",
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'mypy>=1.0.0',
            'ruff>=0.1.0',
        ],
        'docs': [
            'sphinx>=6.0.0',
            'sphinx-rtd-theme>=1.3.0',
            'myst-parser>=2.0.0',
        ],
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mcp-browser=mcp_browser.__main__:main",
            "mcp-browser-daemon=mcp_browser.daemon_main:main",
            "mcp-browser-client=mcp_browser.client_main:main",
        ],
    },
    cmdclass={
        'aidocs': GenerateAIDocs,
        'test': TestCommand,
    },
    license="GPL-3.0-or-later",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="mcp model-context-protocol ai llm tools json-rpc",
)