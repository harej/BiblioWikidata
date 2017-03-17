from .site_credentials import *
from wikidataintegrator import wdi_login

WIKI_SESSION = wdi_login.WDLogin(user=site_username, pwd=site_password)
