"""contents-manager backend 테스트 공통 설정 — backend 루트를 import path에 추가."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
