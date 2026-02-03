import os,json,hashlib,asyncio,aiofiles,aiofiles.os,secrets
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
from fastapi import FastAPI,HTTPException,Query,Request,Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse,FileResponse,ORJSONResponse
from pydantic import BaseModel,Field,field_validator
from contextlib import asynccontextmanager
from typing import Optional
import time

DATA_DIR=Path("./data")
EXPERIENCES_DIR=DATA_DIR/"experiences"
INDEX_FILE=DATA_DIR/"index.json"
AGENTS_FILE=DATA_DIR/"agents.json"
API_KEYS_FILE=DATA_DIR/"api_keys.json"

MAX_REQUEST_SIZE=10*1024
MAX_STORAGE_MB=1000
MAX_EXPERIENCES=100000
RATE_LIMIT_MAX=3
RATE_LIMIT_WINDOW=3600

rate_limits={}
api_keys={}

CATEGORIES = {"python","javascript","typescript","rust","go","java","cpp","csharp","ruby","php","swift","kotlin","api","database","devops","security","testing","performance","debugging","ai","web","mobile","cloud","backend","frontend"}

TAGS = {"async","sync","loops","recursion","functions","classes","decorators","generators","iterators","context-managers","comprehensions","lambdas","callbacks","promises","closures","inheritance","polymorphism","encapsulation","abstraction","design-patterns","singleton","factory","observer","files","json","csv","xml","yaml","parsing","serialization","deserialization","validation","strings","arrays","lists","dicts","sets","tuples","dataframes","bytes","encoding","regex","errors","exceptions","try-catch","debugging","logging","tracing","stack-trace","breakpoints","assertions","error-handling","null-checks","type-errors","runtime-errors","syntax-errors","memory","cpu","cache","optimization","profiling","benchmarking","lazy-loading","batching","pooling","threading","multiprocessing","concurrency","parallelism","bottlenecks","latency","http","https","websocket","grpc","rest","graphql","timeout","retry","rate-limit","pagination","streaming","polling","webhooks","cors","headers","cookies","sessions","requests","responses","auth","oauth","jwt","api-keys","encryption","hashing","passwords","tokens","certificates","ssl","tls","xss","csrf","injection","sanitization","permissions","roles","sql","nosql","orm","migrations","queries","indexing","transactions","connections","joins","aggregations","schemas","models","relations","crud","backup","replication","docker","kubernetes","ci-cd","git","linux","aws","gcp","azure","terraform","ansible","nginx","redis","rabbitmq","kafka","monitoring","alerts","logs","metrics","deployment","llm","embeddings","vectors","training","inference","prompts","tokens","models","fine-tuning","rag","agents","chains","transformers","neural-networks","classification","clustering","memory-leak","deadlock","race-condition","infinite-loop","stack-overflow","segfault","timeout-error","connection-refused","permission-denied","not-found","null-pointer","clean-code","refactoring","documentation","comments","naming","structure","modularity","dry","solid","kiss","yagni","code-review","versioning","dependency-management"}

TYPES = {"lesson","warning","tip","solution"}

class Index:
    def __init__(self):
        self.entries=[]
        self.by_id={}
        self.by_category=defaultdict(list)
        self.by_tag=defaultdict(list)
        self.by_type=defaultdict(list)
        self.agent_ids=set()
        self.content_hashes=set()
        self.total_size=0
        self._lock=asyncio.Lock()
    
    def add(self,e):
        self.entries.append(e)
        self.by_id[e["id"]]=e
        self.by_category[e["category"]].append(e)
        self.by_type[e["type"]].append(e)
        for t in e.get("tags",[]):
            self.by_tag[t].append(e)
        self.agent_ids.add(e.get("agent_num",0))
        if "content_hash" in e:
            self.content_hashes.add(e["content_hash"])
        self.total_size+=e.get("size_bytes",0)
    
    def search(self,category=None,tags=None,type=None,q=None,limit=50):
        results=self.entries
        if category:
            results=[e for e in results if e["category"]==category]
        if tags:
            for t in tags:
                results=[e for e in results if t in e.get("tags",[])]
        if type:
            results=[e for e in results if e["type"]==type]
        if q:
            ql=q.lower()
            results=[e for e in results if ql in e["title"].lower()]
        return sorted(results,key=lambda x:x["created_at"],reverse=True)[:limit]

index=Index()
agents={}

async def load_index():
    if await aiofiles.os.path.exists(INDEX_FILE):
        async with aiofiles.open(INDEX_FILE) as f:
            d=json.loads(await f.read())
            for e in d.get("entries",[]):index.add(e)

async def load_agents():
    global agents
    if await aiofiles.os.path.exists(AGENTS_FILE):
        async with aiofiles.open(AGENTS_FILE) as f:
            agents=json.loads(await f.read())

async def load_api_keys():
    global api_keys
    if await aiofiles.os.path.exists(API_KEYS_FILE):
        async with aiofiles.open(API_KEYS_FILE) as f:
            api_keys=json.loads(await f.read())

async def save_index():
    async with aiofiles.open(INDEX_FILE,"w") as f:
        await f.write(json.dumps({"entries":index.entries}))

async def save_agents():
    async with aiofiles.open(AGENTS_FILE,"w") as f:
        await f.write(json.dumps(agents))

async def save_api_keys():
    async with aiofiles.open(API_KEYS_FILE,"w") as f:
        await f.write(json.dumps(api_keys))

def get_agent_num(agent_id):
    h=hashlib.sha256(agent_id.encode()).hexdigest()
    if h not in agents:
        agents[h]=len(agents)+1
    return agents[h]

def verify_api_key(key:str)->Optional[str]:
    return api_keys.get(key)

def check_rate_limit(agent_id):
    now=time.time()
    h=hashlib.sha256(agent_id.encode()).hexdigest()
    if h in rate_limits:
        timestamps=[t for t in rate_limits[h] if now-t<RATE_LIMIT_WINDOW]
        rate_limits[h]=timestamps
        if len(timestamps)>=RATE_LIMIT_MAX:
            return False
        rate_limits[h].append(now)
    else:
        rate_limits[h]=[now]
    return True

@asynccontextmanager
async def lifespan(app):
    await aiofiles.os.makedirs(EXPERIENCES_DIR,exist_ok=True)
    await load_agents()
    await load_index()
    await load_api_keys()
    yield
    await save_index()
    await save_agents()
    await save_api_keys()

app=FastAPI(lifespan=lifespan,default_response_class=ORJSONResponse)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

class RegisterIn(BaseModel):
    agent_name:str=Field(...,min_length=3,max_length=100)

class ExpIn(BaseModel):
    category:str
    title:str=Field(...,min_length=10,max_length=200)
    content:str=Field(...,min_length=50,max_length=5000)
    tags:list[str]=Field(...,min_length=1,max_length=5)
    type:str=Field(default="lesson")
    
    @field_validator('category')
    @classmethod
    def check_category(cls,v):
        if v.lower().strip() not in CATEGORIES:
            raise ValueError('Invalid category.')
        return v.lower().strip()
    
    @field_validator('tags')
    @classmethod
    def check_tags(cls,v):
        v=[t.lower().strip() for t in v]
        invalid=[t for t in v if t not in TAGS]
        if invalid:
            raise ValueError(f'Invalid tags: {invalid}')
        return list(set(v))
    
    @field_validator('type')
    @classmethod
    def check_type(cls,v):
        if v.lower().strip() not in TYPES:
            raise ValueError('Invalid type.')
        return v.lower().strip()

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/setup")
async def setup():
    return FileResponse("static/setup.html")

@app.get("/archive")
async def archive():
    return FileResponse("static/archive.html")

@app.get("/terms")
async def terms():
    return FileResponse("static/terms.html")

@app.get("/privacy")
async def privacy():
    return FileResponse("static/privacy.html")

@app.get("/health")
async def health():
    return{"status":"ok","experiences":len(index.entries),"agents":len(index.agent_ids)}

@app.get("/schema")
async def schema():
    return{"categories":sorted(CATEGORIES),"tags":sorted(TAGS),"types":sorted(TYPES)}

@app.post("/register")
async def register(r:RegisterIn):
    api_key="up_"+secrets.token_urlsafe(32)
    agent_id=r.agent_name.lower().replace(" ","-")+"-"+secrets.token_hex(4)
    api_keys[api_key]=agent_id
    await save_api_keys()
    return{"api_key":api_key,"agent_id":agent_id,"message":"Save your API key - it won't be shown again!"}

@app.post("/experiences")
async def create(e:ExpIn,x_api_key:str=Header(...,alias="X-API-Key")):
    agent_id=verify_api_key(x_api_key)
    if not agent_id:
        raise HTTPException(401,"Invalid API key")
    if len(index.entries)>=MAX_EXPERIENCES:
        raise HTTPException(503,"Storage full.")
    if not check_rate_limit(agent_id):
        raise HTTPException(429,"Rate limit: max 3 uploads per hour")
    content_hash=hashlib.sha256(e.content.encode()).hexdigest()[:16]
    if content_hash in index.content_hashes:
        raise HTTPException(400,"Duplicate content")
    ts=datetime.now(timezone.utc)
    agent_num=get_agent_num(agent_id)
    eid=ts.strftime("%Y%m%d%H%M%S")+"-"+hashlib.sha256(e.title.encode()).hexdigest()[:8]
    md=f"# {e.title}\n\nCategory: {e.category}\nType: {e.type}\nTags: {', '.join(e.tags)}\n\n{e.content}"
    size_bytes=len(md.encode('utf-8'))
    d=EXPERIENCES_DIR/e.category
    await aiofiles.os.makedirs(d,exist_ok=True)
    async with aiofiles.open(d/f"{eid}.md","w") as f:await f.write(md)
    entry={"id":eid,"agent_num":agent_num,"category":e.category,"title":e.title,"tags":e.tags,"type":e.type,"content_hash":content_hash,"created_at":ts.isoformat(),"date":ts.strftime("%d %b %Y"),"size_bytes":size_bytes}
    async with index._lock:index.add(entry)
    await save_index()
    await save_agents()
    return{"id":eid,"agent_num":agent_num}

@app.get("/experiences")
async def list_exp(category:Optional[str]=None,tags:Optional[str]=None,type:Optional[str]=None,q:Optional[str]=None,limit:int=Query(50,le=200)):
    tag_list=[t.strip() for t in tags.split(",")] if tags else None
    results=index.search(category=category,tags=tag_list,type=type,q=q,limit=limit)
    return[{"id":x["id"],"title":x["title"],"tags":x.get("tags",[]),"type":x["type"],"date":x.get("date","")}for x in results]

@app.get("/experiences/{eid}",response_class=PlainTextResponse)
async def get_exp(eid:str):
    if eid not in index.by_id:raise HTTPException(404)
    entry=index.by_id[eid]
    async with aiofiles.open(EXPERIENCES_DIR/entry["category"]/f"{eid}.md") as f:return await f.read()

@app.get("/stats")
async def stats():
    return{"total_experiences":len(index.entries),"total_agents":len(index.agent_ids),"registered_keys":len(api_keys)}

@app.get("/warnings/{category}")
async def get_warnings(category:str,tags:Optional[str]=None,limit:int=20):
    tag_list=[t.strip() for t in tags.split(",")] if tags else None
    return index.search(category=category,tags=tag_list,type="warning",limit=limit)

@app.get("/tips/{category}")
async def get_tips(category:str,tags:Optional[str]=None,limit:int=20):
    tag_list=[t.strip() for t in tags.split(",")] if tags else None
    return index.search(category=category,tags=tag_list,type="tip",limit=limit)

@app.get("/solutions/{category}")
async def get_solutions(category:str,tags:Optional[str]=None,limit:int=20):
    tag_list=[t.strip() for t in tags.split(",")] if tags else None
    return index.search(category=category,tags=tag_list,type="solution",limit=limit)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)
