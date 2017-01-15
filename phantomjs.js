var page = require('webpage').create();
var system = require('system');
if (system.args.length !== 2){
    phantom.exit(1);
}else{
    var address = system.args[1];
    // 初始化
    page.settings.resourceTimeout = 30000;
    page.settings.loadImage = false;
    page.settings.userAgent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36';
    page.customHeaders = {
        "Connection" : "keep-alive",
        "Cache-Control" : "max-age=0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
    };

    page.onError = function(msg, trace) {
        var msgStack = ['ERROR: ' + msg];
        if (trace && trace.length) {
            msgStack.push('TRACE:');
            trace.forEach(function(t) {
            msgStack.push(' -> ' + t.file + ': ' + t.line + (t.function ? ' (in function "' + t.function +'")' : ''));
            });
        }
        console.error(msgStack.join('\n'));
    };

    page.onInitialized = function(){
        _addEventListener = Element.prototype.addEventListener;
        Element.prototype.addEventListener = function(a,b,c){
            EVENT_LIST.push({"event":event, "element":this});
            _addEventListener.apply(this, arguments);
        };
        //console.dir(EVENT_LIST);
        for (var i in EVENT_LIST){
            var evt = document.createEvent('CustomEvent');
            evt.initCustomEvent(EVENT_LIST[i]["event"], true, true, null);
            EVENT_LIST[i]["element"].dispatchEvent(evt);
        }
    };

    //处理ajax请求
    page.onResourceRequested = function(requestData, request){
        //过滤非HTTP||HTTPS请求
        if ((/^(http:\/\/|https:\/\/).+?/).test(requestData['url'])){
            //过滤资源型请求
            if((/.+?\.(css|jpg|jpeg|gif|png|mp4)$/gi).test(requestData['url'])){
                request.abort();
            }else{
                console.log(requestData['url']);
            }
        }else{
            request.abort();
        }
    };

    //HOOK掉可能造成阻塞的函数
    page.onPrompt = function(){
    };

    page.onAlert = function(){
    };

    page.onConsoleMessage = function(msg){
        //console.log(msg);
    }

    page.onConfirm = function(){
    }

    page.onCallback = function(){
        var links = page.evaluate(function(printMessage){
            var links = '';
            //遍历所有节点内的内联事件
            function trigger_inline(){
                var nodes = document.all;
                for (var i = 0; i < nodes.length; i++) {
                    var attrs = nodes[i].attributes;
                    for (var j = 0; j < attrs.length; j++) {
                        attr_name = attrs[j].nodeName;
                        attr_value = attrs[j].nodeValue;
                        if (attr_name.substr(0, 2) == "on") {
                            //console.log(attr_name + ' : ' + attr_value);
                            eval(attr_value.split('return')[0]+';');
                        }
                        if (attr_name in {"src": 1, "href": 1} && attrs[j].nodeValue.substr(0, 11) == "javascript:") {
                            //console.log(attr_name + ' : ' + attr_value);
                            eval(attr_value.substr(11).split('return')[0]+';');
                        }
                    }
                }
            }
            trigger_inline();
            // 相对地址转绝对地址
            var getAbsoluteUrl = (function(){
                var a;
                return function(url){
                    if(!a){
                        a = document.createElement('a');
                    }
                    a.href = url;
                    return a.href;
                };
            })();
            // 获取a标签的href值
            atags = document.getElementsByTagName("a");
            
            for (var i=0; i<atags.length; i++){
                if (atags[i].getAttribute("href")){
                    links += getAbsoluteUrl(atags[i].getAttribute("href"))+'\n';
                }
            }
            // 获取iframe标签的src值
            iframetag = document.getElementsByTagName("iframe");
            for (var i=0; i<iframetag.length; i++){
                if (iframetag[i].getAttribute("src")){
                    links += getAbsoluteUrl(iframetag[i].getAttribute("src"))+'\n';
                }
            }
            // 获取表单链接
            ftags = document.getElementsByTagName("form");
            for (var i=0; i<ftags.length; i++){
                var link = '';
                var action = getAbsoluteUrl(ftags[i].getAttribute("action"));
                if (action){
                    if (action.substr(action.length-1,1) == '#'){
                        link = action.substr(0, action.length-1);
                    }
                    else{
                        link = action + '?';
                    }
                    for (var j=0; j<ftags[i].elements.length; j++){
                        if (ftags[i].elements[j].tagName == 'INPUT'){
                            link = link + ftags[i].elements[j].name + '=';
                            if (ftags[i].elements[j].value == "" || ftags[i].elements[j].value == null){
                                link = link + 'Abc123456!' + '&';
                            }else{
                                link = link + ftags[i].elements[j].value + '&';
                            }
                        }
                    }
                }
                links += link.substr(0, link.length-1) + '\n';     
            }

            document.addEventListener('DOMNodeInserted', function(e) {
                var node = e.target;
                if(node.src || node.href){
                    links += (node.src || node.href)+'\n';
                }
            }, true);

            return links;
        });
        //输出获取到的所有URL
        if(links != null){
            console.dir(links.trim('\n'));
        }
        phantom.exit();
    }

    page.open(address, "get", "", function(){
        page.evaluateAsync(function(){
            if (typeof window.callPhantom === 'function'){
                window.callPhantom();
            }
        },1000);
    });
}