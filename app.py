import os,json,hashlib,asyncio,aiofiles,aiofiles.os
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
from fastapi import FastAPI,HTTPException,Query,Request
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

# === LIMITS ===
MAX_REQUEST_SIZE=10*1024  # 10KB
MAX_STORAGE_MB=1000  # 1GB
MAX_EXPERIENCES=100000
RATE_LIMIT_MAX=3
RATE_LIMIT_WINDOW=3600

rate_limits={}

# === CATEGORIES ===
CATEGORIES = {
    "python","javascript","typescript","rust","go","java","cpp","csharp","ruby","php","swift","kotlin",
    "api","database","devops","security","testing","performance","debugging","ai","web","mobile","cloud","backend","frontend"
}

# === TAGS ===
TAGS = {
    "async","sync","loops","recursion","functions","classes","decorators","generators","iterators",
    "context-managers","comprehensions","lambdas","callbacks","promises","closures","inheritance",
    "polymorphism","encapsulation","abstraction","design-patterns","singleton","factory","observer",
    "files","json","csv","xml","yaml","parsing","serialization","deserialization","validation",
    "strings","arrays","lists","dicts","sets","tuples","dataframes","bytes","encoding","regex",
    "errors","exceptions","try-catch","debugging","logging","tracing","stack-trace","breakpoints",
    "assertions","error-handling","null-checks","type-errors","runtime-errors","syntax-errors",
    "memory","cpu","cache","optimization","profiling","benchmarking","lazy-loading","batching",
    "pooling","threading","multiprocessing","concurrency","parallelism","bottlenecks","latency",
    "http","https","websocket","grpc","rest","graphql","timeout","retry","rate-limit","pagination",
    "streaming","polling","webhooks","cors","headers","cookies","sessions","requests","responses",
    "auth","oauth","jwt","api-keys","encryption","hashing","passwords","tokens","certificates",
    "ssl","tls","xss","csrf","injection","sanitization","permissions","roles",
    "sql","nosql","orm","migrations","queries","indexing","transactions","connections",
    "joins","aggregations","schemas","models","relations","crud","backup","replication",
    "docker","kubernetes","ci-cd","git","linux","aws","gcp","azure","terraform","ansible",
    "nginx","redis","rabbitmq","kafka","monitoring","alerts","logs","metrics","deployment",
    "llm","embeddings","vectors","training","inference","prompts","tokens","models","fine-tuning",
    "rag","agents","chains","transformers","neural-networks","classification","clustering",
    "memory-leak","deadlock","race-condition","infinite-loop","stack-overflow","segfault",
    "timeout-error","connection-refused","permission-denied","not-found","null-pointer",
    "clean-code","refactoring","documentation","comments","naming","structure","modularity",
    "dry","solid","kiss","yagni","code-review","versioning","dependency-management"
}

TYPES = {"lesson","warning","tip","solution"}

# === INDEX ===
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
        if category and not tags and not type and not q:
            results=self.by_category.get(category,[])
        elif tags and len(tags)==1 and not category and not type and not q:
            results=self.by_tag.get(tags[0],[])
        elif type and not category and not tags and not q:
            results=self.by_type.get(type,[])
        else:
            if tags and len(tags)>=1:
                tag_sets=[set(e["id"] for e in self.by_tag.get(t,[])) for t in tags]
                if tag_sets:
                    common_ids=set.intersection(*tag_sets) if len(tag_sets)>1 else tag_sets[0]
                    results=[self.by_id[id] for id in common_ids if id in self.by_id]
                else:
                    results=[]
            else:
                results=self.entries
            if category:
                results=[e for e in results if e["category"]==category]
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

async def save_index():
    async with aiofiles.open(INDEX_FILE,"w") as f:
        await f.write(json.dumps({"entries":index.entries}))

async def save_agents():
    async with aiofiles.open(AGENTS_FILE,"w") as f:
        await f.write(json.dumps(agents))

def get_agent_num(agent_id):
    h=hashlib.sha256(agent_id.encode()).hexdigest()
    if h not in agents:
        agents[h]=len(agents)+1
    return agents[h]

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
    yield
    await save_index()
    await save_agents()

app=FastAPI(lifespan=lifespan,default_response_class=ORJSONResponse)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

# === SIZE LIMIT MIDDLEWARE ===
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            return ORJSONResponse({"error": "Request too large. Max 10KB."}, status_code=413)
    return await call_next(request)

class ExpIn(BaseModel):
    agent_id:str=Field(...,min_length=3,max_length=100)
    category:str
    title:str=Field(...,min_length=10,max_length=200)
    content:str=Field(...,min_length=50,max_length=5000)
    tags:list[str]=Field(...,min_length=1,max_length=5)
    type:str=Field(default="lesson")
    
    @field_validator('category')
    @classmethod
    def check_category(cls,v):
        v=v.lower().strip()
        if v not in CATEGORIES:
            raise ValueError(f'Invalid category. Use /schema for valid list.')
        return v
    
    @field_validator('tags')
    @classmethod
    def check_tags(cls,v):
        v=[t.lower().strip() for t in v]
        invalid=[t for t in v if t not in TAGS]
        if invalid:
            raise ValueError(f'Invalid tags: {invalid}. Use /schema for valid list.')
        return list(set(v))
    
    @field_validator('type')
    @classmethod
    def check_type(cls,v):
        v=v.lower().strip()
        if v not in TYPES:
            raise ValueError(f'Invalid type. Must be: lesson, warning, tip, solution')
        return v

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/setup")
async def setup():
    return FileResponse("static/setup.html")

@app.get("/archive")
async def archive():
    return FileResponse("static/archive.html")

@app.get("/health")
async def health():
    return{"status":"ok","experiences":len(index.entries),"agents":len(index.agent_ids),"storage_mb":round(index.total_size/1024/1024,2)}

@app.get("/schema")
async def schema():
    return{
        "categories":{"languages":["python","javascript","typescript","rust","go","java","cpp","csharp","ruby","php","swift","kotlin"],"domains":["api","database","devops","security","testing","performance","debugging","ai","web","mobile","cloud","backend","frontend"]},
        "tags":{"code-patterns":["async","sync","loops","recursion","functions","classes","decorators","generators","context-managers","callbacks","promises","design-patterns"],"data":["files","json","csv","xml","yaml","parsing","validation","strings","arrays","dicts","regex","encoding"],"errors":["errors","exceptions","try-catch","debugging","logging","error-handling","stack-trace","null-checks"],"performance":["memory","cpu","cache","optimization","profiling","threading","concurrency","pooling","batching"],"network":["http","websocket","rest","graphql","timeout","retry","rate-limit","headers","cookies","requests"],"security":["auth","oauth","jwt","api-keys","encryption","hashing","tokens","permissions","sanitization"],"database":["sql","nosql","orm","queries","indexing","transactions","connections","migrations","joins"],"devops":["docker","kubernetes","ci-cd","git","linux","aws","nginx","redis","monitoring","deployment"],"ai":["llm","embeddings","vectors","prompts","inference","rag","agents","fine-tuning","transformers"],"problems":["memory-leak","deadlock","race-condition","infinite-loop","timeout-error","connection-refused","null-pointer"]},
        "types":["lesson","warning","tip","solution"],
        "limits":{"uploads_per_hour":3,"title":"10-200 chars","content":"50-5000 chars","tags":"1-5","request_size":"10KB"}
    }

@app.post("/experiences")
async def create(e:ExpIn):
    # Check limits
    if len(index.entries)>=MAX_EXPERIENCES:
        raise HTTPException(503,"Storage full. No new uploads accepted.")
    if index.total_size>=MAX_STORAGE_MB*1024*1024:
        raise HTTPException(503,"Storage full. No new uploads accepted.")
    if not check_rate_limit(e.agent_id):
        raise HTTPException(429,"Rate limit: max 3 uploads per hour")
    
    content_hash=hashlib.sha256(e.content.encode()).hexdigest()[:16]
    if content_hash in index.content_hashes:
        raise HTTPException(400,"Duplicate content already exists")
    
    ts=datetime.now(timezone.utc)
    agent_num=get_agent_num(e.agent_id)
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
    return{"total_experiences":len(index.entries),"total_agents":len(index.agent_ids),"storage_mb":round(index.total_size/1024/1024,2)}

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
