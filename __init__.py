import arrow
import requests
from wikidataintegrator import wdi_core, wdi_login
from .site_credentials import *

WIKI_SESSION = wdi_login.WDLogin(user=site_username, pwd=site_password)
