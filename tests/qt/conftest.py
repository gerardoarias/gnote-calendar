import pytest
import sys, os
# Ensure qt offscreen for headless CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
