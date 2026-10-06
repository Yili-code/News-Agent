import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker,{formatCandidateQuestion,validCandidate} from '../worker.mjs';

const ID='0123456789abcdef01234567';
const candidate=()=>({
  id:ID,
  source_name:'Example',
  category:'AI',
  title:'A grounded source title',
  url:'https://example.com/story',
  source_summary:'The source describes a specific product change.',
  fact_summary:'來源描述了一項具體的產品改變。',
  question_one:'哪個地方讓你停下來？',
  question_two:'它改變了你對什麼產品判斷？',
});

function setup(){
  const db=new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../migrations/0001.sql',import.meta.url),'utf8'));
  const prepare=sql=>({
    bind(...args){return {
      async first(){return db.prepare(sql).get(...args)||null;},
      async all(){return {results:db.prepare(sql).all(...args)};},
      async run(){return db.prepare(sql).run(...args);},
    };},
    async first(){return db.prepare(sql).get()||null;},
    async all(){return {results:db.prepare(sql).all()};},
    async run(){return db.prepare(sql).run();},
  });
  const env={
    JOB_TOKEN:'job-secret',
    TELEGRAM_BOT_TOKEN:'telegram-token',
    TELEGRAM_OWNER_CHAT_ID:'123',
    TELEGRAM_WEBHOOK_SECRET:'webhook-secret',
    THREADS_ACCESS_TOKEN:'threads-token',
    LINKEDIN_ACCESS_TOKEN:'linkedin-token',
    LINKEDIN_PERSON_URN:'urn:li:person:test',
    LINKEDIN_VERSION:'202603',
    DB:{prepare},
  };
  const call=(path,{data,job=false,webhook=false}={})=>worker.fetch(new Request('https://social.example'+path,{
    method:data?'POST':'GET',
    headers:{
      ...(data?{'content-type':'application/json'}:{}),
      ...(job?{authorization:'Bearer job-secret'}:{}),
      ...(webhook?{'x-telegram-bot-api-secret-token':'webhook-secret'}:{}),
    },
    body:data?JSON.stringify(data):undefined,
  }),env);
  return {db,env,call};
}

function telegramFetch(log){
  return async(url,options={})=>{
    log.push({url:String(url),options});
    if(String(url).includes('sendMessage')||String(url).includes('answerCallbackQuery'))return Response.json({ok:true,result:{message_id:1}});
    throw new Error('Unexpected URL '+url);
  };
}

async function addCandidate(call){
  const response=await call('/internal/candidates',{job:true,data:candidate()});
  assert.equal(response.status,201);
}

test('candidate validation requires a safe source URL',()=>{
  assert.equal(validCandidate(candidate()),true);
  const invalid=candidate();invalid.url='javascript:alert(1)';
  assert.equal(validCandidate(invalid),false);
  assert.match(formatCandidateQuestion(candidate()),/無感也可以，我就不發/);
});

test('candidate ingestion is authorized, delivered once, and deduplicated',async()=>{
  const {db,call}=setup();const log=[];const original=globalThis.fetch;globalThis.fetch=telegramFetch(log);
  try{
    assert.equal((await call('/internal/candidates',{data:candidate()})).status,401);
    await addCandidate(call);
    const duplicate=await call('/internal/candidates',{job:true,data:candidate()});
    assert.equal(duplicate.status,200);
    assert.equal((await duplicate.json()).status,'duplicate');
    assert.equal(log.filter(item=>item.url.includes('sendMessage')).length,1);
    assert.equal(db.prepare('SELECT state FROM editorial_candidates WHERE id=?').get(ID).state,'awaiting_response');
  }finally{globalThis.fetch=original;}
});

test('a new candidate does not replace an active conversation',async()=>{
  const {db,call}=setup();const log=[];const original=globalThis.fetch;globalThis.fetch=telegramFetch(log);
  try{
    await addCandidate(call);
    const second=candidate();second.id='abcdef0123456789abcdef01';second.url='https://example.com/second';
    const response=await call('/internal/candidates',{job:true,data:second});
    assert.equal((await response.json()).status,'busy');
    assert.equal(db.prepare('SELECT COUNT(*) AS n FROM editorial_candidates').get().n,1);
    assert.equal(log.filter(item=>item.url.includes('sendMessage')).length,1);
  }finally{globalThis.fetch=original;}
});

test('webhook requires Telegram secret and ignores non-owner messages',async()=>{
  const {db,call}=setup();
  assert.equal((await call('/telegram/webhook',{data:{update_id:1}})).status,401);
  const result=await call('/telegram/webhook',{webhook:true,data:{update_id:2,message:{chat:{id:999},text:'hello'}}});
  assert.equal(result.status,200);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM processed_updates').get().n,1);
});

test('owner can explicitly skip before any AI call or draft',async()=>{
  const {db,env,call}=setup();const log=[];const original=globalThis.fetch;globalThis.fetch=telegramFetch(log);
  let aiCalls=0;env.AI={async run(){aiCalls++;throw new Error('should not run');}};
  try{
    await addCandidate(call);
    await call('/telegram/webhook',{webhook:true,data:{update_id:20,message:{chat:{id:123},text:'無感'}}});
    assert.equal(db.prepare('SELECT state FROM editorial_candidates WHERE id=?').get(ID).state,'skipped');
    assert.equal(aiCalls,0);
    assert.equal(db.prepare('SELECT COUNT(*) AS n FROM publications').get().n,0);
  }finally{globalThis.fetch=original;}
});

test('a meaningful reaction creates drafts but never publishes without approval',async()=>{
  const {db,env,call}=setup();const log=[];const original=globalThis.fetch;globalThis.fetch=telegramFetch(log);
  env.AI={async run(){return {response:JSON.stringify({action:'draft',reason:'有一個具體產品判斷',threads:'我注意到的不是功能本身，而是它改變了小團隊的成本。',linkedin:'我注意到的不是這項功能本身。比較值得看的，是它如何改變小團隊原本負擔不起的工作流程。這還不是需求證據，但會改變我下一步要問的問題。'})};}};
  try{
    await addCandidate(call);
    await call('/telegram/webhook',{webhook:true,data:{update_id:3,message:{chat:{id:123},text:'我在意的是小團隊現在也能負擔這個流程。'}}});
    const row=db.prepare('SELECT state,threads_draft FROM editorial_candidates WHERE id=?').get(ID);
    assert.equal(row.state,'draft_ready');
    assert.match(row.threads_draft,/小團隊/);
    assert.equal(db.prepare('SELECT COUNT(*) AS n FROM publications').get().n,0);
    assert.equal(log.some(item=>item.url.includes('threads.net')),false);
    assert.equal(log.some(item=>item.url.includes('linkedin.com')),false);
  }finally{globalThis.fetch=original;}
});

test('one follow-up is allowed and a model cannot force a second follow-up',async()=>{
  const {db,env,call}=setup();const log=[];const original=globalThis.fetch;globalThis.fetch=telegramFetch(log);
  let calls=0;
  env.AI={async run(){calls++;return {response:JSON.stringify({action:'follow_up',reason:'需要更具體',follow_up:'你說的成本，具體是哪一種成本？'})};}};
  try{
    await addCandidate(call);
    await call('/telegram/webhook',{webhook:true,data:{update_id:4,message:{chat:{id:123},text:'我覺得和成本有關。'}}});
    assert.equal(db.prepare('SELECT state,followup_count FROM editorial_candidates WHERE id=?').get(ID).state,'awaiting_followup');
    await call('/telegram/webhook',{webhook:true,data:{update_id:5,message:{chat:{id:123},text:'主要是維運成本。'}}});
    assert.equal(calls,2);
    assert.equal(db.prepare('SELECT state FROM editorial_candidates WHERE id=?').get(ID).state,'awaiting_followup');
    assert.equal(log.at(-1).url.includes('sendMessage'),true);
  }finally{globalThis.fetch=original;}
});

test('explicit approval publishes both platforms once',async()=>{
  const {db,env,call}=setup();const log=[];const original=globalThis.fetch;
  globalThis.fetch=async(url,options={})=>{
    log.push({url:String(url),options});
    if(String(url).includes('sendMessage')||String(url).includes('answerCallbackQuery'))return Response.json({ok:true,result:{message_id:1}});
    if(String(url).endsWith('/me/threads'))return Response.json({id:'container-1'});
    if(String(url).endsWith('/me/threads_publish'))return Response.json({id:'thread-1'});
    if(String(url).includes('api.linkedin.com/rest/posts'))return new Response('',{status:201,headers:{'x-restli-id':'linkedin-1'}});
    throw new Error('Unexpected URL '+url);
  };
  env.AI={async run(){return {response:JSON.stringify({action:'draft',reason:'具體',threads:'一個具體觀察。',linkedin:'這是一個較完整、但仍克制而具體的觀察。'})};}};
  try{
    await addCandidate(call);
    await call('/telegram/webhook',{webhook:true,data:{update_id:6,message:{chat:{id:123},text:'這讓我想到小團隊的選擇。'}}});
    const callback={update_id:7,callback_query:{id:'callback-1',data:`social:${ID}:both`,message:{chat:{id:123}}}};
    await call('/telegram/webhook',{webhook:true,data:callback});
    assert.equal(db.prepare("SELECT COUNT(*) AS n FROM publications WHERE status='published'").get().n,2);
    assert.equal(db.prepare('SELECT state FROM editorial_candidates WHERE id=?').get(ID).state,'published');
    await call('/telegram/webhook',{webhook:true,data:{...callback,update_id:8}});
    assert.equal(log.filter(item=>item.url.endsWith('/me/threads_publish')).length,1);
    assert.equal(log.filter(item=>item.url.includes('api.linkedin.com/rest/posts')).length,1);
  }finally{globalThis.fetch=original;}
});

test('ambiguous publishing failure is not retried',async()=>{
  const {db,env,call}=setup();const original=globalThis.fetch;let threadAttempts=0;
  globalThis.fetch=async(url)=>{
    if(String(url).includes('sendMessage')||String(url).includes('answerCallbackQuery'))return Response.json({ok:true});
    if(String(url).endsWith('/me/threads')){threadAttempts++;throw new Error('timeout');}
    throw new Error('Unexpected URL');
  };
  env.AI={async run(){return {response:JSON.stringify({action:'draft',reason:'具體',threads:'具體觀察。',linkedin:'較完整的具體觀察。'})};}};
  try{
    await addCandidate(call);
    await call('/telegram/webhook',{webhook:true,data:{update_id:9,message:{chat:{id:123},text:'這值得談。'}}});
    const callback=data=>({update_id:data,callback_query:{id:'cb'+data,data:`social:${ID}:threads`,message:{chat:{id:123}}}});
    await call('/telegram/webhook',{webhook:true,data:callback(10)});
    assert.equal(db.prepare('SELECT status FROM publications WHERE candidate_id=? AND platform=?').get(ID,'threads').status,'unknown');
    await call('/telegram/webhook',{webhook:true,data:callback(11)});
    assert.equal(threadAttempts,1);
  }finally{globalThis.fetch=original;}
});
