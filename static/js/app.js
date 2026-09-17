const state = {
  url: '', platform: 'auto', kind: 'video', quality: 'best', analysis: null,
  taskId: null, lastFile: null, lastHistoryId: null, pollTimer: null, paused: false
};

const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];

function toast(msg, type='info') {
  const t = $('#toast'); if (!t) return;
  t.textContent = msg;
  t.dataset.type = type;
  t.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
}

function escapeHtml(s='') { return String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function fmtDur(sec) {
  if (sec === null || sec === undefined || sec === '' || Number.isNaN(Number(sec))) return '—';
  sec = Math.max(0, Math.round(Number(sec)));
  return `${String(Math.floor(sec/3600)).padStart(2,'0')}:${String(Math.floor(sec%3600/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`;
}
function fmtBytes(n) {
  n = Number(n || 0); if (!n) return '—';
  const u=['B','KB','MB','GB','TB']; let i=0,x=n;
  while(x>=1024&&i<u.length-1){x/=1024;i++;}
  return `${x.toFixed(i?1:0)} ${u[i]}`;
}
function detectPlatform(url) {
  try {
    const h = new URL(url).hostname.toLowerCase();
    if (h.includes('instagram.')) return 'instagram';
    if (h.includes('youtube.') || h.includes('youtu.be')) return 'youtube';
  } catch (_) {}
  return 'auto';
}

function showSection(id) {
  $$('.section, .page-section').forEach(x => x.classList.remove('active-section'));
  const el = document.getElementById(id); if (el) el.classList.add('active-section');
  $$('.nav-link').forEach(x => x.classList.toggle('active', x.dataset.section === id));
  if (id === 'history' || id === 'downloads') loadHistory();
  window.scrollTo({top:0, behavior:'smooth'});
}
window.showSection = showSection;

function setPlatform(platform) {
  state.platform = platform;
  $$('.platform-option').forEach(x => x.classList.toggle('selected', x.dataset.platform === platform));
}
function setKind(kind) {
  state.kind = kind;
  $$('.type-option').forEach(x => x.classList.toggle('selected', x.dataset.kind === kind));
}
function setQuality(q) {
  state.quality = q;
  $$('.quality').forEach(x => x.classList.toggle('selected', x.dataset.quality === q));
}

$$('.nav-link').forEach(b => b.addEventListener('click', () => showSection(b.dataset.section)));
$$('.platform-option').forEach(b => b.addEventListener('click', () => setPlatform(b.dataset.platform)));
$$('.type-option').forEach(b => b.addEventListener('click', () => setKind(b.dataset.kind)));
$$('.quality').forEach(b => b.addEventListener('click', () => setQuality(b.dataset.quality)));

function resetInfo() {
  ['infoResolution','infoQuality','infoFps','infoVcodec','infoAcodec','infoDuration','infoSize','infoBitrate'].forEach(id => { const e=$('#'+id); if(e)e.textContent='—'; });
}
function fillAnalysis(d) {
  state.analysis = d;
  if (d.platform) setPlatform(String(d.platform).toLowerCase() === 'instagram' ? 'instagram' : 'youtube');
  $('#previewEmpty')?.classList.add('hidden');
  $('#previewData')?.classList.remove('hidden');
  const img = $('#thumb');
  if (img) { img.src = d.thumbnail || ''; img.onerror = () => { img.style.display='none'; }; img.onload = () => img.style.display='block'; }
  $('#mediaTitle').textContent = d.title || 'Untitled';
  $('#platformLabel').textContent = `${d.platform || 'Unknown'} • ${d.uploader || 'Unknown uploader'}`;
  $('#durationChip').textContent = fmtDur(d.duration);
  $('#uploaderChip').textContent = d.webpage_url_domain || '';
  $('#description').textContent = d.description || 'No description available.';
  const best = d.qualities?.[0];
  $('#infoResolution').textContent = best ? `up to ${best}p` : '—';
  $('#infoQuality').textContent = best ? `${best}p available` : '—';
  if (d.qualities?.length) {
    $$('.quality').forEach(b => {
      const q=b.dataset.quality;
      if(q==='best') return;
      const h=parseInt(q,10);
      b.disabled = !d.qualities.some(x => Number(x) >= h);
      b.classList.toggle('unavailable', b.disabled);
    });
  }
  toast(`Analyzed ${d.platform || 'media'} successfully.`, 'success');
}

async function analyzeUrl() {
  const url = $('#urlInput').value.trim();
  if (!url) return toast('Paste a URL first.', 'error');
  state.url = url;
  const detected = detectPlatform(url);
  if (detected !== 'auto') setPlatform(detected);
  const btn=$('#analyzeBtn');
  btn.disabled=true; btn.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> Analyzing';
  try {
    const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const j=await r.json(); if(!j.ok) throw Error(j.error || 'Analysis failed.');
    fillAnalysis(j.data);
  } catch(e) { toast(e.message, 'error'); }
  finally { btn.disabled=false; btn.innerHTML='<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze'; }
}
$('#analyzeBtn')?.addEventListener('click', analyzeUrl);
$('#urlInput')?.addEventListener('keydown', e => { if(e.key==='Enter') analyzeUrl(); });

async function startDownload() {
  const url=state.url || $('#urlInput').value.trim();
  if(!url) return toast('Enter a URL first.', 'error');
  state.url=url;
  const detected=detectPlatform(url); if(detected!=='auto') { state.platform=detected; setPlatform(detected); }
  resetInfo();
  $('#progressStatus').textContent='Starting...'; $('#progressBar').style.width='0%'; $('#progressPct').textContent='0%';
  $('#downloadBtn').disabled=true;
  try {
    const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,platform:state.platform,kind:state.kind,quality:state.quality})});
    const j=await r.json(); if(!j.ok) throw Error(j.error || 'Could not start download.');
    state.taskId=j.task_id; state.paused=false; updateControlButtons(); toast('Download started.', 'success'); pollProgress();
  } catch(e) { toast(e.message,'error'); $('#downloadBtn').disabled=false; }
}
$('#downloadBtn')?.addEventListener('click', startDownload);

async function postTaskAction(action) {
  if(!state.taskId) return toast('No active download.', 'error');
  try {
    const r=await fetch(`/api/progress/${state.taskId}/${action}`,{method:'POST'});
    const j=await r.json(); if(!j.ok) throw Error(j.data?.error || `Unable to ${action}.`);
    if(action==='pause') state.paused=true;
    if(action==='resume') state.paused=false;
    if(action==='cancel') { state.taskId=null; $('#progressStatus').textContent='Cancelled'; }
    updateControlButtons();
  } catch(e){toast(e.message,'error');}
}
function updateControlButtons() {
  const p=$('#pauseBtn'), c=$('#cancelBtn');
  if(!p||!c) return;
  const active=!!state.taskId;
  p.disabled=!active; c.disabled=!active;
  p.innerHTML=state.paused?'<i class="fa-solid fa-play"></i> Resume':'<i class="fa-solid fa-pause"></i> Pause';
}
$('#pauseBtn')?.addEventListener('click',()=>postTaskAction(state.paused?'resume':'pause'));
$('#cancelBtn')?.addEventListener('click',()=>postTaskAction('cancel'));

async function pollProgress(){
  if(!state.taskId) return;
  try {
    const r=await fetch('/api/progress/'+state.taskId,{cache:'no-store'}); const j=await r.json(); if(!j.ok) throw Error(j.error);
    const d=j.data, pct=Number(d.progress||0);
    $('#progressPct').textContent=Math.round(pct)+'%'; $('#progressBar').style.width=pct+'%';
    const ring=$('.ring'); if(ring) ring.style.setProperty('--progress', `${pct*3.6}deg`);
    $('#progressStatus').textContent={completed:'Download completed!',error:'Download failed',cancelled:'Download cancelled',paused:'Paused',merging:'Merging media...',analyzing:'Analyzing...',cancelling:'Cancelling...'}[d.status] || 'Downloading...';
    $('#fileName').textContent=d.filename||d.title||'—'; $('#progressSpeed').textContent=d.speed||'—'; $('#progressEta').textContent=d.eta||'—'; $('#eta').textContent='ETA: '+(d.eta||'--');
    $('#progressSize').textContent=d.filesize?fmtBytes(d.filesize):'—';
    if(d.status==='completed'){
      state.lastFile=d.filename; state.lastHistoryId=d.history_id||null; state.taskId=null;
      const i=d.info||{}; $('#infoResolution').textContent=i.resolution||'—'; $('#infoQuality').textContent=i.quality||'—'; $('#infoFps').textContent=i.fps||'—'; $('#infoVcodec').textContent=i.video_codec||'—'; $('#infoAcodec').textContent=i.audio_codec||'—'; $('#infoDuration').textContent=fmtDur(i.duration); $('#infoSize').textContent=fmtBytes(i.filesize); $('#infoBitrate').textContent=i.bitrate?`${(i.bitrate/1e6).toFixed(2)} Mbps`:'—';
      showReadyActions(); $('#downloadBtn').disabled=false; updateControlButtons(); loadHistory(); toast('Download completed successfully!','success'); return;
    }
    if(d.status==='error'||d.status==='cancelled'){state.taskId=null; $('#downloadBtn').disabled=false; updateControlButtons(); toast(d.error||'Download did not complete.','error'); return;}
    updateControlButtons(); state.pollTimer=setTimeout(pollProgress,650);
  } catch(e){ toast(e.message,'error'); $('#downloadBtn').disabled=false; }
}

function showReadyActions(){
  const a=$('#readyActions'); if(!a) return;
  a.classList.remove('hidden');
  if(state.taskId) return;
  const href=state.lastHistoryId?`/api/file/${state.lastHistoryId}`:'';
  const view=state.lastHistoryId?`/api/file/${state.lastHistoryId}/view`:'';
  $('#saveFileBtn').href=href; $('#playMediaBtn').href=view;
}

async function loadHistory(){
  try{
    const r=await fetch('/api/history',{cache:'no-store'}); const j=await r.json(); if(!j.ok)throw Error(j.error);
    const data=j.data||[];
    const row=x=>`<div class="table-row"><div class="history-title"><b>${escapeHtml(x.title||'Untitled')}</b><div class="muted">${escapeHtml(x.platform||'')} • ${escapeHtml(x.quality||'—')}</div></div><div>${fmtBytes(x.filesize)}</div><div class="hide-mobile">${escapeHtml(x.resolution||'—')}</div><div class="history-actions"><span class="badge">${escapeHtml(x.status||'Completed')}</span><a class="small-action" href="/api/file/${x.id}"><i class="fa-solid fa-download"></i></a><a class="small-action" href="/api/file/${x.id}/view" target="_blank"><i class="fa-solid fa-play"></i></a><button class="small-action delete-history" data-id="${x.id}"><i class="fa-solid fa-trash"></i></button></div></div>`;
    const html=data.map(row).join('')||'<p class="muted empty-state">No downloads yet.</p>';
    if($('#historyList')) $('#historyList').innerHTML=html; if($('#downloadsList')) $('#downloadsList').innerHTML=html;
    $('#recentList').innerHTML=data.slice(0,4).map(x=>`<div class="recent-item"><div class="brand-mark mini"><i class="fa-solid fa-play"></i></div><div><b>${escapeHtml(x.title||'Untitled')}</b><small>${escapeHtml(x.platform||'')} • ${escapeHtml(x.quality||'—')} • ${fmtBytes(x.filesize)}</small></div><span class="badge">Completed</span></div>`).join('')||'<p class="muted">No recent downloads.</p>';
  }catch(e){toast('Could not load history: '+e.message,'error');}
}

$('#historyList')?.addEventListener('click', handleHistoryAction);
$('#downloadsList')?.addEventListener('click', handleHistoryAction);
async function handleHistoryAction(e){
  const b=e.target.closest('.delete-history'); if(!b)return;
  const id=b.dataset.id; if(!confirm('Delete this download and its history entry?'))return;
  try{const r=await fetch('/api/history/'+id,{method:'DELETE'});const j=await r.json();if(!j.ok)throw Error(j.error);loadHistory();toast('Deleted.','success');}catch(err){toast(err.message,'error');}
}

$('#copyBtn')?.addEventListener('click',async()=>{if(!state.url)return toast('No URL to copy.','error');try{await navigator.clipboard.writeText(state.url);toast('Link copied.','success')}catch(e){toast('Clipboard permission unavailable.','error')}});
$('#shareBtn')?.addEventListener('click',async()=>{if(!state.url)return toast('Analyze a URL first.','error');if(navigator.share){try{await navigator.share({title:'MediaFlow',url:state.url});}catch(_){}}else toast('Sharing is not available in this browser.','error')});
$('#mp3Btn')?.addEventListener('click',async()=>{if(!state.lastFile)return toast('Download a media file first.','error');try{const r=await fetch('/api/convert-mp3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:state.lastFile})});const j=await r.json();if(!j.ok)throw Error(j.error);toast('MP3 created: '+j.data.output,'success')}catch(e){toast(e.message,'error')}});
$('#openBtn')?.addEventListener('click',()=>{if(state.lastFile)toast('Saved at: '+state.lastFile,'success');else toast('Download a file first.','error')});
$('#playBtn')?.addEventListener('click',()=>{if(state.lastHistoryId)window.open(`/api/file/${state.lastHistoryId}/view`,'_blank');else toast('Download a file first.','error')});
$('#favoriteBtn')?.addEventListener('click',()=>{if(!state.url)return toast('Analyze a URL first.','error');localStorage.setItem('mediaflow.favorite',state.url);toast('Added to favorites.','success')});
$('#deleteCurrentBtn')?.addEventListener('click',async()=>{if(!state.lastHistoryId)return toast('Nothing to delete.','error');if(!confirm('Delete the current downloaded file?'))return;try{const r=await fetch('/api/history/'+state.lastHistoryId,{method:'DELETE'});const j=await r.json();if(!j.ok)throw Error(j.error);state.lastHistoryId=null;state.lastFile=null;loadHistory();toast('File deleted.','success')}catch(e){toast(e.message,'error')}});
$('#saveFileBtn')?.addEventListener('click',()=>{if(!state.lastHistoryId)toast('No completed file yet.','error')});

$('#queueBtn')?.addEventListener('click',()=>{const u=$('#urlInput').value.trim();if(!u)return toast('Enter a URL first.','error');const list=JSON.parse(localStorage.getItem('mediaflow.queue')||'[]');list.push({url:u,platform:state.platform,kind:state.kind,quality:state.quality,added:new Date().toISOString()});localStorage.setItem('mediaflow.queue',JSON.stringify(list));toast('Added to local queue.','success');renderQueue();});
$('#refreshBtn')?.addEventListener('click',()=>{ $('#urlInput').value=''; state.url=''; state.analysis=null; $('#previewEmpty')?.classList.remove('hidden'); $('#previewData')?.classList.add('hidden'); resetInfo(); toast('Dashboard reset.','success'); });

async function runBatch(){const urls=$('#batchUrls').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);if(!urls.length)return toast('Enter at least one URL.','error');let done=0;$('#batchResult').textContent='Starting downloads...';for(const url of urls){try{const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,platform:'auto',kind:'video',quality:'best'})});const j=await r.json();if(j.ok)done++;}catch(_){} }$('#batchResult').textContent=`Started ${done} of ${urls.length} downloads. Check Downloads/History.`;toast(`Started ${done} downloads.`,'success');}
$('#batchBtn')?.addEventListener('click',runBatch);

function renderQueue(){const el=$('#queueList');if(!el)return;const list=JSON.parse(localStorage.getItem('mediaflow.queue')||'[]');el.innerHTML=list.length?list.map((x,i)=>`<div class="queue-item"><span>${i+1}. ${escapeHtml(x.url)}</span><button data-q="${i}" class="small-action remove-queue"><i class="fa-solid fa-xmark"></i></button></div>`).join(''):'<p class="muted">Queue is empty.</p>';}
$('#queueList')?.addEventListener('click',e=>{const b=e.target.closest('.remove-queue');if(!b)return;const list=JSON.parse(localStorage.getItem('mediaflow.queue')||'[]');list.splice(Number(b.dataset.q),1);localStorage.setItem('mediaflow.queue',JSON.stringify(list));renderQueue();});

async function loadSettings(){try{const r=await fetch('/api/settings');const j=await r.json();const s=j.data;$('#settingQuality').value=s.default_quality;$('#settingTheme').value=s.theme;$('#skipDuplicates').checked=!!s.skip_duplicates;$('#animations').checked=!!s.animations;$('#notifications').checked=!!s.notifications;applyTheme(s.theme);}catch(e){}}
async function saveSettings(){const body={default_quality:$('#settingQuality').value,theme:$('#settingTheme').value,skip_duplicates:$('#skipDuplicates').checked,animations:$('#animations').checked,notifications:$('#notifications').checked};try{const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!j.ok)throw Error(j.error);applyTheme(body.theme);toast('Settings saved.','success')}catch(e){toast(e.message,'error')}}
function applyTheme(theme){document.body.classList.toggle('light',theme==='light');}
$('#saveSettings')?.addEventListener('click',saveSettings);
$('#themeBtn')?.addEventListener('click',()=>{const light=!document.body.classList.contains('light');applyTheme(light?'light':'dark');toast(light?'Light theme enabled.':'Dark theme enabled.','success')});
$('#settingTheme')?.addEventListener('change',e=>applyTheme(e.target.value));

async function checkStatus(){try{const r=await fetch('/api/status');const j=await r.json();const d=j.data;const map=[['yt-dlp',d.yt_dlp],['FFmpeg',d.ffmpeg],['FFprobe',d.ffprobe],['Internet',d.internet],['Storage',d.storage]];const box=$('#statusList');if(box)box.innerHTML=map.map(([n,v])=>`<div><i class="fa-solid fa-circle ${v?'ok':'bad'}"></i><span>${n}</span><small>${v?'Available':'Not detected'}</small></div>`).join('');toast('System status refreshed.','success')}catch(e){toast('Status check failed.','error')}}
$('#checkStatus')?.addEventListener('click',checkStatus);
$('#moreInfo')?.addEventListener('click',()=>{if(state.lastFile)toast(JSON.stringify(state.analysis||{}).slice(0,180)+'…');else toast('Download a file to view complete media information.','error')});

function init(){loadSettings();loadHistory();renderQueue();checkStatus();updateControlButtons();}
init();

$('#locationBtn')?.addEventListener('click',()=>toast('Downloads are saved to the MediaFlow download folder. On Termux: Internal Storage/Movies/MediaFlow.','success'));
