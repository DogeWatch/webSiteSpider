from urlparse import urlparse
from urlparse import parse_qs

class parseurl(object):
    def __init__(self, url):
        self.parse = urlparse(url)

    def getHost(self):
        return self.parse.netloc

    def getParam(self):
        return dict([(k,v[0])for k,v in parse_qs(self.parse.query).items()])

    def getPath(self):
        return self.parse.path

    def getParse(self):
        udict = {}
        udict['schema'] = self.parse.scheme
        udict['host'] = self.getHost()
        udict['path'] = self.getPath()
        udict['param'] = self.getParam()
        return udict
