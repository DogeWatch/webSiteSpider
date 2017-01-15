#!/usr/bin/env python
# coding=utf-8
import subprocess32
import sys
import time
import os
from Queue import Queue
from threading import Thread
from threading import Condition
from threading import Lock
from threadpool import makeRequests, ThreadPool
from parseurl import parseurl
from setting import mongodb
from datetime import datetime
from optparse import OptionParser

#页面爬行类
class crawler(object):
    def __init__(self, url, domain, depth, threadNum):
        #当前正在执行的线程数
        self.currentRunning = 0
        #线程池管理线程与爬虫线程同步的条件变量,用于修改currentRunning时的加锁和唤醒管理线程
        self.processCondition = Condition()
        #待访问的URL的队列
        self.urlQueue = Queue()
        #已经访问的URL
        self.readUrls = []
        #URL host、path、param的键值对
        self.urls = {}
        #线程数
        self.threadNum = threadNum
        #设定了线程数的线程池
        #self.threadPool = ThreadPool(self.threadNum)
        self.pool = ThreadPool(self.threadNum)

        #初始化URL队列
        self.urlQueue.put({'url':url,"depth":1})
        #预期爬行深度
        self.depth = depth
        #当前爬行深度
        #self.currentDepth = 1
        #当前运行状态
        self.state = False
        #DOMAIN
        self.domain = domain
        #初始化数据库
        self.db = mongodb(self.domain)
        self.db.clean()

    #URL字典转字符串
    def dic2url(self, udic):
        url = udic['schema'] + '://' + udic['host'] + udic['path'] + '?'
        for k in udic['param']:
            url += k + '=' + udic['param'][k] + '&'
        return url[:-1]

    #获取最后一个/字符的位置
    def find_last(self, string, str):
        last_position=-1
        while True:
            position=string.find(str,last_position+1)
            if position==-1:
                return last_position
            last_position=position

    #URL去重（去伪静态）
    def duplicateFilter3(self, urldict):
        if urldict['host'] not in self.urls:
            self.urls[urldict['host']] = {urldict['path']:[urldict['param']]}
            return True
        else:
            index = self.find_last(urldict['path'], '/')
            if urldict['path'][index+1:].isdigit():
                urldict['path'] = urldict['path'][:index+1]
            if urldict['path'] not in self.urls[urldict['host']]:
                self.urls[urldict['host']][urldict['path']] = [urldict['param']]
                return True
            else:
                flag = True
                for d in self.urls[urldict['host']][urldict['path']]:
                    if urldict['param'].keys() == d.keys():
                        flag = False
                        break
                if flag:
                    self.urls[urldict['host']][urldict['path']].append(urldict['param'])
                    return True
                else:
                    return False

    #URL去重（去参数key相同的）
    def duplicateFilter2(self, urldict):
        if urldict['host'] not in self.urls:
            self.urls[urldict['host']] = {urldict['path']:[urldict['param']]}
            return True
        else:
            if urldict['path'] not in self.urls[urldict['host']]:
                self.urls[urldict['host']][urldict['path']] = [urldict['param']]
                return True
            else:
                flag = True
                for d in self.urls[urldict['host']][urldict['path']]:
                    if urldict['param'].keys() == d.keys():
                        flag = False
                        break
                if flag:
                    self.urls[urldict['host']][urldict['path']].append(urldict['param'])
                    return True
                else:
                    return False

    #URL去重（简单）
    def duplicateFilter(self, result):
        temp = []
        urls = []
        for r in list(set(result.split('\n'))):
            if r != '':
                urldict = parseurl(r).getParse()
                if self.domain in urldict['host']:
                    if urldict not in temp:
                        temp.append(urldict)
        for x in temp:
            if self.duplicateFilter3(x):
                urls.append(self.dic2url(x))
        return urls

    #获取当前页面的URL
    def work(self, urlInfo):
        url = urlInfo['url']
        currentDepth = urlInfo['depth']
        #print '[*] Current url is %s' % url
        try:
            child = subprocess32.Popen(['phantomjs', 'phantomjs.js', url], stdout=subprocess32.PIPE)
            output = child.communicate(None, timeout=10)
            #output = subprocess32.check_output(['phantomjs', 'phantomjs.js', url], timeout=10)
        except Exception, e:
            os.kill(child.pid,9)
            self.processCondition.acquire()
            self.currentRunning = self.currentRunning - 1
            self.processCondition.notify()
            self.processCondition.release()
            print '[!] error in url %s' % url
            return None

        urls = self.duplicateFilter(output[0])
        #urls = self.duplicateFilter(output)
        if currentDepth >= self.depth:
            for i in urls:
                if i not in self.readUrls:
                    self.db.insert(dict([['link',i.decode("unicode_escape")]]))
        else:
            for i in urls:
                if i not in self.readUrls:
                    self.db.insert(dict([['link',i.decode("unicode_escape")]]))
                    self.urlQueue.put({'url':i,'depth':currentDepth+1})

        self.processCondition.acquire()
        self.currentRunning = self.currentRunning - 1
        self.processCondition.notify()
        self.processCondition.release()

    def urlQueueProcesser(self):
        self.processCondition.acquire()
        while True:
            if not(self.urlQueue.empty() and self.currentRunning == 0):
                urls = []
                #收集url队列
                while not self.urlQueue.empty():
                    item = self.urlQueue.get()
                    if item["url"] not in self.readUrls:
                        urls.append(item)
                        self.readUrls.append(item["url"])
                #将队列里的URL都加入到线程池
                threadNum = len(urls)
                requests = makeRequests(self.work, urls)
                self.currentRunning = self.currentRunning + threadNum
                [self.pool.putRequest(req) for req in requests]
                self.processCondition.wait()
            else:
                break

    def start(self):
        self.state = True
        print '\n[-] Starting Crawling...........Domain is %s\n' % self.domain
        self.urlQueueProcesser();

        self.stop()

    def stop(self):
        self.db.close_db()
        self.state = False
        #self.pool.wait()



class printInfo(Thread):
    def __init__(self, crawler):
        Thread.__init__(self)
        self.startTime = datetime.now()
        self.daemon = True
        self.crawler = crawler
        self.start()

    def printEnd(self):
        self.endTime = datetime.now()
        print 'Crawl Depth:%d, Totally visited %d links.\n' % (self.crawler.depth, len(self.crawler.readUrls))
        print 'Start at: %s' % self.startTime
        print 'End at: %s' % self.endTime
        print 'Spend time: %s' % (self.endTime - self.startTime)
        print 'Result count: %s\n' % (self.crawler.db.count())
        print '[-] Finished......'

    def run(self):
        while True:
            if self.crawler.state == True:
                time.sleep(10)
                print '[+] Now totally visited %d links , %d threads is in threads queue .\n' % (len(self.crawler.readUrls),self.crawler.currentRunning)




if __name__ == '__main__':
    print '[+] Run current process pid:%s...' %  os.getpid()
    helpInfo = '%prog -u url -d depth'
    #命令行参数解析
    optParser = OptionParser(usage = helpInfo)
    optParser.add_option("-u",dest="url",type="string",help="Specify the begin url.")
    optParser.add_option("-d",dest="depth",type="int",default="5",help="Specify the crawling depth. Default: 5.")
    optParser.add_option("-t",dest="thread",default="10",type="int",help="The amount of threads. Default: 10.")
    (options,args) = optParser.parse_args()

    #显示帮助信息
    if len(sys.argv) < 3:
        print optParser.print_help()
    else:
        domain = parseurl(options.url).getHost()
        spider = crawler(options.url, domain, options.depth, options.thread)
        info = printInfo(spider)
        spider.start()
        info.printEnd()
