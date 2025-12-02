#!/usr/bin/env python3
"""
服务器模块
提供HTTP API服务，适配OpenAI格式
"""

from .api import DoubaoServer, run_server

__all__ = ["DoubaoServer", "run_server"]