"""课程框架公共设施。"""

from .lesson import Lesson
from .registry import all_lessons, get_lesson, register

__all__ = ["Lesson", "all_lessons", "get_lesson", "register"]
