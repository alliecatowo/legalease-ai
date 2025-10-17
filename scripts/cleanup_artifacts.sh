#!/bin/bash
set -e

echo "🧹 Cleaning up development artifacts..."
echo ""

cd "$(dirname "$0")/.."

# Count files before cleanup
echo "📊 Analyzing artifacts to remove..."
TEST_FILES=$(find backend -maxdepth 1 -type f -name "test_*.py" 2>/dev/null | wc -l)
echo "  - Test files in backend root: $TEST_FILES"

if [ -d "backend/.venv-old" ]; then
    VENV_SIZE=$(du -sh backend/.venv-old 2>/dev/null | cut -f1)
    echo "  - Old virtual environment: $VENV_SIZE"
else
    echo "  - Old virtual environment: Not found"
fi

if [ -d "backend/test_subtitles" ]; then
    echo "  - Test subtitles directory: Found"
fi

echo ""
echo "Press Ctrl+C to cancel, or wait 3 seconds to continue..."
sleep 3

# Remove test files from backend root
echo "🗑️  Removing test files from backend root..."
find backend -maxdepth 1 -type f -name "test_*.py" -delete 2>/dev/null || true
echo "   ✓ Removed $TEST_FILES test_*.py files"

# Remove old venv
if [ -d "backend/.venv-old" ]; then
    echo "🗑️  Removing old virtual environment..."
    rm -rf backend/.venv-old
    echo "   ✓ Removed .venv-old directory"
fi

# Remove test output dirs
if [ -d "backend/test_subtitles" ]; then
    echo "🗑️  Removing test output directories..."
    rm -rf backend/test_subtitles
    echo "   ✓ Removed test_subtitles directory"
fi

# Remove outdated docs
if [ -f "backend/ROCM_SETUP.md" ]; then
    echo "🗑️  Removing outdated documentation..."
    rm -f backend/ROCM_SETUP.md
    echo "   ✓ Removed ROCM_SETUP.md"
fi

# Remove test scripts
echo "🗑️  Removing test scripts..."
find backend/scripts -type f -name "test_*.py" -delete 2>/dev/null || true
echo "   ✓ Removed test scripts from backend/scripts"

echo ""
echo "✅ Cleanup complete!"
echo "📈 Repository is now cleaner and more professional"
echo ""
echo "Summary:"
echo "  - Removed test files and artifacts"
echo "  - Freed up disk space"
echo "  - Improved repository organization"
