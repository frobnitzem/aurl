from importlib.metadata import version
__version__ = version('aurl')

from .urls import URL
from .get import get
from .subst import subst
from .template import Template, TemplateFile
from .mirror import Mirror
from .fetch import fetch_all
