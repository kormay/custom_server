import sys
sys.path.insert(0, '../django_demo')
from django_demo import wsgi
 
app = wsgi.application
