#!/usr/bin/env python3
"""Standard-library Oxen/Wagon client. Credentials come only from environment."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class NoCrossOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old=urllib.parse.urlsplit(req.full_url);new=urllib.parse.urlsplit(newurl)
        if (old.scheme,old.netloc)!=(new.scheme,new.netloc):
            raise RuntimeError('Unexpected authentication redirect; check your service credentials')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class Client:
    def __init__(self,base,http_timeout=120):
        self.base=base.rstrip('/')
        parsed=urllib.parse.urlsplit(self.base)
        if parsed.scheme not in ('https','http') or not parsed.netloc:
            raise ValueError('Use an absolute API URL')
        self.origin=(parsed.scheme,parsed.netloc)
        self.headers={
            'CF-Access-Client-Id':os.environ.get('CF_ACCESS_CLIENT_ID',''),
            'CF-Access-Client-Secret':os.environ.get('CF_ACCESS_CLIENT_SECRET',''),
        }
        if not all(self.headers.values()):
            raise ValueError('Set CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET in your environment')
        self.opener=urllib.request.build_opener(NoCrossOriginRedirect())
        self.http_timeout=http_timeout

    def open(self,path='',method='GET',data=None,raw=False):
        url=path if path.startswith(('https://','http://')) else self.base+path
        parsed=urllib.parse.urlsplit(url)
        if (parsed.scheme,parsed.netloc)!=self.origin:
            raise ValueError('Refusing to send credentials to a different origin')
        headers=dict(self.headers)
        if data is not None:
            headers['Content-Type']='application/octet-stream' if raw else 'application/json'
            if not raw:data=json.dumps(data).encode()
        request=urllib.request.Request(url,data=data,method=method,headers=headers)
        try:return self.opener.open(request,timeout=self.http_timeout)
        except urllib.error.HTTPError as exc:
            message=f'HTTP {exc.code}'
            try:
                body=json.loads(exc.read(4096));message+=': '+str(body.get('error','Request rejected'))
            except (ValueError,AttributeError):pass
            for secret in self.headers.values():message=message.replace(secret,'[redacted]')
            raise RuntimeError(message) from None

    def json(self,path='',method='GET',data=None,raw=False):
        with self.open(path,method,data,raw) as response:
            return json.load(response)

    def wait(self,batch_id,states,interval,wait_timeout):
        end=time.monotonic()+wait_timeout
        while True:
            status=self.json('/'+urllib.parse.quote(batch_id,safe=''))
            if status['state'] in states:return status
            if time.monotonic()>=end:
                raise RuntimeError(f'Polling timed out; batch {batch_id} still exists in state {status["state"]}')
            time.sleep(interval)

    def download(self,url,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix(path.suffix+'.part')
        with self.open(url) as response,temporary.open('wb') as output:
            shutil.copyfileobj(response,output,length=1024*1024)
        temporary.replace(path)
        return str(path)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='https://oxen.lemma.farm/api/v1/batch')
    parser.add_argument('--http-timeout',type=float,default=120)
    parser.add_argument('--poll-interval',type=float,default=5)
    parser.add_argument('--wait-timeout',type=float,default=3600)
    commands=parser.add_subparsers(dest='command',required=True)
    validate=commands.add_parser('validate',help='Upload and validate; never submits model work')
    validate.add_argument('file',type=Path)
    validate.add_argument('--endpoint',default='/v1/chat/completions')
    validate.add_argument('--timeout-seconds',type=int,default=1200)
    validate.add_argument('--resume',help='Resume an existing uploading batch with the same original file')
    for command in ('submit','status','requests','cancel','download'):
        sub=commands.add_parser(command);sub.add_argument('batch_id')
        if command=='requests':
            sub.add_argument('--offset',type=int,default=0);sub.add_argument('--state')
        if command=='cancel':sub.add_argument('--request-id')
        if command=='download':
            sub.add_argument('--output',type=Path,default=Path('oxen-results'));sub.add_argument('--zip',action='store_true')
    args=parser.parse_args(argv)
    if args.poll_interval<=0 or args.wait_timeout<=0 or args.http_timeout<=0:parser.error('Timeouts and polling interval must be positive')
    try:
        client=Client(args.base,args.http_timeout)
        if args.command=='validate':
            size=args.file.stat().st_size
            if not size:raise ValueError('The input file is empty')
            if args.resume:
                batch=client.json('/'+urllib.parse.quote(args.resume,safe=''))
                if batch['state']!='uploading' or batch['filename']!=args.file.name:
                    raise ValueError('Resume requires the same original filename and an uploading batch')
            else:
                batch=client.json('','POST',{'filename':args.file.name,'endpoint':args.endpoint,'timeout_seconds':args.timeout_seconds})
            identifier=batch['batch_id'];position=batch['upload_bytes']
            print('batch_id='+identifier,file=sys.stderr)
            if position>size:raise ValueError('Saved upload is longer than this file')
            with args.file.open('rb') as source:
                # Verify a resume prefix using the saved input, avoiding a silent mixed file.
                if position:
                    digest=hashlib.sha256()
                    with client.open(batch['urls']['input']) as saved:
                        while chunk:=saved.read(1024*1024):digest.update(chunk)
                    local=hashlib.sha256();remaining=position
                    while remaining:
                        chunk=source.read(min(1024*1024,remaining));local.update(chunk);remaining-=len(chunk)
                    if digest.digest()!=local.digest():raise ValueError('Saved upload prefix differs from this file')
                source.seek(position)
                while chunk:=source.read(4*1024*1024):
                    result=client.json('/'+identifier+'/input?offset='+str(position),'PUT',chunk,raw=True)
                    position=result['next_offset'];source.seek(position)
            client.json('/'+identifier+'/validate','POST',{})
            result=client.wait(identifier,('ready','invalid','cancelled'),args.poll_interval,args.wait_timeout)
        else:
            identifier=urllib.parse.quote(args.batch_id,safe='')
            if args.command=='status':result=client.json('/'+identifier)
            elif args.command=='submit':result=client.json('/'+identifier+'/submit','POST',{})
            elif args.command=='requests':result=client.json('/'+identifier+'/requests?'+urllib.parse.urlencode({'offset':args.offset,**({'state':args.state} if args.state else {})}))
            elif args.command=='cancel':
                suffix='/requests/'+urllib.parse.quote(args.request_id,safe='')+'/cancel' if args.request_id else '/cancel'
                result=client.json('/'+identifier+suffix,'POST',{})
            elif args.command=='download':
                batch=client.json('/'+identifier)
                files=[client.download(batch['urls']['results'],args.output/(batch['batch_id']+'-results.jsonl'))]
                if args.zip:
                    snapshot=client.json(batch['urls']['snapshot'],'POST',{})
                    end=time.monotonic()+args.wait_timeout
                    while True:
                        batch=client.json('/'+identifier)
                        entry=next((s for s in batch['snapshots'] if s['id']==snapshot['snapshot_id']),None)
                        if entry and entry['state']=='ready':
                            files.append(client.download(entry['download_url'],args.output/(batch['batch_id']+'-'+entry['id']+'.zip')));break
                        if entry and entry['state']=='failed':raise RuntimeError('Snapshot failed: '+str(entry.get('error')))
                        if time.monotonic()>=end:raise RuntimeError('Snapshot still preparing; query batch status later')
                        time.sleep(args.poll_interval)
                result={'batch_id':batch['batch_id'],'state':batch['state'],'files':files}
        print(json.dumps(result,indent=2))
        return 2 if args.command=='validate' and result['state']!='ready' else 0
    except (OSError,ValueError,RuntimeError,urllib.error.URLError) as exc:
        print(str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
